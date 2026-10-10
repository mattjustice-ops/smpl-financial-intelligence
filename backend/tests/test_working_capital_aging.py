"""AP / AR aging, DPO / DSO and past-due vendors and customers for commentary and the board deck."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.commentary.attribution_verify import build_attribution_package_from_commentary_inputs
from app.services.commentary.schemas import CommentaryInputs
from app.services.dashboard.schemas import ExecutiveFlowResponse
from app.services.reporting.export.board_slides import _risk_matrix_callouts, _working_capital_rows
from app.services.reporting.export.board_commentary_service import SlideCommentary
from app.services.reporting.export.commentary_engine import _cash_commentary
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.working_capital_aging import working_capital_aging

ORG = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _table(session: Session, name: str, rows: list[dict]) -> None:
    cols = ["organization_id", *rows[0].keys()]
    session.execute(text(f"create table {name} ({', '.join(f'{c} text' for c in cols)})"))
    for row in rows:
        session.execute(
            text(f"insert into {name} values ({', '.join(':' + c for c in cols)})"),
            {"organization_id": str(ORG), **row},
        )


def _aging(period: str, vendor: str, current: str, d30: str = "0", d60: str = "0") -> dict:
    return {"period": period, "vendor_id": vendor[:3], "vendor_name": vendor, "current": current,
            "days_1_30": d30, "days_31_60": d60, "days_61_90": "0", "days_over_90": "0"}


def _db(*, ap_on_balance_sheet: str = "1650.00") -> Session:
    session = Session(create_engine("sqlite://"))
    _table(session, "actual_ap_aging", [
        _aging("2026-06", "Amazon Web Services", "1000.00"),
        _aging("2026-06", "Summit Events Group", "0", d30="400.00"),
        _aging("2026-06", "Brennan Cole LLP", "100.00", d30="50.00", d60="100.00"),
        _aging("2026-05", "Summit Events Group", "0", d30="999.00"),
    ])
    _table(session, "actual_vendor_bills", [
        {"bill_date": "2026-04-03", "amount": "1500.00"},
        {"bill_date": "2026-05-03", "amount": "1500.00"},
        {"bill_date": "2026-06-03", "amount": "1500.00"},
        {"bill_date": "2026-03-03", "amount": "9999.00"},
    ])
    _table(session, "actual_vendor_payments", [
        {"payment_date": "2026-06-04", "amount": "300.00", "days_past_due": "0"},
        {"payment_date": "2026-06-18", "amount": "200.00", "days_past_due": "12"},
        {"payment_date": "2026-05-18", "amount": "700.00", "days_past_due": "30"},
    ])
    _table(session, "actual_invoices", [
        {"customer_name": "Acme", "invoice_date": "2026-06-01", "due_date": "2026-07-01", "invoice_amount": "900.00",
         "payment_status": "Open"},
        {"customer_name": "Globex", "invoice_date": "2026-05-01", "due_date": "2026-05-31", "invoice_amount": "300.00",
         "payment_status": "Open"},
        {"customer_name": "Initech", "invoice_date": "2026-04-01", "due_date": "2026-06-30", "invoice_amount": "600.00",
         "payment_status": "Open"},
        {"customer_name": "Acme", "invoice_date": "2026-04-01", "due_date": "2026-05-01", "invoice_amount": "1200.00",
         "payment_status": "Paid"},
    ])
    _table(session, "actual_balance_sheet", [
        {"period": "2026-06-30", "accounts_payable": ap_on_balance_sheet, "accounts_receivable": "1800.00"},
    ])
    return session


def test_payables_aging_dpo_and_past_due_vendors() -> None:
    wc, checks = working_capital_aging(_db(), ORG, "2026-06")
    assert wc is not None
    assert wc.accounts_payable == Decimal("1650.00")
    assert wc.ap_aging_buckets["Current"] == Decimal("1100.00")
    assert wc.ap_aging_buckets["1-30 days past due"] == Decimal("450.00")
    assert wc.ap_past_due == Decimal("550.00")
    # AP / average monthly bills (April-June) x 30.4 days
    assert wc.dpo_days == Decimal("33.4")
    assert [(p.name, p.past_due, p.oldest_bucket) for p in wc.past_due_vendors] == [
        ("Summit Events Group", Decimal("400.00"), "1-30 days past due"),
        ("Brennan Cole LLP", Decimal("150.00"), "31-60 days past due"),
    ]
    assert (wc.vendor_payments, wc.late_vendor_payments, wc.late_vendor_payment_amount) == (2, 1, Decimal("200.00"))
    assert {c.validation_name: c.status for c in checks} == {
        "ap_aging_ties_balance_sheet": "pass", "open_invoices_tie_balance_sheet_ar": "pass"}


def test_receivables_aged_by_due_date_at_the_latest_close() -> None:
    wc, _ = working_capital_aging(_db(), ORG, "2026-06")
    assert wc is not None
    assert wc.accounts_receivable == Decimal("1800.00")
    # Due on the month-end is current; due May 31 is 30 days past due at June 30.
    assert wc.ar_aging_buckets["Current"] == Decimal("1500.00")
    assert wc.ar_past_due == Decimal("300.00")
    assert [(p.name, p.oldest_bucket) for p in wc.past_due_customers] == [("Globex", "1-30 days past due")]
    # AR / average monthly billings (April-June: 1800 + 900 + 300) x 30.4 days
    assert wc.dso_days == Decimal("54.7")
    assert any("no payment dates" in note for note in wc.notes)


def test_customer_aging_only_at_the_latest_close_and_checks_fail_on_breaks() -> None:
    wc, checks = working_capital_aging(_db(), ORG, "2026-05")
    assert wc is not None
    assert wc.accounts_payable == Decimal("999.00")
    assert wc.accounts_receivable is None and wc.past_due_customers == []
    assert any("only available at the latest close (2026-06)" in note for note in wc.notes)
    assert checks == []

    _, broken = working_capital_aging(_db(ap_on_balance_sheet="2000.00"), ORG, "2026-06")
    assert {c.validation_name: c.status for c in broken}["ap_aging_ties_balance_sheet"] == "fail"


def test_nothing_loaded_returns_none() -> None:
    assert working_capital_aging(Session(create_engine("sqlite://")), ORG, "2026-06") == (None, [])


def _bundle(**kwargs) -> ReportingBundle:
    org = str(ORG)
    return ReportingBundle(
        organization_id=org, scenario="Actual", start_period="2026-01", end_period="2026-06",
        as_of_period="2026-06", period_label="June 2026", currency="USD",
        executive_flow=ExecutiveFlowResponse(organization_id=org, scenario="Actual", start_period="2026-01",
                                             end_period="2026-06", as_of_period="2026-06"),
        **kwargs,
    )


def test_commentary_and_board_name_past_due_vendors_and_customers() -> None:
    wc, _ = working_capital_aging(_db(), ORG, "2026-06")
    bundle = _bundle(working_capital=wc)

    field = _cash_commentary(bundle, "2026-06")
    assert "AP $1.6K, DPO 33.4 days, $550 past due." in field.metric_context
    assert "AR $1.8K, DSO 54.7 days, $300 past due." in field.metric_context
    assert "Past-due vendors: Summit Events Group $400 (1-30 days past due)" in field.unfavorable
    assert "Past-due customers: Globex $300 (1-30 days past due)." in field.unfavorable
    assert field.leadership_attention.startswith("1 of 2 vendor payments in 2026-06 were made after the due date")
    assert "no payment dates" in field.recommended_actions

    rows = _working_capital_rows(bundle)
    assert [r[0] for r in rows] == ["AP (DPO 33.4 days)", "AP past due", "AR (DSO 54.7 days)", "AR past due"]
    risks = [c.text for c in _risk_matrix_callouts(bundle, SlideCommentary()) if c.kind == "risk"]
    assert any(t.startswith("Payables") and "Summit Events Group" in t for t in risks)
    assert any(t.startswith("Receivables") and "Globex" in t for t in risks)

    assert _working_capital_rows(_bundle()) == []
    assert _cash_commentary(_bundle(), "2026-06").unfavorable == ""


def test_past_due_names_are_allowlisted_for_ai_commentary() -> None:
    wc, _ = working_capital_aging(_db(), ORG, "2026-06")
    package = build_attribution_package_from_commentary_inputs(
        CommentaryInputs(period_label="June 2026", working_capital=wc))
    drivers = {d["label"]: d for d in package["allowed_drivers"]}
    assert {"Summit Events Group", "Brennan Cole LLP", "Globex", "DPO", "DSO", "Past-due AP"} <= set(drivers)
    assert "primarily summit events group" in drivers["Summit Events Group"]["aliases"]
    assert not any(a.startswith("primarily") for a in drivers["DSO"]["aliases"])
