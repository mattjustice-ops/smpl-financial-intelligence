"""Unit tests for freeze blob serve/stale rules (no warehouse required)."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.close_context.freeze_blob_service import FreezeContext, get_servable_freeze


def test_freeze_context_as_of_iso() -> None:
    built = datetime(2026, 7, 13, 13, 2, tzinfo=timezone.utc)
    ctx = FreezeContext(
        organization_id=__import__("uuid").uuid4(),
        as_of_period="2026-06",
        status="COMPLETE",
        context_text="ARR section…",
        built_at=built,
    )
    assert ctx.context_as_of_iso.startswith("2026-07-13T13:02:00")
    assert ctx.stale is False


def test_get_servable_freeze_none_when_empty() -> None:
    db = MagicMock()
    db.scalars.return_value.first.return_value = None
    assert get_servable_freeze(db, __import__("uuid").uuid4(), "2026-06") is None


def test_get_servable_freeze_marks_stale() -> None:
    built = datetime(2026, 7, 12, 6, 0, tzinfo=timezone.utc)
    row = SimpleNamespace(
        status="STALE",
        context_text="prior COMPLETE text",
        built_at=built,
        validation_status="pass",
        sections_json={"arr": True},
    )
    db = MagicMock()
    db.scalars.return_value.first.return_value = row
    org_id = __import__("uuid").uuid4()
    freeze = get_servable_freeze(db, org_id, "2026-06")
    assert freeze is not None
    assert freeze.stale is True
    assert freeze.status == "STALE"
    assert freeze.context_text == "prior COMPLETE text"
    assert freeze.source == "freeze"
