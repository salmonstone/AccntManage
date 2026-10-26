from __future__ import annotations

import random
import string
from datetime import datetime, timezone
from typing import Any

from backend.app.adapters.base import SMSAdapter


class MockSMSAdapter(SMSAdapter):
    """Deterministic mock SMS adapter for testing. Never contacts real SMS providers."""

    def __init__(self) -> None:
        self._rentals: dict[str, dict] = {}
        self._counter = 0

    async def rent_number(self, country: str = "US") -> dict[str, Any]:
        self._counter += 1
        rental_id = f"mock-rental-{self._counter}"
        number = f"+1555000{self._counter:04d}"
        self._rentals[rental_id] = {
            "rental_id": rental_id,
            "number": number,
            "country": country,
            "rented_at": datetime.now(timezone.utc).isoformat(),
            "expired": False,
        }
        return {
            "rental_id": rental_id,
            "number": number,
            "is_mock": True,
            "status": "active",
        }

    async def get_sms(self, rental_id: str, timeout: int = 60) -> dict[str, Any]:
        if rental_id not in self._rentals:
            return {"error": "Unknown rental ID", "is_mock": True}
        code = "".join(random.choices(string.digits, k=6))
        return {
            "rental_id": rental_id,
            "code": code,
            "message": f"Your verification code is {code}",
            "is_mock": True,
        }

    async def release_number(self, rental_id: str) -> None:
        self._rentals.pop(rental_id, None)

    async def check_balance(self) -> dict[str, Any]:
        return {"balance": 99.99, "currency": "USD", "is_mock": True}

    def is_mock(self) -> bool:
        return True
