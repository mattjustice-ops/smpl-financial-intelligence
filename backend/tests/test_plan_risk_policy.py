"""Plan risk policy (onboarding 7.43-7.58) resolution."""

from __future__ import annotations

from app.services.readiness.engine import normalize_answers
from app.services.readiness.plan_risk_policy import POLICY, resolve_policy
from app.services.readiness.registry import ALL_QUESTIONS, NORMALIZATION_GATES, PLAN_RISK

DECLARED = {"7.43": "25", "7.44": "50", "7.45": "85", "7.46": "5", "7.47": "15", "7.48": "12",
            "7.49": "35", "7.50": "25", "7.51": "0.5", "7.52": "2", "7.53": "15", "7.54": "5",
            "7.55": "5", "7.56": "1000000", "7.57": "2500000", "7.58": "20"}


def test_every_policy_key_is_a_registered_choice_question():
    assert [q.id for q in PLAN_RISK] == [qid for _, qid, _ in POLICY]
    assert NORMALIZATION_GATES["plan_risk"]["questions"] is PLAN_RISK
    for _, qid, _ in POLICY:
        q = ALL_QUESTIONS[qid]
        assert q.choices, qid
        assert DECLARED[qid] in q.choices, qid


def test_declared_answers_resolve_to_fractions_and_counts():
    out = resolve_policy(DECLARED)
    assert out["missing"] == [] and out["conflicts"] == []
    v = out["values"]
    assert v["cash_watch_shortfall"] == 0.25 and v["cash_alarm_shortfall"] == 0.5
    assert v["floor_hard_breach_share"] == 0.85
    assert v["p_floor_watch"] == 0.05 and v["p_floor_break"] == 0.15
    assert v["p_cash_watch_watch"] == 0.12 and v["p_cash_watch_break"] == 0.35
    assert v["p_arr_miss_watch"] == 0.25 and v["arr_miss_tolerance"] == 0.005
    assert v["named_breaks_for_break"] == 2 and isinstance(v["named_breaks_for_break"], int)
    assert v["program_cut"] == 0.15 and v["dso_improvement_days"] == 5
    assert v["case_cash_watch"] == 0.05 and v["case_overspend_watch"] == 0.2
    assert v["case_watch_amount"] == 1_000_000.0 and v["case_break_amount"] == 2_500_000.0


def test_case_materiality_break_must_exceed_watch():
    out = resolve_policy({**DECLARED, "7.57": "1000000"})
    assert out["conflicts"] == ["7.57 (1000000) is not above 7.56 (1000000)"]
    assert out["values"]["case_watch_amount"] is None and out["values"]["case_break_amount"] is None


def test_unanswered_questions_are_missing_not_defaulted():
    out = resolve_policy({"7.43": "25"})
    assert out["values"]["cash_watch_shortfall"] == 0.25
    assert all(v is None for k, v in out["values"].items() if k != "cash_watch_shortfall")
    assert out["missing"] == [qid for _, qid, _ in POLICY if qid != "7.43"]


def test_out_of_order_bands_are_conflicts_and_unset():
    answers = {**DECLARED, "7.44": "25", "7.47": "5"}
    out = resolve_policy(answers)
    assert len(out["conflicts"]) == 2
    v = out["values"]
    assert v["cash_watch_shortfall"] is None and v["cash_alarm_shortfall"] is None
    assert v["p_floor_watch"] is None and v["p_floor_break"] is None
    assert v["p_cash_watch_watch"] == 0.12


def test_answers_outside_the_choices_are_dropped_by_normalization():
    out = resolve_policy(normalize_answers({**DECLARED, "7.43": "33", "7.51": "abc"}))
    assert "7.43" in out["missing"] and "7.51" in out["missing"]
    assert out["values"]["cash_alarm_shortfall"] == 0.5
