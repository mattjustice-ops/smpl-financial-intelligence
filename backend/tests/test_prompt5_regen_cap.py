"""Prompt 5 regenerate cap (per org × close period)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.organization import Organization
from app.models.usage_event import UsageEvent
from app.services.ops.usage_limits import assert_prompt5_regen_cap, count_mda_deck_runs_for_close


@pytest.fixture()
def db_session(monkeypatch):
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.ext.compiler import compiles

    @compiles(JSONB, "sqlite")
    def _compile_jsonb_sqlite(_type, compiler, **kw):  # noqa: ANN001
        return compiler.visit_JSON(_type, **kw)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Organization.__table__, UsageEvent.__table__],
    )
    factory = sessionmaker(bind=engine)
    session = factory()
    monkeypatch.setenv("SMPL_USAGE_LIMITS_ENABLED", "true")
    monkeypatch.setenv("SMPL_PROMPT5_DECK_PER_CLOSE", "2")
    # Clear settings cache if present
    try:
        from app.core.config import get_settings

        get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    yield session
    session.close()
    try:
        from app.core.config import get_settings

        get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass


def test_prompt5_regen_cap_allows_under_limit(db_session, monkeypatch) -> None:
    monkeypatch.setenv("SMPL_PROMPT5_DECK_PER_CLOSE", "3")
    try:
        from app.core.config import get_settings

        get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass

    org = Organization(id=uuid.uuid4(), name="Cap Co", status="active", plan="growth")
    db_session.add(org)
    db_session.add(
        UsageEvent(
            id=uuid.uuid4(),
            organization_id=org.id,
            event_type="export_start",
            feature="mda_deck",
            metadata_json={"as_of_period": "2026-06", "kind": "mda_deck"},
            created_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()
    assert count_mda_deck_runs_for_close(db_session, org.id, "2026-06") == 1
    assert_prompt5_regen_cap(db_session, org, "2026-06")  # should not raise


def test_prompt5_regen_cap_blocks_at_limit(db_session, monkeypatch) -> None:
    monkeypatch.setenv("SMPL_PROMPT5_DECK_PER_CLOSE", "2")
    try:
        from app.core.config import get_settings

        get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass

    org = Organization(id=uuid.uuid4(), name="Cap Co 2", status="active", plan="growth")
    db_session.add(org)
    for _ in range(2):
        db_session.add(
            UsageEvent(
                id=uuid.uuid4(),
                organization_id=org.id,
                event_type="export_start",
                feature="mda_deck",
                metadata_json={"as_of_period": "2026-06", "kind": "mda_deck"},
                created_at=datetime.now(timezone.utc),
            )
        )
    db_session.commit()
    with pytest.raises(HTTPException) as exc:
        assert_prompt5_regen_cap(db_session, org, "2026-06")
    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == "prompt5_regen_cap_exceeded"
