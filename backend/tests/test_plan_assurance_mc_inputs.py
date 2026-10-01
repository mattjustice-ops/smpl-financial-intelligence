"""Server-issued Monte Carlo inputs, prior reconciliation and persisted inputs."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models.budget_version import BudgetVersion
from app.models.plan_assessment import PlanAssessment
from app.services.predictive_planning.mc_inputs import (
    FULL_PLAN_ENGINE,
    SAMPLER,
    build_mc_inputs,
    mc_inputs_hash,
)
from app.services.predictive_planning.monte_carlo import DEFAULT_PRIORS, LEVERS

client = TestClient(app)
ORG = str(uuid.uuid4())

MONTHLY_ARR = [75_000_000, 76_310_000, 77_815_000, 79_505_000, 81_385_000, 83_445_000, 86_100_000]
MONTHLY_PERIODS = ["2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
WAREHOUSE = {"monthly_ending_arr": MONTHLY_ARR, "periods": MONTHLY_PERIODS, "source": "warehouse"}
DEMO = {**WAREHOUSE, "source": "demo_seed"}

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


def _inputs(history, seed=42, n_trials=1000):
    res = client.post(
        "/api/v1/predictive-planning/mc-inputs",
        json={
            "plan_ref": {"organization_id": ORG, "scenario": "budget"},
            "history": history,
            "seed": seed,
            "n_trials": n_trials,
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


def _summary_from_inputs(inputs, **overrides):
    """What the Budget Engine records after a full-plan run with these inputs."""

    summary = {
        "trials": inputs["n_trials"],
        "breaks": [],
        "watches": [],
        "p_arr_miss": 0.41,
        "p_cash_below_floor": 0.0,
        "p_ops_liquidity": 0.0,
        "p_ae_short": 0.0,
        "priors": {**inputs["priors"], "source": inputs["prior_source"]},
        "seed": inputs["seed"],
        "correlations": inputs["correlations"],
        "engine": inputs["engine"],
        "sampler": inputs["sampler"],
        "inputs_hash": inputs["inputs_hash"],
        "plan_fingerprint": "fp-test",
    }
    summary.update(overrides)
    return summary


def _assess(history, simulation, **extra):
    body = {
        "plan_ref": {"organization_id": ORG, "scenario": "budget"},
        "packet": PACKET,
        "persist": False,
        "history": history,
        "simulation": simulation,
        **extra,
    }
    res = client.post("/api/v1/predictive-planning/assess", json=body)
    assert res.status_code == 200, res.text
    return res.json()


def test_mc_inputs_issue_fitted_priors_seed_and_hash():
    a = _inputs(WAREHOUSE, seed=7)
    assert a["engine"] == FULL_PLAN_ENGINE
    assert a["sampler"] == SAMPLER
    assert a["seed"] == 7
    assert a["prior_source"] == "history_partial"
    assert set(a["priors"]) == set(LEVERS)
    assert a["priors"]["yoyPp"] != DEFAULT_PRIORS["yoyPp"]
    assert a["method_card"]["priors"] == a["priors"]
    assert a["method_card"]["simulation"]["inputs_hash"] == a["inputs_hash"]
    assert a["inputs_hash"] == mc_inputs_hash(7, 1000, a["priors"], a["correlations"])

    again = _inputs(WAREHOUSE, seed=7)
    assert again["inputs_hash"] == a["inputs_hash"]
    assert again["priors"] == a["priors"]
    assert _inputs(WAREHOUSE, seed=8)["inputs_hash"] != a["inputs_hash"]


def test_mc_inputs_demo_history_keeps_defaults():
    a = _inputs(DEMO)
    assert a["prior_source"] == "independent_defaults"
    assert a["priors"] == {k: DEFAULT_PRIORS[k] for k in LEVERS}
    assert a["correlations"] == {}
    assert "demo_seed" in a["method_card"]["notes"][0]


def test_mc_inputs_return_applied_correlations_after_shrink():
    inconsistent = {"yoyPp:cplLog": 0.9, "yoyPp:attrPp": 0.9, "cplLog:attrPp": -0.9}
    a = build_mc_inputs({**WAREHOUSE, "correlations": inconsistent})
    assert set(a["correlations"]) == set(inconsistent)
    assert all(abs(a["correlations"][k]) < abs(v) for k, v in inconsistent.items())
    assert any("shrunk" in n for n in a["method_card"]["notes"])


def test_card_priors_match_simulation_priors_when_inputs_are_server_issued():
    inputs = _inputs(WAREHOUSE)
    out = _assess(WAREHOUSE, _summary_from_inputs(inputs))
    card = out["method_card"]
    used = {k: v for k, v in out["simulation_summary"]["priors"].items() if k != "source"}
    assert card["priors"] == used
    assert card["priors"]["yoyPp"] == inputs["priors"]["yoyPp"]
    assert card["source"] == "history_partial"
    assert out["prior_source"] == "history_partial"
    assert card["notes"][0].startswith("Fitted from company history: ARR growth")
    assert card["simulation"]["matches_server_fit"] is True
    assert card["simulation"]["inputs_hash_verified"] is True
    assert card["simulation"]["engine"] == FULL_PLAN_ENGINE


def test_card_shows_used_priors_and_drops_fit_claim_when_simulation_used_other_priors():
    defaults = {k: DEFAULT_PRIORS[k] for k in LEVERS}
    stale = {
        "trials": 1000,
        "p_arr_miss": 0.43,
        "priors": {**defaults, "source": "client_or_server"},
    }
    out = _assess(WAREHOUSE, stale)
    card = out["method_card"]
    assert card["priors"] == defaults
    assert card["source"] == "client_or_server"
    assert out["prior_source"] == "client_or_server"
    assert "differ from the server's fit" in card["notes"][0]
    assert not card["notes"][0].startswith("Fitted")
    assert card["simulation"]["matches_server_fit"] is False


def test_packet_fallback_run_is_labeled_on_card():
    inputs = _inputs(WAREHOUSE)
    fallback = _summary_from_inputs(
        inputs,
        priors={**inputs["priors"], "cashResidMo": 0.04, "source": inputs["prior_source"]},
        engine="server_packet_fallback",
        sampler=None,
        inputs_hash=None,
    )
    out = _assess(WAREHOUSE, fallback)
    sim = out["method_card"]["simulation"]
    assert sim["engine"] == "server_packet_fallback"
    assert sim["sampler"] is None
    assert sim["inputs_hash"] is None
    assert out["method_card"]["priors"]["cashResidMo"] == 0.04


def test_forecast_packet_summary_keeps_only_prior_values_on_card():
    from app.services.predictive_planning.priors import fit_priors_from_history

    fit = fit_priors_from_history(WAREHOUSE)
    forecast_summary = {
        "trials": 1000,
        "p_arr_miss": 0.2,
        "priors": {
            **fit["priors"],
            "source": fit["prior_source"],
            "seed": 42,
            "method": "monte_carlo_packet_lever_shocks_open_month_cash_flow",
            "p_trough_breach": 0.31,
            "correlations": {},
        },
        "seed": 42,
        "correlations": {},
        "engine": "server_packet",
    }
    out = _assess(WAREHOUSE, forecast_summary)
    card = out["method_card"]
    assert set(card["priors"]) == {*LEVERS, "cashResidMo"}
    assert card["simulation"]["matches_server_fit"] is True
    assert card["simulation"]["engine"] == "server_packet"
    assert card["notes"][0].startswith("Fitted from company history")


def test_tampered_inputs_hash_is_flagged():
    inputs = _inputs(WAREHOUSE)
    out = _assess(WAREHOUSE, _summary_from_inputs(inputs, inputs_hash="0" * 16))
    assert out["method_card"]["simulation"]["inputs_hash_verified"] is False


def test_assess_without_simulation_keeps_history_fit_card():
    out = _assess(WAREHOUSE, None)
    assert out["method_card"]["source"] == "history_partial"
    assert out["method_card"]["notes"][0].startswith("Fitted from company history")


@pytest.fixture()
def sqlite_db():
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
    BudgetVersion.__table__.create(engine)
    PlanAssessment.__table__.create(engine)
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


def test_persisted_assessment_records_priors_actually_used(sqlite_db):
    db = sqlite_db()
    version = BudgetVersion(
        id=uuid.uuid4(),
        organization_id=uuid.UUID(ORG),
        version_name="FY27 Final",
        status="final",
        budget_year=2027,
        as_of_period="2026-06",
    )
    db.add(version)
    db.commit()
    budget_version = str(version.id)
    db.close()
    inputs = _inputs(WAREHOUSE, seed=1234)
    sim = _summary_from_inputs(inputs)
    out = _assess(
        WAREHOUSE,
        sim,
        persist=True,
        mc_seed=42,
        plan_ref={"organization_id": ORG, "budget_version_id": budget_version, "scenario": "budget"},
    )
    assert out["persisted"] is True

    db = sqlite_db()
    try:
        row = db.get(PlanAssessment, uuid.UUID(out["assessment_id"]))
        assert row is not None
        assert str(row.budget_version_id) == budget_version
        assert row.mc_seed == 1234
        assert row.prior_source == "history_partial"
        recorded = row.simulation_summary
        assert {k: v for k, v in recorded["priors"].items() if k != "source"} == inputs["priors"]
        assert recorded["seed"] == 1234
        assert recorded["correlations"] == inputs["correlations"]
        assert recorded["engine"] == FULL_PLAN_ENGINE
        assert recorded["inputs_hash"] == inputs["inputs_hash"]
        assert row.assessment["method_card"]["priors"] == inputs["priors"]
        assert row.assessment["simulation_inputs"]["matches_server_fit"] is True
        assert row.assessment["simulation_inputs"]["inputs_hash_verified"] is True
    finally:
        db.close()
