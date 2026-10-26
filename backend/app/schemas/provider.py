from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import ProviderStatus, ProviderType


class ProviderConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_type: ProviderType
    status: ProviderStatus
    last_health_check_at: datetime | None
    last_health_error: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ProviderConfigUpdate(BaseModel):
    config_values: dict = Field(default_factory=dict)
    notes: str | None = Field(None, max_length=2000)


class ProviderHealthResult(BaseModel):
    provider_type: ProviderType
    status: ProviderStatus
    message: str
    is_mock: bool = False
