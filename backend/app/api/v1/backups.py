from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_session
from backend.app.models.enums import AuditAction
from backend.app.schemas.common import SuccessResponse
from backend.app.services.audit_service import AuditService
from backend.app.services.backup_service import BackupService

router = APIRouter(prefix="/backups", tags=["Backups"])


@router.post("", response_model=SuccessResponse)
async def create_backup(session: AsyncSession = Depends(get_session)):
    svc = BackupService()
    audit = AuditService(session)
    try:
        name = await svc.create_backup()
        await audit.log(AuditAction.BACKUP_CREATED, "backup", details=name)
        return SuccessResponse(message=f"Backup created: {name}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_backups():
    svc = BackupService()
    return svc.list_backups()


@router.delete("/{backup_name}", response_model=SuccessResponse)
async def delete_backup(
    backup_name: str,
    confirm: bool = Query(False),
):
    if not confirm:
        raise HTTPException(status_code=400, detail="Destructive action requires confirm=true")
    svc = BackupService()
    try:
        svc.delete_backup(backup_name)
        return SuccessResponse(message=f"Backup deleted: {backup_name}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cleanup", response_model=SuccessResponse)
async def cleanup_backups():
    svc = BackupService()
    removed = svc.cleanup_old_backups()
    return SuccessResponse(message=f"Removed {removed} expired backups")
