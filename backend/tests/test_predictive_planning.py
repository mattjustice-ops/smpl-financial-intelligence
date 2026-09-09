"""PPI Phase 1 — constraints registry, feasibility runner, What Has To Be True.

The parity tests matter most: thresholds here must match ``runBudgetRiskChecks`` in
``frontend/public/budget-engine/index.html``. If the Budget Engine and this module
disagree, the same plan gets two verdicts.
"""

from __future__ import annotations

import pytest

from app.services.predictive_planning.constraints import REGISTRY_BY_ID, resolve_constraints
from app.services.predictive_planning.feasibility import run_feasibility
from app.services.predictive_planning.what_has_to_be_true import generate_what_has_to_be_true


def healthy_packet() -> dict:
    """A plan where every constraint passes."""
    return {
        "period_label": "FY2027 Budget",
        "budget_year": 2027,
        "yoy_growth_pct": 20.0,
        "bop_arr": 90_291_801.85,
        "dec_arr": 108_350_162.22,
        "target_arr": 108_350_162.22,
        "fy_nn": 18_058_360.37,
        "fy_rev": 99_000_000.0,
        "fy_ebitda": 4_000_000.0,
        "end_cash": 14_000_000.0,
        "cash_floor": 10_000_000.0,
        "min_cash": 11_500_000.0,
        "min_cash_period": "2027-07",
        "fy_mkt": 12_000_000.0,
        "fy_mql": 24_000.0,
        "fy_ch_mql": 24_000.0,
        "fy_spend_id": 12_000_000.0,
        "mix_dev_max": 0.001,
        "avg_grr": 0.94,
        "min_grr": 0.93,
        "sales_end": 42.0,
        "cs_end": 18.0,
        "ae_needed": 40.0,
        "cs_needed": 17.0,
        "cover_pct": 65.0,
        "hire_pct": 35.0,
        "bench_target": 60.0,
        "jan_hc": 150.0,
        "jan_hc_expected": 150.0,
        "dec_hc": 190.0,
        "pipeline_coverage": 3.0,
        "pipeline_min": 2.5,
        "fy_is_sm": 30_000_000.0,
        "fy_gtm_sm": 28_000_000.0,
    }


def test_healthy_plan_passes_every_constraint():
    report = run_feasibility(healthy_packet())
    assert report.verdict == "pass"
    assert report.counts["fail"] == 0
    assert report.counts["warn"] == 0
    assert report.counts["skipped"] == 0
    assert len(report.results) == len(REGISTRY_BY_ID)


def test_arr_path_tolerance_matches_budget_engine():
    """Budget Engine: ok when |gap| <= max(1000, target * 0.002)."""
    packet = healthy_packet()
    target = packet["target_arr"]

    packet["dec_arr"] = target + target * 0.0019
    inside = {r.id: r for r in run_feasibility(packet).results}["arr_path"]
    assert inside.status == "pass"

    packet["dec_arr"] = target - target * 0.005
    short = {r.id: r for r in run_feasibility(packet).results}["arr_path"]
    assert short.severity == "high"

    packet["dec_arr"] = target + target * 0.05
    above = {r.id: r for r in run_feasibility(packet).results}["arr_path"]
    assert above.severity == "low"
    assert above.status == "advisory"


def test_arr_bridge_identity_breaks_high():
    packet = healthy_packet()
    packet["fy_nn"] = packet["fy_nn"] - 5_000_000
    result = {r.id: r for r in run_feasibility(packet).results}["arr_bridge"]
    assert result.severity == "high"
    assert result.gap == pytest.approx(-5_000_000, abs=1.0)


@pytest.mark.parametrize(
    "min_grr,avg_grr,expected",
    [
        (0.93, 0.94, "ok"),
        (0.87, 0.90, "medium"),
        (0.80, 0.86, "high"),
    ],
)
def test_grr_floor_bands(min_grr, avg_grr, expected):
    packet = healthy_packet()
    packet["min_grr"] = min_grr
    packet["avg_grr"] = avg_grr
    assert {r.id: r for r in run_feasibility(packet).results}["grr_floor"].severity == expected


def test_cash_floor_hard_breach_ratio():
    """Below floor is medium; below 85% of floor escalates to high."""
    packet = healthy_packet()

    packet["end_cash"] = 9_000_000.0
    assert {r.id: r for r in run_feasibility(packet).results}["cash_floor"].severity == "medium"

    packet["end_cash"] = 8_000_000.0
    assert {r.id: r for r in run_feasibility(packet).results}["cash_floor"].severity == "high"


def test_cash_path_dip_is_medium_when_december_recovers():
    packet = healthy_packet()
    packet["min_cash"] = 8_000_000.0
    results = {r.id: r for r in run_feasibility(packet).results}
    assert results["cash_path"].severity == "medium"
    assert results["cash_floor"].severity == "ok"


def test_capacity_shortfalls_fail_hard():
    packet = healthy_packet()
    packet["sales_end"] = 30.0
    packet["cs_end"] = 10.0
    report = run_feasibility(packet)
    results = {r.id: r for r in report.results}
    assert results["nb_cover"].severity == "high"
    assert results["cs_cover"].severity == "high"
    assert report.verdict == "fail"


def test_missing_inputs_skip_rather_than_pass():
    packet = healthy_packet()
    packet["avg_grr"] = None
    packet["min_grr"] = None
    result = {r.id: r for r in run_feasibility(packet).results}["grr_floor"]
    assert result.status == "skipped"
    assert result.skipped_reason == "missing_inputs"


def test_packet_cash_floor_beats_registry_default():
    packet = healthy_packet()
    packet["cash_floor"] = 20_000_000.0
    resolved = {c.id: c for c in resolve_constraints(packet)}
    assert resolved["cash_floor"].params["floor"] == 20_000_000.0
    assert resolved["cash_floor"].param_sources["floor"] == "packet.cash_floor"
    # end_cash 14M now breaches the raised floor
    assert {r.id: r for r in run_feasibility(packet, list(resolved.values())).results}["cash_floor"].status != "pass"


def test_version_override_beats_tenant_and_packet():
    packet = healthy_packet()
    resolved = {
        c.id: c
        for c in resolve_constraints(
            packet,
            tenant_overrides={"cash_floor": {"floor": 15_000_000.0}},
            version_overrides={"cash_floor": {"floor": 5_000_000.0}},
        )
    }
    assert resolved["cash_floor"].params["floor"] == 5_000_000.0
    assert resolved["cash_floor"].param_sources["floor"] == "version"


def test_disabled_constraint_is_skipped():
    packet = healthy_packet()
    packet["sales_end"] = 1.0  # would otherwise fail hard
    resolved = resolve_constraints(packet, tenant_overrides={"nb_cover": {"enabled": False}})
    report = run_feasibility(packet, resolved)
    result = {r.id: r for r in report.results}["nb_cover"]
    assert result.status == "skipped"
    assert result.skipped_reason == "disabled_by_override"
    assert report.verdict == "pass"


def test_what_has_to_be_true_states_requirements_for_failures():
    packet = healthy_packet()
    packet["end_cash"] = 8_000_000.0
    packet["sales_end"] = 30.0

    report = run_feasibility(packet)
    conditions = generate_what_has_to_be_true(report)
    by_id = {c.constraint_id: c for c in conditions}

    assert by_id["cash_floor"].verdict == "must_close"
    assert "must reach at least" in by_id["cash_floor"].statement
    assert by_id["nb_cover"].verdict == "must_close"
    assert by_id["nb_cover"].levers  # remediation levers are attached
    assert all(c.rationale for c in conditions)


def test_what_has_to_be_true_orders_failures_first():
    packet = healthy_packet()
    packet["end_cash"] = 8_000_000.0  # fail
    packet["pipeline_coverage"] = 1.5  # warn
    conditions = generate_what_has_to_be_true(run_feasibility(packet))
    statuses = [c.verdict for c in conditions]
    assert statuses[0] == "must_close"


def test_stress_breaks_become_must_hold_conditions():
    report = run_feasibility(healthy_packet())
    conditions = generate_what_has_to_be_true(report, stress_breaks=["Dec cash floor", "NB AE cover"])
    by_id = {c.constraint_id: c for c in conditions}

    assert by_id["cash_floor"].verdict == "must_hold"
    assert by_id["cash_floor"].origin == "stress"
    assert by_id["nb_cover"].origin == "stress"


def test_stress_break_does_not_duplicate_an_existing_failure():
    packet = healthy_packet()
    packet["end_cash"] = 8_000_000.0
    report = run_feasibility(packet)
    conditions = generate_what_has_to_be_true(report, stress_breaks=["Dec cash floor"])
    cash_conditions = [c for c in conditions if c.constraint_id == "cash_floor"]
    assert len(cash_conditions) == 1
    assert cash_conditions[0].origin == "feasibility"


def test_include_passing_lists_load_bearing_assumptions():
    conditions = generate_what_has_to_be_true(run_feasibility(healthy_packet()), include_passing=True)
    assert conditions
    assert all(c.verdict == "must_hold" for c in conditions)


def test_registry_definitions_are_complete():
    """Every constraint needs a rationale and levers so WHTT text is never empty."""
    for definition in REGISTRY_BY_ID.values():
        assert definition.rationale, f"{definition.id} missing rationale"
        assert definition.levers, f"{definition.id} missing levers"
        assert definition.reads, f"{definition.id} missing reads"
