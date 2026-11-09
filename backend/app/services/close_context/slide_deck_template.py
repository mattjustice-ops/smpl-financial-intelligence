"""Store and read the PowerPoint template a company uses for its board deck."""

from __future__ import annotations

import hashlib
import uuid
from io import BytesIO

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.slide_deck_template import SlideDeckTemplate

MAX_SLIDE_DECK_BYTES = 20 * 1024 * 1024


class SlideDeckRejected(Exception):
    """The upload is not a deck the close can keep."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def inspect_slide_deck(data: bytes, filename: str | None) -> dict[str, object]:
    """Open a .pptx and return the facts the warehouse row stores. Raises SlideDeckRejected."""
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not name.lower().endswith(".pptx"):
        raise SlideDeckRejected("The file needs to be a PowerPoint template (.pptx).")
    if not data:
        raise SlideDeckRejected("That file is empty.")
    if len(data) > MAX_SLIDE_DECK_BYTES:
        raise SlideDeckRejected("That deck is larger than 20 MB.")
    if data[:2] != b"PK":
        raise SlideDeckRejected("That file is not a PowerPoint deck.")

    from pptx import Presentation

    try:
        presentation = Presentation(BytesIO(data))
        slide_count = len(presentation.slides)
    except Exception as exc:
        raise SlideDeckRejected("That PowerPoint file could not be opened.") from exc
    if slide_count < 1:
        raise SlideDeckRejected("That deck has no slides.")
    return {
        "filename": name[:512],
        "byte_size": len(data),
        "slide_count": slide_count,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def active_slide_deck(db: Session, organization_id: uuid.UUID) -> SlideDeckTemplate | None:
    """The company's current deck, or None. File bytes stay unloaded until read."""
    return db.scalar(
        select(SlideDeckTemplate).where(
            SlideDeckTemplate.organization_id == organization_id,
            SlideDeckTemplate.status == "active",
        )
    )


def active_slide_deck_bytes(db: Session, organization_id: uuid.UUID) -> bytes | None:
    """Bytes of the active deck. This is what the close fill reads."""
    row = active_slide_deck(db, organization_id)
    if row is None:
        return None
    return row.content


def store_slide_deck(
    db: Session,
    organization_id: uuid.UUID,
    data: bytes,
    filename: str | None,
) -> SlideDeckTemplate:
    """Keep this deck as the company's active template. The previous active deck is replaced.

    Uploading the same file again returns the row already stored.
    """
    facts = inspect_slide_deck(data, filename)
    current = active_slide_deck(db, organization_id)
    if current is not None and current.sha256 == facts["sha256"]:
        return current

    db.execute(
        update(SlideDeckTemplate)
        .where(
            SlideDeckTemplate.organization_id == organization_id,
            SlideDeckTemplate.status == "active",
        )
        .values(status="replaced")
    )
    row = SlideDeckTemplate(
        organization_id=organization_id,
        filename=str(facts["filename"]),
        sha256=str(facts["sha256"]),
        byte_size=int(facts["byte_size"]),
        slide_count=int(facts["slide_count"]),
        status="active",
        content=data,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
