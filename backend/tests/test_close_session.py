"""Close Session lineage + Month-End Readiness aggregator tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.close_session import CloseSession
from app.models.organization import Organization
from app.services.close_context.close_session_service import (
    advance_close_session_status,
    build_org_close_readiness,
    get_or_create_close_session,
    mark_freeze_complete,
    mark_validation_complete,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Organization.__table__,
            CloseSession.__table__,
        ],
    )
    factory = sessionmaker(bind=engine)
    session = factory()
    yield session
    session.close()


def test_get_or_create_close_session_is_idempotent(db_session) -> None:
    org = Organization(id=uuid.uuid4(), name="Close Sess Co", status="active")
    db_session.add(org)
    db_session.commit()

    first = get_or_create_close_session(db_session, org.id, "2026-06")
    db_session.commit()
    second = get_or_create_close_session(db_session, org.id, "2026-06")
    assert first.id == second.id
    assert first.status == "open"


def test_close_session_status_advances_monotonically(db_session) -> None:
    org = Organization(id=uuid.uuid4(), name="Advance Co", status="active")
    db_session.add(org)
    db_session.commit()

    mark_validation_complete(db_session, org.id, "2026-06", validation_status="pass")
    row = get_or_create_close_session(db_session, org.id, "2026-06")
    assert row.status == "validation_complete"

    mark_freeze_complete(db_session, org.id, "2026-06")
    assert row.status == "freeze_complete"

    # Never regress.
    advance_close_session_status(db_session, org.id, "2026-06", target_status="open")
    assert row.status == "freeze_complete"


def test_close_ready_phase1_requires_validation_and_complete_freeze() -> None:
    org_id = uuid.uuid4()
    session_row = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=org_id,
        as_of_period="2026-06",
        status="open",
        workflow_state="OPEN",
        current_lock_version=0,
        certified_at=None,
    )
    blob = SimpleNamespace(
        status="COMPLETE",
        validation_status="pass",
        built_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
        metadata_json={"validation_check_ids": ["cash_bridge_bs", "deferred_revenue"]},
    )
    db = MagicMock()

    def _scalars(stmt):  # noqa: ANN001
        result = MagicMock()
        # First call path in build: CloseSession lookup via get_or_create → existing
        # We short-circuit by making get_or_create see existing session.
        sql = str(stmt)
        if "close_sessions" in sql.lower() or "CloseSession" in sql:
            result.first.return_value = session_row
        else:
            result.first.return_value = blob
        result.all.return_value = []
        return result

    db.scalars.side_effect = _scalars
    db.get.return_value = None

    readiness = build_org_close_readiness(
        db,
        org_id,
        as_of_period="2026-06",
        organization_name="Ready Co",
        plan="growth",
        ensure_session=True,
    )
    assert readiness["close_ready_phase1"] is True
    assert readiness["freeze_status"] == "COMPLETE"
    assert readiness["trust_status"] == "verified"
    assert readiness["close_session_id"] == str(session_row.id)
    assert readiness["calculation_status"] == "not_applicable"
    assert readiness["validation_check_ids"] == ["cash_bridge_bs", "deferred_revenue"]
    assert readiness["prompt5_deck_runs_used"] == 0
    assert readiness["prompt5_deck_runs_limit"] >= 1
    assert readiness["prompt5_deck_runs_remaining"] == readiness["prompt5_deck_runs_limit"]
    assert session_row.status == "freeze_complete"
