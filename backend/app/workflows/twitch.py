"""Twitch account workflow — 8-step pipeline for real account creation.

Steps:
1. Configure proxy for browser session
2. Launch browser via Playwright
3. Navigate to Twitch signup page
4. Fill registration form (username, password, DOB)
5. Solve CAPTCHA via CapSolver
6. Submit registration and inspect result
7. Store credentials back to the account record
8. Update account status and record in dashboard
"""
from __future__ import annotations

import asyncio
import logging
import random
import re
import secrets
import string
from typing import Any

from backend.app.workflows.engine import (
    StepResult,
    StepStatus,
    WorkflowDefinition,
    WorkflowStep,
)

logger = logging.getLogger(__name__)

TWITCH_SIGNUP_URL = "https://www.twitch.tv/signup"


def _generate_username(email: str) -> str:
    prefix = email.split("@")[0][:8]
    prefix = re.sub(r"[^a-zA-Z0-9]", "", prefix)
    suffix = "".join(random.choices(string.digits, k=4))
    return f"{prefix}{suffix}"


def _generate_password() -> str:
    chars = string.ascii_letters + string.digits + "!@#$%"
    while True:
        pw = "".join(secrets.choice(chars) for _ in range(16))
        if (any(c.isupper() for c in pw) and any(c.islower() for c in pw)
                and any(c.isdigit() for c in pw) and any(c in "!@#$%" for c in pw)):
            return pw


def _random_dob() -> tuple[int, int, int]:
    from datetime import date
    today = date.today()
    min_year = today.year - 30
    max_year = today.year - 18
    year = random.randint(min_year, max_year)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return year, month, day


class ProxyConfigStep(WorkflowStep):
    """Step 1: Configure proxy for the browser session."""

    name = "proxy_config"
    description = "Configure proxy for browser session"

    async def execute(self, context: dict[str, Any]) -> StepResult:
        if context.get("mock_mode"):
            context["_proxy_config"] = None
            return StepResult(
                StepStatus.COMPLETED,
                "[mock] Proxy config skipped — direct connection.",
                {"proxy_configured": False, "mock": True},
            )

        db_session = context.get("_db_session")
        if not db_session:
            return StepResult(
                StepStatus.COMPLETED,
                "No database session — skipping proxy lookup, direct connection will be used.",
                {"proxy_configured": False},
            )

        from sqlalchemy import select
        from backend.app.models.proxy import Proxy
        from backend.app.models.enums import ProxyTestStatus
        from backend.app.core.security import decrypt_value

        result = await db_session.execute(
            select(Proxy)
            .where(Proxy.test_status == ProxyTestStatus.PASSED)
            .order_by(Proxy.last_latency_ms.asc())
            .limit(1)
        )
        proxy = result.scalar_one_or_none()

        if not proxy:
            context["_proxy_config"] = None
            return StepResult(
                StepStatus.COMPLETED,
                "No tested proxies available — using direct connection.",
                {"proxy_configured": False},
            )

        proxy_url = f"{proxy.protocol.value}://"
        if proxy.username:
            password = ""
            if proxy.encrypted_password:
                try:
                    password = decrypt_value(proxy.encrypted_password)
                except Exception:
                    pass
            proxy_url += f"{proxy.username}:{password}@"
        proxy_url += f"{proxy.host}:{proxy.port}"

        context["_proxy_config"] = {"server": proxy_url}
        return StepResult(
            StepStatus.COMPLETED,
            f"Proxy configured: {proxy.host}:{proxy.port} ({proxy.protocol.value})",
            {"proxy_configured": True, "proxy_host": proxy.host, "proxy_port": proxy.port},
        )


class BrowserLaunchStep(WorkflowStep):
    """Step 2: Launch browser via Playwright."""

    name = "browser_launch"
    description = "Launch browser via Playwright"

    async def execute(self, context: dict[str, Any]) -> StepResult:
        if context.get("mock_mode"):
            return StepResult(
                StepStatus.COMPLETED,
                "[mock] Browser launch simulated.",
                {"headless": True, "has_proxy": False, "mock": True},
            )

        browser_svc = context.get("_browser_service")
        if browser_svc and browser_svc.is_running:
            return StepResult(
                StepStatus.COMPLETED,
                "Browser already running (injected by worker).",
                {"headless": True, "has_proxy": context.get("_proxy_config") is not None},
            )

        from backend.app.services.browser_service import BrowserConfig, BrowserService
        from backend.app.core.config import settings

        proxy_config = context.get("_proxy_config")
        config = BrowserConfig(
            headless=settings.BROWSER_HEADLESS,
            timeout_ms=settings.BROWSER_TIMEOUT_MS,
            proxy=proxy_config,
            locale=settings.BROWSER_LOCALE,
            timezone_id=settings.BROWSER_TIMEZONE,
        )

        browser_svc = BrowserService(config)
        try:
            await browser_svc.start()
        except Exception as e:
            return StepResult(
                StepStatus.FAILED,
                f"Failed to launch browser: {e}",
                {"error": str(e)},
            )

        context["_browser_service"] = browser_svc
        return StepResult(
            StepStatus.COMPLETED,
            f"Browser launched (headless={settings.BROWSER_HEADLESS})",
            {"headless": settings.BROWSER_HEADLESS, "has_proxy": proxy_config is not None},
        )


class NavigateSignupStep(WorkflowStep):
    """Step 3: Navigate to Twitch signup page."""

    name = "navigate_signup"
    description = "Open Twitch registration page"

    async def execute(self, context: dict[str, Any]) -> StepResult:
        if context.get("mock_mode"):
            return StepResult(
                StepStatus.COMPLETED,
                f"[mock] Navigated to {TWITCH_SIGNUP_URL}",
                {"url": TWITCH_SIGNUP_URL, "mock": True},
            )

        browser_svc = context.get("_browser_service")
        if not browser_svc or not browser_svc.is_running:
            return StepResult(StepStatus.FAILED, "Browser not running")

        try:
            page = await browser_svc.new_page()
            context["_page"] = page
            await page.goto(TWITCH_SIGNUP_URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(random.uniform(3.0, 5.0))
        except Exception as e:
            return StepResult(
                StepStatus.FAILED,
                f"Failed to navigate to Twitch signup: {e}",
                {"url": TWITCH_SIGNUP_URL, "error": str(e)},
            )

        try:
            screenshot = await browser_svc.take_screenshot(page, "twitch_signup_loaded")
        except Exception as ss_err:
            logger.warning("Screenshot failed (non-fatal): %s", ss_err)
            screenshot = None
        return StepResult(
            StepStatus.COMPLETED,
            f"Twitch signup page loaded: {TWITCH_SIGNUP_URL}",
            {"url": TWITCH_SIGNUP_URL},
            screenshot,
        )


class FillFormStep(WorkflowStep):
    """Step 4: Fill in username, password, and date of birth."""

    name = "fill_form"
    description = "Fill registration form (username, password, DOB)"

    async def execute(self, context: dict[str, Any]) -> StepResult:
        email = context.get("email")
        if not email:
            return StepResult(StepStatus.FAILED, "No email in workflow context")

        display = context.get("display_name") or ""
        if len(display) >= 4:
            username = display
        else:
            username = _generate_username(email)
        password = _generate_password()
        year, month, day = _random_dob()

        context["generated_username"] = username
        context["generated_password"] = password

        if context.get("mock_mode"):
            return StepResult(
                StepStatus.COMPLETED,
                f"[mock] Form filled — username: {username}, DOB: {year}-{month:02d}-{day:02d}",
                {"username": username, "email": email, "dob": f"{year}-{month:02d}-{day:02d}", "mock": True},
            )

        page = context.get("_page")
        browser_svc = context.get("_browser_service")
        if not page:
            return StepResult(StepStatus.FAILED, "No page available")

        try:
            # --- Page 1: email entry + Continue ---
            email_input = await page.query_selector(
                "#email-input, input[name='email'], input[type='email']"
            )
            if email_input:
                await email_input.fill("")
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await email_input.fill(email)
                await asyncio.sleep(random.uniform(0.5, 1.0))

            continue_btn = await page.query_selector(
                "button[data-a-target='signup-continue-button'], "
                "button:has-text('Continue')"
            )
            if continue_btn:
                await continue_btn.click()
                await asyncio.sleep(random.uniform(2.0, 3.0))

            # --- Page 2: username, password, DOB ---
            username_input = await page.wait_for_selector(
                "input[name='username'], input[autocomplete='username'], #signup-username",
                timeout=10000,
            )
            if username_input:
                await username_input.fill(username)
                await asyncio.sleep(random.uniform(0.3, 0.8))

            password_input = await page.query_selector(
                "#password-input, input[name='password'], input[type='password']"
            )
            if password_input:
                await password_input.fill(password)
                await asyncio.sleep(random.uniform(0.3, 0.8))

            # --- DOB: use JavaScript to find all select elements and identify by option count ---
            dob_result = await page.evaluate("""() => {
                const selects = Array.from(document.querySelectorAll('select'));
                const result = { month: null, day: null, year: null, debug: [] };

                function classifyField(sel) {
                    const target = (sel.getAttribute('data-a-target') || '').toLowerCase();
                    const label = (sel.getAttribute('aria-label') || '').toLowerCase();
                    const id = (sel.id || '').toLowerCase();
                    const name = (sel.name || '').toLowerCase();
                    // Use last word of aria-label to avoid 'birthday' false matches
                    const labelWords = label.split(/\s+/);
                    const lastWord = labelWords[labelWords.length - 1] || '';

                    if (target.includes('month') || lastWord === 'month' || id.includes('month') || name.includes('month')) return 'month';
                    if (lastWord === 'year' || target.includes('year') || id.includes('year') || name.includes('year')) return 'year';
                    if (lastWord === 'day' || target.includes('date') || target.includes('day') || id.includes('day') || name.includes('day')) return 'day';
                    return null;
                }

                for (let i = 0; i < selects.length; i++) {
                    const sel = selects[i];
                    result.debug.push({
                        index: i,
                        ariaLabel: sel.getAttribute('aria-label'),
                        dataTarget: sel.getAttribute('data-a-target'),
                        optionCount: sel.options.length,
                    });
                    const field = classifyField(sel);
                    if (field && result[field] === null) result[field] = i;
                }

                // Fallback: positional after month
                if (result.month !== null && (result.day === null || result.year === null)) {
                    const after = selects.map((s, i) => i).filter(i => i > result.month && i !== result.month && i !== result.day && i !== result.year);
                    if (result.day === null && after.length > 0) result.day = after[0];
                    if (result.year === null && after.length > 1) result.year = after[1];
                }

                // Fallback: option count heuristic
                if (result.month === null || result.day === null || result.year === null) {
                    for (let i = 0; i < selects.length; i++) {
                        if (i === result.month || i === result.day || i === result.year) continue;
                        const n = selects[i].options.length;
                        if (result.month === null && n >= 12 && n <= 14) result.month = i;
                        else if (result.day === null && n >= 28 && n <= 33) result.day = i;
                        else if (result.year === null && n > 40) result.year = i;
                    }
                }

                return result;
            }""")

            logger.info("DOB select discovery: month=%s, day=%s, year=%s, debug=%s",
                        dob_result.get("month"), dob_result.get("day"), dob_result.get("year"),
                        dob_result.get("debug"))

            month_idx = dob_result.get("month")
            day_idx = dob_result.get("day")
            year_idx = dob_result.get("year")

            if month_idx is not None:
                await page.evaluate(
                    """(args) => {
                        const selects = document.querySelectorAll('select');
                        const sel = selects[args.idx];
                        if (!sel) return;
                        // Try setting by value first, then by index
                        const val = String(args.value);
                        for (let i = 0; i < sel.options.length; i++) {
                            if (sel.options[i].value === val) {
                                sel.selectedIndex = i;
                                sel.dispatchEvent(new Event('change', {bubbles: true}));
                                sel.dispatchEvent(new Event('input', {bubbles: true}));
                                return;
                            }
                        }
                        // Fallback: match by text content
                        for (let i = 0; i < sel.options.length; i++) {
                            if (sel.options[i].textContent.trim() === val) {
                                sel.selectedIndex = i;
                                sel.dispatchEvent(new Event('change', {bubbles: true}));
                                sel.dispatchEvent(new Event('input', {bubbles: true}));
                                return;
                            }
                        }
                    }""",
                    {"idx": month_idx, "value": month},
                )
                await asyncio.sleep(random.uniform(0.3, 0.6))

            if day_idx is not None:
                await page.evaluate(
                    """(args) => {
                        const selects = document.querySelectorAll('select');
                        const sel = selects[args.idx];
                        if (!sel) return;
                        const val = String(args.value);
                        for (let i = 0; i < sel.options.length; i++) {
                            if (sel.options[i].value === val) {
                                sel.selectedIndex = i;
                                sel.dispatchEvent(new Event('change', {bubbles: true}));
                                sel.dispatchEvent(new Event('input', {bubbles: true}));
                                return;
                            }
                        }
                        for (let i = 0; i < sel.options.length; i++) {
                            if (sel.options[i].textContent.trim() === val) {
                                sel.selectedIndex = i;
                                sel.dispatchEvent(new Event('change', {bubbles: true}));
                                sel.dispatchEvent(new Event('input', {bubbles: true}));
                                return;
                            }
                        }
                    }""",
                    {"idx": day_idx, "value": day},
                )
                await asyncio.sleep(random.uniform(0.3, 0.6))

            if year_idx is not None:
                await page.evaluate(
                    """(args) => {
                        const selects = document.querySelectorAll('select');
                        const sel = selects[args.idx];
                        if (!sel) return;
                        const val = String(args.value);
                        for (let i = 0; i < sel.options.length; i++) {
                            if (sel.options[i].value === val) {
                                sel.selectedIndex = i;
                                sel.dispatchEvent(new Event('change', {bubbles: true}));
                                sel.dispatchEvent(new Event('input', {bubbles: true}));
                                return;
                            }
                        }
                        for (let i = 0; i < sel.options.length; i++) {
                            if (sel.options[i].textContent.trim() === val) {
                                sel.selectedIndex = i;
                                sel.dispatchEvent(new Event('change', {bubbles: true}));
                                sel.dispatchEvent(new Event('input', {bubbles: true}));
                                return;
                            }
                        }
                    }""",
                    {"idx": year_idx, "value": year},
                )
                await asyncio.sleep(random.uniform(0.3, 0.6))

            dob_filled = (month_idx is not None and day_idx is not None and year_idx is not None)
            if not dob_filled:
                missing = []
                if month_idx is None: missing.append("month")
                if day_idx is None: missing.append("day")
                if year_idx is None: missing.append("year")
                logger.warning("DOB fields not found: %s", ", ".join(missing))

        except Exception as e:
            screenshot = None
            if browser_svc:
                try:
                    screenshot = await browser_svc.take_screenshot(page, "twitch_form_error")
                except Exception:
                    pass
            return StepResult(
                StepStatus.FAILED,
                f"Error filling form: {e}",
                {"username": username, "error": str(e)},
                screenshot,
            )

        screenshot = None
        if browser_svc:
            try:
                screenshot = await browser_svc.take_screenshot(page, "twitch_form_filled")
            except Exception as ss_err:
                logger.warning("Screenshot failed (non-fatal): %s", ss_err)
        return StepResult(
            StepStatus.COMPLETED,
            f"Form filled — username: {username}, DOB: {year}-{month:02d}-{day:02d}",
            {"username": username, "email": email, "dob": f"{year}-{month:02d}-{day:02d}",
             "dob_filled": dob_filled},
            screenshot,
        )


class CaptchaSolveStep(WorkflowStep):
    """Step 5: Detect and solve CAPTCHA via CapSolver."""

    name = "captcha_solve"
    description = "Solve CAPTCHA via CapSolver"

    async def execute(self, context: dict[str, Any]) -> StepResult:
        if context.get("mock_mode"):
            return StepResult(
                StepStatus.COMPLETED,
                "[mock] CAPTCHA solve simulated.",
                {"captcha_detected": True, "captcha_solved": True, "provider": "mock", "mock": True},
            )

        page = context.get("_page")
        browser_svc = context.get("_browser_service")
        captcha_adapter = context.get("_captcha_adapter")
        if not page:
            return StepResult(StepStatus.FAILED, "No page available")

        captcha_frame = await page.query_selector(
            "iframe[src*='arkoselabs'], iframe[src*='funcaptcha'], "
            "[class*='arkose'], [id*='arkose']"
        )

        if not captcha_frame:
            return StepResult(
                StepStatus.COMPLETED,
                "No CAPTCHA detected on page — proceeding.",
                {"captcha_detected": False},
            )

        if not captcha_adapter:
            screenshot = None
            if browser_svc:
                screenshot = await browser_svc.take_screenshot(page, "twitch_captcha_no_solver")
            return StepResult(
                StepStatus.MANUAL_REQUIRED,
                "CAPTCHA detected but no solver configured. Configure CapSolver API key.",
                {"captcha_detected": True, "solver_available": False},
                screenshot,
            )

        arkose_key = None
        for frame in page.frames:
            url = frame.url
            if "arkoselabs" in url or "funcaptcha" in url:
                key_match = re.search(r"pk=([A-F0-9-]+)", url, re.IGNORECASE)
                if key_match:
                    arkose_key = key_match.group(1)
                    break

        if not arkose_key:
            return StepResult(
                StepStatus.COMPLETED,
                "CAPTCHA frame found but no Arkose key detected — may not require solving.",
                {"captcha_detected": True, "arkose_key_found": False},
            )

        solve_result = await captcha_adapter.solve(arkose_key, page.url)
        if not solve_result.get("solved"):
            screenshot = None
            if browser_svc:
                screenshot = await browser_svc.take_screenshot(page, "twitch_captcha_failed")
            return StepResult(
                StepStatus.FAILED,
                f"CAPTCHA solve failed: {solve_result.get('error', 'unknown')}",
                {"captcha_detected": True, "solve_error": solve_result.get("error")},
                screenshot,
            )

        token = solve_result["token"]
        await page.evaluate(f"""
            var el = document.querySelector('[name="fc-token"], [id="fc-token"]');
            if (el) el.value = '{token}';
            if (window.ArkoseEnforcement) {{
                window.ArkoseEnforcement.setConfig({{ data: {{ token: '{token}' }} }});
            }}
        """)
        await asyncio.sleep(random.uniform(0.5, 1.0))

        return StepResult(
            StepStatus.COMPLETED,
            "CAPTCHA solved successfully.",
            {"captcha_detected": True, "captcha_solved": True, "provider": "capsolver"},
        )


class SubmitFormStep(WorkflowStep):
    """Step 6: Submit the registration form and inspect the result."""

    name = "submit_form"
    description = "Submit registration and inspect result"

    async def execute(self, context: dict[str, Any]) -> StepResult:
        if context.get("mock_mode"):
            context["registration_submitted"] = True
            context["final_url"] = "https://www.twitch.tv/signup?mock=1"
            return StepResult(
                StepStatus.COMPLETED,
                "[mock] Registration form submitted.",
                {"final_url": context["final_url"], "submitted": True, "mock": True},
            )

        page = context.get("_page")
        browser_svc = context.get("_browser_service")
        if not page:
            return StepResult(StepStatus.FAILED, "No page available")

        try:
            signup_btn = await page.query_selector(
                "button[data-a-target='passport-signup-button'], "
                "button[type='submit']:has-text('Sign Up'), "
                "button:has-text('Sign Up')"
            )
            if signup_btn:
                await asyncio.sleep(random.uniform(0.5, 1.5))
                await signup_btn.click()
            else:
                screenshot = None
                if browser_svc:
                    screenshot = await browser_svc.take_screenshot(page, "twitch_no_submit_btn")
                return StepResult(
                    StepStatus.FAILED,
                    "Could not find signup submit button on page.",
                    {"error": "submit_button_not_found"},
                    screenshot,
                )

            # Wait for navigation or error — Twitch redirects on success
            try:
                await page.wait_for_url(
                    lambda url: not url.startswith("https://www.twitch.tv/signup"),
                    timeout=15000,
                )
                redirected = True
            except Exception:
                redirected = False

            await asyncio.sleep(random.uniform(1.0, 2.0))
            try:
                screenshot = await browser_svc.take_screenshot(page, "twitch_after_submit")
            except Exception as ss_err:
                logger.warning("Post-submit screenshot failed (non-fatal): %s", ss_err)
                screenshot = None

            # Check for visible error messages
            error_els = await page.query_selector_all(
                "[data-a-target*='error'], [role='alert'], "
                "[class*='error-text'], [class*='form-error'], "
                "p[class*='error'], span[class*='error']"
            )
            error_texts = []
            for el in error_els:
                txt = (await el.inner_text()).strip()
                if txt:
                    error_texts.append(txt)

            if error_texts:
                combined = "; ".join(error_texts)
                return StepResult(
                    StepStatus.FAILED,
                    f"Registration error from Twitch: {combined}",
                    {"error": combined, "final_url": page.url, "redirected": False},
                    screenshot,
                )

            validation_text = await page.query_selector("text=Please select a valid")
            if validation_text:
                msg = (await validation_text.inner_text()).strip()
                return StepResult(
                    StepStatus.FAILED,
                    f"Form validation failed: {msg}",
                    {"error": msg, "final_url": page.url, "redirected": False},
                    screenshot,
                )

            # Grab page body text for diagnostics if still on signup
            if not redirected:
                body_text = await page.evaluate(
                    "() => document.body ? document.body.innerText.slice(0, 2000) : ''"
                )
                logger.warning(
                    "Registration did NOT redirect away from /signup. Page text: %s",
                    body_text[:500],
                )
                return StepResult(
                    StepStatus.FAILED,
                    "Registration failed — Twitch did not redirect after submit. "
                    "Likely silent rejection (fingerprint mismatch, missing proxy, or CAPTCHA).",
                    {
                        "final_url": page.url,
                        "submitted": True,
                        "redirected": False,
                        "page_snippet": body_text[:500],
                    },
                    screenshot,
                )

            context["registration_submitted"] = True
            context["final_url"] = page.url
            return StepResult(
                StepStatus.COMPLETED,
                "Registration submitted — Twitch redirected to post-signup page.",
                {"final_url": page.url, "submitted": True, "redirected": True},
                screenshot,
            )

        except Exception as e:
            screenshot = None
            if browser_svc:
                try:
                    screenshot = await browser_svc.take_screenshot(page, "twitch_submit_error")
                except Exception:
                    pass
            return StepResult(
                StepStatus.FAILED,
                f"Error submitting form: {e}",
                {"error": str(e)},
                screenshot,
            )


class StoreCredentialsStep(WorkflowStep):
    """Step 7: Encrypt and store generated credentials on the account record."""

    name = "store_credentials"
    description = "Store credentials to account record"

    async def execute(self, context: dict[str, Any]) -> StepResult:
        db_session = context.get("_db_session")
        account_id = context.get("account_id")
        username = context.get("generated_username")
        password = context.get("generated_password")

        if not db_session or not account_id:
            return StepResult(
                StepStatus.COMPLETED,
                "No DB session or account ID — credentials stored in workflow context only.",
                {"stored_to_db": False, "username": username},
            )

        from sqlalchemy import select
        from backend.app.models.account import Account
        from backend.app.core.security import encrypt_value

        result = await db_session.execute(
            select(Account).where(Account.id == account_id)
        )
        account = result.scalar_one_or_none()
        if not account:
            return StepResult(
                StepStatus.FAILED,
                f"Account #{account_id} not found in database.",
            )

        if username:
            account.display_name = username
        if password:
            account.credentials_enc = encrypt_value(password)
        if context.get("mock_mode"):
            account.is_simulated = True

        await db_session.commit()
        mock = context.get("mock_mode", False)
        return StepResult(
            StepStatus.COMPLETED,
            f"{'[mock] ' if mock else ''}Credentials stored for account #{account_id} (username: {username}).",
            {"stored_to_db": True, "account_id": account_id, "username": username, "mock": mock},
        )


class UpdateStatusStep(WorkflowStep):
    """Step 8: Update account status and record outcome in dashboard."""

    name = "update_status"
    description = "Update account status and record in dashboard"

    async def execute(self, context: dict[str, Any]) -> StepResult:
        db_session = context.get("_db_session")
        account_id = context.get("account_id")
        submitted = context.get("registration_submitted", False)

        if not db_session or not account_id:
            status_label = "submitted" if submitted else "unknown"
            return StepResult(
                StepStatus.COMPLETED,
                f"No DB session — workflow finished with status: {status_label}.",
                {"status_updated": False},
            )

        from sqlalchemy import select
        from backend.app.models.account import Account
        from backend.app.models.enums import AccountStatus

        result = await db_session.execute(
            select(Account).where(Account.id == account_id)
        )
        account = result.scalar_one_or_none()
        if not account:
            return StepResult(StepStatus.FAILED, f"Account #{account_id} not found.")

        final_url = context.get("final_url", "")
        actually_redirected = submitted and not final_url.startswith("https://www.twitch.tv/signup")

        if actually_redirected:
            account.status = AccountStatus.UNVERIFIED
            account.is_simulated = bool(context.get("mock_mode"))
            status_label = "unverified"
        elif submitted:
            account.status = AccountStatus.FAILED
            status_label = "failed"
        else:
            account.status = AccountStatus.FAILED
            status_label = "failed"

        from backend.app.core.security import generate_correlation_id
        from backend.app.models.account import AccountStatusHistory

        old_status = "draft"
        history = AccountStatusHistory(
            account_id=account_id,
            old_status=old_status,
            new_status=status_label,
            reason=f"Twitch workflow completed — registration {'submitted' if submitted else 'failed'}",
            correlation_id=generate_correlation_id(),
        )
        db_session.add(history)
        await db_session.commit()

        # Clean up browser
        browser_svc = context.get("_browser_service")
        page = context.get("_page")
        if page:
            try:
                await page.close()
            except Exception:
                pass
        if browser_svc:
            try:
                await browser_svc.stop()
            except Exception:
                pass

        return StepResult(
            StepStatus.COMPLETED,
            f"Account #{account_id} status updated to '{status_label}'. Workflow complete.",
            {
                "account_id": account_id,
                "new_status": status_label,
                "status_updated": True,
                "no_email_verification": True,
            },
        )


def create_twitch_workflow(
    browser_service: Any = None,
    captcha_adapter: Any = None,
) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="twitch_account_creation",
        platform="twitch",
        steps=[
            ProxyConfigStep(),
            BrowserLaunchStep(),
            NavigateSignupStep(),
            FillFormStep(),
            CaptchaSolveStep(),
            SubmitFormStep(),
            StoreCredentialsStep(),
            UpdateStatusStep(),
        ],
    )
