from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_session
from backend.app.models.enums import AccountPlatform, AccountStatus, AuditAction
from backend.app.schemas.account import (
    AccountCreate,
    AccountImportPreview,
    AccountImportRequest,
    AccountResponse,
    AccountStatusHistoryResponse,
    AccountUpdate,
)
from backend.app.schemas.common import (
    DestructivePreview,
    PaginatedResponse,
    SuccessResponse,
)
from backend.app.services.account_service import AccountService
from backend.app.services.audit_service import AuditService

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.post("", response_model=AccountResponse, status_code=201)
async def create_account(
    data: AccountCreate,
    session: AsyncSession = Depends(get_session),
):
    svc = AccountService(session)
    try:
        account = await svc.create(data)
        return AccountResponse.model_validate(account)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=PaginatedResponse[AccountResponse])
async def list_accounts(
    platform: AccountPlatform | None = None,
    status: AccountStatus | None = None,
    search: str | None = Query(None, max_length=200),
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    svc = AccountService(session)
    return await svc.list_accounts(platform, status, search, page, page_size)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int, session: AsyncSession = Depends(get_session)):
    svc = AccountService(session)
    account = await svc.get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return AccountResponse.model_validate(account)


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int,
    data: AccountUpdate,
    session: AsyncSession = Depends(get_session),
):
    svc = AccountService(session)
    try:
        account = await svc.update(account_id, data)
        return AccountResponse.model_validate(account)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{account_id}", response_model=SuccessResponse)
async def delete_account(
    account_id: int,
    confirm: bool = Query(False),
    session: AsyncSession = Depends(get_session),
):
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Destructive action requires confirm=true",
        )
    svc = AccountService(session)
    audit = AuditService(session)
    try:
        await svc.delete(account_id)
        await audit.log(AuditAction.ACCOUNT_DELETED, "account", account_id)
        return SuccessResponse(message="Account deleted")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bulk-delete", response_model=SuccessResponse)
async def bulk_delete_accounts(
    account_ids: list[int],
    confirm: bool = Query(False),
    session: AsyncSession = Depends(get_session),
):
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Destructive action requires confirm=true",
        )
    if len(account_ids) > 500:
        raise HTTPException(status_code=400, detail="Max 500 accounts per bulk delete")
    svc = AccountService(session)
    audit = AuditService(session)
    count = await svc.bulk_delete(account_ids)
    await audit.log(AuditAction.BULK_DELETE, "account", details=f"Deleted {count} accounts")
    return SuccessResponse(message=f"Deleted {count} accounts")


@router.post("/bulk-delete/preview", response_model=DestructivePreview)
async def preview_bulk_delete(
    account_ids: list[int],
    session: AsyncSession = Depends(get_session),
):
    return DestructivePreview(
        action="bulk_delete",
        affected_count=len(account_ids),
        affected_summary=f"This will permanently delete {len(account_ids)} account record(s).",
    )


@router.get("/{account_id}/history", response_model=list[AccountStatusHistoryResponse])
async def get_status_history(
    account_id: int,
    session: AsyncSession = Depends(get_session),
):
    svc = AccountService(session)
    history = await svc.get_status_history(account_id)
    return [AccountStatusHistoryResponse.model_validate(h) for h in history]


@router.post("/import/preview", response_model=AccountImportPreview)
async def preview_import(
    data: AccountImportRequest,
    session: AsyncSession = Depends(get_session),
):
    svc = AccountService(session)
    return await svc.preview_import(data.platform, data.raw_text)


@router.post("/import/commit", response_model=SuccessResponse)
async def commit_import(
    data: AccountImportRequest,
    session: AsyncSession = Depends(get_session),
):
    svc = AccountService(session)
    audit = AuditService(session)
    result = await svc.commit_import(data.platform, data.raw_text)
    await audit.log(
        AuditAction.ACCOUNT_IMPORTED,
        "account",
        details=f"Imported {result['imported']} {data.platform.value} accounts",
    )
    return SuccessResponse(
        message=f"Imported {result['imported']} accounts ({result['duplicates']} duplicates, {result['invalid']} invalid)"
    )


@router.get("/export/csv")
async def export_csv(
    platform: AccountPlatform | None = None,
    session: AsyncSession = Depends(get_session),
):
    svc = AccountService(session)
    csv_data = await svc.export_csv(platform)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=accounts_export.csv"},
    )
