"""Company board-deck templates stored with the close."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, deferred, mapped_column

from app.db.base import Base


class SlideDeckTemplate(Base):
    """One company's PowerPoint template. Only one row per company stays active.

    The file bytes are deferred so a listing does not pull the deck. The close
    fill reads the active row when it builds that company's board deck.
    """

    __tablename__ = "slide_deck_templates"

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
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    slide_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # active | replaced
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    content: Mapped[bytes] = deferred(mapped_column(LargeBinary, nullable=False))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
