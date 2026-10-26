"""Generic live SMS provider adapter.

Implements the SMS adapter interface against a configurable HTTP API.
Supports provider-specific implementations via subclassing or configuration.
Credentials are stored encrypted on the backend — never exposed to the frontend.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.app.adapters.base import SMSAdapter

logger = logging.getLogger(__name__)


class LiveSMSAdapter(SMSAdapter):
    def __init__(
        self,
        api_key: str,
        base_url: str = "",
        provider_name: str = "generic",
        timeout: int = 30,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._provider = provider_name
        self._timeout = timeout

    async def rent_number(self, country: str = "US") -> dict[str, Any]:
        if not self._base_url or not self._api_key:
            raise ValueError(f"SMS provider '{self._provider}' not configured")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self._base_url}/stubs/getNumber",
                params={"api_key": self._api_key, "country": country, "service": "other"},
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("error"):
            raise ValueError(f"SMS provider error: {data['error']}")

        return {
            "rental_id": str(data.get("id", data.get("rental_id", ""))),
            "phone_number": data.get("phone", data.get("number", "")),
            "country": country,
            "provider": self._provider,
            "is_mock": False,
        }

    async def get_sms(self, rental_id: str, timeout: int = 60) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self._base_url}/stubs/getStatus",
                params={"api_key": self._api_key, "id": rental_id},
            )
            resp.raise_for_status()
            data = resp.json()

        status = data.get("status", "waiting")
        code = data.get("code", data.get("sms_code"))

        return {
            "status": status,
            "code": code,
            "rental_id": rental_id,
            "is_mock": False,
        }

    async def release_number(self, rental_id: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                await client.get(
                    f"{self._base_url}/stubs/setStatus",
                    params={"api_key": self._api_key, "id": rental_id, "status": "cancel"},
                )
        except Exception:
            logger.warning("Failed to release SMS number %s", rental_id)

    async def check_balance(self) -> dict[str, Any]:
        if not self._base_url or not self._api_key:
            return {"balance": 0, "currency": "USD", "error": "Not configured", "is_mock": False}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{self._base_url}/stubs/getBalance",
                    params={"api_key": self._api_key},
                )
                resp.raise_for_status()
                data = resp.json()
            return {
                "balance": float(data.get("balance", 0)),
                "currency": data.get("currency", "USD"),
                "provider": self._provider,
                "is_mock": False,
            }
        except Exception as e:
            return {"balance": 0, "currency": "USD", "error": str(e), "is_mock": False}

    def is_mock(self) -> bool:
        return False
