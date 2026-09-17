"""Validation Engine Allow + mapping queue + import hard-ID (unit, no Postgres JSONB)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services import validation_engine as ve


def _blob(sections: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        status="COMPLETE",
        sections_json=dict(sections or {"kpis": True}),
        built_at=datetime.now(timezone.utc),
        updated_at=None,
    )


def _db_with_blob(blob: SimpleNamespace) -> MagicMock:
    db = MagicMock()
    db.scalars.return_value.first.return_value = blob

    def _commit():
        pass

    def _refresh(_row):
        pass

    def _add(_row):
        pass

    db.commit.side_effect = _commit
    db.refresh.side_effect = _refresh
    db.add.side_effect = _add
    return db


def test_mapping_queue_blocks_allow_and_import_gate() -> None:
    org_id = uuid.uuid4()
    blob = _blob()
    db = _db_with_blob(blob)

    ve.seed_demo_mapping_queue_if_empty(db, org_id, "2026-06")
    status = ve.get_validation_status(db, org_id, "2026-06")
    assert status["mapping_material_open_count"] >= 1
    assert status["import_hard_id_blocked"] is True

    with pytest.raises(ValueError, match="mapping_queue_open"):
        ve.record_allow(db, org_id, "2026-06", allowed_by="Test Owner")

    with pytest.raises(ValueError, match="validation_engine_mapping_open"):
        ve.assert_import_mapping_clear(db, org_id, "2026-06", fail_closed=True)

    for item in list(status["mapping_queue"]):
        if item.get("status") == "open":
            ve.map_account(
                db,
                org_id,
                "2026-06",
                account_id=item["account_id"],
                mapped_to=item.get("statement_hint") or "ga",
                mapped_by="Test Owner",
            )

    clear = ve.get_validation_status(db, org_id, "2026-06")
    assert clear["mapping_material_open_count"] == 0
    assert clear["import_hard_id_blocked"] is False

    allowed = ve.record_allow(
        db, org_id, "2026-06", allowed_by="Test Owner", notes="Monthly Align"
    )
    assert allowed["allowed"] is True
    assert allowed["monthly_align"]["ready_for_board"] is True


def test_upsert_preserves_mapped_status() -> None:
    org_id = uuid.uuid4()
    blob = _blob()
    db = _db_with_blob(blob)
    ve.upsert_mapping_queue(
        db,
        org_id,
        "2026-06",
        [{"account_id": "9001", "name": "Temp", "amount": 10.0, "status": "open"}],
    )
    ve.map_account(db, org_id, "2026-06", account_id="9001", mapped_to="rd", mapped_by="A")
    ve.upsert_mapping_queue(
        db,
        org_id,
        "2026-06",
        [{"account_id": "9001", "name": "Temp", "amount": 12.0}],
    )
    status = ve.get_validation_status(db, org_id, "2026-06")
    row = next(q for q in status["mapping_queue"] if q["account_id"] == "9001")
    assert row["status"] == "mapped"
    assert row["mapped_to"] == "rd"
    assert row["amount"] == 12.0


def test_management_lines_include_statements() -> None:
    assert "deferred_revenue" in ve.MANAGEMENT_LINES
    assert "arr_bridge" in ve.MANAGEMENT_LINES
