"""AP and AR aging, DPO and DSO, past-due vendors and customers, and collections at one month-end.

Sources (Actual only):
  * actual_ap_aging: open AP by vendor and month-end, in days-past-due buckets.
  * actual_vendor_bills: bills by bill date, for DPO (AP / average monthly bills, last 3 months).
  * actual_vendor_payments: payments in the month and how many were made after the due date.
  * actual_ar_aging: open AR by customer and month-end, in the same buckets. When it isn't loaded, open
    customer invoices are aged by due date, which only works at the latest close (status, not history).
  * actual_invoices: billings for DSO (gross AR / average monthly billings, last 3 months).
  * actual_customer_payments: customer payments in the month and how many came after the due date.
  * actual_allowance_for_doubtful_accounts: allowance at the month-end, bad debt expense and write-offs.
  * actual_collections_cases: customers written off, recovered or still in collections.
  * actual_balance_sheet: AP and net AR at the month-end, to check the aging totals.
"""

from __future__ import annotations

import calendar
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.commentary.schemas import CollectionsCase, PastDueParty, WorkingCapitalInput
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
AR_AGING = "actual_ar_aging"
INVOICES = "actual_invoices"
CUSTOMER_PAYMENTS = "actual_customer_payments"
ALLOWANCE = "actual_allowance_for_doubtful_accounts"
COLLECTIONS_CASES = "actual_collections_cases"
BALANCE_SHEET = "actual_balance_sheet"

# Collections case types in the cases file, as they read once the case is closed.
CLOSED_LABELS = {"no-start": "No-start", "non-payment": "Non-payment churn"}
# Balance sheet AR is net of the allowance when the allowance is loaded.
AR_CHECK_NAMES = {
    (INVOICES, False): "open_invoices_tie_balance_sheet_ar",
    (INVOICES, True): "open_invoices_less_allowance_tie_balance_sheet_ar",
    (AR_AGING, False): "ar_aging_ties_balance_sheet_ar",
    (AR_AGING, True): "ar_aging_less_allowance_ties_balance_sheet_ar",
}


def _period_of(raw: dict, *keys: str) -> str | None:
    for key in keys:
        value = raw.get(key)
        if value not in (None, ""):
            try:
                return to_period(value)
            except (TypeError, ValueError):
                return None
    return None


def _date_of(raw: dict, key: str) -> date | None:
    value = raw.get(key)
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
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


def _aged(rows: list[dict], *name_keys: str) -> tuple[dict[str, Decimal], dict[str, dict[str, Decimal]]]:
    """Totals by bucket and by party from aging rows with one column per bucket."""
    buckets = {label: ZERO for _, label in AGING_COLUMNS}
    by_party: dict[str, dict[str, Decimal]] = {}
    for raw in rows:
        name = next((str(raw[k]) for k in name_keys if raw.get(k) not in (None, "")), "Unknown")
        party = by_party.setdefault(name, {})
        for column, label in AGING_COLUMNS:
            amount = value_any(raw, column)
            buckets[label] += amount
            party[label] = party.get(label, ZERO) + amount
    return buckets, by_party


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


def _payments(rows: list[dict], period: str) -> tuple[int, int, Decimal] | None:
    """(payments in the month, paid after the due date, amount paid late), or None without days past due."""
    in_month = [r for r in rows if _period_of(r, "payment_date", "period") == period]
    if not in_month or not any(r.get("days_past_due") not in (None, "") for r in in_month):
        return None
    late = [r for r in in_month if value_any(r, "days_past_due") > 0]
    return len(in_month), len(late), sum((abs(value_any(r, "amount")) for r in late), ZERO)


def _payables(session: Session, organization_id: uuid.UUID, period: str, out: WorkingCapitalInput) -> None:
    rows = [r for r in fetch_table_rows(session, AP_AGING, organization_id) if _period_of(r, "period") == period]
    if not rows:
        out.notes.append(f"No AP aging for {period} (load Actual_AP_Aging.csv).")
        return
    buckets, by_vendor = _aged(rows, "vendor_name", "vendor_id")
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

    paid = _payments(fetch_table_rows(session, VENDOR_PAYMENTS, organization_id), period)
    if paid:
        out.vendor_payments, out.late_vendor_payments, out.late_vendor_payment_amount = paid


def _open_invoice_aging(
    invoices: list[dict], period: str, out: WorkingCapitalInput
) -> tuple[dict[str, Decimal], dict[str, dict[str, Decimal]]] | None:
    latest = max((p for p in (_period_of(r, "invoice_date", "invoice_period") for r in invoices) if p), default=None)
    if latest != period:
        out.notes.append(
            f"Customer aging is only available at the latest close ({latest}) without an AR aging file "
            "(Actual_AR_Aging.csv): invoices carry their status today, not at past month-ends."
        )
        return None
    close = _month_end(period)
    buckets = {label: ZERO for _, label in AGING_COLUMNS}
    by_customer: dict[str, dict[str, Decimal]] = {}
    for raw in invoices:
        if str(raw.get("payment_status") or "").strip().lower() != "open":
            continue
        amount = value_any(raw, "invoice_amount")
        due = _date_of(raw, "due_date")
        label = _bucket((close - due).days if due else 0)
        buckets[label] += amount
        customer = by_customer.setdefault(str(raw.get("customer_name") or raw.get("customer_id") or "Unknown"), {})
        customer[label] = customer.get(label, ZERO) + amount
    return buckets, by_customer


def _receivables(session: Session, organization_id: uuid.UUID, period: str, out: WorkingCapitalInput) -> str | None:
    """Age AR at the month-end; returns the table the aging came from."""
    invoices = fetch_table_rows(session, INVOICES, organization_id)
    aging_rows = [r for r in fetch_table_rows(session, AR_AGING, organization_id) if _period_of(r, "period") == period]
    if aging_rows:
        source = AR_AGING
        buckets, by_customer = _aged(aging_rows, "customer_name", "customer_id")
    elif invoices:
        aged = _open_invoice_aging(invoices, period, out)
        if aged is None:
            return None
        source = INVOICES
        buckets, by_customer = aged
    else:
        out.notes.append("No AR aging or customer invoices loaded (Actual_AR_Aging.csv, Actual_invoices.csv).")
        return None
    out.accounts_receivable = sum(buckets.values(), ZERO)
    out.ar_aging_buckets = buckets
    out.ar_past_due = sum((buckets[label] for label in PAST_DUE_LABELS), ZERO)
    out.past_due_customers = _parties(by_customer)

    window = _trailing(period)
    billed = sum(
        (value_any(r, "invoice_amount") for r in invoices if _period_of(r, "invoice_date", "invoice_period") in window),
        ZERO,
    )
    out.dso_days = _days(out.accounts_receivable, billed)
    if out.dso_days is None:
        out.notes.append("DSO needs customer invoices for the last 3 months (Actual_invoices.csv).")

    paid = _payments(fetch_table_rows(session, CUSTOMER_PAYMENTS, organization_id), period)
    if paid:
        out.customer_payments, out.late_customer_payments, out.late_customer_payment_amount = paid
    elif not any(raw.get("paid_date") or raw.get("payment_date") for raw in invoices):
        out.notes.append("Invoices have no payment dates, so customer payment history (who paid late) is not available.")
    return source


def _allowance(session: Session, organization_id: uuid.UUID, period: str, out: WorkingCapitalInput) -> dict | None:
    rows = [r for r in fetch_table_rows(session, ALLOWANCE, organization_id) if _period_of(r, "period") == period]
    if not rows:
        if out.accounts_receivable is not None:
            out.notes.append(
                f"No allowance for doubtful accounts for {period} (Actual_allowance_for_doubtful_accounts.csv); "
                "AR is shown gross."
            )
        return None
    row = rows[0]
    out.allowance_for_doubtful_accounts = value_any(row, "ending_allowance")
    out.bad_debt_expense = value_any(row, "provision_for_credit_losses")
    out.ar_write_offs = value_any(row, "write_offs")
    if out.accounts_receivable is not None:
        out.net_accounts_receivable = out.accounts_receivable - out.allowance_for_doubtful_accounts
    return row


def _collections(session: Session, organization_id: uuid.UUID, period: str, out: WorkingCapitalInput) -> None:
    close = _month_end(period)
    outstanding = {}
    for raw in fetch_table_rows(session, AR_AGING, organization_id):
        if _period_of(raw, "period") == period:
            name = str(raw.get("customer_name") or raw.get("customer_id") or "")
            outstanding[name] = outstanding.get(name, ZERO) + value_any(raw, "total")
    cases = []
    for raw in fetch_table_rows(session, COLLECTIONS_CASES, organization_id):
        name = str(raw.get("customer_name") or raw.get("customer_id") or "Unknown customer")
        case_type = str(raw.get("case_type") or "").strip()
        reason = str(raw.get("reason") or "").strip() or None
        written_off, paid = _date_of(raw, "written_off_date"), _date_of(raw, "paid_date")
        first_due = _date_of(raw, "first_unpaid_due_date")
        if written_off and _period_of(raw, "written_off_date") == period:
            label = CLOSED_LABELS.get(case_type.lower(), case_type or "Written off")
            cases.append(CollectionsCase(name=name, status="Written off", label=label,
                                         amount=value_any(raw, "written_off_amount", "amount"), reason=reason))
        elif paid and _period_of(raw, "paid_date") == period:
            cases.append(CollectionsCase(name=name, status="Recovered", label="Recovered after escalation",
                                         amount=value_any(raw, "amount"), reason=reason))
        elif first_due and first_due <= close and not any(d and d <= close for d in (written_off, paid)):
            # How an open case ends isn't known at the month-end, so only a dispute is named.
            label = "In dispute" if "dispute" in case_type.lower() else "In collections"
            cases.append(CollectionsCase(name=name, status="Open", label=label,
                                         amount=outstanding.get(name) or value_any(raw, "amount"),
                                         reason=reason if label == "In dispute" else None))
    order = {"Written off": 0, "Recovered": 1, "Open": 2}
    cases.sort(key=lambda c: (order[c.status], -c.amount, c.name))
    out.collections_cases = cases


def _checks(
    session: Session,
    organization_id: uuid.UUID,
    period: str,
    out: WorkingCapitalInput,
    ar_source: str | None,
    allowance: dict | None,
) -> list[ValidationCheck]:
    checks = []
    if allowance is not None and out.accounts_receivable is not None and ar_source == AR_AGING:
        checks.append(compare_values(
            scenario="Actual", period=period, validation_name="allowance_gross_ar_matches_ar_aging",
            expected_value=value_any(allowance, "gross_accounts_receivable"), actual_value=out.accounts_receivable,
            source_tables_used=[ALLOWANCE, AR_AGING],
        ))
    rows = [r for r in fetch_table_rows(session, BALANCE_SHEET, organization_id) if _period_of(r, "period") == period]
    if not rows:
        return checks
    net = out.net_accounts_receivable is not None
    ar_name = AR_CHECK_NAMES.get((ar_source, net), "")
    ar_sources = [ar_source, ALLOWANCE] if net else [ar_source]
    ar_value = out.net_accounts_receivable if net else out.accounts_receivable
    for name, aged, column, sources in (
        ("ap_aging_ties_balance_sheet", out.accounts_payable, "accounts_payable", [AP_AGING]),
        (ar_name, ar_value, "accounts_receivable", ar_sources),
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
                source_tables_used=[*sources, BALANCE_SHEET],
            )
        )
    return checks


def working_capital_aging(
    session: Session, organization_id: uuid.UUID, period: str
) -> tuple[WorkingCapitalInput | None, list[ValidationCheck]]:
    """Aging for the month-end, or None when neither AP nor AR aging is available."""
    period = to_period(period)
    out = WorkingCapitalInput(period=period)
    _payables(session, organization_id, period, out)
    ar_source = _receivables(session, organization_id, period, out)
    allowance = _allowance(session, organization_id, period, out)
    _collections(session, organization_id, period, out)
    if out.accounts_payable is None and out.accounts_receivable is None:
        return None, []
    return out, _checks(session, organization_id, period, out, ar_source, allowance)
