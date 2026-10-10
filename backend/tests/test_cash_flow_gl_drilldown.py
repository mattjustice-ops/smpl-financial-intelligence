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


def _vendor_db():
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    session = Session(create_engine("sqlite://"))
    session.execute(text("create table actual_vendor_payments (organization_id text, vendor_payment_id text, "
                         "period text, vendor_id text, vendor_name text, expense_category text, payment_date text, "
                         "amount text, bill_id text, due_date text, payment_method text, days_past_due text)"))
    payments = [
        ("VP-1", "2026-06", "Amazon Web Services", "Cloud Infrastructure", "2026-06-04", "1200.00", "B-1",
         "2026-06-04", "ACH", "0"),
        ("VP-2", "2026-06", "Summit Events Group", "Events and Webinars", "2026-06-18", "500.00", "B-2",
         "2026-06-01", "Check", "17"),
        ("VP-3", "2026-06", "Brennan Cole LLP", "Legal", "2026-06-25", "300.00", "B-3", "2026-06-20", "ACH", "5"),
        ("VP-4", "2026-05", "Summit Events Group", "Events and Webinars", "2026-07-02", "50.00", "B-4",
         "2026-06-30", "Check", "2"),
        ("VP-5", "2026-05", "Datadog", "Software", "2026-05-28", "999.00", "B-5", "2026-05-28", "Card", "0"),
    ]
    for row in payments:
        session.execute(text("insert into actual_vendor_payments values (:o, :id, :p, 'V', :n, :c, :pd, :a, :b, "
                             ":due, :m, :late)"),
                        dict(zip(("id", "p", "n", "c", "pd", "a", "b", "due", "m", "late"), row), o=ORG))
    return session


def test_vendor_cash_drills_into_payments_by_payment_date_and_flags_late() -> None:
    import uuid

    from app.services.dashboard.cash_flow_gl_drilldown_service import cash_flow_drilldown

    res = cash_flow_drilldown(_vendor_db(), uuid.UUID(ORG), scenario="Actual", period="2026-06",
                              waterfall_type="vendor_cash_out", expected_amount=Decimal("-2000.00"))
    assert sorted(line.account_name for line in res.lines) == ["Bill B-1", "Bill B-2", "Bill B-3"]
    assert {line.detail_type for line in res.lines} == {"payment"}
    assert res.signed_total == Decimal("-2000.00")
    assert [v.status for v in res.validation] == ["pass"]
    late = {line.vendor_name: line.days_past_due for line in res.lines}
    assert late == {"Amazon Web Services": 0, "Summit Events Group": 17, "Brennan Cole LLP": 5}
    summit = next(line for line in res.lines if line.vendor_name == "Summit Events Group")
    assert summit.notes == "paid 2026-06-18; due 2026-06-01; 17 days late; Check"
    assert res.message == ("2 of 3 vendor payments in 2026-06 were past due ($800, up to 17 days late): "
                           "Summit Events Group, Brennan Cole LLP.")

    july = cash_flow_drilldown(_vendor_db(), uuid.UUID(ORG), scenario="Actual", period="2026-07",
                               waterfall_type="vendor_cash_out")
    assert [line.account_name for line in july.lines] == ["Bill B-4"]

    on_time = cash_flow_drilldown(_vendor_db(), uuid.UUID(ORG), scenario="Actual", period="2026-05",
                                  waterfall_type="vendor_cash_out", expected_amount=Decimal("-1500.00"))
    assert on_time.message is None
    assert [v.status for v in on_time.validation] == ["fail"]


def test_vendor_cash_without_payments_falls_back_to_gl_and_says_so(monkeypatch) -> None:
    import uuid

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.services.dashboard import cash_flow_gl_drilldown_service as svc

    hosting = _entry(account_number="6410", account_name="Cloud Infrastructure", account_group="Hosting",
                     department="G&A", expense_type="Vendor", amount=Decimal("-700"))
    monkeypatch.setattr(svc, "_load_gl_entries_for_cell", lambda *_a, **_k: [(hosting, {"vendor_name": "AWS"})])
    res = svc.cash_flow_drilldown(Session(create_engine("sqlite://")), uuid.UUID(ORG), scenario="Budget",
                                  period="2026-09", waterfall_type="vendor_cash_out")
    assert [(line.account_number, line.detail_type) for line in res.lines] == [("6410", "gl")]
    assert res.message == svc.VENDOR_EXPENSE_NOTE


def test_gl_entry_matches_revenue_collections() -> None:
    entry = _entry(
        account_number="4000",
        account_name="Subscription Revenue",
        account_group="Subscription Revenue",
        department="Revenue",
        amount=Decimal("25000"),
    )
    assert gl_entry_matches("cash_collections", entry, {})
