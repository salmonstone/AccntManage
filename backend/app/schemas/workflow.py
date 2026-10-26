from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import AccountPlatform


class WorkflowCreateRequest(BaseModel):
    platform: AccountPlatform
    account_id: int = Field(gt=0)
    context: dict[str, Any] = Field(default_factory=dict)


class WorkflowStepResultResponse(BaseModel):
    step: str
    description: str
    status: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    screenshot: str | None = None
    timestamp: str | None = None


class WorkflowResponse(BaseModel):
    id: int
    workflow_name: str
    platform: str
    account_id: int
    job_id: int | None = None
    status: str
    current_step_index: int
    total_steps: int
    step_results: list[WorkflowStepResultResponse] = Field(default_factory=list)
    error_message: str | None = None
    correlation_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
