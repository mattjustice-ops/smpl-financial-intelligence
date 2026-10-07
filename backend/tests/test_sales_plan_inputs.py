"""Sales quota and comp plan answers (7.25–7.29) checked against the loaded sales team."""

from __future__ import annotations

import uuid

import pytest

from app.services.readiness.engine import _normalization_status, validate_answers

ORG = "8571e520-0687-4516-bdee-379f37c58c1f"
AGREES = {"7.25": "65", "7.26": "new_business_arr", "7.27": "monthly", "7.28": "account_executives",
          "7.29": "through_commission_plan"}


def _db(senior_target: str = "110000"):
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    s = Session(create_engine("sqlite://"))
    s.execute(text("create table actual_sales_quotas (organization_id text, period text, employee_id text, rep_name text, "
                   "quota_type text, ramped_monthly_quota_arr text, quota_attainment_actual_arr text, "
                   "quota_attainment_pct text)"))
    # Ann 120 of 100 in Jan, 0 in Feb; Bob 50 then 90: 260 of 400 ramped quota = 65%.
    for row in (("2026-01", "E1", "Ann", "Bookings ARR", "100", "120", "1.2"),
                ("2026-01", "E2", "Bob", "Bookings ARR", "100", "50", "0.5"),
                ("2026-02", "E1", "Ann", "Bookings ARR", "100", "0", "0"),
                ("2026-02", "E2", "Bob", "Bookings ARR", "100", "90", "0.9"),
                ("2026-02", "E3", "Sid", "Pipeline ARR", "25", "40", "1.6")):
        s.execute(text("insert into actual_sales_quotas values (:o, :p, :e, :n, :t, :r, :a, :pct)"),
                  dict(zip(("o", "p", "e", "n", "t", "r", "a", "pct"), (ORG, *row))))
    s.execute(text("create table actual_opportunities (organization_id text, period text, opportunity_id text, "
                   "opportunity_type text, close_status text, owner text, amount_arr text)"))
    for row in (("2026-01", "O1", "New Business", "Closed Won", "Ann", "120"),
                ("2026-01", "O2", "New Business", "Closed Won", "Bob", "50"),
                ("2026-02", "O3", "New Business", "Closed Won", "Bob", "90"),
                ("2026-02", "O4", "Expansion", "Closed Won", "Ann", "30"),
                ("2026-02", "O5", "New Business", "Open", "Ann", "500")):
        s.execute(text("insert into actual_opportunities values (:o, :p, :id, :k, :s, :w, :a)"),
                  dict(zip(("o", "p", "id", "k", "s", "w", "a"), (ORG, *row))))
    s.execute(text("create table actual_employees (organization_id text, employee_id text, employee_name text, "
                   "department text, role text, annual_quota_arr text, commission_target text)"))
    for row in (("E1", "Ann", "Sales", "Account Executive", "800000", "80000"),
                ("E2", "Bob", "Sales", "Senior Account Executive", "1100000", senior_target),
                ("E3", "Sid", "Sales", "Sales Development Rep", "300000", "25000"),
                ("E4", "Cara", "Customer Success", "Customer Success Manager", "450000", "15000")):
        s.execute(text("insert into actual_employees values (:o, :e, :n, :d, :r, :q, :t)"),
                  dict(zip(("o", "e", "n", "d", "r", "q", "t"), (ORG, *row))))
    s.execute(text("create table actual_commission_plans (organization_id text, plan_id text, "
                   "eligible_opportunity_type text, base_commission_rate text, accelerated_rate text, "
                   "accelerator_threshold text)"))
    for row in (("PLAN-AE-NEW", "New Business", "0.1", "0.15", "1.0"), ("PLAN-AM-EXP", "Expansion", "0.06", "0.078", "1.0"),
                ("PLAN-RENEWAL", "Renewal", "0.02", "0.02", "1.0")):
        s.execute(text("insert into actual_commission_plans values (:o, :p, :k, :b, :a, :t)"),
                  dict(zip(("o", "p", "k", "b", "a", "t"), (ORG, *row))))
    s.execute(text("create table actual_commission_payouts (organization_id text, period text, rep_id text, "
                   "plan_id text, commission_rate text)"))
    # Accelerated exactly when the month's attainment reached 100%.
    for row in (("2026-01", "E1", "PLAN-AE-NEW", "0.15"), ("2026-01", "E2", "PLAN-AE-NEW", "0.1"),
                ("2026-02", "E2", "PLAN-AE-NEW", "0.1"), ("2026-02", "E1", "PLAN-AM-EXP", "0.06")):
        s.execute(text("insert into actual_commission_payouts values (:o, :p, :r, :pl, :c)"),
                  dict(zip(("o", "p", "r", "pl", "c"), (ORG, *row))))
    return s


def _run(db, answers):
    from app.services.readiness.sales_plan_inputs import sales_plan

    return sales_plan(db, uuid.UUID(ORG), answers, "2026-06")


def test_answers_that_match_the_loaded_team_pass() -> None:
    out = _run(_db(), AGREES)
    assert {c["id"]: c["status"] for c in out["checks"]} == {
        "expected_attainment_vs_quotas": "pass",
        "quota_credit_vs_attainment": "pass",
        "attainment_period_vs_payouts": "pass",
        "expansion_owner_vs_opportunities": "pass",
        "variable_pay_vs_commission_plan": "pass",
    }
    m = out["measured"]
    assert m["closer_attainment"] == pytest.approx(0.65)
    assert m["months"] == ["2026-01", "2026-02"]
    assert m["quota_credit_matches"] == ["new_business_arr"]
    assert (m["accelerator_payouts_tested"], m["accelerator_payouts_off_monthly"]) == (4, 0)
    assert m["expansion_owners"] == {"account_executives": 1}
    assert out["missing"] == []


def test_answers_that_contradict_the_loaded_team_are_flagged() -> None:
    answers = {"7.25": "100", "7.26": "new_and_expansion_arr", "7.27": "quarterly", "7.28": "customer_success",
               "7.29": "through_commission_plan"}
    out = _run(_db(senior_target="75000"), answers)
    checks = {c["id"]: c for c in out["checks"]}
    assert {k: c["status"] for k, c in checks.items()} == {
        "expected_attainment_vs_quotas": "review",
        "quota_credit_vs_attainment": "conflict",
        "attainment_period_vs_payouts": "conflict",
        "expansion_owner_vs_opportunities": "conflict",
        "variable_pay_vs_commission_plan": "review",
    }
    assert "closers attained 65% of ramped quota" in checks["expected_attainment_vs_quotas"]["finding"]
    assert "Senior Account Executive: $110,000 at quota vs $75,000 commission target" in \
        checks["variable_pay_vs_commission_plan"]["finding"]


def test_bonus_in_addition_is_shown_for_review() -> None:
    out = _run(_db(), {"7.29": "bonus_in_addition"})
    assert [(c["id"], c["status"]) for c in out["checks"]] == [("variable_pay_vs_commission_plan", "review")]


def test_nothing_loaded_is_reported_not_assumed() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    out = _run(Session(create_engine("sqlite://")), AGREES)
    assert out["checks"] == []
    assert out["measured"]["closer_attainment"] is None
    assert any("actual_sales_quotas" in m for m in out["missing"])
    assert any("actual_opportunities" in m for m in out["missing"])
    assert any("actual_employees" in m for m in out["missing"])


def test_sales_plan_questions_validate_and_resolve() -> None:
    assert validate_answers({"7.25": "80", "7.26": "net_new_arr"}) == []
    assert validate_answers({"7.25": "83"}) == ["7.25: '83' is not one of " + ", ".join(str(p) for p in range(50, 125, 5))]
    assert _normalization_status({})["sales_plan"]["unresolved_questions"] == ["7.25", "7.26"]
    assert _normalization_status({"7.14": "capitalized"})["sales_plan"]["unresolved_questions"] == \
        ["7.25", "7.26", "7.27", "7.28", "7.29"]
    assert _normalization_status({"7.14": "capitalized", **AGREES})["sales_plan"]["resolved"] is True
