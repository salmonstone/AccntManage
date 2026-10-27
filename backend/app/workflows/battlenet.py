"""Battle.net account workflow — automated multi-step pipeline.

Steps: registration (with CAPTCHA solving) → email verification → phone verification.
Falls back to MANUAL_REQUIRED when browser or adapters are unavailable.
"""
from __future__ import annotations

import asyncio
import logging
import random
import re
import string
from typing import Any

from backend.app.workflows.engine import (
    StepResult,
    StepStatus,
    WorkflowDefinition,
    WorkflowStep,
)

logger = logging.getLogger(__name__)

BATTLENET_REGISTRATION_URL = "https://account.battle.net/creation/flow/creation-full"
BATTLENET_PHONE_VERIFY_URL = "https://account.battle.net/overview"

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
    "Linda", "David", "Elizabeth", "William", "Barbara", "Richard", "Susan",
    "Joseph", "Jessica", "Thomas", "Sarah", "Daniel", "Karen",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson",
    "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee",
]


def _random_name() -> tuple[str, str]:
    return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)


def _random_password(length: int = 16) -> str:
    chars = string.ascii_letters + string.digits + "!@#$%"
    pwd = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice("!@#$%"),
    ]
    pwd += [random.choice(chars) for _ in range(length - 4)]
    random.shuffle(pwd)
    return "".join(pwd)


def _random_dob() -> tuple[str, str, str]:
    year = random.randint(1985, 2000)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return str(month), str(day), str(year)


class BattlenetRegistrationStep(WorkflowStep):
    name = "battlenet_registration"
    description = "Navigate to Battle.net registration and create account"

    def __init__(self, browser_service: Any = None, captcha_adapter: Any = None) -> None:
        self._browser = browser_service
        self._captcha = captcha_adapter

    async def execute(self, context: dict[str, Any]) -> StepResult:
        if not self._browser or not self._browser.is_running:
            return StepResult(
                StepStatus.MANUAL_REQUIRED,
                "Browser not available. Create the Battle.net account manually at "
                f"{BATTLENET_REGISTRATION_URL} and update the account record.",
                {"url": BATTLENET_REGISTRATION_URL},
            )

        email = context.get("email")
        if not email:
            return StepResult(StepStatus.FAILED, "No email address in workflow context.")

        page = None
        try:
            page = await self._browser.new_page()
            await page.goto(BATTLENET_REGISTRATION_URL, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(random.uniform(1.0, 2.0))

            first_name, last_name = _random_name()
            password = _random_password()
            month, day, year = _random_dob()

            context["generated_password"] = password
            context["first_name"] = first_name
            context["last_name"] = last_name

            for selector, value in [
                ("#capture-first-name, input[name='firstName'], input[placeholder*='irst']", first_name),
                ("#capture-last-name, input[name='lastName'], input[placeholder*='ast']", last_name),
            ]:
                el = await page.query_selector(selector)
                if el:
                    await el.fill(value)
                    await asyncio.sleep(random.uniform(0.3, 0.8))

            dob_month = await page.query_selector("select[name='dob-month'], #capture-dob-month, select[data-testid*='month']")
            dob_day = await page.query_selector("select[name='dob-day'], #capture-dob-day, select[data-testid*='day']")
            dob_year = await page.query_selector("select[name='dob-year'], #capture-dob-year, select[data-testid*='year']")

            if dob_month:
                await dob_month.select_option(value=month)
                await asyncio.sleep(random.uniform(0.2, 0.5))
            if dob_day:
                await dob_day.select_option(value=day)
                await asyncio.sleep(random.uniform(0.2, 0.5))
            if dob_year:
                await dob_year.select_option(value=year)
                await asyncio.sleep(random.uniform(0.3, 0.8))

            for selector in [
                "#capture-email, input[name='emailAddress'], input[type='email']",
                "#capture-confirm-email, input[name='confirmEmailAddress']",
            ]:
                el = await page.query_selector(selector)
                if el:
                    await el.fill(email)
                    await asyncio.sleep(random.uniform(0.3, 0.8))

            for selector in [
                "#capture-password, input[name='password']:not([name*='confirm'])",
                "#capture-confirm-password, input[name='confirmPassword']",
            ]:
                el = await page.query_selector(selector)
                if el:
                    await el.fill(password)
                    await asyncio.sleep(random.uniform(0.3, 0.8))

            for selector in [
                "input[name='tos'], input[type='checkbox'][id*='tos']",
                "input[name='consent'], input[type='checkbox'][id*='consent']",
                "input[type='checkbox'][id*='agree']",
            ]:
                checkbox = await page.query_selector(selector)
                if checkbox:
                    checked = await checkbox.is_checked()
                    if not checked:
                        await checkbox.click()
                        await asyncio.sleep(random.uniform(0.2, 0.5))

            await self._browser.take_screenshot(page, "bnet_form_filled")

            captcha_frame = await page.query_selector(
                "iframe[src*='recaptcha'], iframe[src*='captcha'], "
                "[class*='captcha'], [id*='captcha']"
            )

            if captcha_frame and self._captcha:
                site_key = await page.evaluate("""() => {
                    const el = document.querySelector('[data-sitekey]');
                    return el ? el.getAttribute('data-sitekey') : null;
                }""")

                if site_key:
                    logger.info("Solving reCAPTCHA with site key: %s...", site_key[:12])
                    solve_result = await self._captcha.solve(site_key, page.url)

                    if solve_result.get("solved"):
                        token = solve_result["token"]
                        await page.evaluate(f"""() => {{
                            const el = document.getElementById('g-recaptcha-response');
                            if (el) {{ el.value = '{token}'; el.style.display = 'block'; }}
                            const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                            if (textarea) {{ textarea.value = '{token}'; }}
                        }}""")
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                        logger.info("CAPTCHA token injected")
                    else:
                        screenshot = await self._browser.take_screenshot(page, "bnet_captcha_failed")
                        return StepResult(
                            StepStatus.FAILED,
                            f"CAPTCHA solve failed: {solve_result.get('error', 'unknown')}",
                            {"url": page.url},
                            screenshot,
                        )
                else:
                    logger.warning("CAPTCHA detected but no site key found")
            elif captcha_frame and not self._captcha:
                screenshot = await self._browser.take_screenshot(page, "bnet_captcha_no_solver")
                return StepResult(
                    StepStatus.MANUAL_REQUIRED,
                    "CAPTCHA detected but no solver configured.",
                    {"url": page.url, "reason": "captcha_no_solver"},
                    screenshot,
                )

            submit_btn = await page.query_selector(
                "button[type='submit'], button[data-testid*='submit'], "
                "button[id*='submit'], button[id*='creation'], "
                "#flow-form-submit-btn, button.btn-primary"
            )
            if submit_btn:
                await submit_btn.click()
            else:
                await page.keyboard.press("Enter")

            await asyncio.sleep(random.uniform(2.0, 4.0))

            current_url = page.url
            page_content = await page.content()

            success_indicators = [
                "account.battle.net/overview" in current_url,
                "verify" in current_url.lower(),
                "success" in current_url.lower(),
                "verification" in page_content.lower() and "error" not in page_content.lower()[:500],
                "check your email" in page_content.lower(),
            ]

            screenshot = await self._browser.take_screenshot(page, "bnet_after_submit")

            if any(success_indicators):
                return StepResult(
                    StepStatus.COMPLETED,
                    f"Battle.net account registration submitted for {email}.",
                    {
                        "url": current_url,
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                    },
                    screenshot,
                )

            error_el = await page.query_selector(
                ".error-message, [class*='error'], [role='alert'], .form-error"
            )
            if error_el:
                error_text = await error_el.text_content()
                return StepResult(
                    StepStatus.FAILED,
                    f"Registration form error: {(error_text or '').strip()[:200]}",
                    {"url": current_url, "error": (error_text or "").strip()[:200]},
                    screenshot,
                )

            return StepResult(
                StepStatus.COMPLETED,
                f"Registration form submitted for {email}. Verify result via email.",
                {"url": current_url, "email": email},
                screenshot,
            )

        except Exception as e:
            logger.exception("Browser error during Battle.net registration")
            if page:
                try:
                    screenshot = await self._browser.take_screenshot(page, "bnet_reg_error")
                    return StepResult(StepStatus.FAILED, f"Browser error: {e}", screenshot_path=screenshot)
                except Exception:
                    pass
            return StepResult(StepStatus.FAILED, f"Browser error: {e}")
        finally:
            if page:
                await page.close()


class BattlenetEmailVerificationStep(WorkflowStep):
    name = "battlenet_email_verification"
    description = "Verify email via Microsoft Graph mailbox access"

    def __init__(self, mailbox_adapter: Any = None, browser_service: Any = None) -> None:
        self._mailbox = mailbox_adapter
        self._browser = browser_service

    async def execute(self, context: dict[str, Any]) -> StepResult:
        access_token = context.get("mailbox_access_token")
        if not access_token:
            return StepResult(
                StepStatus.MANUAL_REQUIRED,
                "No mailbox access token available. Configure Microsoft Graph "
                "authorization for the associated mailbox.",
            )

        if not self._mailbox:
            return StepResult(
                StepStatus.UNSUPPORTED,
                "Mailbox adapter not configured.",
            )

        try:
            for attempt in range(6):
                if attempt > 0:
                    await asyncio.sleep(10)

                messages = await self._mailbox.search_messages(
                    access_token,
                    sender_filter="noreply@blizzard.com",
                    subject_filter="Verify",
                    max_results=5,
                )

                if messages:
                    break
            else:
                return StepResult(
                    StepStatus.MANUAL_REQUIRED,
                    "No Battle.net verification email found after polling. "
                    "Check that the email was sent and the mailbox token has Mail.Read permission.",
                    {"searched_sender": "noreply@blizzard.com"},
                )

            latest = messages[0]
            body = latest.get("body_preview", "") + " " + latest.get("body", {}).get("content", "")

            link_match = re.search(r"https://[^\s\"'<>]+verify[^\s\"'<>]*", body, re.IGNORECASE)
            code_match = re.search(r"\b(\d{6})\b", body)

            if link_match:
                verify_link = link_match.group(0)
                context["verification_link"] = verify_link

                if self._browser and self._browser.is_running:
                    page = None
                    try:
                        page = await self._browser.new_page()
                        await page.goto(verify_link, wait_until="networkidle", timeout=30000)
                        await asyncio.sleep(random.uniform(2.0, 3.0))

                        screenshot = await self._browser.take_screenshot(page, "bnet_email_verified")
                        page_content = await page.content()

                        if any(kw in page_content.lower() for kw in ["verified", "confirmed", "success", "thank you"]):
                            return StepResult(
                                StepStatus.COMPLETED,
                                "Email verification completed via link.",
                                {"verification_link": verify_link, "is_mock": latest.get("is_mock", False)},
                                screenshot,
                            )

                        return StepResult(
                            StepStatus.COMPLETED,
                            "Verification link opened. Check account status.",
                            {"verification_link": verify_link, "url": page.url},
                            screenshot,
                        )
                    except Exception as e:
                        logger.warning("Failed to open verification link: %s", e)
                        return StepResult(
                            StepStatus.MANUAL_REQUIRED,
                            f"Verification link found but browser failed: {e}",
                            {"verification_link": verify_link},
                        )
                    finally:
                        if page:
                            await page.close()

                return StepResult(
                    StepStatus.MANUAL_REQUIRED,
                    "Verification link found but browser not available.",
                    {"verification_link": verify_link, "is_mock": latest.get("is_mock", False)},
                )

            elif code_match:
                code = code_match.group(1)
                context["verification_code"] = code

                if self._browser and self._browser.is_running:
                    page = None
                    try:
                        page = await self._browser.new_page()
                        await page.goto(
                            "https://account.battle.net/creation/flow/creation-full",
                            wait_until="networkidle", timeout=30000,
                        )
                        await asyncio.sleep(random.uniform(1.0, 2.0))

                        code_input = await page.query_selector(
                            "input[name='verificationCode'], input[name='code'], "
                            "input[type='text'][maxlength='6'], input[placeholder*='code']"
                        )
                        if code_input:
                            await code_input.fill(code)
                            await asyncio.sleep(random.uniform(0.5, 1.0))

                            submit = await page.query_selector(
                                "button[type='submit'], button[data-testid*='verify']"
                            )
                            if submit:
                                await submit.click()
                            else:
                                await page.keyboard.press("Enter")

                            await asyncio.sleep(random.uniform(2.0, 3.0))
                            screenshot = await self._browser.take_screenshot(page, "bnet_code_verified")

                            return StepResult(
                                StepStatus.COMPLETED,
                                "Email verification code submitted.",
                                {"verification_code": code},
                                screenshot,
                            )

                    except Exception as e:
                        logger.warning("Failed to submit verification code: %s", e)
                    finally:
                        if page:
                            await page.close()

                return StepResult(
                    StepStatus.MANUAL_REQUIRED,
                    "Verification code found. Enter it on the Battle.net verification page.",
                    {"verification_code": code, "is_mock": latest.get("is_mock", False)},
                )

            return StepResult(
                StepStatus.MANUAL_REQUIRED,
                "Verification email found but no link or code could be extracted.",
                {"email_subject": latest.get("subject", ""), "is_mock": latest.get("is_mock", False)},
            )

        except Exception as e:
            return StepResult(StepStatus.FAILED, f"Mailbox search error: {e}")


class BattlenetPhoneVerificationStep(WorkflowStep):
    name = "battlenet_phone_verification"
    description = "Verify phone number via SMS provider"

    def __init__(self, sms_adapter: Any = None, browser_service: Any = None) -> None:
        self._sms = sms_adapter
        self._browser = browser_service

    async def execute(self, context: dict[str, Any]) -> StepResult:
        if not self._sms:
            return StepResult(
                StepStatus.UNSUPPORTED,
                "SMS provider not configured.",
            )

        if self._sms.is_mock():
            rental = await self._sms.rent_number(context.get("country", "US"))
            sms_result = await self._sms.get_sms(rental["rental_id"])
            await self._sms.release_number(rental["rental_id"])
            return StepResult(
                StepStatus.COMPLETED,
                "Mock phone verification completed (simulated).",
                {
                    "phone_number": rental["phone_number"],
                    "code": sms_result["code"],
                    "is_mock": True,
                },
            )

        rental = None
        try:
            rental = await self._sms.rent_number(context.get("country", "US"))
            phone_number = rental["phone_number"]
            rental_id = rental["rental_id"]
            context["phone_number"] = phone_number
            context["sms_rental_id"] = rental_id

            if not self._browser or not self._browser.is_running:
                return StepResult(
                    StepStatus.MANUAL_REQUIRED,
                    f"Phone number {phone_number} obtained. "
                    "Submit it to the Battle.net phone verification page manually.",
                    {"phone_number": phone_number, "rental_id": rental_id, "is_mock": False},
                )

            page = None
            try:
                page = await self._browser.new_page()
                await page.goto(BATTLENET_PHONE_VERIFY_URL, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(random.uniform(1.0, 2.0))

                phone_link = await page.query_selector(
                    "a[href*='phone'], button[data-testid*='phone'], "
                    "[class*='phone-verify'], a[href*='sms']"
                )
                if phone_link:
                    await phone_link.click()
                    await asyncio.sleep(random.uniform(1.0, 2.0))

                phone_input = await page.query_selector(
                    "input[name='phoneNumber'], input[type='tel'], "
                    "input[name='phone'], input[placeholder*='phone'], "
                    "input[placeholder*='number']"
                )

                if not phone_input:
                    screenshot = await self._browser.take_screenshot(page, "bnet_no_phone_input")
                    return StepResult(
                        StepStatus.MANUAL_REQUIRED,
                        f"Phone number {phone_number} obtained but could not find phone input field.",
                        {"phone_number": phone_number, "url": page.url},
                        screenshot,
                    )

                clean_number = re.sub(r"[^\d+]", "", phone_number)
                await phone_input.fill(clean_number)
                await asyncio.sleep(random.uniform(0.5, 1.0))

                send_btn = await page.query_selector(
                    "button[data-testid*='send'], button[type='submit'], "
                    "button:has-text('Send'), button:has-text('Continue'), "
                    "button:has-text('Verify')"
                )
                if send_btn:
                    await send_btn.click()
                else:
                    await page.keyboard.press("Enter")

                await asyncio.sleep(random.uniform(2.0, 3.0))
                await self._browser.take_screenshot(page, "bnet_sms_sent")

                sms_code = None
                for poll in range(12):
                    await asyncio.sleep(5)
                    sms_result = await self._sms.get_sms(rental_id)
                    if sms_result.get("code"):
                        sms_code = sms_result["code"]
                        break
                    logger.info("Polling SMS attempt %d/12 — waiting for code", poll + 1)

                if not sms_code:
                    screenshot = await self._browser.take_screenshot(page, "bnet_sms_timeout")
                    await self._sms.release_number(rental_id)
                    return StepResult(
                        StepStatus.FAILED,
                        f"SMS code not received for {phone_number} after 60s.",
                        {"phone_number": phone_number},
                        screenshot,
                    )

                code_input = await page.query_selector(
                    "input[name='code'], input[name='verificationCode'], "
                    "input[type='text'][maxlength='6'], input[placeholder*='code']"
                )
                if code_input:
                    await code_input.fill(sms_code)
                    await asyncio.sleep(random.uniform(0.5, 1.0))

                    verify_btn = await page.query_selector(
                        "button[type='submit'], button:has-text('Verify'), "
                        "button:has-text('Confirm'), button[data-testid*='verify']"
                    )
                    if verify_btn:
                        await verify_btn.click()
                    else:
                        await page.keyboard.press("Enter")

                    await asyncio.sleep(random.uniform(2.0, 3.0))

                screenshot = await self._browser.take_screenshot(page, "bnet_phone_verified")
                await self._sms.release_number(rental_id)

                return StepResult(
                    StepStatus.COMPLETED,
                    f"Phone verification completed with {phone_number}.",
                    {"phone_number": phone_number, "code": sms_code, "is_mock": False},
                    screenshot,
                )

            except Exception as e:
                logger.exception("Browser error during phone verification")
                if page:
                    try:
                        screenshot = await self._browser.take_screenshot(page, "bnet_phone_error")
                        return StepResult(
                            StepStatus.FAILED,
                            f"Phone verification browser error: {e}",
                            {"phone_number": phone_number},
                            screenshot,
                        )
                    except Exception:
                        pass
                return StepResult(StepStatus.FAILED, f"Phone verification browser error: {e}")
            finally:
                if page:
                    await page.close()

        except Exception as e:
            if rental:
                try:
                    await self._sms.release_number(rental["rental_id"])
                except Exception:
                    pass
            return StepResult(StepStatus.FAILED, f"SMS provider error: {e}")


def create_battlenet_workflow(
    browser_service: Any = None,
    mailbox_adapter: Any = None,
    sms_adapter: Any = None,
    captcha_adapter: Any = None,
) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="battlenet_full_verification",
        platform="battlenet",
        steps=[
            BattlenetRegistrationStep(browser_service, captcha_adapter),
            BattlenetEmailVerificationStep(mailbox_adapter, browser_service),
            BattlenetPhoneVerificationStep(sms_adapter, browser_service),
        ],
    )
