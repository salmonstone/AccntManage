from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.db.base import get_session
from backend.app.models.audit import AppSetting
from backend.app.models.enums import AuditAction
from backend.app.schemas.settings import AppSettingsResponse, AppSettingsUpdate
from backend.app.services.audit_service import AuditService

router = APIRouter(prefix="/settings", tags=["Settings"])


async def _get_setting(session: AsyncSession, key: str, default: str) -> str:
    result = await session.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else default


async def _set_setting(session: AsyncSession, key: str, value: str) -> None:
    result = await session.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
    else:
        session.add(AppSetting(key=key, value=value))


@router.get("", response_model=AppSettingsResponse)
async def get_settings(session: AsyncSession = Depends(get_session)):
    return AppSettingsResponse(
        max_worker_count=int(await _get_setting(session, "max_worker_count", str(settings.MAX_WORKER_COUNT))),
        max_queue_size=int(await _get_setting(session, "max_queue_size", str(settings.MAX_QUEUE_SIZE))),
        job_timeout_seconds=int(await _get_setting(session, "job_timeout_seconds", str(settings.JOB_TIMEOUT_SECONDS))),
        max_retries=int(await _get_setting(session, "max_retries", str(settings.MAX_RETRIES))),
        import_max_rows=int(await _get_setting(session, "import_max_rows", str(settings.IMPORT_MAX_ROWS))),
        backup_retention_days=int(await _get_setting(session, "backup_retention_days", str(settings.BACKUP_RETENTION_DAYS))),
        theme=await _get_setting(session, "theme", "light"),
    )


@router.patch("", response_model=AppSettingsResponse)
async def update_settings(
    data: AppSettingsUpdate,
    session: AsyncSession = Depends(get_session),
):
    audit = AuditService(session)
    changes = []

    for field_name, value in data.model_dump(exclude_none=True).items():
        await _set_setting(session, field_name, str(value))
        changes.append(f"{field_name}={value}")

    if changes:
        await audit.log(
            AuditAction.SETTING_CHANGED,
            "settings",
            details="; ".join(changes),
        )

    await session.commit()
    return await get_settings(session)
