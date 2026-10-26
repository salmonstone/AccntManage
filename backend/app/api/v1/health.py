from __future__ import annotations

import platform
import sys
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.db.base import get_session
from backend.app.models.enums import ProviderStatus

router = APIRouter(prefix="/health", tags=["Health"])


def _resolve_provider_status(provider: str) -> ProviderStatus:
    if provider == "sms":
        if not settings.SMS_PROVIDER_API_KEY:
            return ProviderStatus.MOCK_ONLY if settings.SMS_PROVIDER_NAME else ProviderStatus.UNCONFIGURED
        return ProviderStatus.CONFIGURED_NOT_TESTED
    if provider == "captcha":
        if not settings.CAPTCHA_SOLVE_ENABLED:
            return ProviderStatus.DISABLED
        key_map = {
            "capsolver": settings.CAPSOLVER_API_KEY,
            "anticaptcha": settings.ANTICAPTCHA_API_KEY,
            "twocaptcha": settings.TWOCAPTCHA_API_KEY,
            "ezcaptcha": settings.EZCAPTCHA_API_KEY,
        }
        active_key = key_map.get(settings.CAPTCHA_PROVIDER, "")
        if not active_key:
            return ProviderStatus.UNCONFIGURED
        return ProviderStatus.CONFIGURED_NOT_TESTED
    if provider == "msgraph":
        if not settings.MSGRAPH_CLIENT_ID or not settings.MSGRAPH_TENANT_ID:
            return ProviderStatus.UNCONFIGURED
        return ProviderStatus.CONFIGURED_NOT_TESTED
    if provider == "browser":
        return ProviderStatus.CONFIGURED_NOT_TESTED
    return ProviderStatus.UNSUPPORTED


@router.get("")
async def health_check(session: AsyncSession = Depends(get_session)):
    db_ok = False
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    provider_statuses = {
        name: _resolve_provider_status(name).value
        for name in ("sms", "captcha", "msgraph", "browser")
    }
    mock_providers = {
        name: status in (ProviderStatus.MOCK_ONLY.value, ProviderStatus.UNCONFIGURED.value, ProviderStatus.DISABLED.value)
        for name, status in provider_statuses.items()
    }
    all_mock = all(mock_providers.values())

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "error",
        "timestamp": datetime.now(UTC).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "mock_mode": all_mock,
        "providers_mock": mock_providers,
        "provider_statuses": provider_statuses,
    }
