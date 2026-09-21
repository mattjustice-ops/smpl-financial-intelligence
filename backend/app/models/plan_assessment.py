"""Persisted Plan Assurance assessments — version-keyed, board-citable."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlanAssessment(Base):
    __tablename__ = "plan_assessments"

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
    budget_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("budget_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    forecast_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("forecast_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scenario: Mapped[str] = mapped_column(String(64), nullable=False, default="budget")
    period_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    budget_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    feasibility_verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    assessment: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    simulation_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    method_notes: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    prior_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mc_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    citation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
