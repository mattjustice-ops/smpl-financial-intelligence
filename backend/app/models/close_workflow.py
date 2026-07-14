"""Close Workflow lineage tables — lock events and load receipts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CloseLockEvent(Base):
    """Append-only Lock / Reopen events on a Close Session (immutable versions)."""

    __tablename__ = "close_lock_events"
    __table_args__ = (
        UniqueConstraint(
            "close_session_id",
            "lock_version",
            "event_type",
            name="uq_close_lock_events_session_version_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    close_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("close_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    as_of_period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False)
    # lock | reopen
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    checklist_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class CloseLoadReceipt(Base):
    """Customer-visible load integrity receipt (staged / applied / rejected)."""

    __tablename__ = "close_load_receipts"

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
    close_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("close_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ingest_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingest_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    as_of_period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    rows_staged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_applied: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
