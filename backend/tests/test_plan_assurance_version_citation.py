"""Assessments persist against real plan versions; Board cites the active forecast version's."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models.budget_version import BudgetVersion
from app.models.forecast_version import ForecastVersion
from app.models.organization import Organization
from app.models.plan_assessment import PlanAssessment
from app.services.predictive_planning.board_citation import (
    board_plan_assurance_for_org,
    metrics_from_plan_assurance,
)

client = TestClient(app)
pytestmark = pytest.mark.usefixtures("plan_assurance_member")

PACKET = {
    "bopArr": 90e6,
    "decArr": 108e6,
    "targetArr": 108e6,
    "yoyGrowthPct": 20.0,
    "endCash": 14e6,
    "cashFloor": 10e6,
    "salesEnd": 42,
    "aeNeeded": 40,
}
SIM = {
    "trials": 1000,
    "p_arr_miss": 0.2,
    "priors": {"yoyPp": 3.2, "cplLog": 0.28, "attrPp": 2.5, "pipe": 0.55, "source": "server_packet"},
    "seed": 42,
    "engine": "server_packet",
}


@pytest.fixture()
def db_factory():
    from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
    from sqlalchemy.ext.compiler import compiles

    @compiles(JSONB, "sqlite")
    def _jsonb(_type, compiler, **kw):  # noqa: ANN001
        return compiler.visit_JSON(_type, **kw)

    @compiles(PG_UUID, "sqlite")
    def _uuid(_type, compiler, **kw):  # noqa: ANN001
        return "CHAR(36)"

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        Organization.__table__,
        BudgetVersion.__table__,
        ForecastVersion.__table__,
        PlanAssessment.__table__,
    ):
        table.create(engine)
    factory = sessionmaker(bind=engine)

    def _override():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    try:
        yield factory
    finally:
        app.dependency_overrides.pop(get_db, None)


def _org(db, **kw) -> Organization:
    org = Organization(id=uuid.uuid4(), name="Plan Co", status="active", plan="growth", **kw)
    db.add(org)
    db.flush()
    return org


def _forecast_version(db, org_id, *, status="final", name="Jun close", promoted_offset_days=0):
    now = datetime.now(timezone.utc)
    v = ForecastVersion(
        id=uuid.uuid4(),
        organization_id=org_id,
        version_name=name,
        status=status,
        as_of_period="2026-06",
        promoted_at=now + timedelta(days=promoted_offset_days) if status == "final" else None,
        created_at=now,
    )
    db.add(v)
    db.flush()
    return v


def _budget_version(db, org_id):
    v = BudgetVersion(
        id=uuid.uuid4(),
        organization_id=org_id,
        version_name="FY27 Final",
        status="final",
        budget_year=2027,
        as_of_period="2026-06",
    )
    db.add(v)
    db.flush()
    return v


def _assess(plan_ref, **extra):
    res = client.post(
        "/api/v1/predictive-planning/assess",
        json={"plan_ref": plan_ref, "packet": PACKET, "persist": True, "simulation": SIM, **extra},
    )
    assert res.status_code == 200, res.text
    return res.json()


def test_forecast_assessment_persists_against_its_version(db_factory):
    db = db_factory()
    org = _org(db)
    fv = _forecast_version(db, org.id)
    db.commit()
    out = _assess(
        {"organization_id": str(org.id), "forecast_version_id": str(fv.id), "scenario": "forecast"},
        plan_fingerprint="fc-123",
    )
    assert out["persisted"] is True
    row = db_factory().get(PlanAssessment, uuid.UUID(out["assessment_id"]))
    assert row.forecast_version_id == fv.id
    assert row.budget_version_id is None
    assert row.scenario == "forecast"
    assert row.mc_seed == 42
    assert row.assessment["plan_fingerprint"] == "fc-123"

    listed = client.get(
        "/api/v1/predictive-planning/assessments",
        params={"organization_id": str(org.id), "forecast_version_id": str(fv.id), "latest": "true"},
    ).json()
    assert [r["id"] for r in listed] == [out["assessment_id"]]


def test_budget_assessment_persists_against_its_version(db_factory):
    db = db_factory()
    org = _org(db)
    bv = _budget_version(db, org.id)
    db.commit()
    out = _assess({"organization_id": str(org.id), "budget_version_id": str(bv.id), "scenario": "budget"})
    assert out["persisted"] is True
    row = db_factory().get(PlanAssessment, uuid.UUID(out["assessment_id"]))
    assert row.budget_version_id == bv.id


def test_unknown_or_foreign_version_is_not_persisted(db_factory):
    db = db_factory()
    org = _org(db)
    other = _org(db)
    foreign = _forecast_version(db, other.id)
    db.commit()

    missing = _assess(
        {"organization_id": str(org.id), "forecast_version_id": str(uuid.uuid4()), "scenario": "forecast"}
    )
    assert missing["persisted"] is False
    assert any(n.startswith("Not persisted: forecast version") for n in missing["method_notes"])

    cross = _assess(
        {"organization_id": str(org.id), "forecast_version_id": str(foreign.id), "scenario": "forecast"}
    )
    assert cross["persisted"] is False
    assert db_factory().query(PlanAssessment).count() == 0


def test_board_cites_latest_assessment_for_active_forecast_version(db_factory):
    db = db_factory()
    org = _org(db)
    old = _forecast_version(db, org.id, name="May close", promoted_offset_days=-30)
    active = _forecast_version(db, org.id, name="Jun close")
    draft = _forecast_version(db, org.id, status="draft", name="Jul draft")
    org.active_forecast_version_id = active.id
    db.commit()

    org_ref = str(org.id)
    _assess({"organization_id": org_ref, "forecast_version_id": str(old.id), "scenario": "forecast"})
    first = _assess({"organization_id": org_ref, "forecast_version_id": str(active.id), "scenario": "forecast"})
    latest = _assess(
        {
            "organization_id": org_ref,
            "forecast_version_id": str(active.id),
            "scenario": "forecast",
            "as_of": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        }
    )
    _assess({"organization_id": org_ref, "forecast_version_id": str(draft.id), "scenario": "forecast"})
    _assess({"organization_id": org_ref, "scenario": "forecast"})

    evidence = board_plan_assurance_for_org(db_factory(), org.id)
    assert evidence is not None
    assert evidence["assessment_id"] == latest["assessment_id"] != first["assessment_id"]
    assert evidence["forecast_version_id"] == str(active.id)
    assert evidence["cited_for"]["forecast_version_name"] == "Jun close"
    metrics = metrics_from_plan_assurance(evidence)
    assert metrics["plan_assurance_assessment_id"] == latest["assessment_id"]
    assert str(active.id) in metrics["plan_assurance_version"]


def test_board_cites_nothing_without_an_assessment_for_the_active_version(db_factory):
    db = db_factory()
    org = _org(db)
    old = _forecast_version(db, org.id, name="May close", promoted_offset_days=-30)
    active = _forecast_version(db, org.id, name="Jun close")
    org.active_forecast_version_id = active.id
    db.commit()
    _assess({"organization_id": str(org.id), "forecast_version_id": str(old.id), "scenario": "forecast"})

    assert board_plan_assurance_for_org(db_factory(), org.id) is None


def test_board_cites_nothing_without_a_final_forecast(db_factory):
    db = db_factory()
    org = _org(db)
    draft = _forecast_version(db, org.id, status="draft")
    db.commit()
    _assess({"organization_id": str(org.id), "forecast_version_id": str(draft.id), "scenario": "forecast"})

    assert board_plan_assurance_for_org(db_factory(), org.id) is None
