"""Frozen close-context packs — sectioned packs for Copilot / Prompt 5 (Rev 4 blob v1)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CloseContextBlob(Base):
    """One hot freeze pack per (organization, as_of_period).

    Completeness: only COMPLETE rows are served as authoritative. STALE means a prior
    COMPLETE pack is still readable but labeled — never serve partial builds.
    """

    __tablename__ = "close_context_blobs"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "as_of_period",
            name="uq_close_context_blobs_org_period",
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
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # COMPLETE | STALE — no "building" / partial served state
    sections_json: Mapped[dict[str, Any] | None] = mapped_column("sections", JSONB, nullable=True)
    context_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    built_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
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
