from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.app.adapters.base import MailboxAdapter


class MockMailboxAdapter(MailboxAdapter):
    """Deterministic mock mailbox adapter. Does not contact Microsoft Graph."""

    async def search_messages(
        self,
        access_token: str,
        sender_filter: str | None = None,
        subject_filter: str | None = None,
        max_results: int = 25,
    ) -> list[dict[str, Any]]:
        messages = [
            {
                "message_id": "mock-msg-001",
                "sender": "noreply@example.com",
                "subject": "Welcome to the mock mailbox",
                "received_at": datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC).isoformat(),
                "body_preview": "This is a mock message for testing purposes.",
                "is_mock": True,
            },
            {
                "message_id": "mock-msg-002",
                "sender": "verification@example.com",
                "subject": "Mock verification email",
                "received_at": datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC).isoformat(),
                "body_preview": "Your mock verification code is 123456. (This is a test.)",
                "is_mock": True,
            },
        ]
        result = messages
        if sender_filter:
            result = [m for m in result if sender_filter.lower() in str(m["sender"]).lower()]
        if subject_filter:
            result = [m for m in result if subject_filter.lower() in str(m["subject"]).lower()]
        return result[:max_results]

    async def validate_token(self, access_token: str) -> dict[str, Any]:
        return {
            "valid": True,
            "email": "mock-user@example.com",
            "scopes": ["Mail.Read"],
            "is_mock": True,
        }

    def is_mock(self) -> bool:
        return True
