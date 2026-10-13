"""History-fitted priors and correlated lever draws for Plan Assurance Monte Carlo."""

from __future__ import annotations

import math
import uuid

import pytest
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
pytestmark = pytest.mark.usefixtures("plan_assurance_member")
ORG = str(uuid.uuid4())

# Dec'25 BOP + Jan..Jun'26 closed month-end ARR (Forecast Engine demo actuals shape).
MONTHLY_ARR = [75_000_000, 76_310_000, 77_815_000, 79_505_000, 81_385_000, 83_445_000, 86_100_000]
MONTHLY_PERIODS = ["2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]

PACKET = {
    "bop_arr": 90e6,
    "dec_arr": 108e6,
    "target_arr": 108e6,
    "yoy_growth_pct": 20.0,
    "end_cash": 14e6,
    "cash_floor": 10e6,
    "sales_end": 42,
    "ae_needed": 40,
    "cash_by_month": [12e6] * 12,
    "program_by_month": [0.5e6] * 12,
    "open_nb": 9e6,
    "pipeline_coverage": 3.0,
    "cfo_plan_error_sd": 150_000.0,
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


def test_cpl_and_coverage_history_fit_with_their_basis():
    cpl = [0.12, -0.08, 0.20, -0.15, 0.05, 0.10]
    cover = [2.6, 3.4, 2.9, 3.8, 3.1]
    fit = fit_priors_from_history({
        "monthly_ending_arr": MONTHLY_ARR,
        "periods": MONTHLY_PERIODS,
        "cpl_log_ratios": cpl,
        "cpl_periods": [f"2025-{m:02d}" for m in range(1, 7)],
        "pipeline_cover": cover,
        "pipeline_cover_periods": ["2024-Q4", "2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"],
        "source": "warehouse",
    })
    assert set(fit["fitted"]) == {"yoyPp", "cplLog", "pipe"}

    def sd(xs):
        mu = sum(xs) / len(xs)
        return math.sqrt(sum((x - mu) ** 2 for x in xs) / (len(xs) - 1))

    assert math.isclose(fit["priors"]["cplLog"], sd(cpl), rel_tol=1e-9)
    assert math.isclose(fit["priors"]["pipe"], sd(cover), rel_tol=1e-9)
    basis = fit["method_card"]["history_basis"]
    assert basis["cplLog"]["method"] == "same_month_yoy_log_cpl" and basis["cplLog"]["span"] == "2025-01..2025-06"
    assert basis["pipe"]["method"] == "quarterly_pipeline_over_won" and basis["pipe"]["span"] == "2024-Q4..2025-Q4"
    notes = " ".join(fit["method_card"]["notes"])
    assert "Cost per lead history: 6 observations" in notes
    assert "Pipeline coverage history: 5 observations" in notes


def test_a_measured_spread_outside_the_bounds_is_reported_not_hidden():
    flat_cover = [3.3333333, 3.3333334, 3.3333332, 3.3333333]
    fit = fit_priors_from_history({"pipeline_cover": flat_cover, "source": "warehouse"})
    assert fit["priors"]["pipe"] == 0.15
    assert fit["method_card"]["history_basis"]["pipe"]["measured"] < 1e-6
    assert any("pipeline coverage measured sd" in n and "drawn at 0.150" in n for n in fit["method_card"]["notes"])


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


def test_growth_cpl_correlation_widens_the_joint_cash_tail():
    """Growth down with CPL up stacks two cash headwinds (less billing, dearer leads); positive rho offsets them."""

    priors = {"yoyPp": 3.0, "cplLog": 0.6}
    neg = run_packet_monte_carlo(PACKET, n=4000, seed=5, priors=priors, correlations={"yoyPp:cplLog": -0.8})
    ind = run_packet_monte_carlo(PACKET, n=4000, seed=5, priors=priors)
    pos = run_packet_monte_carlo(PACKET, n=4000, seed=5, priors=priors, correlations={"yoyPp:cplLog": 0.8})

    assert neg.cash["sd"] > ind.cash["sd"] > pos.cash["sd"]
    assert neg.cash["p10"] < ind.cash["p10"] < pos.cash["p10"]
    assert neg.correlations == {"yoyPp:cplLog": -0.8}
    assert ind.correlations == {}
    assert any("Correlated lever draws" in n for n in neg.method_notes)
    assert any("Independent lever draws" in n for n in ind.method_notes)


def test_growth_shock_moves_arr_by_bop_over_the_open_months_only():
    only_growth = {k: PACKET[k] for k in ("bop_arr", "dec_arr", "target_arr", "close_month_idx")}
    res = run_packet_monte_carlo(only_growth, n=4000, seed=2, priors={"yoyPp": 4.0})
    # 6 open months: sd = BOP x 4pp x 6/12.
    assert math.isclose(res.arr["sd"], 90e6 * 0.04 * 0.5, rel_tol=0.05)
    assert math.isclose(res.arr["mean"], 108e6, rel_tol=0.002)


def test_closed_months_stay_on_plan_and_residual_is_the_measured_spread():
    only_resid = {
        "cash_by_month": [12e6] * 12,
        "end_cash": 12e6,
        "close_month_idx": 5,
        "cfo_plan_error_sd": 200_000.0,
    }
    res = run_packet_monte_carlo(only_resid, n=4000, seed=4)
    for m in res.cash_path_monthly[:6]:
        assert m["p10"] == m["p90"] == 12e6
    # Six open months of independent monthly error: Dec sd = 200k x sqrt(6).
    assert math.isclose(res.cash["sd"], 200_000.0 * math.sqrt(6), rel_tol=0.05)


def test_inputs_that_are_not_loaded_are_reported_not_defaulted():
    res = run_packet_monte_carlo({"cash_by_month": [12e6] * 12}, n=100, seed=1)
    assert res.p_arr_miss is None and res.arr is None
    assert res.p_ae_short is None
    assert res.p_cash_below_floor is None and res.p_ops_liquidity is None and res.p_trough_breach is None
    notes = " ".join(res.method_notes)
    for missing in ("ARR is not simulated", "AE shortfall is not reported", "Cash floor not loaded",
                    "cost-per-lead shock does not move cash", "coverage shock does not move ARR",
                    "no residual cash noise"):
        assert missing in notes
    # Nothing moves the plan path when no lever input is loaded.
    assert res.cash["sd"] == 0.0

    no_target = run_packet_monte_carlo({k: v for k, v in PACKET.items() if k != "target_arr"}, n=100, seed=1)
    assert no_target.arr is not None and no_target.p_arr_miss is None
    assert "miss rate is not reported" in " ".join(no_target.method_notes)

    no_cash = run_packet_monte_carlo({k: v for k, v in PACKET.items() if k != "cash_by_month"}, n=100, seed=1)
    assert no_cash.cash == {} and no_cash.cash_path_monthly == [] and no_cash.p_cash_below_floor is None


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
