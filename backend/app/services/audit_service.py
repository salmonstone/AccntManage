from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import generate_correlation_id
from backend.app.models.audit import AuditLog
from backend.app.models.enums import AuditAction

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log(
        self,
        action: AuditAction,
        entity_type: str | None = None,
        entity_id: int | None = None,
        details: str | None = None,
        correlation_id: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details[:2000] if details else None,
            correlation_id=correlation_id or generate_correlation_id(),
        )
        self._session.add(entry)
        await self._session.commit()
        return entry
