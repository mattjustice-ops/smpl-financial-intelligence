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
    return s


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
