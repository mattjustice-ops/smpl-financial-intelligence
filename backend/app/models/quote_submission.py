"""Inbound quote request submissions from the marketing site."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QuoteSubmission(Base):
    __tablename__ = "quote_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    lead_score: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_package: Mapped[str] = mapped_column(String(64), nullable=False)
    hubspot_contact_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hubspot_company_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hubspot_deal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hubspot_sync_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    hubspot_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
