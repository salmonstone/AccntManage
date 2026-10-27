"""Twitch account workflow — creation only, no email verification per client spec.

Twitch accounts are intentionally left unverified. The UI must clearly
state this is by design, not an error.
"""
from __future__ import annotations

import asyncio
import logging
import random
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
    year = random.randint(1985, 2000)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return year, month, day


class TwitchRegistrationStep(WorkflowStep):
    name = "twitch_registration"
    description = "Navigate to Twitch signup and create account"

    def __init__(self, browser_service: Any = None, captcha_adapter: Any = None) -> None:
        self._browser = browser_service
        self._captcha = captcha_adapter

    async def execute(self, context: dict[str, Any]) -> StepResult:
        if context.get("mock_mode"):
            email = context.get("email")
            if not email:
                return StepResult(StepStatus.FAILED, "No email in workflow context")
            username = _generate_username(email)
            password = _generate_password()
            context["generated_username"] = username
            context["generated_password"] = password
            context["no_email_verification"] = True
            await asyncio.sleep(2)
            return StepResult(
                StepStatus.COMPLETED,
                f"[MOCK] Twitch account signup simulated for {username}. "
                "No real account was created.",
                {
                    "username": username,
                    "email": email,
                    "no_email_verification": True,
                    "is_mock": True,
                    "url": TWITCH_SIGNUP_URL,
                },
            )

        if not self._browser or not self._browser.is_running:
            return StepResult(
                StepStatus.MANUAL_REQUIRED,
                "Browser not available. Create the Twitch account manually at "
                f"{TWITCH_SIGNUP_URL} and update the account record.",
                {"url": TWITCH_SIGNUP_URL},
            )

        email = context.get("email")
        if not email:
            return StepResult(StepStatus.FAILED, "No email in workflow context")

        username = _generate_username(email)
        password = _generate_password()
        year, month, day = _random_dob()

        page = None
        try:
            page = await self._browser.new_page()
            await page.goto(TWITCH_SIGNUP_URL, wait_until="networkidle")
            await asyncio.sleep(random.uniform(1.0, 2.0))

            username_input = await page.query_selector("#signup-username, input[name='username'], input[autocomplete='username']")
            password_input = await page.query_selector("#password-input, input[name='password'], input[type='password']")

            if username_input:
                await username_input.fill(username)
                await asyncio.sleep(random.uniform(0.3, 0.8))

            if password_input:
                await password_input.fill(password)
                await asyncio.sleep(random.uniform(0.3, 0.8))

            password_confirm = await page.query_selector("input[name='passwordConfirm'], input[autocomplete='new-password']:nth-of-type(2)")
            if password_confirm:
                await password_confirm.fill(password)
                await asyncio.sleep(random.uniform(0.3, 0.8))

            month_select = await page.query_selector("select[data-a-target='birthday-month-select'], select[aria-label*='Month']")
            if month_select:
                await month_select.select_option(value=str(month))
                await asyncio.sleep(random.uniform(0.2, 0.5))

            day_input = await page.query_selector("select[data-a-target='birthday-day-select'], select[aria-label*='Day']")
            if day_input:
                await day_input.select_option(value=str(day))
                await asyncio.sleep(random.uniform(0.2, 0.5))

            year_input = await page.query_selector("input[data-a-target='birthday-year-input'], input[aria-label*='Year'], input[placeholder*='Year']")
            if year_input:
                await year_input.fill(str(year))
                await asyncio.sleep(random.uniform(0.2, 0.5))

            email_phase_btn = await page.query_selector("button[data-a-target='signup-with-email-button'], button:has-text('Use email instead')")
            if email_phase_btn:
                await email_phase_btn.click()
                await asyncio.sleep(random.uniform(0.5, 1.0))

            email_input = await page.query_selector("#email-input, input[name='email'], input[type='email']")
            if email_input:
                await email_input.fill(email)
                await asyncio.sleep(random.uniform(0.3, 0.8))

            captcha_frame = await page.query_selector(
                "iframe[src*='arkoselabs'], iframe[src*='funcaptcha'], "
                "[class*='arkose'], [id*='arkose']"
            )
            if captcha_frame and self._captcha:
                arkose_key = None
                frames = page.frames
                for frame in frames:
                    url = frame.url
                    if "arkoselabs" in url or "funcaptcha" in url:
                        import re
                        key_match = re.search(r"pk=([A-F0-9-]+)", url, re.IGNORECASE)
                        if key_match:
                            arkose_key = key_match.group(1)
                            break

                if arkose_key:
                    solve_result = await self._captcha.solve(arkose_key, page.url)
                    if solve_result.get("solved"):
                        token = solve_result["token"]
                        await page.evaluate(f"""
                            var el = document.querySelector('[name="fc-token"], [id="fc-token"]');
                            if (el) el.value = '{token}';
                            if (window.ArkoseEnforcement) {{
                                window.ArkoseEnforcement.setConfig({{ data: {{ token: '{token}' }} }});
                            }}
                        """)
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                    else:
                        screenshot = await self._browser.take_screenshot(page, "twitch_captcha_failed")
                        return StepResult(
                            StepStatus.FAILED,
                            f"CAPTCHA solve failed: {solve_result.get('error', 'unknown')}",
                            {"reason": "captcha_failed"},
                            screenshot,
                        )
            elif captcha_frame and not self._captcha:
                screenshot = await self._browser.take_screenshot(page, "twitch_captcha_no_solver")
                return StepResult(
                    StepStatus.MANUAL_REQUIRED,
                    "CAPTCHA detected but no solver configured.",
                    {"reason": "captcha_no_solver"},
                    screenshot,
                )

            signup_btn = await page.query_selector(
                "button[data-a-target='passport-signup-button'], "
                "button[type='submit']:has-text('Sign Up'), "
                "button:has-text('Sign Up')"
            )
            if signup_btn:
                await asyncio.sleep(random.uniform(0.5, 1.5))
                await signup_btn.click()
                await asyncio.sleep(random.uniform(2.0, 4.0))

            context["generated_username"] = username
            context["generated_password"] = password
            context["no_email_verification"] = True

            screenshot = await self._browser.take_screenshot(page, "twitch_after_signup")

            error_el = await page.query_selector("[class*='error'], [data-a-target*='error'], [role='alert']")
            if error_el:
                error_text = await error_el.inner_text()
                return StepResult(
                    StepStatus.FAILED,
                    f"Signup error: {error_text}",
                    {"username": username, "error": error_text},
                    screenshot,
                )

            return StepResult(
                StepStatus.COMPLETED,
                f"Twitch account signup submitted for {username}. "
                "Email verification skipped per client policy.",
                {
                    "username": username,
                    "email": email,
                    "no_email_verification": True,
                    "url": page.url,
                },
                screenshot,
            )

        except Exception as e:
            logger.exception("Browser error during Twitch registration")
            screenshot_path = None
            if page:
                try:
                    screenshot_path = await self._browser.take_screenshot(page, "twitch_error")
                except Exception:
                    pass
            return StepResult(StepStatus.FAILED, f"Browser error: {e}", screenshot=screenshot_path)
        finally:
            if page:
                await page.close()


class TwitchNoVerificationStep(WorkflowStep):
    """Explicit marker that Twitch email verification is skipped by policy."""

    name = "twitch_email_verification_skipped"
    description = "Email verification intentionally skipped per client policy"
    required = False

    async def execute(self, context: dict[str, Any]) -> StepResult:
        return StepResult(
            StepStatus.SKIPPED,
            "Twitch accounts are intentionally left unverified per client policy. "
            "No email verification step will be performed.",
            {"policy": "no_twitch_email_verification"},
        )


def create_twitch_workflow(
    browser_service: Any = None,
    captcha_adapter: Any = None,
) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="twitch_creation_only",
        platform="twitch",
        steps=[
            TwitchRegistrationStep(browser_service, captcha_adapter),
            TwitchNoVerificationStep(),
        ],
    )
