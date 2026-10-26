from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, le=10000)
    page_size: int = Field(25, ge=1, le=100)


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    correlation_id: str | None = None


class SuccessResponse(BaseModel):
    message: str
    correlation_id: str | None = None


class DestructivePreview(BaseModel):
    action: str
    affected_count: int
    affected_summary: str
    requires_confirmation: bool = True
