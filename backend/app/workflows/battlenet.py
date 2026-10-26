"""Battle.net account workflow — multi-step pipeline with manual handoff.

Steps: registration → email verification → phone verification.
Each step that cannot be automated reports MANUAL_REQUIRED or UNSUPPORTED.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from backend.app.workflows.engine import (
    StepResult,
    StepStatus,
    WorkflowDefinition,
    WorkflowStep,
)

logger = logging.getLogger(__name__)

BATTLENET_REGISTRATION_URL = "https://account.battle.net/creation/flow/creation-full"


class BattlenetRegistrationStep(WorkflowStep):
    name = "battlenet_registration"
    description = "Navigate to Battle.net registration and create account"

    def __init__(self, browser_service: Any = None) -> None:
        self._browser = browser_service

    async def execute(self, context: dict[str, Any]) -> StepResult:
        if not self._browser or not self._browser.is_running:
            return StepResult(
                StepStatus.MANUAL_REQUIRED,
                "Browser not available. Create the Battle.net account manually at "
                f"{BATTLENET_REGISTRATION_URL} and update the account record.",
                {"url": BATTLENET_REGISTRATION_URL},
            )

        page = None
        try:
            page = await self._browser.new_page()
            await page.goto(BATTLENET_REGISTRATION_URL, wait_until="domcontentloaded")

            has_captcha = await page.query_selector("[class*='captcha'], [id*='captcha'], iframe[src*='captcha']")
            if has_captcha:
                screenshot = await self._browser.take_screenshot(page, "bnet_captcha_detected")
                return StepResult(
                    StepStatus.MANUAL_REQUIRED,
                    "CAPTCHA detected on registration page. Complete registration manually.",
                    {"url": page.url, "reason": "captcha_detected"},
                    screenshot,
                )

            has_antibot = await page.query_selector("[class*='challenge'], [id*='challenge']")
            if has_antibot:
                screenshot = await self._browser.take_screenshot(page, "bnet_antibot")
                return StepResult(
                    StepStatus.MANUAL_REQUIRED,
                    "Anti-bot challenge detected. Complete registration manually.",
                    {"url": page.url, "reason": "antibot_challenge"},
                    screenshot,
                )

            screenshot = await self._browser.take_screenshot(page, "bnet_registration_page")
            return StepResult(
                StepStatus.MANUAL_REQUIRED,
                "Battle.net registration page loaded. No authorized automation API exists. "
                "Complete registration manually and update the account status.",
                {"url": page.url},
                screenshot,
            )
        except Exception as e:
            logger.exception("Browser error during Battle.net registration")
            return StepResult(StepStatus.FAILED, f"Browser error: {e}")
        finally:
            if page:
                await page.close()


class BattlenetEmailVerificationStep(WorkflowStep):
    name = "battlenet_email_verification"
    description = "Verify email via Microsoft Graph mailbox access"

    def __init__(self, mailbox_adapter: Any = None) -> None:
        self._mailbox = mailbox_adapter

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
            messages = await self._mailbox.search_messages(
                access_token,
                sender_filter="noreply@blizzard.com",
                subject_filter="Verify",
                max_results=5,
            )

            if not messages:
                return StepResult(
                    StepStatus.MANUAL_REQUIRED,
                    "No Battle.net verification email found. "
                    "Check that the email was sent and the mailbox token has Mail.Read permission.",
                    {"searched_sender": "noreply@blizzard.com"},
                )

            latest = messages[0]
            body = latest.get("body_preview", "")

            link_match = re.search(r"https://[^\s\"'<>]+verify[^\s\"'<>]*", body, re.IGNORECASE)
            code_match = re.search(r"\b(\d{6})\b", body)

            if link_match:
                context["verification_link"] = link_match.group(0)
                return StepResult(
                    StepStatus.MANUAL_REQUIRED,
                    "Verification link found. Open it in a browser to complete email verification.",
                    {"verification_link": link_match.group(0), "is_mock": latest.get("is_mock", False)},
                )
            elif code_match:
                context["verification_code"] = code_match.group(1)
                return StepResult(
                    StepStatus.MANUAL_REQUIRED,
                    "Verification code found. Enter it on the Battle.net verification page.",
                    {"verification_code": code_match.group(1), "is_mock": latest.get("is_mock", False)},
                )

            return StepResult(
                StepStatus.MANUAL_REQUIRED,
                "Verification email found but no link or code could be extracted. "
                "Check the email manually.",
                {"email_subject": latest.get("subject", ""), "is_mock": latest.get("is_mock", False)},
            )

        except Exception as e:
            return StepResult(StepStatus.FAILED, f"Mailbox search error: {e}")


class BattlenetPhoneVerificationStep(WorkflowStep):
    name = "battlenet_phone_verification"
    description = "Verify phone number via SMS provider"

    def __init__(self, sms_adapter: Any = None) -> None:
        self._sms = sms_adapter

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

        try:
            rental = await self._sms.rent_number(context.get("country", "US"))
            context["phone_number"] = rental["phone_number"]
            context["sms_rental_id"] = rental["rental_id"]

            return StepResult(
                StepStatus.MANUAL_REQUIRED,
                f"Phone number {rental['phone_number']} obtained. "
                "Submit it to the Battle.net phone verification page, "
                "then the workflow will poll for the incoming SMS code.",
                {
                    "phone_number": rental["phone_number"],
                    "rental_id": rental["rental_id"],
                    "is_mock": False,
                },
            )
        except Exception as e:
            return StepResult(StepStatus.FAILED, f"SMS provider error: {e}")


def create_battlenet_workflow(
    browser_service: Any = None,
    mailbox_adapter: Any = None,
    sms_adapter: Any = None,
) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="battlenet_full_verification",
        platform="battlenet",
        steps=[
            BattlenetRegistrationStep(browser_service),
            BattlenetEmailVerificationStep(mailbox_adapter),
            BattlenetPhoneVerificationStep(sms_adapter),
        ],
    )
