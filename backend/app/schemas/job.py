from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.app.models.enums import JobStatus, JobType


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_type: JobType
    status: JobStatus
    progress: float
    total_items: int
    completed_items: int
    failed_items: int
    correlation_id: str
    error_message: str | None
    retry_count: int
    max_retries: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime


class JobCreateRequest(BaseModel):
    job_type: JobType
    params: dict | None = None
