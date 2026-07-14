"""Unit tests for Customer Close Workflow Ready-to-Lock + Lock gate."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.close_context.close_workflow_service import (
    build_lock_checklist,
    derive_workflow_state,
    lock_close,
)


def test_checklist_blocks_without_successful_loads() -> None:
    db = MagicMock()
    db.scalars.return_value.all.return_value = []
    checklist = build_lock_checklist(db, uuid.uuid4(), "2026-06")
    assert checklist["ready_to_lock"] is False
    assert any("No successful data load" in b for b in checklist["blockers"])


def test_checklist_ready_with_successful_receipt() -> None:
    receipt = SimpleNamespace(
        rows_applied=1000,
        rows_rejected=0,
        status="complete",
        entity_type="gl_actuals",
    )
    db = MagicMock()
    db.scalars.return_value.all.return_value = [receipt]
    # Second scalars call in build_lock_checklist is freeze blob probe
    blob_empty = MagicMock()
    blob_empty.first.return_value = None

    def _scalars(stmt):  # noqa: ANN001
        sql = str(stmt).lower()
        result = MagicMock()
        if "close_load_receipts" in sql or "closeloadreceipt" in sql:
            result.all.return_value = [receipt]
        else:
            result.first.return_value = None
            result.all.return_value = []
        return result

    db.scalars.side_effect = _scalars
    checklist = build_lock_checklist(db, uuid.uuid4(), "2026-06")
    assert checklist["ready_to_lock"] is True
    assert checklist["blockers"] == []


def test_derive_ready_to_lock_state() -> None:
    session = SimpleNamespace(workflow_state="LOADING_DATA", current_lock_version=0, certified_at=None)
    checklist = {"ready_to_lock": True, "receipt_count": 1, "items": []}
    assert derive_workflow_state(session, checklist, "missing") == "READY_TO_LOCK"


def test_lock_close_refuses_when_not_ready() -> None:
    org_id = uuid.uuid4()
    org = SimpleNamespace(id=org_id, name="Test", close_month="2026-06")
    session = SimpleNamespace(
        id=uuid.uuid4(),
        workflow_state="LOADING_DATA",
        current_lock_version=0,
        certified_at=None,
        status="open",
        updated_at=None,
    )
    db = MagicMock()
    db.get.return_value = org

    with (
        patch(
            "app.services.reporting.org_reporting_settings.resolve_org_reporting_window",
            return_value=("2026-06", "2026-01", "2026-06"),
        ),
        patch(
            "app.services.close_context.close_workflow_service.get_or_create_close_session",
            return_value=session,
        ),
        patch(
            "app.services.close_context.close_workflow_service.build_lock_checklist",
            return_value={"ready_to_lock": False, "blockers": ["No successful data load"], "items": []},
        ),
    ):
        result = lock_close(db, org_id, run_freeze=False)
    assert result["ok"] is False
    assert result["code"] == "not_ready_to_lock"


def test_lock_close_records_version_without_freeze() -> None:
    org_id = uuid.uuid4()
    org = SimpleNamespace(id=org_id, name="Test", close_month="2026-06")
    session = SimpleNamespace(
        id=uuid.uuid4(),
        workflow_state="READY_TO_LOCK",
        current_lock_version=0,
        certified_at=None,
        status="open",
        updated_at=None,
    )
    db = MagicMock()
    db.get.return_value = org

    with (
        patch(
            "app.services.reporting.org_reporting_settings.resolve_org_reporting_window",
            return_value=("2026-06", "2026-01", "2026-06"),
        ),
        patch(
            "app.services.close_context.close_workflow_service.get_or_create_close_session",
            return_value=session,
        ),
        patch(
            "app.services.close_context.close_workflow_service.build_lock_checklist",
            return_value={"ready_to_lock": True, "blockers": [], "items": []},
        ),
    ):
        result = lock_close(db, org_id, run_freeze=False, locked_by="tester")
    assert result["ok"] is True
    assert result["lock_version"] == 1
    assert session.current_lock_version == 1
    assert session.workflow_state == "LOCKED"
    db.add.assert_called()
    db.commit.assert_called()
