from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import ProxyProtocol, ProxyTestStatus


class ProxyCreate(BaseModel):
    protocol: ProxyProtocol
    host: str = Field(..., max_length=255)
    port: int = Field(..., ge=1, le=65535)
    username: str | None = Field(None, max_length=255)
    password: str | None = Field(None, max_length=255)
    label: str | None = Field(None, max_length=255)
    enabled: bool = True


class ProxyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    protocol: ProxyProtocol
    host: str
    port: int
    username: str | None
    label: str | None
    enabled: bool
    test_status: ProxyTestStatus
    last_test_at: datetime | None
    last_latency_ms: float | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class ProxyImportRequest(BaseModel):
    raw_text: str = Field(..., max_length=500_000)
    default_protocol: ProxyProtocol = ProxyProtocol.HTTP


class ProxyTestResult(BaseModel):
    proxy_id: int
    status: ProxyTestStatus
    latency_ms: float | None = None
    error: str | None = None
    ip_address: str | None = None
    dns_ok: bool | None = None
    tls_ok: bool | None = None
