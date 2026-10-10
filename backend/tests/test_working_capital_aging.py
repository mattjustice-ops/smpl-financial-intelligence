"""AP / AR aging, DPO / DSO and past-due vendors and customers for commentary and the board deck."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.commentary.attribution_verify import build_attribution_package_from_commentary_inputs
from app.services.commentary.schemas import CommentaryInputs
from app.services.dashboard.schemas import ExecutiveFlowResponse
from app.services.reporting.export.board_slides import _risk_matrix_callouts, _working_capital_rows, fmt_money
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


def _db(*, ap_on_balance_sheet: str = "1650.00", ar_on_balance_sheet: str = "1800.00") -> Session:
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
        {"period": "2026-06-30", "accounts_payable": ap_on_balance_sheet, "accounts_receivable": ar_on_balance_sheet},
    ])
    return session


def _ar_aging(period: str, customer: str, current: str = "0", d30: str = "0", d60: str = "0",
              d90: str = "0") -> dict:
    total = sum(Decimal(x) for x in (current, d30, d60, d90))
    return {"period": period, "customer_id": customer[:3], "customer_name": customer, "current": current,
            "days_1_30": d30, "days_31_60": d60, "days_61_90": d90, "days_over_90": "0", "total": str(total)}


def _case(name: str, case_type: str, first_due: str, amount: str, *, written_off: str = "", paid: str = "",
          reason: str = "") -> dict:
    return {"customer_name": name, "case_type": case_type, "reason": reason, "first_unpaid_due_date": first_due,
            "amount": amount, "written_off_date": written_off, "written_off_amount": amount if written_off else "0",
            "paid_date": paid}


def _collections_db(*, ar_on_balance_sheet: str = "1800.00") -> Session:
    """AR aged by customer, net of a $100 allowance, with customer payments and collections cases."""
    session = _db(ar_on_balance_sheet=ar_on_balance_sheet)
    _table(session, "actual_ar_aging", [
        _ar_aging("2026-06", "Acme", current="900.00"),
        _ar_aging("2026-06", "Globex", d30="300.00"),
        _ar_aging("2026-06", "BlueRiver Labs", d60="500.00"),
        _ar_aging("2026-06", "Summit Health", d90="200.00"),
        _ar_aging("2026-05", "Acme", current="1200.00"),
    ])
    _table(session, "actual_allowance_for_doubtful_accounts", [
        {"period": "2026-06", "ending_allowance": "100.00", "provision_for_credit_losses": "40.00",
         "write_offs": "400.00", "gross_accounts_receivable": "1900.00"},
    ])
    _table(session, "actual_customer_payments", [
        {"payment_date": "2026-06-01", "amount": "1200.00", "days_past_due": "5"},
        {"payment_date": "2026-06-10", "amount": "800.00", "days_past_due": "0"},
        {"payment_date": "2026-06-20", "amount": "100.00", "days_past_due": "-2"},
        {"payment_date": "2026-05-20", "amount": "999.00", "days_past_due": "40"},
    ])
    _table(session, "actual_collections_cases", [
        _case("Nimbus Works", "Non-payment", "2026-03-01", "250.00", written_off="2026-06-15", reason="Budget cut"),
        _case("Vertex Group", "No-start", "2026-02-01", "150.00", written_off="2026-06-03", reason="Tax registration"),
        _case("Northstar", "Non-payment", "2025-01-01", "999.00", written_off="2025-04-01"),
        _case("Pioneer Group", "Recovered after escalation", "2026-03-31", "340.00", paid="2026-06-21",
              reason="Payment plan"),
        _case("BlueRiver Labs", "In dispute at close", "2026-05-01", "450.00", reason="Disputed usage charges"),
        _case("Summit Health", "Non-payment", "2026-04-30", "700.00", written_off="2026-08-01",
              reason="Went out of business"),
        _case("Later Co", "Non-payment", "2026-07-31", "50.00", written_off="2026-10-01"),
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


def test_ar_aging_file_allowance_and_customer_payments() -> None:
    wc, checks = working_capital_aging(_collections_db(), ORG, "2026-06")
    assert wc is not None
    assert wc.accounts_receivable == Decimal("1900.00")
    assert wc.ar_past_due == Decimal("1000.00")
    assert (wc.allowance_for_doubtful_accounts, wc.net_accounts_receivable) == (Decimal("100.00"), Decimal("1800.00"))
    assert (wc.bad_debt_expense, wc.ar_write_offs) == (Decimal("40.00"), Decimal("400.00"))
    assert [p.name for p in wc.past_due_customers] == ["BlueRiver Labs", "Globex", "Summit Health"]
    # Gross AR / average monthly billings (April-June: 1800 + 300 + 900) x 30.4 days
    assert wc.dso_days == Decimal("57.8")
    assert (wc.customer_payments, wc.late_customer_payments, wc.late_customer_payment_amount) == (
        3, 1, Decimal("1200.00"))
    assert not any("no payment dates" in note for note in wc.notes)
    assert {c.validation_name: c.status for c in checks} == {
        "allowance_gross_ar_matches_ar_aging": "pass",
        "ap_aging_ties_balance_sheet": "pass",
        "ar_aging_less_allowance_ties_balance_sheet_ar": "pass",
    }

    # Balance sheet AR is net: gross aging against it fails.
    _, gross = working_capital_aging(_collections_db(ar_on_balance_sheet="1900.00"), ORG, "2026-06")
    assert {c.validation_name: c.status for c in gross}["ar_aging_less_allowance_ties_balance_sheet_ar"] == "fail"

    # The AR aging file ages any month-end, not only the latest close.
    may, _ = working_capital_aging(_collections_db(), ORG, "2026-05")
    assert may is not None and may.accounts_receivable == Decimal("1200.00")
    assert any("No allowance for doubtful accounts for 2026-05" in note for note in may.notes)


def test_collections_cases_by_status_without_hindsight() -> None:
    wc, _ = working_capital_aging(_collections_db(), ORG, "2026-06")
    assert wc is not None
    assert [(c.name, c.status, c.label, c.amount, c.reason) for c in wc.collections_cases] == [
        ("Nimbus Works", "Written off", "Non-payment churn", Decimal("250.00"), "Budget cut"),
        ("Vertex Group", "Written off", "No-start", Decimal("150.00"), "Tax registration"),
        ("Pioneer Group", "Recovered", "Recovered after escalation", Decimal("340.00"), "Payment plan"),
        ("BlueRiver Labs", "Open", "In dispute", Decimal("500.00"), "Disputed usage charges"),
        # Written off in August: at June it is only in collections, and its outcome is not shown.
        ("Summit Health", "Open", "In collections", Decimal("200.00"), None),
    ]


def test_commentary_and_board_report_allowance_bad_debt_and_collections() -> None:
    wc, _ = working_capital_aging(_collections_db(), ORG, "2026-06")
    bundle = _bundle(working_capital=wc)

    field = _cash_commentary(bundle, "2026-06")
    assert ("AR $1.9K less $100 allowance for doubtful accounts = $1.8K net, DSO 57.8 days, $1.0K past due."
            in field.metric_context)
    assert "Bad debt expense $40 in 2026-06; $400 written off." in field.metric_context
    assert ("Written off in 2026-06: Nimbus Works $250 (Non-payment churn: Budget cut); "
            "Vertex Group $150 (No-start: Tax registration). No-starts are churn inside the first year and also reduce new business."
            in field.unfavorable)
    assert field.favorable == ("Recovered from collections in 2026-06: Pioneer Group $340 "
                               "(Recovered after escalation: Payment plan).")
    assert ("In collections at 2026-06: BlueRiver Labs $500 (In dispute: Disputed usage charges); "
            "Summit Health $200 (In collections)." in field.leadership_attention)
    assert field.leadership_attention.startswith("1 of 2 vendor payments")
    assert "1 of 3 customer payments in 2026-06 were made after the due date ($1.2K)." in field.leadership_attention

    rows = _working_capital_rows(bundle)
    assert rows[2] == [f"AR net of {fmt_money(Decimal('100.00'), 'USD')} allowance (DSO 57.8 days)",
                       fmt_money(Decimal("1800.00"), "USD")]
    assert rows[3][0] == "AR past due"
    risks = [c.text for c in _risk_matrix_callouts(bundle, SlideCommentary()) if c.kind == "risk"]
    collections = next(t for t in risks if t.startswith("Collections"))
    assert "Nimbus Works" in collections and "Non-payment churn, written off" in collections
    assert "in dispute" in collections and "Pioneer Group" not in collections

    released = wc.model_copy(update={"bad_debt_expense": Decimal("-30.00")})
    field = _cash_commentary(_bundle(working_capital=released), "2026-06")
    assert "Allowance release of $30 (bad debt expense below zero) in 2026-06" in field.metric_context


def test_collections_customers_and_bad_debt_are_allowlisted_for_ai_commentary() -> None:
    wc, _ = working_capital_aging(_collections_db(), ORG, "2026-06")
    package = build_attribution_package_from_commentary_inputs(
        CommentaryInputs(period_label="June 2026", working_capital=wc))
    labels = {d["label"] for d in package["allowed_drivers"]}
    assert {"Nimbus Works", "Vertex Group", "BlueRiver Labs", "Bad debt expense", "Allowance for doubtful accounts",
            "AR write-offs", "Late customer payments"} <= labels
