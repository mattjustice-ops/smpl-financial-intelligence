"""Add one-time Implementation & Onboarding revenue to the demo dataset.

Writes a full copy of the source folder with these files changed (never touches the database):
  <v>_implementation_schedule.csv        new: one row per new customer (the sub-ledger)
  <v>_chart_of_accounts.csv              + account 4100 Implementation & Onboarding Revenue
  <v>_invoices.csv                       + one implementation invoice per new customer
  <v>_revenue_recognition.csv            + "Implementation" rows (Actual, Budget)
  <v>_accounts_receivable_rollforward.csv billings, collections and balances include the invoices
  <v>_cash_collections.csv               collections and cash include the payments
  implementation_revenue_log.csv

Rules (agreed with Matt, Oct 5 2026):
  * Implementation is non-recurring revenue on top of subscription revenue; ARR and MRR
    do not change.
  * One fee per new customer by segment: SMB 2,000; Mid-Market 3,500; Enterprise 5,000.
  * New customers: customer start dates for 2024-2025 (Actual_customers.csv) and closed-won
    "New Business" deals for 2026 (<v>_opportunities.csv).
  * Invoiced and recognized when the customer signs, Net 30; collected in the month the
    invoice is due.
  * Budget and Forecast continue from Actual: the months before their first month come
    from the Actual schedule (Budget from 2026-01, Forecast from 2026-07).

Usage:
  python add_implementation_revenue.py <source_folder> <output_folder>
"""

from __future__ import annotations

import csv
import os
import shutil
import sys
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

FEE_BY_SEGMENT = {"SMB": Decimal("2000"), "Mid-Market": Decimal("3500"), "Enterprise": Decimal("5000")}
TERMS_DAYS = 30
ACCOUNT = {
    "account_number": "4100",
    "account_name": "Implementation & Onboarding Revenue",
    "statement": "Income Statement",
    "statement_category": "Revenue",
    "account_group": "Revenue",
    "expense_type": "Implementation & Onboarding",
    "description": "One-time implementation and onboarding fees, recognized when the customer signs",
}
VERSION_START = {"Actual": "2024-01", "Budget": "2026-01", "Forecast": "2026-07"}
VERSION_END = {"Actual": "2026-06", "Budget": "2026-12", "Forecast": "2026-12"}
CUSTOMER_START_YEARS = ("2024", "2025")
SCHEDULE_FIELDS = [
    "organization_id", "version", "period", "customer_id", "customer_name", "segment", "source",
    "source_record_id", "implementation_fee", "invoice_id", "invoice_date", "due_date", "collection_period",
]


def _read(path: str) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def _write(path: str, fields: list[str], rows: list[dict[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def _num(value) -> Decimal:
    text = str(value or "0").replace(",", "").strip()
    return Decimal(text or "0")


def _entry(org: str, version: str, signed: date, customer_id: str, customer_name: str, segment: str,
           source: str, record_id: str, seq: int) -> dict[str, str]:
    due = signed + timedelta(days=TERMS_DAYS)
    return {
        "organization_id": org, "version": version, "period": signed.strftime("%Y-%m"),
        "customer_id": customer_id, "customer_name": customer_name, "segment": segment, "source": source,
        "source_record_id": record_id, "implementation_fee": _money(FEE_BY_SEGMENT[segment]),
        "invoice_id": f"IMP-{version[0]}-{seq:05d}", "invoice_date": signed.isoformat(),
        "due_date": due.isoformat(), "collection_period": due.strftime("%Y-%m"),
    }


def build_schedule(src: str, version: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """One row per new customer in the version's own months."""
    start, end = VERSION_START[version], VERSION_END[version]
    rows: list[dict[str, str]] = []
    log: list[dict[str, str]] = []
    if version == "Actual":
        _, customers = _read(os.path.join(src, "Actual_customers.csv"))
        for c in sorted(customers, key=lambda r: (r["customer_start_date"], r["customer_id"])):
            if c["customer_start_date"][:4] in CUSTOMER_START_YEARS:
                rows.append(_entry(c["organization_id"], version, date.fromisoformat(c["customer_start_date"][:10]),
                                   c["customer_id"], c["customer_name"], c["segment"], "Actual_customers.csv",
                                   c["customer_id"], len(rows) + 1))
    _, opps = _read(os.path.join(src, f"{version}_opportunities.csv"))
    skipped: dict[str, int] = defaultdict(int)
    for o in sorted(opps, key=lambda r: (r["actual_close_date"] or r["expected_close_date"], r["opportunity_id"])):
        if o["opportunity_type"] != "New Business" or o["close_status"] != "Closed Won":
            continue
        closed = (o["actual_close_date"] or o["expected_close_date"])[:10]
        month = closed[:7]
        if not month.startswith("2026"):
            continue
        if not (start <= month <= end):
            skipped[month] += 1
            continue
        rows.append(_entry(o["organization_id"], version, date.fromisoformat(closed), o["customer_id"],
                           o["customer_name"], o["segment"], f"{version}_opportunities.csv",
                           o["opportunity_id"], len(rows) + 1))
    for month, n in sorted(skipped.items()):
        log.append({"version": version, "period": month, "file": f"{version}_opportunities.csv", "action": "not used",
                    "detail": f"{n} closed-won New Business deals fall outside {version} months {start}..{end}"})
    return rows, log


def chain_schedule(schedules: dict[str, list[dict[str, str]]], version: str) -> list[dict[str, str]]:
    """Version schedule preceded by the Actual schedule for months before the version starts."""
    if version == "Actual":
        return schedules["Actual"]
    start = VERSION_START[version]
    return [r for r in schedules["Actual"] if r["period"] < start] + schedules[version]


def _outstanding(chain: list[dict[str, str]], month: str) -> Decimal:
    return sum((_num(r["implementation_fee"]) for r in chain if r["period"] <= month < r["collection_period"]),
               Decimal("0"))


def _billed(chain: list[dict[str, str]], month: str) -> Decimal:
    return sum((_num(r["implementation_fee"]) for r in chain if r["period"] == month), Decimal("0"))


def _collected(chain: list[dict[str, str]], month: str) -> Decimal:
    return sum((_num(r["implementation_fee"]) for r in chain if r["collection_period"] == month), Decimal("0"))


def _prior(period: str) -> str:
    y, m = int(period[:4]), int(period[5:])
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def update_ar_rollforward(path: str, chain: list[dict[str, str]], log: list[dict[str, str]], version: str) -> None:
    fields, rows = _read(path)
    for r in rows:
        p = r["period"][:7]
        add_begin, add_end = _outstanding(chain, _prior(p)), _outstanding(chain, p)
        billed, collected = _billed(chain, p), _collected(chain, p)
        if add_begin + billed - collected != add_end:
            raise ValueError(f"{version} {p}: implementation AR does not roll ({add_begin} + {billed} - {collected} != {add_end})")
        r["beginning_accounts_receivable"] = _money(_num(r["beginning_accounts_receivable"]) + add_begin)
        r["new_billings"] = _money(_num(r["new_billings"]) + billed)
        r["cash_collections"] = _money(_num(r["cash_collections"]) + collected)
        r["ending_accounts_receivable"] = _money(_num(r["ending_accounts_receivable"]) + add_end)
        if billed or collected:
            log.append({"version": version, "period": p, "file": os.path.basename(path), "action": "added",
                        "detail": f"implementation billings {billed:,.2f}; collections {collected:,.2f}; "
                                  f"open at month end {add_end:,.2f}", "amount": _money(billed)})
    _write(path, fields, rows)


def update_cash_collections(path: str, chain: list[dict[str, str]], log: list[dict[str, str]], version: str) -> None:
    fields, rows = _read(path)
    for r in rows:
        p = r["period"][:7]
        before = sum((_num(x["implementation_fee"]) for x in chain if x["collection_period"] < p), Decimal("0"))
        collected = _collected(chain, p)
        r["cash_collections"] = _money(_num(r["cash_collections"]) + collected)
        r["beginning_cash"] = _money(_num(r["beginning_cash"]) + before)
        r["ending_cash"] = _money(_num(r["ending_cash"]) + before + collected)
    log.append({"version": version, "period": "", "file": os.path.basename(path), "action": "added",
                "detail": "implementation collections added to cash_collections; beginning and ending cash include "
                          "implementation cash collected to date", "amount": ""})
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
            "service_period_start": s["invoice_date"], "service_period_end": s["invoice_date"],
            "invoice_date": s["invoice_date"], "due_date": s["due_date"], "invoice_amount": s["implementation_fee"],
            "payment_status": "Paid" if s["collection_period"] <= last_month else "Open",
            "billing_cadence": "One-time", "billing_terms": f"Net {TERMS_DAYS}", "currency": "USD",
        })
        added += 1
    log.append({"version": version, "period": "", "file": os.path.basename(path), "action": "added",
                "detail": f"{added} implementation invoices (invoice file covers {min(months)}..{max(months)})",
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
            "recognized_revenue": s["implementation_fee"], "recognized_arr": "0", "revenue_type": "Implementation",
        })
        added += 1
    log.append({"version": version, "period": "", "file": os.path.basename(path), "action": "added",
                "detail": f"{added} Implementation rows (file covers {min(months)}..{max(months)})", "amount": ""})
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

    log: list[dict[str, str]] = []
    schedules: dict[str, list[dict[str, str]]] = {}
    for version in ("Actual", "Budget", "Forecast"):
        schedules[version], slog = build_schedule(src, version)
        log.extend(slog)

    for version in ("Actual", "Budget", "Forecast"):
        schedule = schedules[version]
        chain = chain_schedule(schedules, version)
        _write(os.path.join(dst, f"{version}_implementation_schedule.csv"), SCHEDULE_FIELDS, schedule)
        log.append({"version": version, "period": "", "file": f"{version}_implementation_schedule.csv", "action": "created",
                    "detail": f"{len(schedule)} new customers", "amount": _money(sum((_num(r['implementation_fee']) for r in schedule), Decimal('0')))})
        update_chart_of_accounts(os.path.join(dst, f"{version}_chart_of_accounts.csv"), log, version)
        update_invoices(os.path.join(dst, f"{version}_invoices.csv"), schedule, VERSION_END[version], log, version)
        rr = os.path.join(dst, f"{version}_revenue_recognition.csv")
        if os.path.exists(rr):
            update_revenue_recognition(rr, schedule, log, version)
        else:
            log.append({"version": version, "period": "", "file": f"{version}_revenue_recognition.csv", "action": "not in dataset",
                        "detail": "no revenue recognition file for this version", "amount": ""})
        update_ar_rollforward(os.path.join(dst, f"{version}_accounts_receivable_rollforward.csv"), chain, log, version)
        update_cash_collections(os.path.join(dst, f"{version}_cash_collections.csv"), chain, log, version)

    _write(os.path.join(dst, "implementation_revenue_log.csv"), ["version", "period", "file", "action", "detail", "amount"], log)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
