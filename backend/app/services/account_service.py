from __future__ import annotations

import csv
import io
import logging
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import generate_correlation_id, mask_secret
from backend.app.models.account import Account, AccountStatusHistory
from backend.app.models.enums import AccountPlatform, AccountStatus
from backend.app.schemas.account import (
    AccountCreate,
    AccountImportPreview,
    AccountResponse,
    AccountUpdate,
)
from backend.app.schemas.common import PaginatedResponse

logger = logging.getLogger(__name__)


class AccountService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: AccountCreate) -> Account:
        existing = await self._session.execute(
            select(Account).where(
                Account.platform == data.platform,
                Account.email == data.email,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Account already exists for {data.platform.value}: {mask_secret(data.email, 6)}")

        account = Account(
            platform=data.platform,
            email=data.email,
            display_name=data.display_name,
            notes=data.notes,
            status=AccountStatus.DRAFT,
        )
        self._session.add(account)
        await self._session.flush()

        await self._record_status_change(account.id, None, AccountStatus.DRAFT, "Created")
        await self._session.commit()
        return account

    async def get(self, account_id: int) -> Account | None:
        result = await self._session.execute(select(Account).where(Account.id == account_id))
        return result.scalar_one_or_none()

    async def list_accounts(
        self,
        platform: AccountPlatform | None = None,
        status: AccountStatus | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> PaginatedResponse[AccountResponse]:
        query = select(Account)
        count_query = select(func.count(Account.id))

        if platform:
            query = query.where(Account.platform == platform)
            count_query = count_query.where(Account.platform == platform)
        if status:
            query = query.where(Account.status == status)
            count_query = count_query.where(Account.status == status)
        if search:
            pattern = f"%{search}%"
            query = query.where(Account.email.ilike(pattern) | Account.display_name.ilike(pattern))
            count_query = count_query.where(
                Account.email.ilike(pattern) | Account.display_name.ilike(pattern)
            )

        total = (await self._session.execute(count_query)).scalar() or 0
        offset = (page - 1) * page_size
        query = query.order_by(Account.created_at.desc()).offset(offset).limit(page_size)
        result = await self._session.execute(query)
        items = [AccountResponse.model_validate(a) for a in result.scalars().all()]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size if total > 0 else 0,
        )

    async def update(self, account_id: int, data: AccountUpdate) -> Account:
        account = await self.get(account_id)
        if not account:
            raise ValueError("Account not found")

        if data.status and data.status != account.status:
            old_status = account.status
            account.status = data.status
            await self._record_status_change(account_id, old_status, data.status, "Manual update")

        if data.display_name is not None:
            account.display_name = data.display_name
        if data.notes is not None:
            account.notes = data.notes

        await self._session.commit()
        return account

    async def delete(self, account_id: int) -> None:
        account = await self.get(account_id)
        if not account:
            raise ValueError("Account not found")
        await self._session.delete(account)
        await self._session.commit()

    async def bulk_delete(self, account_ids: list[int]) -> int:
        count = 0
        for aid in account_ids:
            account = await self.get(aid)
            if account:
                await self._session.delete(account)
                count += 1
        await self._session.commit()
        return count

    async def preview_import(
        self, platform: AccountPlatform, raw_text: str
    ) -> AccountImportPreview:
        lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]
        valid = []
        invalid_lines = []
        seen_emails: set[str] = set()

        for line in lines:
            email = self._extract_email(line)
            if not email:
                invalid_lines.append(line[:80])
                continue
            if email in seen_emails:
                continue
            seen_emails.add(email)
            valid.append(email)

        existing_result = await self._session.execute(
            select(Account.email).where(
                Account.platform == platform,
                Account.email.in_(valid),
            )
        )
        existing_emails = {r[0] for r in existing_result.all()}
        new_emails = [e for e in valid if e not in existing_emails]

        return AccountImportPreview(
            total_parsed=len(lines),
            valid_count=len(new_emails),
            duplicate_count=len(valid) - len(new_emails),
            invalid_count=len(invalid_lines),
            invalid_lines=invalid_lines[:50],
            preview_items=[],
        )

    async def commit_import(
        self, platform: AccountPlatform, raw_text: str
    ) -> dict:
        preview = await self.preview_import(platform, raw_text)
        lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]
        imported = 0
        seen: set[str] = set()

        for line in lines:
            email = self._extract_email(line)
            if not email or email in seen:
                continue
            seen.add(email)

            existing = await self._session.execute(
                select(Account).where(
                    Account.platform == platform, Account.email == email
                )
            )
            if existing.scalar_one_or_none():
                continue

            status = AccountStatus.UNVERIFIED if platform == AccountPlatform.TWITCH else AccountStatus.DRAFT
            account = Account(platform=platform, email=email, status=status)
            self._session.add(account)
            imported += 1

        await self._session.commit()
        return {"imported": imported, "duplicates": preview.duplicate_count, "invalid": preview.invalid_count}

    async def get_status_history(self, account_id: int) -> list[AccountStatusHistory]:
        result = await self._session.execute(
            select(AccountStatusHistory)
            .where(AccountStatusHistory.account_id == account_id)
            .order_by(AccountStatusHistory.created_at.desc())
        )
        return list(result.scalars().all())

    async def export_csv(self, platform: AccountPlatform | None = None) -> str:
        query = select(Account)
        if platform:
            query = query.where(Account.platform == platform)
        result = await self._session.execute(query.order_by(Account.created_at.desc()))
        accounts = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "platform", "email", "status", "display_name", "created_at"])
        for a in accounts:
            row = [a.id, a.platform.value, a.email, a.status.value, a.display_name or "", a.created_at.isoformat()]
            safe_row = [self._csv_safe(str(c)) for c in row]
            writer.writerow(safe_row)
        return output.getvalue()

    async def _record_status_change(
        self,
        account_id: int,
        old_status: AccountStatus | None,
        new_status: AccountStatus,
        reason: str,
    ) -> None:
        history = AccountStatusHistory(
            account_id=account_id,
            old_status=old_status.value if old_status else None,
            new_status=new_status.value,
            reason=reason,
            correlation_id=generate_correlation_id(),
        )
        self._session.add(history)

    @staticmethod
    def _extract_email(line: str) -> str | None:
        parts = re.split(r"[:\t|,;]", line)
        for part in parts:
            part = part.strip().lower()
            if re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", part):
                return part
        return None

    @staticmethod
    def _csv_safe(value: str) -> str:
        if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + value
        return value
