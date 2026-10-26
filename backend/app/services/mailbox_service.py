from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.adapters.base import MailboxAdapter
from backend.app.core.security import decrypt_value, encrypt_value, mask_secret
from backend.app.models.enums import MailboxStatus
from backend.app.models.mailbox import Mailbox
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.mailbox import MailboxImportPreview, MailboxResponse

logger = logging.getLogger(__name__)


class MailboxService:
    def __init__(self, session: AsyncSession, adapter: MailboxAdapter) -> None:
        self._session = session
        self._adapter = adapter

    async def get(self, mailbox_id: int) -> Mailbox | None:
        result = await self._session.execute(select(Mailbox).where(Mailbox.id == mailbox_id))
        return result.scalar_one_or_none()

    async def list_mailboxes(
        self,
        status: MailboxStatus | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> PaginatedResponse[MailboxResponse]:
        query = select(Mailbox)
        count_query = select(func.count(Mailbox.id))

        if status:
            query = query.where(Mailbox.status == status)
            count_query = count_query.where(Mailbox.status == status)

        total = (await self._session.execute(count_query)).scalar() or 0
        offset = (page - 1) * page_size
        result = await self._session.execute(
            query.order_by(Mailbox.created_at.desc()).offset(offset).limit(page_size)
        )
        items = [MailboxResponse.model_validate(m) for m in result.scalars().all()]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size if total > 0 else 0,
        )

    async def preview_import(self, raw_text: str, format_hint: str | None = None) -> MailboxImportPreview:
        lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]
        valid_emails: list[str] = []
        invalid_lines: list[str] = []
        seen: set[str] = set()

        for line in lines:
            parsed = self._parse_credential_line(line, format_hint)
            if not parsed:
                invalid_lines.append(line[:80])
                continue
            email = parsed["email"]
            if email in seen:
                continue
            seen.add(email)
            valid_emails.append(email)

        existing = await self._session.execute(
            select(Mailbox.email).where(Mailbox.email.in_(valid_emails))
        )
        existing_set = {r[0] for r in existing.all()}
        new_count = len([e for e in valid_emails if e not in existing_set])

        return MailboxImportPreview(
            total_parsed=len(lines),
            valid_count=new_count,
            duplicate_count=len(valid_emails) - new_count,
            invalid_count=len(invalid_lines),
            invalid_lines=invalid_lines[:50],
        )

    async def commit_import(self, raw_text: str, format_hint: str | None = None) -> dict:
        lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]
        imported = 0
        seen: set[str] = set()

        for line in lines:
            parsed = self._parse_credential_line(line, format_hint)
            if not parsed or parsed["email"] in seen:
                continue
            seen.add(parsed["email"])

            existing = await self._session.execute(
                select(Mailbox).where(Mailbox.email == parsed["email"])
            )
            if existing.scalar_one_or_none():
                continue

            mailbox = Mailbox(
                email=parsed["email"],
                status=MailboxStatus.PENDING,
                encrypted_password=encrypt_value(parsed["password"]) if parsed.get("password") else None,
                client_id=parsed.get("client_id"),
                encrypted_token=encrypt_value(parsed["token"]) if parsed.get("token") else None,
                token_type=parsed.get("token_type"),
            )
            self._session.add(mailbox)
            imported += 1

        await self._session.commit()
        return {"imported": imported}

    async def validate_mailbox(self, mailbox_id: int) -> dict:
        mailbox = await self.get(mailbox_id)
        if not mailbox:
            raise ValueError("Mailbox not found")
        if not mailbox.encrypted_token:
            return {"valid": False, "error": "No token stored", "is_mock": self._adapter.is_mock()}

        token = decrypt_value(mailbox.encrypted_token)
        result = await self._adapter.validate_token(token)

        if result.get("valid"):
            mailbox.status = MailboxStatus.AUTHORIZED
        else:
            mailbox.status = MailboxStatus.TOKEN_EXPIRED

        await self._session.commit()
        return result

    async def search_messages(
        self,
        mailbox_id: int,
        sender_filter: str | None = None,
        subject_filter: str | None = None,
        max_results: int = 25,
    ) -> list[dict]:
        mailbox = await self.get(mailbox_id)
        if not mailbox:
            raise ValueError("Mailbox not found")
        if not mailbox.encrypted_token:
            raise ValueError("No token stored for this mailbox")

        token = decrypt_value(mailbox.encrypted_token)
        return await self._adapter.search_messages(token, sender_filter, subject_filter, max_results)

    async def revoke(self, mailbox_id: int) -> None:
        mailbox = await self.get(mailbox_id)
        if not mailbox:
            raise ValueError("Mailbox not found")
        mailbox.encrypted_token = None
        mailbox.status = MailboxStatus.REVOKED
        await self._session.commit()

    async def delete(self, mailbox_id: int) -> None:
        mailbox = await self.get(mailbox_id)
        if not mailbox:
            raise ValueError("Mailbox not found")
        await self._session.delete(mailbox)
        await self._session.commit()

    @staticmethod
    def _extract_email(line: str) -> str | None:
        parts = re.split(r"[:\t|,;]", line)
        for part in parts:
            part = part.strip().lower()
            if re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", part):
                return part
        return None

    @staticmethod
    def _parse_credential_line(line: str, format_hint: str | None = None) -> dict | None:
        """Parse credential lines in supported formats.

        Primary:  email:password:clientId:authToken
        Alternate: email:password:refreshToken:clientId
        Fallback: bare email address
        """
        parts = line.split(":")
        if len(parts) >= 4:
            email_candidate = parts[0].strip().lower()
            if not re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email_candidate):
                return None

            password = parts[1]
            field3 = parts[2]
            field4 = ":".join(parts[3:])

            if format_hint == "email:password:refreshToken:clientId":
                return {
                    "email": email_candidate,
                    "password": password,
                    "token": field3,
                    "token_type": "refresh_token",
                    "client_id": field4.strip(),
                }

            is_uuid_like = bool(re.match(r"^[a-f0-9\-]{32,}$", field3.strip(), re.IGNORECASE))
            if format_hint == "email:password:clientId:authToken" or is_uuid_like:
                return {
                    "email": email_candidate,
                    "password": password,
                    "client_id": field3.strip(),
                    "token": field4.strip(),
                    "token_type": "auth_token",
                }

            return {
                "email": email_candidate,
                "password": password,
                "client_id": field3.strip(),
                "token": field4.strip(),
                "token_type": "auth_token",
            }

        email = MailboxService._extract_email(line)
        if email:
            return {"email": email}
        return None
