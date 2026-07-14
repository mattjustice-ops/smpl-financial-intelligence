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


def test_should_auto_freeze_for_validation() -> None:
    from app.services.close_context.freeze_blob_service import should_auto_freeze_for_validation

    assert should_auto_freeze_for_validation("pass") is True
    assert should_auto_freeze_for_validation("warning") is True
    assert should_auto_freeze_for_validation("fail") is False
    assert should_auto_freeze_for_validation(None) is False


def test_schedule_auto_freeze_skips_fail_without_thread() -> None:
    from app.services.close_context.freeze_blob_service import schedule_auto_freeze_after_validation

    db = MagicMock()
    queued = schedule_auto_freeze_after_validation(
        db,
        __import__("uuid").uuid4(),
        validation_status="fail",
        as_of_period="2026-06",
        start_period="2026-01",
        end_period="2026-06",
    )
    assert queued is False


def test_prewarm_isolates_per_org_failures(monkeypatch) -> None:
    """One failing org must not abort the batch."""
    import uuid

    from app.services.close_context import freeze_blob_service as fbs

    org_ok = SimpleNamespace(id=uuid.uuid4(), name="OK Co", status="active", close_month="2026-06")
    org_bad = SimpleNamespace(id=uuid.uuid4(), name="Bad Co", status="active", close_month="2026-06")

    db = MagicMock()
    db.scalars.return_value.all.return_value = [org_ok, org_bad]

    def _window(_db, org):  # noqa: ANN001
        return ("2026-06", "2026-01", "2026-06")

    calls: list[uuid.UUID] = []

    def _build(_db, organization_id, **kwargs):  # noqa: ANN001
        calls.append(organization_id)
        if organization_id == org_bad.id:
            raise RuntimeError("warehouse down")
        return FreezeContext(
            organization_id=organization_id,
            as_of_period="2026-06",
            status="COMPLETE",
            context_text="ok",
            built_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
            validation_status="pass",
        )

    monkeypatch.setattr(
        "app.services.reporting.org_reporting_settings.resolve_org_reporting_window",
        _window,
    )
    monkeypatch.setattr(fbs, "build_and_store_freeze_blob", _build)

    payload = fbs.prewarm_freeze_blobs(db, dry_run=False)
    assert payload["total"] == 2
    assert payload["succeeded"] == 1
    assert payload["failed"] == 1
    assert payload["ok"] is False
    assert len(calls) == 2
    assert {r["status"] for r in payload["results"]} == {"complete", "failed"}


def test_prewarm_dry_run_does_not_build(monkeypatch) -> None:
    import uuid

    from app.services.close_context import freeze_blob_service as fbs

    org = SimpleNamespace(id=uuid.uuid4(), name="Dry Co", status="active", close_month="2026-06")
    db = MagicMock()
    db.scalars.return_value.all.return_value = [org]

    monkeypatch.setattr(
        "app.services.reporting.org_reporting_settings.resolve_org_reporting_window",
        lambda _db, _org: ("2026-06", "2026-01", "2026-06"),
    )

    def _boom(*_a, **_k):  # noqa: ANN001
        raise AssertionError("build must not run in dry_run")

    monkeypatch.setattr(fbs, "build_and_store_freeze_blob", _boom)
    payload = fbs.prewarm_freeze_blobs(db, dry_run=True)
    assert payload["succeeded"] == 1
    assert payload["failed"] == 0
    assert payload["results"][0]["status"] == "dry_run"
