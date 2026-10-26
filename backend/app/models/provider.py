from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.models.enums import ProviderStatus, ProviderType


class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider_type: Mapped[ProviderType] = mapped_column(
        Enum(ProviderType), nullable=False, unique=True
    )
    status: Mapped[ProviderStatus] = mapped_column(
        Enum(ProviderStatus), nullable=False, default=ProviderStatus.UNCONFIGURED
    )
    encrypted_config_json: Mapped[str | None] = mapped_column(Text)
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_health_error: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
