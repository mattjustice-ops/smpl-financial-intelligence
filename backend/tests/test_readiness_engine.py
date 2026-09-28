"""Readiness Score engine — CAL.4–CAL.7 rules."""

from __future__ import annotations

from app.services.readiness.engine import assess, validate_answers
from app.services.readiness.registry import MODULES, OBJECTS, ObjectEvidence

ALL_GATES_YES = {"0.1": "yes", "0.2": "yes", "0.3": "yes", "0.4": "yes", "0.5": "yes"}
NORMALIZED = {"4.1": "exclude", "4.2": "exclude", "4.3": "not_applicable", "9.1": "resolved"}
POLICIES_YES = {q: "yes" for q in ("7.7", "7.8", "7.9", "7.10", "7.11", "7.12", "7.13")}


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
    r = assess(full_evidence(), {**ALL_GATES_YES, "9.1": "resolved", **POLICIES_YES})
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


def test_validate_answers():
    assert validate_answers({"0.1": "yes", "4.1": "exclude", "7.7": None}) == []
    errs = validate_answers({"0.1": "maybe", "99.9": "yes"})
    assert len(errs) == 2
