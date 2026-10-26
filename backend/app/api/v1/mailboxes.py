from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.adapters.base import MailboxAdapter
from backend.app.adapters.live_mailbox import LiveMailboxAdapter
from backend.app.adapters.mock_mailbox import MockMailboxAdapter
from backend.app.core.config import settings
from backend.app.db.base import get_session
from backend.app.models.enums import AuditAction, MailboxStatus
from backend.app.schemas.common import PaginatedResponse, SuccessResponse
from backend.app.schemas.mailbox import (
    MailboxImportPreview,
    MailboxImportRequest,
    MailboxMessageResponse,
    MailboxResponse,
    MailboxSearchRequest,
)
from backend.app.services.audit_service import AuditService
from backend.app.services.mailbox_service import MailboxService

router = APIRouter(prefix="/mailboxes", tags=["Mailboxes"])


def _get_mailbox_service(session: AsyncSession) -> MailboxService:
    adapter: MailboxAdapter
    if settings.MSGRAPH_CLIENT_ID:
        adapter = LiveMailboxAdapter()
    else:
        adapter = MockMailboxAdapter()
    return MailboxService(session, adapter)


@router.get("", response_model=PaginatedResponse[MailboxResponse])
async def list_mailboxes(
    status: MailboxStatus | None = None,
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    svc = _get_mailbox_service(session)
    return await svc.list_mailboxes(status, page, page_size)


@router.get("/{mailbox_id}", response_model=MailboxResponse)
async def get_mailbox(mailbox_id: int, session: AsyncSession = Depends(get_session)):
    svc = _get_mailbox_service(session)
    mailbox = await svc.get(mailbox_id)
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    return MailboxResponse.model_validate(mailbox)


@router.post("/import/preview", response_model=MailboxImportPreview)
async def preview_import(
    data: MailboxImportRequest,
    session: AsyncSession = Depends(get_session),
):
    svc = _get_mailbox_service(session)
    return await svc.preview_import(data.raw_text, data.format_hint)


@router.post("/import/commit", response_model=SuccessResponse)
async def commit_import(
    data: MailboxImportRequest,
    session: AsyncSession = Depends(get_session),
):
    svc = _get_mailbox_service(session)
    result = await svc.commit_import(data.raw_text, data.format_hint)
    return SuccessResponse(message=f"Imported {result['imported']} mailboxes")


@router.post("/{mailbox_id}/validate")
async def validate_mailbox(mailbox_id: int, session: AsyncSession = Depends(get_session)):
    svc = _get_mailbox_service(session)
    try:
        return await svc.validate_mailbox(mailbox_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/search", response_model=list[MailboxMessageResponse])
async def search_messages(
    data: MailboxSearchRequest,
    session: AsyncSession = Depends(get_session),
):
    svc = _get_mailbox_service(session)
    try:
        messages = await svc.search_messages(
            data.mailbox_id, data.sender_filter, data.subject_filter, data.max_results
        )
        return [MailboxMessageResponse(**m) for m in messages]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{mailbox_id}/refresh")
async def refresh_mailbox_token(mailbox_id: int, session: AsyncSession = Depends(get_session)):
    svc = _get_mailbox_service(session)
    try:
        return await svc.refresh_token(mailbox_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{mailbox_id}/diagnostics")
async def mailbox_diagnostics(mailbox_id: int, session: AsyncSession = Depends(get_session)):
    svc = _get_mailbox_service(session)
    try:
        return await svc.diagnostics(mailbox_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{mailbox_id}/revoke", response_model=SuccessResponse)
async def revoke_mailbox(mailbox_id: int, session: AsyncSession = Depends(get_session)):
    svc = _get_mailbox_service(session)
    audit = AuditService(session)
    try:
        await svc.revoke(mailbox_id)
        await audit.log(AuditAction.MAILBOX_REVOKED, "mailbox", mailbox_id)
        return SuccessResponse(message="Mailbox token revoked")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{mailbox_id}", response_model=SuccessResponse)
async def delete_mailbox(
    mailbox_id: int,
    confirm: bool = Query(False),
    session: AsyncSession = Depends(get_session),
):
    if not confirm:
        raise HTTPException(status_code=400, detail="Destructive action requires confirm=true")
    svc = _get_mailbox_service(session)
    try:
        await svc.delete(mailbox_id)
        return SuccessResponse(message="Mailbox deleted")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
