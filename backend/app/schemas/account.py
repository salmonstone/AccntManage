from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.models.enums import AccountPlatform, AccountStatus


class AccountCreate(BaseModel):
    platform: AccountPlatform
    email: str = Field(..., max_length=320)
    display_name: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=2000)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or len(v) < 5:
            raise ValueError("Invalid email format")
        return v


class AccountUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=2000)
    status: AccountStatus | None = None


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: AccountPlatform
    email: str
    status: AccountStatus
    display_name: str | None
    generated_password: str | None = None
    notes: str | None
    is_simulated: bool
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="wrap")
    @classmethod
    def _decrypt_credentials(cls, data, handler):
        obj = handler(data)
        creds = getattr(data, "credentials_enc", None) if hasattr(data, "credentials_enc") else None
        if creds:
            try:
                from backend.app.core.security import decrypt_value
                obj.generated_password = decrypt_value(creds)
            except Exception:
                obj.generated_password = None
        return obj


class AccountStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    old_status: str | None
    new_status: str
    reason: str | None
    correlation_id: str | None
    created_at: datetime


class AccountImportRequest(BaseModel):
    platform: AccountPlatform
    raw_text: str = Field(..., max_length=500_000)
    format_hint: str | None = Field(None, max_length=50)
    auto_workflow: bool = False


class AccountImportPreview(BaseModel):
    total_parsed: int
    valid_count: int
    duplicate_count: int
    invalid_count: int
    invalid_lines: list[str] = Field(default_factory=list, max_length=50)
    preview_items: list[AccountResponse] = Field(default_factory=list, max_length=25)
