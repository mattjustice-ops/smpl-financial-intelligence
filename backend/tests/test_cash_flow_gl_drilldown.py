"""Cash flow GL drilldown service tests."""

from __future__ import annotations

from decimal import Decimal

from app.services.dashboard.cash_flow_gl_drilldown_service import (
    CASH_BALANCE_TYPES,
    CASH_DRILLDOWN_TYPES,
    gl_entry_matches,
)
from app.services.management_pl.gl_hierarchy import GlEntry


def _entry(**kwargs) -> GlEntry:
    defaults = {
        "period": "2026-06",
        "version": "Forecast",
        "account_number": "6000",
        "account_name": "Engineering Payroll",
        "account_group": "Engineering Payroll",
        "section_key": "research_and_development",
        "department": "R&D",
        "source_department": "Engineering",
        "expense_type": "Payroll",
        "amount": Decimal("-10000"),
    }
    defaults.update(kwargs)
    return GlEntry(**defaults)


def test_cash_drilldown_type_sets() -> None:
    assert "payroll_cash_out" in CASH_DRILLDOWN_TYPES
    assert "beginning_cash" in CASH_BALANCE_TYPES
    assert "beginning_cash" not in CASH_DRILLDOWN_TYPES


def test_gl_entry_matches_payroll_not_commission() -> None:
    payroll = _entry(account_group="Engineering Payroll", account_name="Engineering Payroll")
    commission = _entry(account_group="Commissions", account_name="Sales Commissions")
    raw = {}
    assert gl_entry_matches("payroll_cash_out", payroll, raw)
    assert not gl_entry_matches("payroll_cash_out", commission, raw)
    assert gl_entry_matches("commission_cash_out", commission, raw)


def test_gl_entry_matches_vendor_with_vendor_name() -> None:
    entry = _entry(account_group="Software", account_name="SaaS Tools", amount=Decimal("-500"))
    raw = {"vendor_name": "Acme SaaS Co"}
    assert gl_entry_matches("vendor_cash_out", entry, raw)


ORG = "11111111-1111-1111-1111-111111111111"


def _commission_db():
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    session = Session(create_engine("sqlite://"))
    cols = "organization_id text, period text, rep_id text, rep_name text, customer_id text, opportunity_id text, " \
           "plan_id text, commission_amount text"
    session.execute(text(f"create table actual_commission_payouts ({cols})"))
    session.execute(text(f"create table actual_renewal_commissions ({cols})"))
    session.execute(text("create table actual_commission_schedule (organization_id text, period text, plan_id text, "
                         "commission_payout text, source text)"))
    payouts = [("2026-06", "A-1", "Jordan Wilson", "PLAN-AE-NEW", "1000.00"),
               ("2026-06", "A-2", "Avery Johnson", "PLAN-AM-EXP", "250.00"),
               ("2026-05", "A-1", "Jordan Wilson", "PLAN-AE-NEW", "999.00")]
    for period, rep, name, plan, amt in payouts:
        session.execute(text("insert into actual_commission_payouts values (:o, :p, :r, :n, 'C-1', 'O-1', :pl, :a)"),
                        {"o": ORG, "p": period, "r": rep, "n": name, "pl": plan, "a": amt})
    for plan, amt, src in (("PLAN-AE-NEW", "1000.00", "Actual_commission_payouts.csv"),
                           ("PLAN-AM-EXP", "250.00", "Actual_commission_payouts.csv"),
                           ("PLAN-RENEWAL", "80.00", "beginning ARR x renewal share x renewal rate")):
        session.execute(text("insert into actual_commission_schedule values (:o, '2026-06', :pl, :a, :s)"),
                        {"o": ORG, "pl": plan, "a": amt, "s": src})
    return session


def test_commission_cash_drills_into_payouts_and_labels_estimates() -> None:
    import uuid

    from app.services.dashboard.cash_flow_gl_drilldown_service import cash_flow_drilldown

    session = _commission_db()
    res = cash_flow_drilldown(session, uuid.UUID(ORG), scenario="Actual", period="2026-06",
                              waterfall_type="commission_cash_out", expected_amount=Decimal("-1330.00"))
    kinds = sorted((line.detail_type, line.account_group, line.amount) for line in res.lines)
    assert kinds == [("estimate", "PLAN-RENEWAL", Decimal("-80.00")),
                     ("payout", "PLAN-AE-NEW", Decimal("-1000.00")),
                     ("payout", "PLAN-AM-EXP", Decimal("-250.00"))]
    assert res.signed_total == Decimal("-1330.00")
    assert [v.status for v in res.validation] == ["pass"]
    assert "PLAN-RENEWAL" in (res.message or "")
    assert {line.source_table for line in res.lines} == {"actual_commission_payouts", "actual_commission_schedule"}

    off = cash_flow_drilldown(session, uuid.UUID(ORG), scenario="Actual", period="2026-06",
                              waterfall_type="commission_cash_out", expected_amount=Decimal("-1500.00"))
    assert [v.status for v in off.validation] == ["fail"]


def test_commission_cash_without_payouts_shows_expense_only_and_says_so(monkeypatch) -> None:
    import uuid

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.services.dashboard import cash_flow_gl_drilldown_service as svc

    expense = _entry(account_number="6200", account_name="Sales Commissions", account_group="Commissions",
                     amount=Decimal("120"))
    asset = _entry(account_number="1550", account_name="Deferred Commissions - Noncurrent",
                   account_group="Deferred Commissions", amount=Decimal("900"))
    monkeypatch.setattr(svc, "_load_gl_entries_for_cell", lambda *_a, **_k: [
        (expense, {"statement": "Income Statement"}), (asset, {"statement": "Balance Sheet"})])
    res = svc.cash_flow_drilldown(Session(create_engine("sqlite://")), uuid.UUID(ORG), scenario="Actual",
                                  period="2026-06", waterfall_type="commission_cash_out")
    assert [line.account_number for line in res.lines] == ["6200"]
    assert res.message == svc.COMMISSION_EXPENSE_NOTE


def test_gl_entry_matches_revenue_collections() -> None:
    entry = _entry(
        account_number="4000",
        account_name="Subscription Revenue",
        account_group="Subscription Revenue",
        department="Revenue",
        amount=Decimal("25000"),
    )
    assert gl_entry_matches("cash_collections", entry, {})
