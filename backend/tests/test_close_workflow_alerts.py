"""Tests for close-week Close Workflow Ops alerts."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.ops.close_workflow_alerts import assess_close_workflow_alerts


def test_detects_stuck_freezing() -> None:
    org_id = uuid.uuid4()
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    session = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=org_id,
        as_of_period="2026-06",
        workflow_state="FREEZING",
        current_lock_version=1,
        certified_at=None,
        updated_at=old,
        created_at=old,
    )
    org = SimpleNamespace(id=org_id, name="Stuck Co")
    db = MagicMock()

    def _scalars(stmt):  # noqa: ANN001
        result = MagicMock()
        sql = str(stmt).lower()
        if "close_sessions" in sql or "closesession" in sql:
            result.all.return_value = [session]
        else:
            result.all.return_value = [org]
        return result

    db.scalars.side_effect = _scalars
    payload = assess_close_workflow_alerts(db, freeze_stuck_minutes=30)
    assert payload["ok"] is False
    assert payload["summary"]["stuck_freezing"] == 1
    assert any(i["code"] == "freeze_stuck" for i in payload["issues"])
    assert any(not c["ok"] for c in payload["checks"] if c["name"] == "close_workflow_freeze_stuck")


def test_ready_to_lock_is_not_an_error() -> None:
    org_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    session = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=org_id,
        as_of_period="2026-06",
        workflow_state="READY_TO_LOCK",
        current_lock_version=0,
        certified_at=None,
        updated_at=now,
        created_at=now,
    )
    db = MagicMock()

    def _scalars(stmt):  # noqa: ANN001
        result = MagicMock()
        sql = str(stmt).lower()
        if "close_sessions" in sql or "closesession" in sql:
            result.all.return_value = [session]
        else:
            result.all.return_value = [SimpleNamespace(id=org_id, name="Ready Co")]
        return result

    db.scalars.side_effect = _scalars
    payload = assess_close_workflow_alerts(db)
    assert payload["ok"] is True
    assert payload["summary"]["ready_to_lock"] == 1
    assert payload["issues"] == []
