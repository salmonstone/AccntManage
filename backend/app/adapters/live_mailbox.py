from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.app.adapters.base import MailboxAdapter

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class LiveMailboxAdapter(MailboxAdapter):
    """
    Microsoft Graph mailbox adapter using authorized OAuth tokens.
    Only accesses mailboxes the operator has explicitly authorized.
    Requires minimum scopes: Mail.Read
    """

    def __init__(self, timeout: int = 30) -> None:
        self._timeout = timeout

    async def search_messages(
        self,
        access_token: str,
        sender_filter: str | None = None,
        subject_filter: str | None = None,
        max_results: int = 25,
    ) -> list[dict[str, Any]]:
        max_results = min(max_results, 100)

        filters = []
        if sender_filter:
            safe_sender = sender_filter.replace("'", "''")
            filters.append(f"from/emailAddress/address eq '{safe_sender}'")
        if subject_filter:
            safe_subject = subject_filter.replace("'", "''")
            filters.append(f"contains(subject, '{safe_subject}')")

        params: dict[str, Any] = {
            "$top": max_results,
            "$select": "id,from,subject,receivedDateTime,bodyPreview",
            "$orderby": "receivedDateTime desc",
        }
        if filters:
            params["$filter"] = " and ".join(filters)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{GRAPH_BASE}/me/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        messages = []
        for msg in data.get("value", []):
            messages.append({
                "message_id": msg["id"],
                "sender": msg.get("from", {}).get("emailAddress", {}).get("address", ""),
                "subject": msg.get("subject", ""),
                "received_at": msg.get("receivedDateTime", ""),
                "body_preview": msg.get("bodyPreview", "")[:500],
                "is_mock": False,
            })
        return messages

    async def validate_token(self, access_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{GRAPH_BASE}/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code == 401:
                return {"valid": False, "error": "Token expired or invalid", "is_mock": False}
            resp.raise_for_status()
            data = resp.json()
            return {
                "valid": True,
                "email": data.get("mail") or data.get("userPrincipalName", ""),
                "display_name": data.get("displayName", ""),
                "is_mock": False,
            }

    def is_mock(self) -> bool:
        return False
