"""Workflow API routes — create, list, get, cancel workflow executions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_session
from backend.app.schemas.workflow import WorkflowCreateRequest, WorkflowResponse
from backend.app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    req: WorkflowCreateRequest,
    session: AsyncSession = Depends(get_session),
):
    svc = WorkflowService(session)
    try:
        return await svc.create_and_enqueue(req.platform, req.account_id, req.context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=dict)
async def list_workflows(
    platform: str | None = Query(None),
    status: str | None = Query(None),
    account_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    svc = WorkflowService(session)
    return await svc.list_workflows(platform, status, account_id, page, page_size)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: int,
    session: AsyncSession = Depends(get_session),
):
    svc = WorkflowService(session)
    result = await svc.get(workflow_id)
    if not result:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return result


@router.post("/{workflow_id}/cancel", response_model=WorkflowResponse)
async def cancel_workflow(
    workflow_id: int,
    session: AsyncSession = Depends(get_session),
):
    svc = WorkflowService(session)
    try:
        return await svc.cancel(workflow_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
