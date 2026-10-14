"""API + platform-engine tests for Plan Assurance (/assess, /simulate, priors)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.predictive_planning.forecast_adapter import build_forecast_plan_packet
from app.services.predictive_planning.monte_carlo import run_packet_monte_carlo
from app.services.predictive_planning.priors import fit_priors_from_history
from app.services.predictive_planning.board_citation import metrics_from_plan_assurance


client = TestClient(app)
pytestmark = pytest.mark.usefixtures("plan_assurance_member")

ORG = str(uuid.uuid4())


def budget_shaped_packet():
    return {
        "period_label": "FY2027 Budget",
        "budget_year": 2027,
        "yoyGrowthPct": 20.0,
        "bopArr": 90_291_801.85,
        "decArr": 108_350_162.22,
        "targetArr": 108_350_162.22,
        "fyNn": 18_058_360.37,
        "fyRev": 99_000_000.0,
        "fyEbitda": 4_000_000.0,
        "endCash": 14_000_000.0,
        "cashFloor": 10_000_000.0,
        "minCash": 11_500_000.0,
        "minCashPeriod": "2027-07",
        "cashByMonth": [12e6, 12.2e6, 12.5e6, 12.8e6, 12.0e6, 11.5e6, 11.8e6, 12.5e6, 13.0e6, 13.4e6, 13.7e6, 14.0e6],
        "programByMonth": [1e6] * 12,
        "openNb": 30_000_000.0,
        "cfoPlanErrorSd": 400_000.0,
        "fyMkt": 12_000_000.0,
        "fyMql": 24_000.0,
        "fySpendId": 12_000_000.0,
        "mixDevMax": 0.001,
        "avgGrr": 0.94,
        "minGrr": 0.93,
        "salesEnd": 42.0,
        "csEnd": 18.0,
        "aeNeeded": 40.0,
        "csNeeded": 17.0,
        "coverPct": 65.0,
        "hirePct": 35.0,
        "benchTarget": 60.0,
        "janHc": 150.0,
        "janHcExpected": 150.0,
        "decHc": 190.0,
        "pipelineCoverage": 3.0,
        "pipelineMin": 2.5,
        "fyIsSm": 30_000_000.0,
        "fyPlProgram": 12_000_000.0,
    }


def test_assess_accepts_budget_camelcase_packet():
    res = client.post(
        "/api/v1/predictive-planning/assess",
        json={
            "plan_ref": {"organization_id": ORG, "scenario": "budget"},
            "packet": budget_shaped_packet(),
            "persist": False,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["feasibility"]["verdict"] in ("pass", "warn", "fail")
    assert body["persisted"] is False
    assert body["what_has_to_be_true"] is not None
    assert any("stress frequency" in n.lower() or "priors" in n.lower() for n in body["method_notes"])
    ids = {r["id"] for r in body["feasibility"]["results"]}
    assert "arr_path" in ids
    assert "cash_floor" in ids


@pytest.fixture
def declared_policy(monkeypatch):
    """The organization's plan risk policy as answered at onboarding (7.43-7.54)."""

    from app.api import predictive_planning_routes as routes
    from app.services.readiness.plan_risk_policy import resolve_policy

    answers = {"7.43": "25", "7.44": "50", "7.45": "85", "7.46": "5", "7.47": "15", "7.48": "12",
               "7.49": "35", "7.50": "25", "7.51": "0.5", "7.52": "2", "7.53": "15", "7.54": "5"}
    monkeypatch.setattr(routes, "plan_risk_policy", lambda db, organization_id: resolve_policy(answers))
    return answers


@pytest.mark.usefixtures("declared_policy")
def test_assess_whtt_must_close_on_cash_failure():
    packet = budget_shaped_packet()
    packet["endCash"] = 8_000_000.0
    packet["salesEnd"] = 30.0
    res = client.post(
        "/api/v1/predictive-planning/assess",
        json={
            "plan_ref": {"organization_id": ORG, "scenario": "budget"},
            "packet": packet,
            "simulation": {"breaks": ["Dec cash floor"], "watches": []},
            "persist": False,
        },
    )
    assert res.status_code == 200
    conditions = res.json()["what_has_to_be_true"]
    by_id = {c["constraint_id"]: c for c in conditions}
    assert by_id["cash_floor"]["verdict"] == "must_close"
    assert by_id["nb_cover"]["verdict"] == "must_close"


@pytest.mark.usefixtures("declared_policy")
def test_simulate_is_seed_reproducible():
    payload = {
        "plan_ref": {"organization_id": ORG, "scenario": "budget"},
        "packet": budget_shaped_packet(),
        "n_trials": 200,
        "seed": 99,
    }
    a = client.post("/api/v1/predictive-planning/simulate", json=payload).json()
    b = client.post("/api/v1/predictive-planning/simulate", json=payload).json()
    assert a["result"]["p_arr_miss"] == b["result"]["p_arr_miss"]
    assert a["result"]["p_cash_below_floor"] == b["result"]["p_cash_below_floor"]
    assert a["simulation_summary"]["priors"]["seed"] == 99
    assert "not calibrated" in " ".join(a["method_notes"]).lower() or "not" in " ".join(
        a["method_notes"]
    ).lower()


def test_simulate_applies_the_organization_risk_policy(declared_policy):
    payload = {
        "plan_ref": {"organization_id": ORG, "scenario": "budget"},
        "packet": budget_shaped_packet(),
        "n_trials": 200,
        "seed": 99,
        "priors": {"yoyPp": 3.0, "cplLog": 0.3, "attrPp": 2.0, "pipe": 0.5},
    }
    body = client.post("/api/v1/predictive-planning/simulate", json=payload).json()
    assert body["result"]["prior_source"] == "caller_override"
    assert body["result"]["policy"] == {
        "arr_miss_tolerance": 0.005,
        "cash_watch_shortfall": 0.25,
        "cash_alarm_shortfall": 0.5,
    }
    assert body["result"]["p_arr_miss"] is not None
    assert body["result"]["cash"]["pWatch"] is not None
    assert not any("Risk policy" in n for n in body["method_notes"])


def test_simulate_without_a_risk_policy_reports_the_rates_as_not_set(monkeypatch):
    from app.api import predictive_planning_routes as routes
    from app.services.readiness.plan_risk_policy import resolve_policy

    monkeypatch.setattr(routes, "plan_risk_policy", lambda db, organization_id: resolve_policy({}))
    payload = {
        "plan_ref": {"organization_id": ORG, "scenario": "budget"},
        "packet": budget_shaped_packet(),
        "n_trials": 200,
        "seed": 99,
    }
    body = client.post("/api/v1/predictive-planning/simulate", json=payload).json()
    result = body["result"]
    assert result["p_arr_miss"] is None and result["p_ops_liquidity"] is None
    assert result["cash"]["pWatch"] is None and result["cash"]["pAlarm"] is None
    assert result["p_cash_below_floor"] is not None
    notes = " ".join(body["method_notes"])
    for qid in ("7.51", "7.43", "7.44"):
        assert f"Risk policy {qid}" in notes


def test_assess_escalates_cash_floor_by_the_organization_policy(monkeypatch):
    from app.api import predictive_planning_routes as routes
    from app.services.readiness.plan_risk_policy import resolve_policy

    packet = budget_shaped_packet()
    packet["endCash"] = 8_000_000.0
    severities = {}
    for share in ("75", "85"):
        monkeypatch.setattr(routes, "plan_risk_policy", lambda db, organization_id, s=share: resolve_policy({"7.45": s}))
        body = client.post(
            "/api/v1/predictive-planning/assess",
            json={"plan_ref": {"organization_id": ORG, "scenario": "budget"}, "packet": packet, "persist": False},
        ).json()
        result = {r["id"]: r for r in body["feasibility"]["results"]}["cash_floor"]
        applied = {c["id"]: c for c in body["constraints_applied"]}["cash_floor"]
        assert applied["param_sources"]["hard_breach_ratio"] == "tenant"
        severities[share] = result["severity"]
    assert severities == {"75": "medium", "85": "high"}


def test_monte_carlo_unit_seed_stable():
    packet = {
        "bop_arr": 90e6,
        "dec_arr": 108e6,
        "target_arr": 108e6,
        "yoy_growth_pct": 20.0,
        "end_cash": 14e6,
        "cash_floor": 10e6,
        "sales_end": 42,
        "ae_needed": 40,
        "cash_by_month": [12e6] * 12,
        "program_by_month": [1e6] * 12,
        "open_nb": 30e6,
        "pipeline_coverage": 3.0,
        "cfo_plan_error_sd": 400_000.0,
    }
    policy = {"arr_miss_tolerance": 0.005, "cash_watch_shortfall": 0.25, "cash_alarm_shortfall": 0.5}
    priors = {"yoyPp": 3.0, "cplLog": 0.3, "attrPp": 2.0, "pipe": 0.5}
    a = run_packet_monte_carlo(packet, n=100, seed=7, priors=priors, policy=policy)
    b = run_packet_monte_carlo(packet, n=100, seed=7, priors=priors, policy=policy)
    c = run_packet_monte_carlo(packet, n=100, seed=8, priors=priors, policy=policy)
    assert a.p_arr_miss == b.p_arr_miss
    assert a.p_arr_miss != c.p_arr_miss or a.p_cash_below_floor != c.p_cash_below_floor


def test_priors_history_fit_and_nothing_without_history():
    none = fit_priors_from_history(None)
    assert none["prior_source"] == "not_fitted" and none["priors"] == {}

    fit = fit_priors_from_history(
        {
            "ending_arr_yoy_pp": [18.0, 21.0, 19.5, 22.0, 20.0, 17.5],
            "cpl_log_ratios": [0.0, 0.1, -0.05, 0.2, 0.05, -0.1],
            "attrition_pp": [8.0, 9.0, 10.0, 11.0, 9.5, 10.5],
            "pipeline_cover": [2.8, 3.0, 3.2, 2.9, 3.1, 3.0],
        }
    )
    assert fit["prior_source"] == "history_fit"
    assert "yoyPp" in fit["fitted"]
    assert "Calibrated Probability of Attainment" in fit["method_card"]["not_claimed"]


def test_forecast_adapter_packet_shape():
    packet = build_forecast_plan_packet(
        period_label="FY2027 Forecast",
        budget_year=2027,
        bop_arr=90e6,
        dec_arr=105e6,
        target_arr=108e6,
        yoy_growth_pct=16.5,
        end_cash=12e6,
        cash_floor=10e6,
        sales_end=40,
        ae_needed=42,
    )
    assert packet["surface"] == "forecast"
    assert packet["fyNn"] == 15e6
    res = client.post(
        "/api/v1/predictive-planning/assess",
        json={
            "plan_ref": {"organization_id": ORG, "scenario": "forecast"},
            "packet": packet,
            "persist": False,
        },
    )
    assert res.status_code == 200
    assert any("Forecast" in n for n in res.json()["method_notes"])


def test_metrics_from_plan_assurance():
    evidence = {
        "assessment_id": "abc",
        "feasibility_verdict": "fail",
        "prior_source": "not_fitted",
        "what_has_to_be_true": {
            "must_close": [{"statement": "Cash must reach floor"}],
            "must_hold": [],
        },
        "simulation": {"trials": 1000, "p_cash_below_floor": 0.12, "p_arr_miss": 0.08},
    }
    m = metrics_from_plan_assurance(evidence)
    assert m["plan_assurance_verdict"] == "fail"
    assert "Cash must reach floor" in m["plan_assurance_must_close"]
    assert m["plan_assurance_p_cash_below_floor"] == "12.0%"
