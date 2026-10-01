"""History-fitted priors and correlated lever draws for Plan Assurance Monte Carlo."""

from __future__ import annotations

import math
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.services.predictive_planning.monte_carlo import (
    DEFAULT_PRIORS,
    correlation_cholesky,
    normalize_correlations,
    run_packet_monte_carlo,
)
from app.services.predictive_planning.priors import MIN_CORRELATION_PAIRS, fit_priors_from_history

client = TestClient(app)
ORG = str(uuid.uuid4())

# Dec'25 BOP + Jan..Jun'26 closed month-end ARR (Forecast Engine demo actuals shape).
MONTHLY_ARR = [75_000_000, 76_310_000, 77_815_000, 79_505_000, 81_385_000, 83_445_000, 86_100_000]
MONTHLY_PERIODS = ["2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]

PACKET = {
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
    "close_month_idx": 5,
}


def _expected_annualised_sd(levels):
    growth = [(levels[i] / levels[i - 1] - 1) * 100 for i in range(1, len(levels))]
    mu = sum(growth) / len(growth)
    sd = math.sqrt(sum((g - mu) ** 2 for g in growth) / (len(growth) - 1))
    return sd * math.sqrt(12)


def test_monthly_warehouse_history_activates_growth_prior():
    fit = fit_priors_from_history(
        {"monthly_ending_arr": MONTHLY_ARR, "periods": MONTHLY_PERIODS, "source": "warehouse"}
    )
    assert fit["prior_source"] == "history_partial"
    assert fit["fitted"] == ["yoyPp"]
    assert set(fit["skipped"]) == {"cplLog", "attrPp", "pipe"}
    expected = max(1.0, min(12.0, _expected_annualised_sd(MONTHLY_ARR)))
    assert math.isclose(fit["priors"]["yoyPp"], expected, rel_tol=1e-9)
    assert fit["priors"]["yoyPp"] != DEFAULT_PRIORS["yoyPp"]
    basis = fit["method_card"]["history_basis"]["yoyPp"]
    assert basis["observations"] == 6
    assert basis["span"] == "2025-12..2026-06"
    assert basis["fitted"] is True
    assert "Defaults kept for cost per lead" in fit["label"]


def test_four_monthly_levels_is_the_minimum_for_a_fit():
    assert fit_priors_from_history({"monthly_ending_arr": MONTHLY_ARR[:4], "source": "warehouse"})[
        "fitted"
    ] == ["yoyPp"]
    thin = fit_priors_from_history({"monthly_ending_arr": MONTHLY_ARR[:3], "source": "warehouse"})
    assert thin["prior_source"] == "independent_defaults"
    assert thin["priors"]["yoyPp"] == DEFAULT_PRIORS["yoyPp"]
    assert "not enough company history" in thin["label"]
    assert "2 ARR growth observations; 3 needed" in thin["label"]


def test_legacy_three_year_end_values_fall_back_visibly():
    fit = fit_priors_from_history({"ending_arr": [77e6, 90e6, 108e6]})
    assert fit["prior_source"] == "independent_defaults"
    assert fit["method_card"]["notes"][0].startswith("Default priors")


def test_demo_seed_history_is_never_fitted():
    fit = fit_priors_from_history(
        {"monthly_ending_arr": MONTHLY_ARR, "periods": MONTHLY_PERIODS, "source": "demo_seed"}
    )
    assert fit["prior_source"] == "independent_defaults"
    assert fit["fitted"] == []
    assert "demo_seed data, not company actuals" in fit["label"]
    assert fit["priors"]["yoyPp"] == DEFAULT_PRIORS["yoyPp"]


def test_correlations_fitted_only_with_enough_paired_history():
    n = MIN_CORRELATION_PAIRS
    yoy = [15.0 + (i % 5) * 1.5 for i in range(n)]
    cpl = [0.3 - (v - 15.0) * 0.05 for v in yoy]  # CPL rises when growth falls
    fit = fit_priors_from_history({"ending_arr_yoy_pp": yoy, "cpl_log_ratios": cpl, "source": "warehouse"})
    assert fit["correlations"]["yoyPp:cplLog"] < -0.9
    assert fit["method_card"]["correlation_basis"]["yoyPp:cplLog"] == {
        "source": "history_fit",
        "observations": n,
    }

    short = fit_priors_from_history(
        {"ending_arr_yoy_pp": yoy[: n - 1], "cpl_log_ratios": cpl[: n - 1], "source": "warehouse"}
    )
    assert short["correlations"] is None
    assert any("Independent draws" in note for note in short["method_card"]["notes"])


def test_caller_correlations_are_validated():
    clean, rejected = normalize_correlations(
        {"cplLog:yoyPp": -0.4, "yoyPp:nope": 0.2, "attrPp:pipe": 1.5, "pipe|yoyPp": "0.3"}
    )
    assert clean == {"yoyPp:cplLog": -0.4, "yoyPp:pipe": 0.3}
    assert len(rejected) == 2


def test_inconsistent_correlations_are_shrunk_and_reported():
    lower, applied, notes = correlation_cholesky(
        {"yoyPp:cplLog": 0.95, "yoyPp:attrPp": 0.95, "cplLog:attrPp": -0.95}
    )
    assert applied and all(abs(v) < 0.95 for v in applied.values())
    assert any("shrunk toward independence" in n for n in notes)
    assert lower[0][0] == 1.0


def test_zero_correlation_reproduces_independent_draws():
    a = run_packet_monte_carlo(PACKET, n=300, seed=11)
    b = run_packet_monte_carlo(PACKET, n=300, seed=11, correlations={"yoyPp:cplLog": 0.0})
    assert a.arr == b.arr
    assert a.cash_path_monthly == b.cash_path_monthly


def test_growth_cpl_correlation_widens_the_joint_arr_tail():
    """Growth down with CPL up stacks two ARR headwinds; positive rho offsets them."""

    priors = {"yoyPp": 3.0, "cplLog": 0.6}
    neg = run_packet_monte_carlo(PACKET, n=4000, seed=5, priors=priors, correlations={"yoyPp:cplLog": -0.8})
    ind = run_packet_monte_carlo(PACKET, n=4000, seed=5, priors=priors)
    pos = run_packet_monte_carlo(PACKET, n=4000, seed=5, priors=priors, correlations={"yoyPp:cplLog": 0.8})

    assert neg.arr["sd"] > ind.arr["sd"] > pos.arr["sd"]
    assert neg.arr["p10"] < ind.arr["p10"] < pos.arr["p10"]
    assert neg.p_arr_miss > ind.p_arr_miss
    assert neg.correlations == {"yoyPp:cplLog": -0.8}
    assert ind.correlations == {}
    assert any("Correlated lever draws" in n for n in neg.method_notes)
    assert any("Independent lever draws" in n for n in ind.method_notes)


def test_simulate_endpoint_uses_history_priors_and_correlations():
    payload = {
        "plan_ref": {"organization_id": ORG, "scenario": "budget"},
        "packet": {
            "bopArr": 90e6,
            "targetArr": 108e6,
            "yoyGrowthPct": 20.0,
            "endCash": 14e6,
            "cashFloor": 10e6,
            "cashByMonth": [12e6] * 12,
            "salesEnd": 42,
            "aeNeeded": 40,
            "pipelineCoverage": 3.0,
            "hirePct": 10.0,
        },
        "n_trials": 500,
        "seed": 3,
        "history": {
            "monthly_ending_arr": MONTHLY_ARR,
            "periods": MONTHLY_PERIODS,
            "source": "warehouse",
            "correlations": {"yoyPp:cplLog": -0.5},
        },
    }
    res = client.post("/api/v1/predictive-planning/simulate", json=payload)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["prior_source"] == "history_partial"
    fitted = max(1.0, min(12.0, _expected_annualised_sd(MONTHLY_ARR)))
    assert math.isclose(body["result"]["sig"]["yoyPp"], fitted, rel_tol=1e-9)
    assert body["result"]["correlations"] == {"yoyPp:cplLog": -0.5}
    assert body["simulation_summary"]["priors"]["correlations"] == {"yoyPp:cplLog": -0.5}
    assert body["method_card"]["history_basis"]["yoyPp"]["observations"] == 6
    assert any("Correlated lever draws" in n for n in body["method_notes"])

    payload["history"]["source"] = "demo_seed"
    demo = client.post("/api/v1/predictive-planning/simulate", json=payload).json()
    assert demo["prior_source"] == "independent_defaults"
    assert demo["result"]["sig"]["yoyPp"] == DEFAULT_PRIORS["yoyPp"]


def test_assess_reports_prior_basis_in_method_notes():
    res = client.post(
        "/api/v1/predictive-planning/assess",
        json={
            "plan_ref": {"organization_id": ORG, "scenario": "budget"},
            "packet": {"bopArr": 90e6, "decArr": 108e6, "targetArr": 108e6},
            "persist": False,
            "history": {"monthly_ending_arr": MONTHLY_ARR[:3], "source": "warehouse"},
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["prior_source"] == "independent_defaults"
    assert any(n.startswith("Default priors") for n in body["method_notes"])
    assert any("Independent draws" in n for n in body["method_notes"])
