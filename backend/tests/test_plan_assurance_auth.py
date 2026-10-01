"""Plan Assurance routes require a signed-in member of the organization acted on."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

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
from app.models.user import OrganizationMember, User

client = TestClient(app)

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
HISTORY = {
    "monthly_ending_arr": [75e6, 76.3e6, 77.8e6, 79.5e6, 81.4e6],
    "periods": ["2026-02", "2026-03", "2026-04", "2026-05", "2026-06"],
    "source": "warehouse",
}


@pytest.fixture()
def world():
    from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
    from sqlalchemy.ext.compiler import compiles

    @compiles(JSONB, "sqlite")
    def _jsonb(_type, compiler, **kw):  # noqa: ANN001
        return compiler.visit_JSON(_type, **kw)

    @compiles(PG_UUID, "sqlite")
    def _uuid(_type, compiler, **kw):  # noqa: ANN001
        return "CHAR(36)"

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    for table in (
        Organization.__table__,
        User.__table__,
        OrganizationMember.__table__,
        BudgetVersion.__table__,
        ForecastVersion.__table__,
        PlanAssessment.__table__,
    ):
        table.create(engine)
    factory = sessionmaker(bind=engine)

    db = factory()
    own_org, other_org, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    version_id = uuid.uuid4()
    db.add_all(
        [
            Organization(id=own_org, name="Own Co", plan="growth", status="active"),
            Organization(id=other_org, name="Other Co", plan="growth", status="active"),
            User(id=user_id, email="fpa@own.example"),
            OrganizationMember(organization_id=own_org, user_id=user_id, role="member", status="active"),
            BudgetVersion(
                id=version_id,
                organization_id=own_org,
                version_name="FY27 Final",
                status="final",
                budget_year=2027,
                as_of_period="2026-06",
            ),
        ]
    )
    db.commit()
    db.close()

    def _override():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override
    try:
        yield {
            "factory": factory,
            "own_org": str(own_org),
            "other_org": str(other_org),
            "user_id": str(user_id),
            "version_id": str(version_id),
        }
    finally:
        app.dependency_overrides.pop(get_db, None)


def _requests(org: str, version_id: str | None = None):
    plan_ref = {"organization_id": org, "scenario": "budget"}
    if version_id:
        plan_ref["budget_version_id"] = version_id
    return {
        "assess": ("post", "/api/v1/predictive-planning/assess",
                   {"json": {"plan_ref": plan_ref, "packet": PACKET, "persist": bool(version_id)}}),
        "simulate": ("post", "/api/v1/predictive-planning/simulate",
                     {"json": {"plan_ref": plan_ref, "packet": PACKET, "n_trials": 100, "seed": 7}}),
        "mc-inputs": ("post", "/api/v1/predictive-planning/mc-inputs",
                      {"json": {"plan_ref": plan_ref, "history": HISTORY, "seed": 7, "n_trials": 100}}),
        "assessments": ("get", "/api/v1/predictive-planning/assessments",
                        {"params": {"organization_id": org, "budget_version_id": version_id or str(uuid.uuid4())}}),
    }


def _call(spec, headers=None):
    method, path, kwargs = spec
    return getattr(client, method)(path, headers=headers or {}, **kwargs)


@pytest.mark.parametrize("route", ["assess", "simulate", "mc-inputs", "assessments"])
def test_unauthenticated_request_is_rejected(world, route):
    res = _call(_requests(world["own_org"], world["version_id"])[route])
    assert res.status_code == 401, res.text


def test_unauthenticated_constraints_and_record_lookup_are_rejected(world):
    assert client.get("/api/v1/predictive-planning/constraints").status_code == 401
    assert client.get(f"/api/v1/predictive-planning/assessments/{uuid.uuid4()}").status_code == 401


@pytest.mark.parametrize("route", ["assess", "simulate", "mc-inputs", "assessments"])
def test_other_organization_is_rejected(world, route):
    res = _call(_requests(world["other_org"])[route], headers={"X-SFI-User-Id": world["user_id"]})
    assert res.status_code == 403, res.text


def test_unknown_user_is_rejected(world):
    res = _call(_requests(world["own_org"])["assess"], headers={"X-SFI-User-Id": str(uuid.uuid4())})
    assert res.status_code == 403


def test_rejected_assess_persists_nothing(world):
    _call(_requests(world["own_org"], world["version_id"])["assess"])
    _call(_requests(world["other_org"])["assess"], headers={"X-SFI-User-Id": world["user_id"]})
    db = world["factory"]()
    try:
        assert db.query(PlanAssessment).count() == 0
    finally:
        db.close()


@pytest.mark.parametrize("route", ["assess", "simulate", "mc-inputs", "assessments"])
def test_member_on_own_organization_succeeds(world, route):
    res = _call(
        _requests(world["own_org"], world["version_id"])[route],
        headers={"X-SFI-User-Id": world["user_id"]},
    )
    assert res.status_code == 200, res.text


def test_member_persists_and_reads_back_own_assessment(world):
    headers = {"X-SFI-User-Id": world["user_id"]}
    out = _call(_requests(world["own_org"], world["version_id"])["assess"], headers=headers).json()
    assert out["persisted"] is True

    res = client.get(f"/api/v1/predictive-planning/assessments/{out['assessment_id']}", headers=headers)
    assert res.status_code == 200
    assert res.json()["organization_id"] == world["own_org"]
    assert client.get("/api/v1/predictive-planning/constraints", headers=headers).status_code == 200


def test_assessment_record_of_another_org_is_rejected(world):
    db = world["factory"]()
    try:
        row = PlanAssessment(
            id=uuid.uuid4(),
            organization_id=uuid.UUID(world["other_org"]),
            scenario="budget",
            as_of=datetime.now(timezone.utc),
            feasibility_verdict="pass",
            assessment={},
        )
        db.add(row)
        db.commit()
        row_id = row.id
    finally:
        db.close()
    res = client.get(
        f"/api/v1/predictive-planning/assessments/{row_id}",
        headers={"X-SFI-User-Id": world["user_id"]},
    )
    assert res.status_code == 403
