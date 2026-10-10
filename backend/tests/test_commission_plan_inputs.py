"""Commission inputs for the planning engines: opening runoff, rates and read-only policy."""

from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.readiness.commission_plan_inputs import cumulative_amortization, opening_layer

ORG = "8571e520-0687-4516-bdee-379f37c58c1f"
SCHEDULE_COLS = ("organization_id text, version text, period text, plan_id text, commission_base_arr text, "
                 "commission_rate text, commission_payout text, capitalize text, capitalized_amount text, "
                 "expensed_amount text, amortization_months text, source text")
ROLLFORWARD_COLS = ("organization_id text, version text, period text, ending_deferred_commissions text, "
                    "current_portion text, total_commission_payouts text, payroll_tax_on_commissions text")
PLAN_COLS = ("organization_id text, plan_id text, role text, eligible_opportunity_type text, capitalize text, "
             "amortization_months text, payout_lag_months text, capitalize_payroll_taxes text")


def test_payout_month_carries_one_nth_and_runoff_ends_at_zero() -> None:
    cohorts = {"2026-12": [(Decimal("600.00"), 60)]}
    assert cumulative_amortization(cohorts, "2026-11") == Decimal("0.00")
    assert cumulative_amortization(cohorts, "2026-12") == Decimal("10.00")
    layer = opening_layer(cohorts, "2026-12")
    assert layer["balance"] == 590.0
    assert layer["current_portion"] == 120.0
    assert layer["noncurrent_portion"] == 470.0
    assert len(layer["runoff"]) == 59
    assert layer["runoff"][0] == {"period": "2027-01", "amortization": 10.0}
    assert layer["runoff"][-1]["period"] == "2031-11"


def test_runoff_is_exact_to_the_cent_and_ignores_later_cohorts() -> None:
    cohorts = {"2026-11": [(Decimal("100.00"), 3)], "2026-12": [(Decimal("50.00"), 12)],
               "2027-01": [(Decimal("999.00"), 12)]}
    layer = opening_layer(cohorts, "2026-12")
    # 100/3 x 2 + 50/12 = 70.8333 -> 70.83 amortized through Dec.
    assert layer["balance"] == pytest.approx(150.0 - 70.83)
    assert sum(r["amortization"] for r in layer["runoff"]) == pytest.approx(layer["balance"])
    assert layer["current_portion"] == pytest.approx(layer["balance"])
    assert layer["runoff"][0]["amortization"] == pytest.approx(37.50)


def _db(rollforward_balance: str = "640.00"):
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    s = Session(create_engine("sqlite://"))
    for v in ("actual", "forecast"):
        s.execute(text(f"create table {v}_commission_schedule ({SCHEDULE_COLS})"))
        s.execute(text(f"create table {v}_deferred_commissions_rollforward ({ROLLFORWARD_COLS})"))
    s.execute(text(f"create table forecast_commission_plans ({PLAN_COLS})"))
    for plan, kind, cap, months in (("PLAN-AE-NEW", "New Business", "Y", "60"), ("PLAN-AM-EXP", "Expansion", "Y", "60"),
                                    ("PLAN-RENEWAL", "Renewal", "N", "0")):
        s.execute(text("insert into forecast_commission_plans values (:o, :p, 'r', :k, :c, :m, '0', 'N')"),
                  {"o": ORG, "p": plan, "k": kind, "c": cap, "m": months})
    rows = [
        ("actual", "2026-05", "PLAN-AE-NEW", "1000", "150.00", "Y", "150.00", "60"),
        ("actual", "2026-06", "PLAN-AE-NEW", "2000", "300.00", "Y", "300.00", "60"),
        ("actual", "2026-06", "PLAN-RENEWAL", "5000", "100.00", "N", "0.00", "0"),
        ("forecast", "2026-07", "PLAN-AM-EXP", "1000", "60.00", "Y", "60.00", "60"),
        ("forecast", "2026-07", "PLAN-RENEWAL", "6000", "120.00", "N", "0.00", "0"),
        ("forecast", "2026-08", "PLAN-AE-NEW", "1000", "150.00", "Y", "150.00", "60"),
    ]
    for v, period, plan, base, payout, cap, capped, months in rows:
        s.execute(text(f"insert into {v}_commission_schedule values (:o, :v, :p, :pl, :b, '', :pay, :c, :ca, '', :m, '')"),
                  {"o": ORG, "v": v.title(), "p": period, "pl": plan, "b": base, "pay": payout, "c": cap,
                   "ca": capped, "m": months})
    s.execute(text("insert into forecast_deferred_commissions_rollforward values (:o, 'Forecast', '2026-08', :b, "
                   "'132.00', '330.00', '27.06')"), {"o": ORG, "b": rollforward_balance})
    s.execute(text(f"create table actual_opportunities ({OPP_COLS})"))
    s.execute(text(f"create table actual_commission_payouts ({PAYOUT_COLS})"))
    for opp, cust, period, kind, status, amount in OPPS:
        s.execute(text("insert into actual_opportunities values (:o, 'Actual', :p, :id, :c, :k, :s, :a)"),
                  {"o": ORG, "p": period, "id": opp, "c": cust, "k": kind, "s": status, "a": amount})
    s.execute(text("insert into actual_commission_payouts values (:o, 'Actual', '2026-03', 'O-R1', 'A', '120', "
                   "'18.00', 'PLAN-AE-NEW')"), {"o": ORG})
    return s


OPP_COLS = ("organization_id text, version text, period text, opportunity_id text, customer_id text, "
            "opportunity_type text, close_status text, amount_arr text")
PAYOUT_COLS = ("organization_id text, version text, period text, opportunity_id text, customer_id text, "
               "booked_arr text, commission_amount text, plan_id text")
OPPS = (
    # A left with 100 and came back at 120: 20 above its prior ARR.
    ("O-C1", "A", "2026-01", "Churn", "Churn", "100"),
    ("O-R1", "A", "2026-03", "Reactivation", "Closed Won", "120"),
    # B came back with no departure on record.
    ("O-R2", "B", "2026-04", "Reactivation", "Closed Won", "50"),
    # C contracted 30, then expanded 50 (30 recovered, 20 above) and 40 more (all above).
    ("O-X1", "C", "2026-02", "Contraction", "Contraction", "30"),
    ("O-E1", "C", "2026-04", "Expansion", "Closed Won", "50"),
    ("O-E2", "C", "2026-06", "Expansion", "Closed Won", "40"),
    # An open expansion is not a booking; a later churn and same-month return pays only above it.
    ("O-E3", "C", "2026-07", "Expansion", "Open", "500"),
    ("O-C2", "D", "2026-05", "Churn", "Churn", "80"),
    ("O-R3", "D", "2026-05", "Reactivation", "Closed Won", "60"),
)


@pytest.fixture
def no_answers(monkeypatch):
    import app.services.readiness.evidence as evidence
    import app.services.readiness.service as service

    monkeypatch.setattr(service, "get_answers", lambda db, org: None)
    monkeypatch.setattr(evidence, "build_commission_facts", lambda db, org: {"as_of": "2026-06"})


def test_plan_inputs_chain_actual_then_forecast_and_tie_to_the_rollforward(no_answers) -> None:
    from app.services.readiness.commission_plan_inputs import build_plan_inputs

    org = SimpleNamespace(id=uuid.UUID(ORG))
    # Cohorts 150 (May) + 300 (Jun) + 60 (Jul) + 150 (Aug) = 660; amortized through Aug:
    # 150 x 4/60 + 300 x 3/60 + 60 x 2/60 + 150 x 1/60 = 10 + 15 + 2 + 2.5 = 29.50 -> balance 630.50.
    out = build_plan_inputs(_db("630.50"), org, "2026-08")
    opening = out["opening"]
    assert opening["balance"] == pytest.approx(630.50)
    assert opening["source_tables"] == ["actual_commission_schedule", "forecast_commission_schedule"]
    assert opening["first_cohort"] == "2026-05"
    assert opening["amortization_months"] == [60]
    assert sum(r["amortization"] for r in opening["runoff"]) == pytest.approx(630.50)
    assert opening["current_portion"] == pytest.approx(132.0)
    assert [c["status"] for c in out["checks"]] == ["pass", "pass"]

    assert out["rates"]["new_business"]["rate"] == pytest.approx(600 / 4000)
    assert out["rates"]["expansion"]["rate"] == pytest.approx(0.06)
    assert out["rates"]["renewal"]["rate"] == pytest.approx(0.02)
    assert out["rates"]["renewal"]["base_by_period"] == {"2026-06": 5000.0, "2026-07": 6000.0}
    assert out["payroll_tax_rate"] == pytest.approx(27.06 / 330.0)
    assert out["policy"]["answered"] is False
    assert out["policy"]["gate_resolved"] is False
    assert out["missing"] == []


def test_a_schedule_that_does_not_tie_is_a_conflict_and_gaps_are_reported(no_answers) -> None:
    from sqlalchemy import text

    from app.services.readiness.commission_plan_inputs import build_plan_inputs

    org = SimpleNamespace(id=uuid.UUID(ORG))
    out = build_plan_inputs(_db("640.00"), org, "2026-08")
    assert [c["status"] for c in out["checks"]] == ["conflict", "pass"]
    assert "difference -9.50" in out["checks"][0]["finding"]

    db = _db("630.50")
    db.execute(text("insert into forecast_commission_schedule values (:o, 'Forecast', '2026-08', 'PLAN-X', '1', '', "
                    "'1.00', 'Y', '1.00', '', '', '')"), {"o": ORG})
    out = build_plan_inputs(db, org, "2026-10")
    assert any("2026-09–2026-10" in m for m in out["missing"])
    assert any("PLAN-X" in m and "no amortization months" in m for m in out["missing"])
    assert any("PLAN-X" in m and "not in the commission plans" in m for m in out["missing"])
    assert any("roll-forward row at 2026-10" in m for m in out["missing"])


def test_return_history_measures_arr_above_the_prior_level(no_answers) -> None:
    from app.services.readiness.commission_plan_inputs import build_plan_inputs

    out = build_plan_inputs(_db("630.50"), SimpleNamespace(id=uuid.UUID(ORG)), "2026-08")
    r = out["returns"]
    assert r["answers"] == {"7.21": None, "7.22": None, "7.23": None, "7.24": None}
    react = r["history"]["reactivation"]
    assert (react["count"], react["arr"], react["with_departure"], react["arr_with_departure"]) == (3, 230.0, 2, 180.0)
    assert react["above_baseline_arr"] == 20.0  # A: 120 - 100; D came back at 60 < 80
    assert react["above_baseline_share"] == pytest.approx(20 / 180)
    exp = r["history"]["expansion"]
    assert (exp["arr"], exp["above_prior_level_arr"]) == (90.0, 60.0)
    assert (r["history"]["source"], r["history"]["from"], r["history"]["to"]) == ("opportunities", "2026-01", "2026-07")
    assert r["loaded_practice"] == {"payouts": 1, "booked_arr": 120.0, "commission_base_arr": 120.0, "commission": 18.0,
                                    "paid_on_full_amount": True, "paid_above_prior_arr": None,
                                    "rate_type": "new_business"}
    assert r["checks"] == []


HISTORY_COLS = ("organization_id text, version text, period text, customer_id text, movement_type text, "
                "beginning_arr text, movement_arr text, ending_arr text, opportunity_id text")
HISTORY = (
    # A churned at 100 in 2024 and came back at 120 within the window (winback): 20 above.
    ("2023-12", "A", "Opening balance", "0", "100", "100", ""),
    ("2024-02", "A", "Churn", "100", "-100", "0", ""),
    ("2024-05", "A", "Reactivation", "0", "120", "120", "O-R1"),
    # P paused at 80, restarted at 50 (30 short), then expanded 40: 30 recovers the shortfall, 10 above.
    ("2023-12", "P", "Opening balance", "0", "80", "80", ""),
    ("2025-01", "P", "Pause", "80", "-80", "0", ""),
    ("2025-04", "P", "Reactivation", "0", "50", "50", "O-R2"),
    ("2025-09", "P", "Expansion", "50", "40", "90", "O-E1"),
    # N churned and came back as new business: nothing carries over.
    ("2023-12", "N", "Opening balance", "0", "70", "70", ""),
    ("2024-03", "N", "Churn", "70", "-70", "0", ""),
    ("2025-06", "N", "New Business", "0", "90", "90", ""),
    ("2025-08", "N", "Expansion", "90", "30", "120", ""),
    # Past the as-of month: ignored.
    ("2026-10", "A", "Contraction", "120", "-20", "100", ""),
)


def _history_db(payout_base: str | None):
    from sqlalchemy import text

    db = _db("630.50")
    db.execute(text(f"create table actual_customer_arr_history ({HISTORY_COLS})"))
    for period, cust, kind, beg, mv, end, opp in HISTORY:
        db.execute(text("insert into actual_customer_arr_history values (:o, 'Actual', :p, :c, :k, :b, :m, :e, :op)"),
                   {"o": ORG, "p": period, "c": cust, "k": kind, "b": beg, "m": mv, "e": end, "op": opp})
    if payout_base is not None:
        db.execute(text("alter table actual_commission_payouts add column commission_base_arr text"))
        db.execute(text("update actual_commission_payouts set commission_base_arr = :b, commission_amount = '3.00'"),
                   {"b": payout_base})
    return db


def test_customer_arr_history_measures_returns_with_every_departure_on_record(no_answers) -> None:
    from app.services.readiness.commission_plan_inputs import build_plan_inputs

    out = build_plan_inputs(_history_db("20"), SimpleNamespace(id=uuid.UUID(ORG)), "2026-08")
    hist = out["returns"]["history"]
    assert (hist["source"], hist["from"], hist["to"]) == ("customer_arr_history", "2023-12", "2025-09")
    react = hist["reactivation"]
    assert (react["count"], react["arr"], react["with_departure"], react["arr_with_departure"]) == (2, 170.0, 2, 170.0)
    assert react["above_baseline_arr"] == 20.0
    assert react["above_baseline_share"] == pytest.approx(20 / 170)
    assert react["after_cancelling"] == {"count": 1, "arr": 120.0}
    assert react["after_pause"] == {"count": 1, "arr": 50.0}
    assert react["back_as_new_business"] == 1
    assert (hist["expansion"]["arr"], hist["expansion"]["above_prior_level_arr"]) == (70.0, 40.0)
    assert "bases" not in hist
    practice = out["returns"]["loaded_practice"]
    assert (practice["booked_arr"], practice["commission_base_arr"]) == (120.0, 20.0)
    assert practice["paid_on_full_amount"] is False
    assert practice["paid_above_prior_arr"] is True
    assert out["missing"] == []


@pytest.mark.parametrize(("answer", "payout_base", "conflict"), [
    ("above_prior_arr", "20", None),
    ("above_prior_arr", "35", "pause_returns_above_prior_arr_vs_payouts"),
    ("full_amount", "20", "pause_returns_full_amount_vs_payouts"),
    ("full_amount", "120", None),
])
def test_return_answers_are_checked_against_the_payout_base(monkeypatch, answer, payout_base, conflict) -> None:
    import app.services.readiness.evidence as evidence
    import app.services.readiness.service as service
    from app.services.readiness.commission_plan_inputs import build_plan_inputs

    monkeypatch.setattr(service, "get_answers", lambda db, org: SimpleNamespace(answers={"7.22": answer}))
    monkeypatch.setattr(evidence, "build_commission_facts", lambda db, org: {"as_of": "2026-06"})
    out = build_plan_inputs(_history_db(payout_base), SimpleNamespace(id=uuid.UUID(ORG)), "2026-08")
    ids = [c["id"] for c in out["returns"]["checks"]]
    assert ids == ([conflict] if conflict else [])


def test_return_answers_that_contradict_the_loaded_payouts_are_conflicts(monkeypatch) -> None:
    import app.services.readiness.evidence as evidence
    import app.services.readiness.service as service
    from app.services.readiness.commission_plan_inputs import build_plan_inputs

    answers = {"7.21": "not_paid", "7.22": "above_prior_arr", "7.23": "expansion_rate", "7.24": "all_expansion"}
    monkeypatch.setattr(service, "get_answers", lambda db, org: SimpleNamespace(answers=answers))
    monkeypatch.setattr(evidence, "build_commission_facts", lambda db, org: {"as_of": "2026-06"})
    out = build_plan_inputs(_db("630.50"), SimpleNamespace(id=uuid.UUID(ORG)), "2026-08")
    r = out["returns"]
    assert r["answers"] == answers
    assert {c["id"]: c["status"] for c in r["checks"]} == {
        "cancel_returns_not_paid_vs_payouts": "conflict",
        "pause_returns_above_prior_arr_vs_payouts": "conflict",
        "return_rate_vs_payouts": "conflict",
    }
    assert "1 commissions ($18)" in r["checks"][0]["finding"]
    assert r["checks"][0]["finding"].startswith("7.21 says customers back after cancelling are not paid")
    assert "customers back after a pause" in r["checks"][1]["finding"]


def test_return_questions_name_how_the_customer_left_not_the_waterfall_line() -> None:
    from app.services.readiness.registry import COMMISSION_POLICY_GATE

    prompts = {q.id: q.prompt for q in COMMISSION_POLICY_GATE}
    assert "cancelling" in prompts["7.21"] and "restart window (4.10)" in prompts["7.21"]
    assert "pause of any length" in prompts["7.22"]
    assert "cancelling or a pause" in prompts["7.23"]
    for q in ("7.21", "7.22", "7.23"):
        assert "winbacks" not in prompts[q].lower() and "restarts" not in prompts[q].lower()


def test_no_opportunities_loaded_is_reported_not_assumed(no_answers) -> None:
    from sqlalchemy import text

    from app.services.readiness.commission_plan_inputs import build_plan_inputs

    db = _db("630.50")
    db.execute(text("delete from actual_opportunities"))
    out = build_plan_inputs(db, SimpleNamespace(id=uuid.UUID(ORG)), "2026-08")
    assert out["returns"]["history"]["reactivation"]["above_baseline_share"] is None
    assert out["returns"]["history"]["expansion"]["above_prior_level_share"] is None
    assert out["returns"]["loaded_practice"]["payouts"] == 0
    assert any("Neither actual_customer_arr_history nor actual_opportunities is loaded" in m for m in out["missing"])


CLAW_PLANS = {
    "PLAN-AE-NEW": {"plan_id": "PLAN-AE-NEW", "opportunity_type": "new_business", "clawback_window_months": 6},
    "PLAN-AM-EXP": {"plan_id": "PLAN-AM-EXP", "opportunity_type": "expansion", "clawback_window_months": 6},
    "PLAN-RENEWAL": {"plan_id": "PLAN-RENEWAL", "opportunity_type": "renewal", "clawback_window_months": 0},
}
# The three no-starts in the demo data: stopped paying after 0 and 2 months (clawed back in full) and after
# 7 months (outside the 6-month window, written down).
CLAWBACKS = [
    {"customer_id": "CUST-0765", "commission_paid": "15814.47", "months_paid_before_stop": "0",
     "treatment": "Clawed back", "clawback_amount": "15814.47", "unamortized_removed": "0"},
    {"customer_id": "CUST-0766", "commission_paid": "14386.62", "months_paid_before_stop": "2",
     "treatment": "Clawed back", "clawback_amount": "14386.62", "unamortized_removed": "0"},
    {"customer_id": "CUST-0767", "commission_paid": "8451.50", "months_paid_before_stop": "7",
     "treatment": "Written down", "clawback_amount": "0.00", "unamortized_removed": "7605.00"},
]


def _claw(answers, plans=CLAW_PLANS, rows=CLAWBACKS):
    from app.services.readiness.commission_plan_inputs import clawback_policy

    missing: list[str] = []
    out = clawback_policy(answers, plans, rows, missing)
    return out, {c["id"]: c["status"] for c in out["checks"]}, missing


def test_clawback_answers_that_match_the_plans_and_rows_pass() -> None:
    out, checks, missing = _claw({"7.41": "6", "7.42": "full"})
    assert checks == {"clawback_window_vs_plans": "pass", "clawbacks_follow_window": "pass",
                      "clawback_amount_vs_policy": "pass"}
    assert out["plan_windows"] == {"PLAN-AE-NEW": 6, "PLAN-AM-EXP": 6}
    assert out["loaded_practice"] == {"clawed_back": 2, "clawed_back_amount": pytest.approx(30201.09),
                                      "written_down": 1, "written_down_amount": pytest.approx(7605.0)}
    assert missing == []


def test_a_longer_window_than_the_plans_conflicts_with_the_write_down() -> None:
    _, checks, _ = _claw({"7.41": "12", "7.42": "full"})
    assert checks["clawback_window_vs_plans"] == "conflict"
    assert checks["clawbacks_follow_window"] == "conflict"  # month 7 is inside 12 but was written down


def test_prorated_answer_conflicts_with_full_recoveries() -> None:
    out, checks, _ = _claw({"7.41": "6", "7.42": "prorated"})
    assert checks["clawback_amount_vs_policy"] == "conflict"
    finding = next(c["finding"] for c in out["checks"] if c["id"] == "clawback_amount_vs_policy")
    assert "CUST-0766" in finding and "CUST-0765" not in finding  # 0 months paid: prorated is the full amount


def test_no_clawback_answer_conflicts_with_clawed_back_rows() -> None:
    _, checks, _ = _claw({"7.41": "none"})
    assert checks == {"clawback_window_vs_plans": "conflict", "clawbacks_follow_window": "conflict"}


def test_missing_windows_and_files_are_reported_not_assumed() -> None:
    plans = {k: dict(v, clawback_window_months=None) for k, v in CLAW_PLANS.items()}
    _, checks, missing = _claw({"7.41": "6"}, plans=plans, rows=None)
    assert checks == {}
    assert "Commission plan PLAN-AE-NEW has no clawback_window_months" in missing
    assert any("actual_commission_clawbacks is not loaded" in m for m in missing)


def test_unanswered_clawback_policy_runs_no_checks() -> None:
    out, checks, missing = _claw({})
    assert checks == {} and missing == []
    assert out["answers"] == {"7.41": None, "7.42": None}


def test_plan_inputs_report_the_clawback_policy(monkeypatch) -> None:
    import app.services.readiness.evidence as evidence
    import app.services.readiness.service as service
    from sqlalchemy import text

    from app.services.readiness.commission_plan_inputs import build_plan_inputs

    monkeypatch.setattr(service, "get_answers", lambda db, org: SimpleNamespace(answers={"7.41": "6", "7.42": "full"}))
    monkeypatch.setattr(evidence, "build_commission_facts", lambda db, org: {"as_of": "2026-06"})
    db = _db("630.50")
    db.execute(text("create table actual_commission_clawbacks (organization_id text, period text, customer_id text, "
                    "commission_paid text, months_paid_before_stop text, treatment text, clawback_amount text, "
                    "unamortized_removed text)"))
    for period, cid, paid, months, treatment, amount in (("2026-03", "A", "100.00", "1", "Clawed back", "100.00"),
                                                         ("2026-09", "B", "50.00", "0", "Clawed back", "50.00")):
        db.execute(text("insert into actual_commission_clawbacks values (:o, :p, :c, :paid, :m, :t, :a, '0')"),
                   {"o": ORG, "p": period, "c": cid, "paid": paid, "m": months, "t": treatment, "a": amount})
    out = build_plan_inputs(db, SimpleNamespace(id=uuid.UUID(ORG)), "2026-08")
    claw = out["clawbacks"]
    assert claw["loaded_practice"]["clawed_back"] == 1  # the September row is after as_of
    assert {c["id"]: c["status"] for c in claw["checks"]} == {"clawbacks_follow_window": "pass",
                                                              "clawback_amount_vs_policy": "pass"}
    # The test plans table has no clawback_window_months column.
    assert "Commission plan PLAN-AE-NEW has no clawback_window_months" in out["missing"]


TERM_PRORATED = [  # 12-month contracts: paid × (12 − months paid) / 12
    {"customer_id": "T0", "commission_paid": "1200.00", "months_paid_before_stop": "0", "treatment": "Clawed back",
     "clawback_amount": "1200.00", "contract_term_months": "12"},
    {"customer_id": "T3", "commission_paid": "1200.00", "months_paid_before_stop": "3", "treatment": "Clawed back",
     "clawback_amount": "900.00", "opportunity_id": "O-T3"},
]


def test_prorated_over_the_term_uses_the_row_or_its_opportunity_term() -> None:
    out, checks, missing = _claw({"7.41": "6", "7.42": "prorated_term"}, rows=TERM_PRORATED)
    check = next(c for c in out["checks"] if c["id"] == "clawback_amount_vs_policy")
    assert check["finding"].endswith("1 clawbacks recovered prorated over the contract term")  # T0 only
    assert any("T3: no contract term" in m for m in missing)

    from app.services.readiness.commission_plan_inputs import clawback_policy
    missing = []
    out = clawback_policy({"7.41": "6", "7.42": "prorated_term"}, CLAW_PLANS, TERM_PRORATED, missing, {"O-T3": 12})
    check = next(c for c in out["checks"] if c["id"] == "clawback_amount_vs_policy")
    assert check["status"] == "pass" and missing == []
    assert check["finding"] == "7.42 says prorated over the contract term; 2 clawbacks recovered prorated over the contract term"


def test_prorated_over_the_term_conflicts_with_full_recoveries_after_months_paid() -> None:
    rows = [dict(r, contract_term_months="12") for r in CLAWBACKS]
    out, checks, missing = _claw({"7.41": "6", "7.42": "prorated_term"}, rows=rows)
    assert checks["clawback_amount_vs_policy"] == "conflict" and missing == []
    finding = next(c["finding"] for c in out["checks"] if c["id"] == "clawback_amount_vs_policy")
    assert "CUST-0766 recovered 14,386.62 of 14,386.62 paid (prorated over the contract term: 11,988.85)" in finding
    assert "CUST-0765" not in finding  # 0 months paid: prorated is the full amount


def test_clawbacks_with_no_term_on_record_are_missing_not_assumed() -> None:
    out, checks, missing = _claw({"7.41": "6", "7.42": "prorated_term"})
    assert "clawback_amount_vs_policy" not in checks
    assert [m for m in missing if "no contract term" in m] == [
        "actual_commission_clawbacks CUST-0765: no contract term on the row (contract_term_months) or its "
        "opportunity, so the 7.42 amount can't be checked",
        "actual_commission_clawbacks CUST-0766: no contract term on the row (contract_term_months) or its "
        "opportunity, so the 7.42 amount can't be checked"]


def test_plan_inputs_read_the_term_from_the_booking_opportunity(monkeypatch) -> None:
    import app.services.readiness.evidence as evidence
    import app.services.readiness.service as service
    from sqlalchemy import text

    from app.services.readiness.commission_plan_inputs import build_plan_inputs

    monkeypatch.setattr(service, "get_answers",
                        lambda db, org: SimpleNamespace(answers={"7.41": "6", "7.42": "prorated_term"}))
    monkeypatch.setattr(evidence, "build_commission_facts", lambda db, org: {"as_of": "2026-06"})
    db = _db("630.50")
    db.execute(text("alter table actual_opportunities add column contract_term_months text"))
    db.execute(text("insert into actual_opportunities values (:o, 'Actual', '2026-01', 'O-T3', 'T3', 'New Business', "
                    "'Closed Won', '10000', '24')"), {"o": ORG})
    db.execute(text("create table actual_commission_clawbacks (organization_id text, period text, customer_id text, "
                    "opportunity_id text, commission_paid text, months_paid_before_stop text, treatment text, "
                    "clawback_amount text, unamortized_removed text)"))
    db.execute(text("insert into actual_commission_clawbacks values (:o, '2026-04', 'T3', 'O-T3', '2400.00', '3', "
                    "'Clawed back', '2100.00', '0')"), {"o": ORG})
    out = build_plan_inputs(db, SimpleNamespace(id=uuid.UUID(ORG)), "2026-08")
    checks = {c["id"]: c["status"] for c in out["clawbacks"]["checks"]}
    assert checks["clawback_amount_vs_policy"] == "pass"  # 2,400 × (24 − 3) / 24
    assert not any("no contract term" in m for m in out["missing"])
