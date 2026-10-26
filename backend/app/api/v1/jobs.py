from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_session
from backend.app.models.enums import AuditAction, JobStatus, JobType
from backend.app.schemas.common import PaginatedResponse, SuccessResponse
from backend.app.schemas.job import JobCreateRequest, JobResponse
from backend.app.services.audit_service import AuditService
from backend.app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(data: JobCreateRequest, session: AsyncSession = Depends(get_session)):
    svc = JobService(session)
    try:
        job = await svc.create(data.job_type, data.params)
        return JobResponse.model_validate(job)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=PaginatedResponse[JobResponse])
async def list_jobs(
    status: JobStatus | None = None,
    job_type: JobType | None = None,
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    svc = JobService(session)
    return await svc.list_jobs(status, job_type, page, page_size)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, session: AsyncSession = Depends(get_session)):
    svc = JobService(session)
    job = await svc.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(job_id: int, session: AsyncSession = Depends(get_session)):
    svc = JobService(session)
    audit = AuditService(session)
    try:
        job = await svc.cancel(job_id)
        await audit.log(AuditAction.JOB_CANCELLED, "job", job_id)
        return JobResponse.model_validate(job)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
