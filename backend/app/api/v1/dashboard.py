from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_session
from backend.app.schemas.dashboard import DashboardMetrics, RecentActivity
from backend.app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/metrics", response_model=DashboardMetrics)
async def get_metrics(session: AsyncSession = Depends(get_session)):
    svc = DashboardService(session)
    return await svc.get_metrics()


@router.get("/activity", response_model=list[RecentActivity])
async def get_recent_activity(
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    if limit > 100:
        limit = 100
    svc = DashboardService(session)
    return await svc.get_recent_activity(limit)
