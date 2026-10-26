from __future__ import annotations

from pydantic import BaseModel, Field


class AppSettingsResponse(BaseModel):
    max_worker_count: int
    max_queue_size: int
    job_timeout_seconds: int
    max_retries: int
    import_max_rows: int
    backup_retention_days: int
    theme: str = "light"


class AppSettingsUpdate(BaseModel):
    max_worker_count: int | None = Field(None, ge=1, le=16)
    max_queue_size: int | None = Field(None, ge=10, le=10000)
    job_timeout_seconds: int | None = Field(None, ge=30, le=3600)
    max_retries: int | None = Field(None, ge=0, le=10)
    import_max_rows: int | None = Field(None, ge=100, le=100000)
    backup_retention_days: int | None = Field(None, ge=1, le=365)
    theme: str | None = Field(None, max_length=20)
