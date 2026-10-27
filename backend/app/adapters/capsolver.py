"""CapSolver adapter — integrates with the CapSolver API for authorized CAPTCHA workflows.

This adapter is a provider integration only. It must NOT be used to bypass
third-party registration, login, or anti-abuse protections.

Credentials stay on the backend and are redacted from all logs and responses.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.app.adapters.base import CaptchaAdapter
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

CAPSOLVER_API_URL = "https://api.capsolver.com"

CAPTCHA_POLICY_MESSAGE = (
    "Live CAPTCHA solving is disabled by policy. "
    "Set CAPTCHA_SOLVE_ENABLED=true in .env to enable for authorized workflows only."
)


class CapSolverAdapter(CaptchaAdapter):
    def __init__(self, api_key: str, timeout: int = 120) -> None:
        self._api_key = api_key
        self._timeout = timeout

    async def solve(self, site_key: str, page_url: str) -> dict[str, Any]:
        if not settings.CAPTCHA_SOLVE_ENABLED:
            logger.warning("CAPTCHA solve blocked by policy (CAPTCHA_SOLVE_ENABLED=false)")
            return {
                "solved": False,
                "error": CAPTCHA_POLICY_MESSAGE,
                "provider": "capsolver",
                "is_mock": False,
                "policy_blocked": True,
            }

        if not self._api_key:
            raise ValueError("CapSolver API key not configured")

        try:
            import asyncio
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                task_payload: dict[str, Any] = {
                    "clientKey": self._api_key,
                    "task": {
                        "type": "FunCaptchaTaskProxyLess",
                        "websiteURL": page_url,
                        "websitePublicKey": site_key,
                    },
                }
                logger.info("CapSolver createTask: type=FunCaptchaTaskProxyLess, key=%s..., url=%s",
                            site_key[:12], page_url)

                create_resp = await client.post(
                    f"{CAPSOLVER_API_URL}/createTask",
                    json=task_payload,
                )

                create_data = create_resp.json()
                logger.info("CapSolver createTask response: status=%s, errorId=%s, errorDesc=%s",
                            create_resp.status_code,
                            create_data.get("errorId"),
                            create_data.get("errorDescription"))

                if create_data.get("errorId", 0) != 0:
                    return {
                        "solved": False,
                        "error": create_data.get("errorDescription", "Unknown error"),
                        "provider": "capsolver",
                        "is_mock": False,
                    }

                task_id = create_data.get("taskId")

                for attempt in range(45):
                    await asyncio.sleep(3)
                    result_resp = await client.post(
                        f"{CAPSOLVER_API_URL}/getTaskResult",
                        json={"clientKey": self._api_key, "taskId": task_id},
                    )
                    result_data = result_resp.json()

                    if result_data.get("status") == "ready":
                        solution = result_data.get("solution", {})
                        token = solution.get("token", "")
                        logger.info("CapSolver solved FunCaptcha (task=%s, attempt=%d)", task_id, attempt + 1)
                        return {
                            "solved": True,
                            "token": token,
                            "task_id": task_id,
                            "provider": "capsolver",
                            "is_mock": False,
                        }

                    if result_data.get("errorId", 0) != 0:
                        return {
                            "solved": False,
                            "error": result_data.get("errorDescription", "Task failed"),
                            "provider": "capsolver",
                            "is_mock": False,
                        }

                return {
                    "solved": False,
                    "error": "Solve timed out after 135s",
                    "provider": "capsolver",
                    "is_mock": False,
                }

        except httpx.TimeoutException:
            return {"solved": False, "error": "Request timed out", "provider": "capsolver", "is_mock": False}
        except Exception as e:
            logger.exception("CapSolver unexpected error")
            return {"solved": False, "error": str(e), "provider": "capsolver", "is_mock": False}

    async def check_balance(self) -> dict[str, Any]:
        if not self._api_key:
            return {"balance": 0, "error": "Not configured", "provider": "capsolver", "is_mock": False}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{CAPSOLVER_API_URL}/getBalance",
                    json={"clientKey": self._api_key},
                )
                resp.raise_for_status()
                data = resp.json()

            if data.get("errorId", 0) != 0:
                return {
                    "balance": 0,
                    "error": data.get("errorDescription", "Unknown error"),
                    "provider": "capsolver",
                    "is_mock": False,
                }

            return {
                "balance": float(data.get("balance", 0)),
                "provider": "capsolver",
                "is_mock": False,
            }
        except Exception as e:
            return {"balance": 0, "error": str(e), "provider": "capsolver", "is_mock": False}

    def is_mock(self) -> bool:
        return False
