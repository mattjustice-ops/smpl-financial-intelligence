"""API + platform-engine tests for Plan Assurance (/assess, /simulate, priors)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.services.predictive_planning.forecast_adapter import build_forecast_plan_packet
from app.services.predictive_planning.monte_carlo import run_packet_monte_carlo
from app.services.predictive_planning.priors import fit_priors_from_history
from app.services.predictive_planning.board_citation import metrics_from_plan_assurance


client = TestClient(app)

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
        "fyMkt": 12_000_000.0,
        "fyMql": 24_000.0,
        "fyChMql": 24_000.0,
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
        "fyGtmSm": 28_000_000.0,
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


def test_monte_carlo_unit_seed_stable():
    packet = {
        "bop_arr": 90e6,
        "target_arr": 108e6,
        "yoy_growth_pct": 20.0,
        "end_cash": 14e6,
        "cash_floor": 10e6,
        "sales_end": 42,
        "ae_needed": 40,
        "cash_by_month": [12e6] * 12,
        "pipeline_coverage": 3.0,
        "hire_pct": 10.0,
    }
    a = run_packet_monte_carlo(packet, n=100, seed=7)
    b = run_packet_monte_carlo(packet, n=100, seed=7)
    c = run_packet_monte_carlo(packet, n=100, seed=8)
    assert a.p_arr_miss == b.p_arr_miss
    assert a.p_arr_miss != c.p_arr_miss or a.p_cash_below_floor != c.p_cash_below_floor


def test_priors_history_fit_and_fallback():
    fall = fit_priors_from_history(None)
    assert fall["prior_source"] == "independent_defaults"

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
        "prior_source": "independent_defaults",
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
