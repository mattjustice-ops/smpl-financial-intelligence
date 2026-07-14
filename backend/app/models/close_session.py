"""Immutable close-session lineage per organization × reporting period (Close Peak §4E)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CloseSession(Base):
    """One lineage anchor per (organization, as_of_period) for a close cycle.

    Status advances with existing signals (validation / freeze). Calculation and
    narrative stages remain reserved until Close Ready Phase 2 / Class 2.
    Customer Close Workflow denorm: workflow_state + lock_version + certified_at.
    """

    __tablename__ = "close_sessions"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "as_of_period",
            name="uq_close_sessions_org_period",
        ),
    )

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
    as_of_period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    # open | validation_complete | freeze_complete | archived
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    # Customer Close Workflow state machine (see docs/CUSTOMER_CLOSE_WORKFLOW.md)
    workflow_state: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="OPEN",
        index=True,
    )
    current_lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    certified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
