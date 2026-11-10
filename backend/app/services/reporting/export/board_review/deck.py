"""Fill the bundled Board Operating Review and return the PowerPoint bytes."""

from __future__ import annotations

import io
import json
from pathlib import Path

from app.services.reporting.export.board_review.fill import Deck, fill
from app.services.reporting.export.board_review.from_bundle import review_input
from app.services.reporting.export.schemas import ReportingBundle

_HERE = Path(__file__).resolve().parent


def build_named_slot_deck(
    bundle: ReportingBundle, *, finalized: bool = False, ts_data: dict | None = None
) -> tuple[bytes, str] | None:
    """Bytes of the filled deck, or None when the bundle has no close-month P&L."""
    payload = review_input(bundle, finalized=finalized, ts_data=ts_data)
    if payload is None:
        return None
    reg = json.loads((_HERE / "slots.json").read_text(encoding="utf-8"))
    deck = Deck(str(_HERE / "template.pptx"), reg)
    fill(deck, payload)
    buf = io.BytesIO()
    deck.prs.save(buf)
    return buf.getvalue(), "named_slots"
