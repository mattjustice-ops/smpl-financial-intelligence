"""Rebuild the demo GL so actuals, budget and forecast add up to the P&L summary.

Writes new files only (never touches the database):
  <out>/Actual_gl_detail.csv, <out>/Budget_gl_detail.csv, <out>/Forecast_gl_detail.csv,
  <out>/gl_rebuild_log.csv

Rules (agreed with Matt, Oct 5-6 2026):
  * Every P&L line (revenue, cost of revenue, S&M, R&D, G&A, D&A, interest, tax) adds up
    to the summary total for that month. Within a line, accounts keep their mix and
    are scaled by one factor, logged per month and line.
  * Customer Success and Support labor already posted to cost-of-revenue accounts stays
    there; the duplicate opex payroll for those same cost centers is removed.
  * Customer Success is part of Sales (S&M). Remaining Support stays in opex (G&A).
  * The "Accounting True-Up" plug is removed.
  * Months whose source GL holds only summary postings get team detail from a month that
    has it (same rows, relabeled and noted), then sized to the month's summary: June 2026
    from May 2026, and every 2024 and 2025 month from January 2026.
  * The July–December forecast uses the same layout, accounts and teams as actuals: each
    month starts from June's actual rows and is sized to the forecast summary. It replaces
    the old planning-layout forecast file.
  * Amounts are debit-positive (expenses positive, revenue negative), matching the
    rest of the GL.
  * Implementation & Onboarding revenue (account 4100) comes from
    <version>_implementation_schedule.csv and Recurring Services revenue (account 4200)
    from <version>_recurring_services_schedule.csv, one row per month each. They are part
    of the summary's revenue: subscription revenue is the summary revenue less those two,
    so total revenue and net income equal the summary.
  * Balance sheet: the old month-end balance rows are replaced by opening balances at
    Jan 2024 and monthly activity from the dataset's schedules (build_gl_balance_sheet.py).
    gl_balance_sheet_check.csv compares the GL balances with the balance sheet files.

Usage:
  python rebuild_gl_to_summary.py <source_folder> <output_folder>
"""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_gl_balance_sheet import balances, build_balance_sheet_rows, check_against_statements  # noqa: E402

CENT = Decimal("0.01")

DUPLICATE_OPEX_COST_CENTERS = {"CS-IMPL", "SUP-TIER1"}
DROP_ACCOUNTS = {"Accounting True-Up"}

LINE_BY_DEPARTMENT = {
    "Sales": "sales_and_marketing",
    "Marketing": "sales_and_marketing",
    "Customer Success": "sales_and_marketing",
    "Engineering": "research_and_development",
    "Product": "research_and_development",
    "Finance": "general_and_administrative",
    "G&A": "general_and_administrative",
    "Support": "general_and_administrative",
}

LINE_BY_CATEGORY = {
    "Revenue": "revenue",
    "Cost of Revenue": "cost_of_revenue",
    "D&A": "depreciation_and_amortization",
    "Interest": "interest_expense",
    "Taxes": "tax_expense",
}

HISTORY_MONTHS = [f"{y}-{m:02d}" for y in (2024, 2025) for m in range(1, 13)]

REBUILD_PERIODS = {
    "Actual": set(HISTORY_MONTHS) | {f"2026-{m:02d}" for m in range(1, 7)},
    "Budget": {f"2026-{m:02d}" for m in range(1, 13)},
    "Forecast": {f"2026-{m:02d}" for m in range(7, 13)},
}

# Months whose source GL holds only summary postings: target month -> month whose detail mix is used.
DETAIL_FROM_MONTH = {
    "Actual": {**{p: "2026-01" for p in HISTORY_MONTHS}, "2026-06": "2026-05"},
    "Budget": {},
    "Forecast": {},
}

FORECAST_TEMPLATE_MONTH = "2026-06"
IMPLEMENTATION_ACCOUNT = "4100"
RECURRING_SERVICES_ACCOUNT = "4200"
ADDED_REVENUE_ACCOUNTS = {IMPLEMENTATION_ACCOUNT, RECURRING_SERVICES_ACCOUNT}


def _clone_to(row: dict[str, str], target: str, template: str) -> dict[str, str]:
    nr = dict(row)
    nr["period"] = target
    if nr.get("source_record_id"):
        nr["source_record_id"] = nr["source_record_id"].replace(template, target)
    nr["notes"] = f"{target} detail built from {template} account and team mix, sized to {target} summary"
    return nr


def _line(row: dict[str, str]) -> str | None:
    if row["statement"] == "Balance Sheet":
        return None
    category = row["statement_category"]
    if category == "Operating Expense":
        return LINE_BY_DEPARTMENT[row["department"]]
    return LINE_BY_CATEGORY[category]


def _keep(row: dict[str, str]) -> bool:
    if row["account_name"] in DROP_ACCOUNTS:
        return False
    if row["statement_category"] == "Operating Expense" and row["cost_center"] in DUPLICATE_OPEX_COST_CENTERS:
        return False
    return True


def _read(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def rebuild(version: str, gl_rows: list[dict[str, str]], summary_rows: list[dict[str, str]],
            added_revenue: dict[str, Decimal]):
    """``added_revenue``: implementation + recurring services by month, carved out of the summary revenue."""
    summary = {r["period"][:7]: r for r in summary_rows}
    periods = REBUILD_PERIODS[version]
    fill = DETAIL_FROM_MONTH[version]
    out: list[dict[str, str]] = []
    log: list[dict[str, str]] = []
    by_period_line: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)

    for row in gl_rows:
        period = row["period"][:7]
        if period not in periods or row["statement"] == "Balance Sheet":
            out.append(row)
            continue
        if period in fill:
            log.append({"version": version, "period": period, "line": row["account_group"], "action": "replaced",
                        "detail": f"summary posting {row['account_name']}; detail built from {fill[period]}",
                        "amount": row["amount"]})
            continue
        if not _keep(row):
            log.append({"version": version, "period": period, "line": _line(row) or "", "action": "removed",
                        "detail": f"{row['department']} / {row['cost_center']} / {row['account_name']}",
                        "amount": row["amount"]})
            continue
        by_period_line[(period, _line(row))].append(row)

    for target, template in fill.items():
        for (period, line), rows in list(by_period_line.items()):
            if period == template:
                by_period_line[(target, line)] = [_clone_to(r, target, template) for r in rows]

    for (period, line), rows in sorted(by_period_line.items()):
        target = Decimal(str(summary[period][line]))
        if line == "revenue":
            target -= added_revenue.get(period, Decimal("0"))
        posted = sum((Decimal(r["amount"]) for r in rows), Decimal("0"))
        # Source P&L rows are credit-positive: revenue +, expenses -.
        current = posted if line == "revenue" else -posted
        want = -target if line == "revenue" else target
        if current == 0:
            if len(rows) != 1:
                raise ValueError(f"{version} {period} {line}: {len(rows)} zero rows cannot carry {target}")
            nr = dict(rows[0])
            nr["amount"] = f"{want:.2f}"
            out.append(nr)
            log.append({"version": version, "period": period, "line": line, "action": "set",
                        "detail": "single account was 0; set to summary", "amount": f"{target:.2f}"})
            continue
        factor = target / current
        sign = Decimal("-1")
        new_amounts = [(Decimal(r["amount"]) * factor * sign).quantize(CENT, ROUND_HALF_UP) for r in rows]
        drift = want - sum(new_amounts, Decimal("0"))
        largest = max(range(len(rows)), key=lambda i: abs(new_amounts[i]))
        new_amounts[largest] += drift
        for r, amt in zip(rows, new_amounts):
            nr = dict(r)
            nr["amount"] = f"{amt:.2f}"
            out.append(nr)
        log.append({"version": version, "period": period, "line": line, "action": "scaled",
                    "detail": f"{len(rows)} rows; factor {factor:.4f}", "amount": f"{target:.2f}"})

    for (period, line) in {(p, l) for p in periods for l in set(LINE_BY_CATEGORY.values()) | set(LINE_BY_DEPARTMENT.values())}:
        if (period, line) not in by_period_line and Decimal(str(summary[period][line] or 0)) != 0:
            raise ValueError(f"{version} {period} {line}: summary has a total but the GL has no rows")
    return out, log


def forecast_seed(actual_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Forecast months start from the last actual month's P&L rows, in the source sign convention."""
    seed: list[dict[str, str]] = []
    template_rows = [r for r in actual_rows if r["period"][:7] == FORECAST_TEMPLATE_MONTH and r["statement"] != "Balance Sheet"
                     and r["account_number"] not in ADDED_REVENUE_ACCOUNTS]
    for target in sorted(REBUILD_PERIODS["Forecast"]):
        for r in template_rows:
            nr = _clone_to(r, target, FORECAST_TEMPLATE_MONTH)
            nr["version"] = "Forecast"
            nr["amount"] = f"{-Decimal(r['amount']):.2f}"
            nr["notes"] = f"Forecast {target} built from {FORECAST_TEMPLATE_MONTH} actual account and team mix, sized to forecast summary"
            seed.append(nr)
    return seed


def implementation_rows(src: str, version: str, template: dict[str, str]) -> list[dict[str, str]]:
    """One 4100 revenue row per month from <version>_implementation_schedule.csv, when the file exists."""
    path = os.path.join(src, f"{version}_implementation_schedule.csv")
    if not os.path.exists(path):
        return []
    by_month: dict[str, list[Decimal]] = defaultdict(list)
    customers: dict[str, Decimal] = defaultdict(Decimal)
    for r in _read(path):
        by_month[r["period"][:7]].append(Decimal(r["implementation_fee"]))
        customers[r["period"][:7]] += Decimal(r.get("win_probability") or "1")
    rows = []
    for period, fees in sorted(by_month.items()):
        rows.append({
            **{k: "" for k in template},
            "organization_id": template["organization_id"], "version": version, "period": period,
            "account_number": IMPLEMENTATION_ACCOUNT, "account_name": "Implementation & Onboarding Revenue",
            "statement": "Income Statement", "statement_category": "Revenue", "account_group": "Revenue",
            "expense_type": "Implementation & Onboarding", "department": "Revenue", "cost_center": "REV-IMPL",
            "sub_department": "Implementation & Onboarding", "source_file": f"{version}_implementation_schedule.csv",
            "source_record_id": f"{version}-{period}-{IMPLEMENTATION_ACCOUNT}", "amount": f"{-sum(fees, Decimal('0')):.2f}",
            "currency": "USD", "subsidiary": "US Parent", "source_system": "Demo Model",
            "notes": f"{customers[period]:g} expected new customers from {len(fees)} deals; "
                     f"one-time implementation fee by segment",
        })
    return rows


def recurring_services_rows(src: str, version: str, template: dict[str, str]) -> list[dict[str, str]]:
    """One 4200 revenue row per month from <version>_recurring_services_schedule.csv, when the file exists."""
    path = os.path.join(src, f"{version}_recurring_services_schedule.csv")
    if not os.path.exists(path):
        return []
    by_month: dict[str, Decimal] = defaultdict(Decimal)
    customers: dict[str, int] = defaultdict(int)
    for r in _read(path):
        by_month[r["period"][:7]] += Decimal(r["recurring_services_revenue"])
        customers[r["period"][:7]] += 1
    rows = []
    for period, amount in sorted(by_month.items()):
        rows.append({
            **{k: "" for k in template},
            "organization_id": template["organization_id"], "version": version, "period": period,
            "account_number": RECURRING_SERVICES_ACCOUNT, "account_name": "Recurring Services Revenue",
            "statement": "Income Statement", "statement_category": "Revenue", "account_group": "Revenue",
            "expense_type": "Recurring Services", "department": "Revenue", "cost_center": "REV-RSVC",
            "sub_department": "Recurring Services", "source_file": f"{version}_recurring_services_schedule.csv",
            "source_record_id": f"{version}-{period}-{RECURRING_SERVICES_ACCOUNT}", "amount": f"{-amount:.2f}",
            "currency": "USD", "subsidiary": "US Parent", "source_system": "Demo Model",
            "notes": f"{customers[period]} customers; support and technical account management, "
                     f"10% of subscription revenue",
        })
    return rows


def main(src: str, dst: str) -> None:
    os.makedirs(dst, exist_ok=True)
    all_log: list[dict[str, str]] = []
    fieldnames: list[str] = []
    rebuilt: dict[str, list[dict[str, str]]] = {}
    for version in ("Actual", "Budget", "Forecast"):
        if version == "Forecast":
            gl = forecast_seed(rebuilt["Actual"])
        else:
            gl = _read(os.path.join(src, f"{version}_gl_detail.csv"))
            fieldnames = fieldnames or list(gl[0].keys())
        summary = _read(os.path.join(src, f"{version}_income_statement.csv"))
        impl = implementation_rows(src, version, gl[0])
        rsvc = recurring_services_rows(src, version, gl[0])
        added: dict[str, Decimal] = defaultdict(Decimal)
        for r in impl + rsvc:
            added[r["period"]] -= Decimal(r["amount"])
        rows, log = rebuild(version, gl, summary, added)
        old_bs = [r for r in rows if r["statement"] == "Balance Sheet"]
        if old_bs:
            log.append({"version": version, "period": "", "line": "balance sheet", "action": "replaced",
                        "detail": f"{len(old_bs)} month-end balance rows replaced by opening balances and monthly activity",
                        "amount": ""})
        rebuilt[version] = [r for r in rows if r["statement"] != "Balance Sheet"] + impl + rsvc
        for name, account, added_rows in (("implementation", IMPLEMENTATION_ACCOUNT, impl),
                                          ("recurring services", RECURRING_SERVICES_ACCOUNT, rsvc)):
            if added_rows:
                log.append({"version": version, "period": "", "line": "revenue", "action": "carved out",
                            "detail": f"{len(added_rows)} months of {name} revenue (account {account}); "
                                      f"subscription revenue is the summary revenue less this",
                            "amount": f"{-sum(Decimal(r['amount']) for r in added_rows):.2f}"})
        all_log.extend(log)

    bs_rows, bs_log = build_balance_sheet_rows(src, rebuilt)
    all_log.extend(bs_log)
    for version, rows in rebuilt.items():
        rows = rows + bs_rows[version]
        rows.sort(key=lambda r: (r["period"], r["statement"], r["department"], r["account_number"], r["cost_center"]))
        with open(os.path.join(dst, f"{version}_gl_detail.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
    with open(os.path.join(dst, "gl_rebuild_log.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["version", "period", "line", "action", "detail", "amount"])
        w.writeheader()
        w.writerows(all_log)
    check = check_against_statements(src, balances(bs_rows, rebuilt))
    with open(os.path.join(dst, "gl_balance_sheet_check.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["version", "period", "line", "gl", "statement", "difference"])
        w.writeheader()
        w.writerows(check)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
