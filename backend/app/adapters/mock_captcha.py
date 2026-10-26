from __future__ import annotations

from typing import Any

from backend.app.adapters.base import CaptchaAdapter


class MockCaptchaAdapter(CaptchaAdapter):
    """
    Deterministic mock CAPTCHA adapter.
    Live CAPTCHA solving is prohibited — this adapter returns mock tokens only.
    It will NEVER contact AntiCaptcha, 2Captcha, CapSolver, EzCaptcha, or any real provider.
    """

    POLICY_MESSAGE = (
        "Live CAPTCHA solving is disabled by policy. "
        "This adapter produces deterministic mock results for testing only."
    )

    async def solve(self, site_key: str, page_url: str) -> dict[str, Any]:
        return {
            "token": "mock-captcha-token-deterministic-test-only",
            "is_mock": True,
            "policy": self.POLICY_MESSAGE,
        }

    async def check_balance(self) -> dict[str, Any]:
        return {
            "balance": 0.0,
            "currency": "USD",
            "is_mock": True,
            "policy": self.POLICY_MESSAGE,
        }

    def is_mock(self) -> bool:
        return True
