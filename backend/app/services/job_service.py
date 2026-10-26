from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.security import generate_correlation_id
from backend.app.models.enums import JobStatus, JobType
from backend.app.models.job import Job
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.job import JobResponse

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.TIMED_OUT}


class JobService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        job_type: JobType,
        params: dict | None = None,
        idempotency_key: str | None = None,
    ) -> Job:
        if idempotency_key:
            existing = await self._session.execute(
                select(Job).where(Job.idempotency_key == idempotency_key)
            )
            found = existing.scalar_one_or_none()
            if found:
                return found

        queued_count = (
            await self._session.execute(
                select(func.count(Job.id)).where(
                    Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING])
                )
            )
        ).scalar() or 0

        if queued_count >= settings.MAX_QUEUE_SIZE:
            raise ValueError(f"Job queue full ({settings.MAX_QUEUE_SIZE} jobs)")

        job = Job(
            job_type=job_type,
            status=JobStatus.QUEUED,
            correlation_id=generate_correlation_id(),
            idempotency_key=idempotency_key,
            params_json=json.dumps(params) if params else None,
            max_retries=settings.MAX_RETRIES,
        )
        self._session.add(job)
        await self._session.commit()
        return job

    async def get(self, job_id: int) -> Job | None:
        result = await self._session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        status: JobStatus | None = None,
        job_type: JobType | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> PaginatedResponse[JobResponse]:
        query = select(Job)
        count_query = select(func.count(Job.id))

        if status:
            query = query.where(Job.status == status)
            count_query = count_query.where(Job.status == status)
        if job_type:
            query = query.where(Job.job_type == job_type)
            count_query = count_query.where(Job.job_type == job_type)

        total = (await self._session.execute(count_query)).scalar() or 0
        offset = (page - 1) * page_size
        result = await self._session.execute(
            query.order_by(Job.created_at.desc()).offset(offset).limit(page_size)
        )
        items = [JobResponse.model_validate(j) for j in result.scalars().all()]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size if total > 0 else 0,
        )

    async def cancel(self, job_id: int) -> Job:
        job = await self.get(job_id)
        if not job:
            raise ValueError("Job not found")
        if job.status in TERMINAL_STATUSES:
            raise ValueError(f"Cannot cancel job in {job.status.value} state")
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now(UTC)
        await self._session.commit()
        return job

    async def update_progress(
        self,
        job_id: int,
        progress: float,
        completed_items: int | None = None,
        failed_items: int | None = None,
    ) -> None:
        job = await self.get(job_id)
        if not job or job.status in TERMINAL_STATUSES:
            return
        job.progress = max(job.progress, min(progress, 100.0))
        if completed_items is not None:
            job.completed_items = completed_items
        if failed_items is not None:
            job.failed_items = failed_items
        await self._session.commit()

    async def mark_running(self, job_id: int) -> None:
        job = await self.get(job_id)
        if not job or job.status != JobStatus.QUEUED:
            return
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        await self._session.commit()

    async def mark_completed(self, job_id: int, result_data: dict | None = None) -> None:
        job = await self.get(job_id)
        if not job:
            return
        job.status = JobStatus.COMPLETED
        job.progress = 100.0
        job.completed_at = datetime.now(UTC)
        if result_data:
            job.result_json = json.dumps(result_data)
        await self._session.commit()

    async def mark_failed(self, job_id: int, error: str) -> None:
        job = await self.get(job_id)
        if not job:
            return
        job.status = JobStatus.FAILED
        job.error_message = error[:2000]
        job.completed_at = datetime.now(UTC)
        await self._session.commit()

    async def recover_interrupted(self) -> int:
        result = await self._session.execute(
            select(Job).where(Job.status == JobStatus.RUNNING)
        )
        jobs = result.scalars().all()
        count = 0
        for job in jobs:
            job.status = JobStatus.INTERRUPTED
            job.error_message = "Interrupted by server restart"
            count += 1
        await self._session.commit()
        return count
