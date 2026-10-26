"""Twitch account workflow — creation only, no email verification per client spec.

Twitch accounts are intentionally left unverified. The UI must clearly
state this is by design, not an error.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.app.workflows.engine import (
    StepResult,
    StepStatus,
    WorkflowDefinition,
    WorkflowStep,
)

logger = logging.getLogger(__name__)

TWITCH_SIGNUP_URL = "https://www.twitch.tv/signup"


class TwitchRegistrationStep(WorkflowStep):
    name = "twitch_registration"
    description = "Navigate to Twitch signup and create account"

    def __init__(self, browser_service: Any = None) -> None:
        self._browser = browser_service

    async def execute(self, context: dict[str, Any]) -> StepResult:
        if not self._browser or not self._browser.is_running:
            return StepResult(
                StepStatus.MANUAL_REQUIRED,
                "Browser not available. Create the Twitch account manually at "
                f"{TWITCH_SIGNUP_URL} and update the account record.",
                {"url": TWITCH_SIGNUP_URL},
            )

        page = None
        try:
            page = await self._browser.new_page()
            await page.goto(TWITCH_SIGNUP_URL, wait_until="domcontentloaded")

            has_captcha = await page.query_selector(
                "[class*='captcha'], [id*='captcha'], iframe[src*='captcha'], "
                "[class*='arkose'], iframe[src*='arkoselabs']"
            )
            if has_captcha:
                screenshot = await self._browser.take_screenshot(page, "twitch_captcha_detected")
                return StepResult(
                    StepStatus.MANUAL_REQUIRED,
                    "CAPTCHA detected on Twitch signup. Complete registration manually.",
                    {"url": page.url, "reason": "captcha_detected"},
                    screenshot,
                )

            screenshot = await self._browser.take_screenshot(page, "twitch_signup_page")
            return StepResult(
                StepStatus.MANUAL_REQUIRED,
                "Twitch signup page loaded. No authorized registration API exists. "
                "Complete registration manually. Email verification will NOT be performed "
                "(client policy: Twitch accounts remain unverified).",
                {"url": page.url, "no_email_verification": True},
                screenshot,
            )
        except Exception as e:
            logger.exception("Browser error during Twitch registration")
            return StepResult(StepStatus.FAILED, f"Browser error: {e}")
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
) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="twitch_creation_only",
        platform="twitch",
        steps=[
            TwitchRegistrationStep(browser_service),
            TwitchNoVerificationStep(),
        ],
    )
