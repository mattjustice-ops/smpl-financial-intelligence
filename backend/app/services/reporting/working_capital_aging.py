"""AP and AR aging, DPO and DSO, and past-due vendors and customers at one month-end.

Sources (Actual only):
  * actual_ap_aging: open AP by vendor and month-end, in days-past-due buckets.
  * actual_vendor_bills: bills by bill date, for DPO (AP / average monthly bills, last 3 months).
  * actual_vendor_payments: payments in the month and how many were made after the due date.
  * actual_invoices: open customer invoices aged by due date; DSO = AR / average monthly billings, last 3 months.
    Invoices carry a status, not a payment date, so customer aging is only available at the latest close.
  * actual_balance_sheet: AP and AR at the month-end, to check the aging totals.
"""

from __future__ import annotations

import calendar
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.commentary.schemas import PastDueParty, WorkingCapitalInput
from app.services.dashboard.query_utils import fetch_table_rows, table_exists, value_any
from app.services.reporting.period_utils import period_to_date, to_period
from app.services.reporting.validation_service import ValidationCheck, compare_values

AGING_COLUMNS = (
    ("current", "Current"),
    ("days_1_30", "1-30 days past due"),
    ("days_31_60", "31-60 days past due"),
    ("days_61_90", "61-90 days past due"),
    ("days_over_90", "Over 90 days past due"),
)
PAST_DUE_LABELS = tuple(label for _, label in AGING_COLUMNS[1:])
DAYS_PER_MONTH = Decimal("30.4")
TRAILING_MONTHS = 3
TOP_PARTIES = 5
ZERO = Decimal("0")

AP_AGING = "actual_ap_aging"
VENDOR_BILLS = "actual_vendor_bills"
VENDOR_PAYMENTS = "actual_vendor_payments"
INVOICES = "actual_invoices"
BALANCE_SHEET = "actual_balance_sheet"


def _period_of(raw: dict, *keys: str) -> str | None:
    for key in keys:
        value = raw.get(key)
        if value not in (None, ""):
            try:
                return to_period(value)
            except (TypeError, ValueError):
                return None
    return None


def _trailing(period: str) -> set[str]:
    start = period_to_date(period)
    out = set()
    year, month = start.year, start.month
    for _ in range(TRAILING_MONTHS):
        out.add(f"{year:04d}-{month:02d}")
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return out


def _month_end(period: str) -> date:
    first = period_to_date(period)
    return date(first.year, first.month, calendar.monthrange(first.year, first.month)[1])


def _bucket(days_past_due: int) -> str:
    if days_past_due <= 0:
        return AGING_COLUMNS[0][1]
    if days_past_due <= 30:
        return AGING_COLUMNS[1][1]
    if days_past_due <= 60:
        return AGING_COLUMNS[2][1]
    if days_past_due <= 90:
        return AGING_COLUMNS[3][1]
    return AGING_COLUMNS[4][1]


def _days(balance: Decimal, flow: Decimal) -> Decimal | None:
    if flow <= 0:
        return None
    return (balance / (flow / TRAILING_MONTHS) * DAYS_PER_MONTH).quantize(Decimal("0.1"))


def _parties(by_party: dict[str, dict[str, Decimal]]) -> list[PastDueParty]:
    parties = []
    for name, buckets in by_party.items():
        past_due = sum((buckets.get(label, ZERO) for label in PAST_DUE_LABELS), ZERO)
        if past_due <= 0:
            continue
        oldest = next(label for label in reversed(PAST_DUE_LABELS) if buckets.get(label, ZERO) > 0)
        parties.append(PastDueParty(name=name, past_due=past_due, oldest_bucket=oldest))
    parties.sort(key=lambda p: (-p.past_due, p.name))
    return parties[:TOP_PARTIES]


def _payables(session: Session, organization_id: uuid.UUID, period: str, out: WorkingCapitalInput) -> None:
    rows = [r for r in fetch_table_rows(session, AP_AGING, organization_id) if _period_of(r, "period") == period]
    if not rows:
        out.notes.append(f"No AP aging for {period} (load Actual_AP_Aging.csv).")
        return
    buckets = {label: ZERO for _, label in AGING_COLUMNS}
    by_vendor: dict[str, dict[str, Decimal]] = {}
    for raw in rows:
        name = str(raw.get("vendor_name") or raw.get("vendor_id") or "Unknown vendor")
        vendor = by_vendor.setdefault(name, {})
        for column, label in AGING_COLUMNS:
            amount = value_any(raw, column)
            buckets[label] += amount
            vendor[label] = vendor.get(label, ZERO) + amount
    out.accounts_payable = sum(buckets.values(), ZERO)
    out.ap_aging_buckets = buckets
    out.ap_past_due = sum((buckets[label] for label in PAST_DUE_LABELS), ZERO)
    out.past_due_vendors = _parties(by_vendor)

    window = _trailing(period)
    if table_exists(session, VENDOR_BILLS):
        billed = sum(
            (value_any(r, "amount") for r in fetch_table_rows(session, VENDOR_BILLS, organization_id)
             if _period_of(r, "bill_date", "period") in window),
            ZERO,
        )
        out.dpo_days = _days(out.accounts_payable, billed)
    if out.dpo_days is None:
        out.notes.append("DPO needs vendor bills for the last 3 months (Actual_vendor_bills.csv).")

    payments = [
        r for r in fetch_table_rows(session, VENDOR_PAYMENTS, organization_id)
        if _period_of(r, "payment_date", "period") == period
    ]
    if payments and any(r.get("days_past_due") not in (None, "") for r in payments):
        late = [r for r in payments if value_any(r, "days_past_due") > 0]
        out.vendor_payments = len(payments)
        out.late_vendor_payments = len(late)
        out.late_vendor_payment_amount = sum((abs(value_any(r, "amount")) for r in late), ZERO)


def _receivables(session: Session, organization_id: uuid.UUID, period: str, out: WorkingCapitalInput) -> None:
    invoices = fetch_table_rows(session, INVOICES, organization_id)
    if not invoices:
        out.notes.append("No customer invoices loaded (Actual_invoices.csv); customer aging is not available.")
        return
    dated = [(r, _period_of(r, "invoice_date", "invoice_period")) for r in invoices]
    latest = max((p for _, p in dated if p), default=None)
    if latest != period:
        out.notes.append(
            f"Customer aging is only available at the latest close ({latest}): invoices carry a payment status, "
            "not payment dates."
        )
        return
    window = _trailing(period)
    billed = sum((value_any(r, "invoice_amount") for r, p in dated if p in window), ZERO)
    close = _month_end(period)
    buckets = {label: ZERO for _, label in AGING_COLUMNS}
    by_customer: dict[str, dict[str, Decimal]] = {}
    for raw in invoices:
        if str(raw.get("payment_status") or "").strip().lower() != "open":
            continue
        amount = value_any(raw, "invoice_amount")
        due = raw.get("due_date")
        days_late = (close - date.fromisoformat(str(due)[:10])).days if due not in (None, "") else 0
        label = _bucket(days_late)
        buckets[label] += amount
        customer = by_customer.setdefault(str(raw.get("customer_name") or raw.get("customer_id") or "Unknown"), {})
        customer[label] = customer.get(label, ZERO) + amount
    out.accounts_receivable = sum(buckets.values(), ZERO)
    out.ar_aging_buckets = buckets
    out.ar_past_due = sum((buckets[label] for label in PAST_DUE_LABELS), ZERO)
    out.dso_days = _days(out.accounts_receivable, billed)
    out.past_due_customers = _parties(by_customer)
    if not any(raw.get("paid_date") or raw.get("payment_date") for raw in invoices):
        out.notes.append("Invoices have no payment dates, so customer payment history (who paid late) is not available.")


def _balance_sheet_checks(
    session: Session, organization_id: uuid.UUID, period: str, out: WorkingCapitalInput
) -> list[ValidationCheck]:
    rows = [r for r in fetch_table_rows(session, BALANCE_SHEET, organization_id) if _period_of(r, "period") == period]
    if not rows:
        return []
    checks = []
    for name, aged, column, source in (
        ("ap_aging_ties_balance_sheet", out.accounts_payable, "accounts_payable", AP_AGING),
        ("open_invoices_tie_balance_sheet_ar", out.accounts_receivable, "accounts_receivable", INVOICES),
    ):
        if aged is None or rows[0].get(column) in (None, ""):
            continue
        checks.append(
            compare_values(
                scenario="Actual",
                period=period,
                validation_name=name,
                expected_value=value_any(rows[0], column),
                actual_value=aged,
                source_tables_used=[source, BALANCE_SHEET],
            )
        )
    return checks


def working_capital_aging(
    session: Session, organization_id: uuid.UUID, period: str
) -> tuple[WorkingCapitalInput | None, list[ValidationCheck]]:
    """Aging for the month-end, or None when neither AP aging nor invoices are loaded."""
    period = to_period(period)
    out = WorkingCapitalInput(period=period)
    _payables(session, organization_id, period, out)
    _receivables(session, organization_id, period, out)
    if out.accounts_payable is None and out.accounts_receivable is None:
        return None, []
    return out, _balance_sheet_checks(session, organization_id, period, out)
