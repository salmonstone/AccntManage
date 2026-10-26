from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_session
from backend.app.models.enums import ProxyTestStatus
from backend.app.schemas.common import PaginatedResponse, SuccessResponse
from backend.app.schemas.proxy import (
    ProxyCreate,
    ProxyImportRequest,
    ProxyResponse,
    ProxyTestResult,
)
from backend.app.services.proxy_service import ProxyService

router = APIRouter(prefix="/proxies", tags=["Proxies"])


@router.post("", response_model=ProxyResponse, status_code=201)
async def create_proxy(data: ProxyCreate, session: AsyncSession = Depends(get_session)):
    svc = ProxyService(session)
    try:
        proxy = await svc.create(data)
        return ProxyResponse.model_validate(proxy)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=PaginatedResponse[ProxyResponse])
async def list_proxies(
    status: ProxyTestStatus | None = None,
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    svc = ProxyService(session)
    return await svc.list_proxies(status, page, page_size)


@router.get("/{proxy_id}", response_model=ProxyResponse)
async def get_proxy(proxy_id: int, session: AsyncSession = Depends(get_session)):
    svc = ProxyService(session)
    proxy = await svc.get(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return ProxyResponse.model_validate(proxy)


@router.delete("/{proxy_id}", response_model=SuccessResponse)
async def delete_proxy(
    proxy_id: int,
    confirm: bool = Query(False),
    session: AsyncSession = Depends(get_session),
):
    if not confirm:
        raise HTTPException(status_code=400, detail="Destructive action requires confirm=true")
    svc = ProxyService(session)
    try:
        await svc.delete(proxy_id)
        return SuccessResponse(message="Proxy deleted")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{proxy_id}/test", response_model=ProxyTestResult)
async def test_proxy(proxy_id: int, session: AsyncSession = Depends(get_session)):
    svc = ProxyService(session)
    try:
        return await svc.test_proxy(proxy_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/import", response_model=SuccessResponse)
async def import_proxies(
    data: ProxyImportRequest,
    session: AsyncSession = Depends(get_session),
):
    svc = ProxyService(session)
    result = await svc.import_proxies(data.raw_text, data.default_protocol)
    return SuccessResponse(
        message=f"Imported {result['imported']} proxies ({result['skipped']} duplicates, {result['invalid']} invalid)"
    )
