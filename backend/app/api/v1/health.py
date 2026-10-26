from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_session

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check(session: AsyncSession = Depends(get_session)):
    db_ok = False
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    from backend.app.core.config import settings

    providers_mock = {
        "sms": not bool(settings.SMS_PROVIDER_API_KEY),
        "captcha": not settings.CAPTCHA_SOLVE_ENABLED or not bool(settings.CAPSOLVER_API_KEY),
        "msgraph": not bool(settings.MSGRAPH_CLIENT_ID),
    }
    all_mock = all(providers_mock.values())

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "error",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "mock_mode": all_mock,
        "providers_mock": providers_mock,
    }
