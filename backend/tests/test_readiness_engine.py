"""Readiness Score engine — CAL.4–CAL.7 rules."""

from __future__ import annotations

from app.services.readiness.engine import assess, validate_answers
from app.services.readiness.registry import MODULES, OBJECTS, ObjectEvidence

ALL_GATES_YES = {"0.1": "yes", "0.2": "yes", "0.3": "yes", "0.4": "yes", "0.5": "yes"}
COMMISSION = {"7.14": "capitalized", "7.15": "60", "7.16": "60", "7.17": "expensed",
              "7.18": "month_of_booking", "7.19": "expensed", "7.20": "comp_tool",
              "7.21": "above_prior_arr", "7.22": "above_prior_arr", "7.23": "new_business_rate",
              "7.24": "above_prior_level"}
NORMALIZED = {"4.1": "exclude", "4.2": "exclude", "4.3": "not_applicable", "9.1": "resolved", **COMMISSION}
POLICIES_YES = {q: "yes" for q in ("7.7", "7.8", "7.9", "7.10", "7.11", "7.12", "7.13")}
# Shaped like the v6 demo GL at the June 2026 close.
V6_RECONCILIATION = {"first": "2026-01", "last": "2026-05", "tables": ["actual_commission_payouts"],
                     "payouts": 2_200_000.0, "commission_expense": 1_400_000.0,
                     "change_in_deferred_commissions": 800_000.0, "change_in_accrued_commissions": 0.0}
V6_FACTS = {"as_of": "2026-06", "deferred_commissions": 5_055_495.41, "accrued_commissions": 0.0,
            "commission_expense_12m": 3_700_000.0, "commission_expense_months": 12, "commission_payout_rows": 104,
            "payout_reconciliation": V6_RECONCILIATION}


def full_evidence(**overrides: ObjectEvidence) -> dict[str, ObjectEvidence]:
    ev = {oid: ObjectEvidence(present=True, confidence=1.0, rows=10) for oid in OBJECTS}
    ev.update(overrides)
    return ev


def module(result: dict, mid: str) -> dict:
    return next(m for m in result["modules"] if m["id"] == mid)


def test_everything_in_place_scores_100_and_all_ready():
    r = assess(full_evidence(), {**ALL_GATES_YES, **NORMALIZED, **POLICIES_YES})
    assert r["readiness_score"] == 100.0
    assert r["score_state"] == "final"
    assert r["summary"]["ready"] == len(MODULES)
    assert r["recommended_next"] == []


def test_failed_gate_produces_no_score():
    r = assess(full_evidence(), {**ALL_GATES_YES, "0.1": "no", **NORMALIZED})
    assert r["readiness_score"] is None
    assert r["score_state"] == "not_scored"
    assert r["gates"]["failed"] == ["0.1"]
    assert r["recommended_next"] == []


def test_pending_gates_are_provisional():
    r = assess(full_evidence(), {**NORMALIZED, **POLICIES_YES})
    assert r["score_state"] == "provisional"
    assert r["readiness_score"] == 100.0
    assert r["gates"]["pending"] == ["0.1", "0.2", "0.3", "0.4", "0.5"]


def test_partial_never_rounded_up():
    # 89% coverage against a 90% ready threshold stays PARTIAL.
    ev = full_evidence(arr_waterfall=ObjectEvidence(present=True, confidence=0.89, missing_periods=["2026-01"]))
    r = assess(ev, {**ALL_GATES_YES, **NORMALIZED, **POLICIES_YES})
    arr = module(r, "arr_analytics")
    assert arr["status"] == "PARTIAL"
    assert "CONFIDENCE_BELOW_READY_THRESHOLD" in arr["reasons"]
    assert any("2026-01" in p["text"] for p in arr["improvement_paths"])


def test_unresolved_subscription_gate_blocks_arr_ready():
    r = assess(full_evidence(), {**ALL_GATES_YES, "9.1": "resolved", **COMMISSION, **POLICIES_YES})
    arr = module(r, "arr_analytics")
    assert arr["status"] == "PARTIAL"
    assert "GATE_UNRESOLVED" in arr["reasons"]
    assert module(r, "financial_statements")["status"] == "READY"
    top = r["recommended_next"][0]
    assert top["kind"] == "questionnaire" and top["ref"] == "subscription"


def test_unresolved_crm_stage_blocks_pipeline_ready():
    answers = {**ALL_GATES_YES, **NORMALIZED, "9.1": "unresolved", **POLICIES_YES}
    r = assess(full_evidence(), answers)
    assert module(r, "pipeline_forecasting")["status"] == "PARTIAL"
    assert module(r, "gtm_analytics")["status"] == "PARTIAL"
    assert module(r, "cash_forecasting")["status"] == "READY"


def test_missing_objects_partial_with_connector_path():
    ev = full_evidence(health_score=ObjectEvidence(present=False, confidence=0.0))
    r = assess(ev, {**ALL_GATES_YES, **NORMALIZED, **POLICIES_YES})
    ren = module(r, "renewal_analytics")
    assert ren["status"] == "PARTIAL"
    assert ren["missing_objects"] == ["health_score"]
    assert ren["improvement_paths"][0]["kind"] == "connector"
    rec = next(x for x in r["recommended_next"] if x["ref"] == "CS")
    assert rec["expected_delta"] > 0 and "Renewal Analytics" in rec["modules_to_ready"]


def test_structural_ceiling_is_unavailable():
    ev = full_evidence(health_score=ObjectEvidence(present=False, confidence=0.0, structural=True))
    r = assess(ev, {**ALL_GATES_YES, **NORMALIZED, **POLICIES_YES})
    ren = module(r, "renewal_analytics")
    assert ren["status"] == "UNAVAILABLE"
    assert ren["reasons"] == ["STRUCTURAL_CEILING"]
    assert ren["contribution"] == 0
    assert not any(x["ref"] == "CS" for x in r["recommended_next"])


def test_cost_of_revenue_policy_gap_caps_management_pl():
    r = assess(full_evidence(), {**ALL_GATES_YES, **NORMALIZED, **POLICIES_YES, "7.7": "no"})
    mpl = module(r, "management_pl")
    assert mpl["status"] == "PARTIAL"
    assert "POLICY_GAP" in mpl["reasons"]
    assert module(r, "financial_statements")["status"] == "READY"
    assert any(x["ref"] == "7.7" and x["kind"] == "customer_action" for x in r["recommended_next"])


def test_monthly_accrual_gap_lowers_confidence():
    r = assess(full_evidence(), {**ALL_GATES_YES, **NORMALIZED, **POLICIES_YES, "7.10": "no"})
    bva = module(r, "budget_vs_actual")
    assert bva["confidence"] == 0.85
    assert bva["status"] == "PARTIAL"  # 85% < 90% ready threshold


def test_score_formula():
    # One module PARTIAL at 0.5 confidence; everything else READY at 1.0.
    ev = full_evidence(assumption_driver=ObjectEvidence(present=True, confidence=0.5))
    r = assess(ev, {**ALL_GATES_YES, **NORMALIZED, **POLICIES_YES})
    sp = module(r, "scenario_planning")
    assert sp["status"] == "PARTIAL"
    total_w = sum(m.weight for m in MODULES)
    expected = round((total_w - sp["weight"] + 0.5 * sp["weight"] * 0.5) / total_w * 100, 1)
    assert r["readiness_score"] == expected


BASE = {**ALL_GATES_YES, **NORMALIZED, **POLICIES_YES}
GATED = ("cash_forecasting", "scenario_planning", "board_reporting")


def without(*qids: str) -> dict[str, str]:
    return {k: v for k, v in BASE.items() if k not in qids}


def checks(r: dict) -> dict[str, str]:
    return {c["id"]: c["status"] for c in r["policy_checks"]}


def test_unanswered_commission_policy_blocks_cash_forecast_ready():
    r = assess(full_evidence(), without(*COMMISSION))
    gate = next(g for g in r["normalization_gates"] if g["id"] == "commission_policy")
    assert gate["unresolved_questions"] == ["7.14"]
    for mid in GATED:
        assert module(r, mid)["status"] == "PARTIAL" and "GATE_UNRESOLVED" in module(r, mid)["reasons"]
    assert module(r, "financial_statements")["status"] == "READY"
    assert any(x["ref"] == "commission_policy" for x in r["recommended_next"])


def test_commission_gate_requirements_follow_the_policy_answer():
    def unresolved(answers):
        r = assess(full_evidence(), answers)
        return next(g for g in r["normalization_gates"] if g["id"] == "commission_policy")["unresolved_questions"]

    assert unresolved({**BASE, "7.14": "not_sure"}) == ["7.14"]
    assert unresolved({**without("7.15", "7.16")}) == ["7.15", "7.16"]
    assert unresolved({**BASE, "7.15": "not_applicable"}) == ["7.15"]
    assert unresolved({**without("7.15", "7.16"), "7.14": "expensed"}) == []
    assert unresolved({**without("7.21", "7.24"), "7.14": "expensed"}) == ["7.21", "7.24"]
    assert unresolved({**without(*COMMISSION), "7.14": "no_commissions"}) == []


def test_policy_and_gl_agree_scores_100():
    r = assess(full_evidence(), BASE, V6_FACTS)
    assert set(checks(r).values()) == {"pass"}
    assert set(checks(r)) == {"deferred_commissions_in_gl", "commission_expense_in_gl", "amortization_period_vs_gl",
                              "accrued_commissions_in_gl", "commission_payouts_tie_to_gl", "commission_payout_detail"}
    assert r["readiness_score"] == 100.0


def test_capitalized_without_gl_asset_is_a_conflict():
    r = assess(full_evidence(), BASE, {**V6_FACTS, "deferred_commissions": 0.0})
    assert checks(r)["deferred_commissions_in_gl"] == "conflict"
    for mid in GATED:
        assert module(r, mid)["status"] == "PARTIAL" and "POLICY_CONFLICT" in module(r, mid)["reasons"]
    assert module(r, "financial_statements")["status"] == "READY"
    rec = next(x for x in r["recommended_next"] if x["ref"] == "deferred_commissions_in_gl")
    assert rec["expected_score"] == 100.0


def test_expensed_with_gl_asset_is_a_conflict():
    r = assess(full_evidence(), {**without("7.15", "7.16"), "7.14": "expensed"}, V6_FACTS)
    assert checks(r)["deferred_commissions_in_gl"] == "conflict"
    assert "amortization_period_vs_gl" not in checks(r)


def test_no_commissions_with_commission_expense_is_a_conflict():
    r = assess(full_evidence(), {**without(*COMMISSION), "7.14": "no_commissions"},
               {**V6_FACTS, "deferred_commissions": 0.0})
    assert checks(r) == {"deferred_commissions_in_gl": "pass", "commission_expense_in_gl": "conflict"}


def test_missing_commission_expense_is_a_conflict():
    r = assess(full_evidence(), BASE, {**V6_FACTS, "commission_expense_12m": 0.0})
    assert checks(r)["commission_expense_in_gl"] == "conflict"


def test_balance_larger_than_the_amortization_period_allows_is_a_conflict():
    # $5.06M of deferred commissions is ~16 months of expense: fine for 60 months, impossible for 12.
    r = assess(full_evidence(), {**BASE, "7.15": "12", "7.16": "12"}, V6_FACTS)
    assert checks(r)["amortization_period_vs_gl"] == "conflict"
    assert checks(assess(full_evidence(), {**BASE, "7.15": "24", "7.16": "12"}, V6_FACTS))[
        "amortization_period_vs_gl"] == "pass"


def test_lagged_payout_without_accrual_conflicts_and_unexpected_accrual_is_review():
    lagged = assess(full_evidence(), {**BASE, "7.18": "month_after_booking"}, V6_FACTS)
    assert checks(lagged)["accrued_commissions_in_gl"] == "conflict"
    unexpected = assess(full_evidence(), BASE, {**V6_FACTS, "accrued_commissions": 50_000.0})
    assert checks(unexpected)["accrued_commissions_in_gl"] == "review"
    assert module(unexpected, "cash_forecasting")["status"] == "READY"


def test_payout_detail_missing_conflicts_and_no_system_is_review():
    r = assess(full_evidence(), BASE, {**V6_FACTS, "commission_payout_rows": 0})
    assert checks(r)["commission_payout_detail"] == "conflict"
    r = assess(full_evidence(), {**BASE, "7.20": "none"}, V6_FACTS)
    assert checks(r)["commission_payout_detail"] == "review"


def test_payouts_must_tie_to_expense_plus_asset_and_accrual_changes():
    # v5 shape: payouts paid in cash, but only a sliver of them reached the GL.
    v5 = {**V6_RECONCILIATION, "commission_expense": 137_000.0, "change_in_deferred_commissions": 0.0}
    r = assess(full_evidence(), BASE, {**V6_FACTS, "payout_reconciliation": v5})
    c = next(c for c in r["policy_checks"] if c["id"] == "commission_payouts_tie_to_gl")
    assert c["status"] == "conflict" and "difference $2,063,000" in c["finding"]
    # An accrual build-up explains the gap: expense booked, cash not yet paid.
    accrued = {**V6_RECONCILIATION, "commission_expense": 1_500_000.0, "change_in_accrued_commissions": 100_000.0}
    assert checks(assess(full_evidence(), BASE, {**V6_FACTS, "payout_reconciliation": accrued}))[
        "commission_payouts_tie_to_gl"] == "pass"
    # Within 1% passes; beyond it does not.
    near = {**V6_RECONCILIATION, "payouts": 2_215_000.0}
    far = {**V6_RECONCILIATION, "payouts": 2_240_000.0}
    assert checks(assess(full_evidence(), BASE, {**V6_FACTS, "payout_reconciliation": near}))[
        "commission_payouts_tie_to_gl"] == "pass"
    assert checks(assess(full_evidence(), BASE, {**V6_FACTS, "payout_reconciliation": far}))[
        "commission_payouts_tie_to_gl"] == "conflict"


def test_unreadable_facts_skip_checks_rather_than_assume():
    r = assess(full_evidence(), BASE, {"as_of": "2026-06", "deferred_commissions": None, "accrued_commissions": None,
                                       "commission_expense_12m": None, "commission_payout_rows": None})
    assert r["policy_checks"] == []
    assert assess(full_evidence(), BASE)["policy_checks"] == []


def test_validate_answers():
    assert validate_answers({"0.1": "yes", "4.1": "exclude", "7.7": None}) == []
    errs = validate_answers({"0.1": "maybe", "99.9": "yes"})
    assert len(errs) == 2
