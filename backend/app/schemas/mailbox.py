from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import MailboxStatus


class MailboxResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    status: MailboxStatus
    token_expires_at: datetime | None
    scopes: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class MailboxImportRequest(BaseModel):
    raw_text: str = Field(..., max_length=500_000)
    format_hint: str | None = Field(None, max_length=50)


class MailboxImportPreview(BaseModel):
    total_parsed: int
    valid_count: int
    duplicate_count: int
    invalid_count: int
    invalid_lines: list[str] = Field(default_factory=list, max_length=50)


class MailboxSearchRequest(BaseModel):
    mailbox_id: int
    sender_filter: str | None = Field(None, max_length=320)
    subject_filter: str | None = Field(None, max_length=500)
    max_results: int = Field(25, ge=1, le=100)


class MailboxMessageResponse(BaseModel):
    message_id: str
    sender: str
    subject: str
    received_at: datetime
    body_preview: str
    is_mock: bool = False
