"""Add Recurring Services revenue (support and technical account management) to the demo dataset.

Writes a full copy of the source folder with these files changed (never touches the database):
  <v>_recurring_services_schedule.csv     new: one row per customer per month (the sub-ledger)
  <v>_chart_of_accounts.csv               + account 4200 Recurring Services Revenue
  <v>_invoices.csv                        + one monthly recurring services invoice per customer
  <v>_revenue_recognition.csv             + "Recurring Services" rows (Actual, Budget)
  <v>_accounts_receivable_rollforward.csv billings, collections and balances include the invoices
  <v>_cash_collections.csv                collections and cash include the payments
  recurring_services_log.csv

Rules (agreed with Matt, Oct 6 2026):
  * Recurring services is recurring revenue on top of subscription revenue; ARR and MRR
    do not change.
  * Each month it is 10% of that month's subscription revenue in <v>_income_statement.csv,
    so the GL line ties to the summary. The month's total is spread across customers by
    ARR: 2026 months use each customer's subscription ARR in revenue recognition (Forecast
    uses the Actual file, which has no Forecast version); 2024-2025 months use the
    customers who had started by that month, weighted by their Jan 2026 starting ARR.
  * Billed monthly at month end, Net 30, collected the following month.
  * Budget and Forecast continue from Actual: the months before their first month come
    from the Actual schedule (Budget from 2026-01, Forecast from 2026-07).

Usage:
  python add_recurring_services_revenue.py <source_folder> <output_folder>
"""

from __future__ import annotations

import calendar
import os
import shutil
import sys
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_implementation_revenue import VERSION_END, VERSION_START, _money, _num, _prior, _read, _write  # noqa: E402

RATE = Decimal("0.10")
CENT = Decimal("0.01")
TERMS_DAYS = 30
AMOUNT = "recurring_services_revenue"
ACCOUNT = {
    "account_number": "4200",
    "account_name": "Recurring Services Revenue",
    "statement": "Income Statement",
    "statement_category": "Revenue",
    "account_group": "Revenue",
    "expense_type": "Recurring Services",
    "description": "Recurring support and technical account management, 10% of subscription revenue, billed monthly",
}
WEIGHTS_FROM = {"Actual": "Actual", "Budget": "Budget", "Forecast": "Actual"}
SCHEDULE_FIELDS = [
    "organization_id", "version", "period", "customer_id", "customer_name", "segment", "weight_source",
    "customer_arr", "month_subscription_revenue", "rate", AMOUNT, "invoice_id", "invoice_date", "due_date",
    "collection_period",
]


def _months(start: str, end: str) -> list[str]:
    out, y, m = [], int(start[:4]), int(start[5:])
    while f"{y}-{m:02d}" <= end:
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _month_end(period: str) -> date:
    y, m = int(period[:4]), int(period[5:])
    return date(y, m, calendar.monthrange(y, m)[1])


def _subscription_arr(src: str, version: str) -> dict[str, dict[str, Decimal]]:
    """{month: {customer_id: subscription ARR}} from revenue recognition (one value per customer)."""
    path = os.path.join(src, f"{version}_revenue_recognition.csv")
    out: dict[str, dict[str, Decimal]] = defaultdict(dict)
    if not os.path.exists(path):
        return out
    _, rows = _read(path)
    for r in rows:
        if r["revenue_type"] != "Subscription":
            continue
        arr = _num(r["recognized_arr"])
        if arr > 0:
            month = out[r["period"][:7]]
            month[r["customer_id"]] = max(month.get(r["customer_id"], Decimal("0")), arr)
    return out


def build_schedule(src: str, version: str, customers: dict[str, dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    log: list[dict[str, str]] = []
    _, summary = _read(os.path.join(src, f"{version}_income_statement.csv"))
    revenue = {r["period"][:7]: _num(r["revenue"]) for r in summary}
    org = next(iter(customers.values()))["organization_id"]
    weights_file = f"{WEIGHTS_FROM[version]}_revenue_recognition.csv"
    arr_by_month = _subscription_arr(src, WEIGHTS_FROM[version])
    for period in _months(VERSION_START[version], VERSION_END[version]):
        if period not in revenue:
            raise ValueError(f"{version} {period}: no subscription revenue in {version}_income_statement.csv")
        weights = arr_by_month.get(period)
        source = weights_file
        if not weights:
            weights = {cid: _num(c["starting_arr_jan_2026"]) for cid, c in customers.items()
                       if c["customer_start_date"][:7] <= period and _num(c["starting_arr_jan_2026"]) > 0}
            source = "Actual_customers.csv (started by month, Jan 2026 ARR)"
        if not weights:
            raise ValueError(f"{version} {period}: no customers to spread recurring services across")
        total = (revenue[period] * RATE).quantize(CENT, ROUND_HALF_UP)
        arr_total = sum(weights.values(), Decimal("0"))
        ids = sorted(weights)
        amounts = [(total * weights[c] / arr_total).quantize(CENT, ROUND_HALF_UP) for c in ids]
        largest = max(range(len(ids)), key=lambda i: amounts[i])
        amounts[largest] += total - sum(amounts, Decimal("0"))
        invoiced = _month_end(period)
        due = invoiced + timedelta(days=TERMS_DAYS)
        for cid, amt in zip(ids, amounts):
            c = customers.get(cid, {})
            rows.append({
                "organization_id": org, "version": version, "period": period, "customer_id": cid,
                "customer_name": c.get("customer_name", ""), "segment": c.get("segment", ""), "weight_source": source,
                "customer_arr": _money(weights[cid]), "month_subscription_revenue": _money(revenue[period]),
                "rate": f"{RATE}", AMOUNT: _money(amt),
                "invoice_id": f"RSV-{version[0]}-{period.replace('-', '')}-{cid}",
                "invoice_date": invoiced.isoformat(), "due_date": due.isoformat(),
                "collection_period": due.strftime("%Y-%m"),
            })
        log.append({"version": version, "period": period, "file": f"{version}_recurring_services_schedule.csv",
                    "action": "created", "detail": f"10% of subscription revenue {revenue[period]:,.2f}; "
                                                   f"{len(ids)} customers by ARR from {source}",
                    "amount": _money(total)})
    return rows, log


def chain_schedule(schedules: dict[str, list[dict[str, str]]], version: str) -> list[dict[str, str]]:
    """Version schedule preceded by the Actual schedule for months before the version starts."""
    if version == "Actual":
        return schedules["Actual"]
    start = VERSION_START[version]
    return [r for r in schedules["Actual"] if r["period"] < start] + schedules[version]


class Totals:
    """Billed, collected and open amounts by month for a chained schedule."""

    def __init__(self, chain: list[dict[str, str]]):
        self.billed: dict[str, Decimal] = defaultdict(Decimal)
        self.collected: dict[str, Decimal] = defaultdict(Decimal)
        for r in chain:
            self.billed[r["period"]] += _num(r[AMOUNT])
            self.collected[r["collection_period"]] += _num(r[AMOUNT])

    def billed_through(self, month: str) -> Decimal:
        return sum((v for p, v in self.billed.items() if p <= month), Decimal("0"))

    def collected_through(self, month: str) -> Decimal:
        return sum((v for p, v in self.collected.items() if p <= month), Decimal("0"))

    def outstanding(self, month: str) -> Decimal:
        return self.billed_through(month) - self.collected_through(month)


def update_ar_rollforward(path: str, t: Totals, log: list[dict[str, str]], version: str) -> None:
    fields, rows = _read(path)
    for r in rows:
        p = r["period"][:7]
        add_begin, add_end = t.outstanding(_prior(p)), t.outstanding(p)
        billed, collected = t.billed.get(p, Decimal("0")), t.collected.get(p, Decimal("0"))
        if add_begin + billed - collected != add_end:
            raise ValueError(f"{version} {p}: recurring services AR does not roll")
        r["beginning_accounts_receivable"] = _money(_num(r["beginning_accounts_receivable"]) + add_begin)
        r["new_billings"] = _money(_num(r["new_billings"]) + billed)
        r["cash_collections"] = _money(_num(r["cash_collections"]) + collected)
        r["ending_accounts_receivable"] = _money(_num(r["ending_accounts_receivable"]) + add_end)
        log.append({"version": version, "period": p, "file": os.path.basename(path), "action": "added",
                    "detail": f"recurring services billings {billed:,.2f}; collections {collected:,.2f}; "
                              f"open at month end {add_end:,.2f}", "amount": _money(billed)})
    _write(path, fields, rows)


def update_cash_collections(path: str, t: Totals, log: list[dict[str, str]], version: str) -> None:
    fields, rows = _read(path)
    for r in rows:
        p = r["period"][:7]
        before = t.collected_through(_prior(p))
        collected = t.collected.get(p, Decimal("0"))
        r["cash_collections"] = _money(_num(r["cash_collections"]) + collected)
        r["beginning_cash"] = _money(_num(r["beginning_cash"]) + before)
        r["ending_cash"] = _money(_num(r["ending_cash"]) + before + collected)
    log.append({"version": version, "period": "", "file": os.path.basename(path), "action": "added",
                "detail": "recurring services collections added to cash_collections; beginning and ending cash "
                          "include recurring services cash collected to date", "amount": ""})
    _write(path, fields, rows)


def update_invoices(path: str, schedule: list[dict[str, str]], last_month: str, log: list[dict[str, str]], version: str) -> None:
    fields, rows = _read(path)
    months = {r["invoice_period"][:7] for r in rows}
    added = 0
    for s in schedule:
        if s["period"] not in months:
            continue
        rows.append({
            "organization_id": s["organization_id"], "version": version, "invoice_id": s["invoice_id"],
            "customer_id": s["customer_id"], "customer_name": s["customer_name"], "invoice_period": s["period"],
            "service_period_start": f"{s['period']}-01", "service_period_end": s["invoice_date"],
            "invoice_date": s["invoice_date"], "due_date": s["due_date"], "invoice_amount": s[AMOUNT],
            "payment_status": "Paid" if s["collection_period"] <= last_month else "Open",
            "billing_cadence": "Monthly", "billing_terms": f"Net {TERMS_DAYS}", "currency": "USD",
        })
        added += 1
    log.append({"version": version, "period": "", "file": os.path.basename(path), "action": "added",
                "detail": f"{added} recurring services invoices (invoice file covers {min(months)}..{max(months)})",
                "amount": ""})
    _write(path, fields, rows)


def update_revenue_recognition(path: str, schedule: list[dict[str, str]], log: list[dict[str, str]], version: str) -> None:
    fields, rows = _read(path)
    months = {r["period"][:7] for r in rows}
    added = 0
    for s in schedule:
        if s["period"] not in months:
            continue
        rows.append({
            "organization_id": s["organization_id"], "version": version, "period": s["period"],
            "customer_id": s["customer_id"], "customer_name": s["customer_name"],
            "recognized_revenue": s[AMOUNT], "recognized_arr": "0", "revenue_type": "Recurring Services",
        })
        added += 1
    log.append({"version": version, "period": "", "file": os.path.basename(path), "action": "added",
                "detail": f"{added} Recurring Services rows (file covers {min(months)}..{max(months)})", "amount": ""})
    _write(path, fields, rows)


def update_chart_of_accounts(path: str, log: list[dict[str, str]], version: str) -> None:
    fields, rows = _read(path)
    if any(r["account_number"] == ACCOUNT["account_number"] for r in rows):
        raise ValueError(f"{path} already has account {ACCOUNT['account_number']}")
    rows.append({k: ACCOUNT.get(k, "") for k in fields})
    rows.sort(key=lambda r: r["account_number"])
    log.append({"version": version, "period": "", "file": os.path.basename(path), "action": "added",
                "detail": f"account {ACCOUNT['account_number']} {ACCOUNT['account_name']}", "amount": ""})
    _write(path, fields, rows)


def main(src: str, dst: str) -> None:
    if os.path.abspath(src) == os.path.abspath(dst):
        raise ValueError("output folder must differ from the source folder")
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        if name.lower().endswith(".csv") and os.path.isfile(os.path.join(src, name)):
            shutil.copy2(os.path.join(src, name), os.path.join(dst, name))

    _, customer_rows = _read(os.path.join(src, "Actual_customers.csv"))
    customers = {c["customer_id"]: c for c in customer_rows}
    log: list[dict[str, str]] = []
    schedules: dict[str, list[dict[str, str]]] = {}
    for version in ("Actual", "Budget", "Forecast"):
        schedules[version], slog = build_schedule(src, version, customers)
        log.extend(slog)

    for version in ("Actual", "Budget", "Forecast"):
        schedule = schedules[version]
        totals = Totals(chain_schedule(schedules, version))
        _write(os.path.join(dst, f"{version}_recurring_services_schedule.csv"), SCHEDULE_FIELDS, schedule)
        update_chart_of_accounts(os.path.join(dst, f"{version}_chart_of_accounts.csv"), log, version)
        update_invoices(os.path.join(dst, f"{version}_invoices.csv"), schedule, VERSION_END[version], log, version)
        rr = os.path.join(dst, f"{version}_revenue_recognition.csv")
        if os.path.exists(rr):
            update_revenue_recognition(rr, schedule, log, version)
        else:
            log.append({"version": version, "period": "", "file": f"{version}_revenue_recognition.csv",
                        "action": "not in dataset", "detail": "no revenue recognition file for this version", "amount": ""})
        update_ar_rollforward(os.path.join(dst, f"{version}_accounts_receivable_rollforward.csv"), totals, log, version)
        update_cash_collections(os.path.join(dst, f"{version}_cash_collections.csv"), totals, log, version)

    _write(os.path.join(dst, "recurring_services_log.csv"), ["version", "period", "file", "action", "detail", "amount"], log)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
