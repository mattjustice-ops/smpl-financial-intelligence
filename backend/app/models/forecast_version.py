"""Forecast version registry — draft/final lifecycle for rolling forecasts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ForecastVersion(Base):
    __tablename__ = "forecast_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    horizon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    as_of_period: Mapped[str] = mapped_column(String(7), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    levers: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    req_active: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    results: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    table_manifest: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="forecast_versions",
        foreign_keys=[organization_id],
    )
