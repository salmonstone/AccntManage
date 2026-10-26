from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SMSAdapter(ABC):
    @abstractmethod
    async def rent_number(self, country: str = "US") -> dict[str, Any]:
        ...

    @abstractmethod
    async def get_sms(self, rental_id: str, timeout: int = 60) -> dict[str, Any]:
        ...

    @abstractmethod
    async def release_number(self, rental_id: str) -> None:
        ...

    @abstractmethod
    async def check_balance(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def is_mock(self) -> bool:
        ...


class CaptchaAdapter(ABC):
    @abstractmethod
    async def solve(self, site_key: str, page_url: str) -> dict[str, Any]:
        ...

    @abstractmethod
    async def check_balance(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def is_mock(self) -> bool:
        ...


class MailboxAdapter(ABC):
    @abstractmethod
    async def search_messages(
        self,
        access_token: str,
        sender_filter: str | None = None,
        subject_filter: str | None = None,
        max_results: int = 25,
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def validate_token(self, access_token: str) -> dict[str, Any]:
        ...

    @abstractmethod
    def is_mock(self) -> bool:
        ...
