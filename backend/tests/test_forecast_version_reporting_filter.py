"""Reporting must not mix multiple forecast versions in forecast_* tables."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.forecast_version import ForecastVersion
from app.models.organization import Organization
from app.services.dashboard.query_utils import fetch_table_rows
from app.services.demo_csv.loader import promote_forecast_tables
from app.services.forecast_version_service import get_active_forecast_version


@pytest.fixture()
def db_session():
    from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
    from sqlalchemy.ext.compiler import compiles

    @compiles(JSONB, "sqlite")
    def _compile_jsonb_sqlite(_type, compiler, **kw):  # noqa: ANN001
        return compiler.visit_JSON(_type, **kw)

    @compiles(PG_UUID, "sqlite")
    def _compile_uuid_sqlite(_type, compiler, **kw):  # noqa: ANN001
        return "CHAR(36)"

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Organization.__table__, ForecastVersion.__table__],
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                create table forecast_mrr_waterfall (
                    organization_id text not null,
                    forecast_version_id text,
                    version text,
                    period text,
                    new_arr real
                )
                """
            )
        )
    factory = sessionmaker(bind=engine)
    session = factory()
    yield session
    session.close()


def test_fetch_table_rows_uses_active_forecast_version_only(db_session) -> None:
    org_id = uuid.uuid4()
    v1 = uuid.uuid4()
    v2 = uuid.uuid4()
    org = Organization(
        id=org_id,
        name="Version Co",
        status="active",
        plan="growth",
        active_forecast_version_id=v2,
    )
    db_session.add(org)
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            ForecastVersion(
                id=v1,
                organization_id=org_id,
                version_name="V1",
                status="superseded",
                as_of_period="2026-05",
                promoted_at=now.replace(day=1),
                created_at=now.replace(day=1),
                updated_at=now.replace(day=1),
            ),
            ForecastVersion(
                id=v2,
                organization_id=org_id,
                version_name="V2",
                status="final",
                as_of_period="2026-06",
                promoted_at=now,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    db_session.execute(
        text(
            """
            insert into forecast_mrr_waterfall
            (organization_id, forecast_version_id, version, period, new_arr)
            values
            (:org, :v1, 'Forecast', '2026-07', 100),
            (:org, :v2, 'Forecast', '2026-07', 250),
            (:org, :v2, 'Actual', '2026-07', 999)
            """
        ),
        {"org": str(org_id), "v1": str(v1), "v2": str(v2)},
    )
    db_session.commit()

    rows = fetch_table_rows(db_session, "forecast_mrr_waterfall", org_id)
    assert len(rows) == 1
    assert rows[0]["forecast_version_id"] == str(v2)
    assert float(rows[0]["new_arr"]) == 250.0


def test_get_active_falls_back_to_most_recent_final(db_session) -> None:
    org_id = uuid.uuid4()
    older = uuid.uuid4()
    newer = uuid.uuid4()
    org = Organization(id=org_id, name="Fallback Co", status="active", plan="growth")
    db_session.add(org)
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            ForecastVersion(
                id=older,
                organization_id=org_id,
                version_name="Older",
                status="final",
                as_of_period="2026-05",
                promoted_at=now.replace(day=1),
                created_at=now.replace(day=1),
                updated_at=now.replace(day=1),
            ),
            ForecastVersion(
                id=newer,
                organization_id=org_id,
                version_name="Newer",
                status="final",
                as_of_period="2026-06",
                promoted_at=now,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    db_session.commit()

    active = get_active_forecast_version(db_session, org)
    assert active is not None
    assert active.id == newer


def test_promote_strips_actual_rows(db_session) -> None:
    org_id = uuid.uuid4()
    version_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Promote Co", status="active", plan="growth"))
    db_session.commit()

    # Promote uses physical loader; stub into a simple table via replace semantics
    # by calling promote then reading with SQL (not fetch_table_rows schema sync).
    # Use load path that creates dynamic columns — skip full physical promote on sqlite
    # and unit-test the Actual filter contract by importing the filter loop logic via
    # promote_forecast_tables against an existing forecast_* table.
    with db_session.get_bind().begin() as conn:
        # table already created in fixture
        pass

    # Monkeypatch load_physical_table_rows to capture rows without PG DDL
    captured: dict[str, list[dict[str, str]]] = {}

    def _capture(session, organization_id, *, table_name, rows, filename=None):  # noqa: ANN001
        captured[table_name] = rows
        return len(rows)

    import app.services.demo_csv.loader as loader

    original = loader.load_physical_table_rows
    loader.load_physical_table_rows = _capture  # type: ignore[assignment]
    try:
        promote_forecast_tables(
            db_session,
            org_id,
            tables={
                "forecast_mrr_waterfall": [
                    {"version": "Actual", "period": "2026-06", "new_arr": "10"},
                    {"version": "Forecast", "period": "2026-07", "new_arr": "20"},
                ]
            },
            forecast_version_id=version_id,
            as_of_period="2026-06",
        )
    finally:
        loader.load_physical_table_rows = original  # type: ignore[assignment]

    rows = captured["forecast_mrr_waterfall"]
    assert len(rows) == 1
    assert rows[0]["version"] == "Forecast"
    assert rows[0]["forecast_version_id"] == str(version_id)
    assert rows[0]["new_arr"] == "20"
