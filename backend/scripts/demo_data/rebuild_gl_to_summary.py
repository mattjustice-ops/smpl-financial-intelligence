"""Rebuild the demo GL so 2026 actuals, budget and forecast add up to the P&L summary.

Writes new files only (never touches the database):
  <out>/Actual_gl_detail.csv, <out>/Budget_gl_detail.csv, <out>/Forecast_gl_detail.csv,
  <out>/gl_rebuild_log.csv

Rules (agreed with Matt, Oct 5 2026):
  * Every P&L line (revenue, cost of revenue, S&M, R&D, G&A, D&A, interest, tax) adds up
    to the summary total for that month. Within a line, accounts keep their mix and
    are scaled by one factor, logged per month and line.
  * Customer Success and Support labor already posted to cost-of-revenue accounts stays
    there; the duplicate opex payroll for those same cost centers is removed.
  * Customer Success is part of Sales (S&M). Remaining Support stays in opex (G&A).
  * The "Accounting True-Up" plug is removed.
  * June 2026 actuals only had summary postings. Its team detail is built from May's
    accounts and teams (same rows, relabeled and noted), then sized to June's summary.
  * The July–December forecast uses the same layout, accounts and teams as actuals: each
    month starts from June's actual rows and is sized to the forecast summary. It replaces
    the old planning-layout forecast file.
  * Amounts are debit-positive (expenses positive, revenue negative), matching the
    rest of the GL. Balance sheet rows and months outside the rebuild are untouched.

Usage:
  python rebuild_gl_to_summary.py <source_folder> <output_folder>
"""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

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

REBUILD_PERIODS = {
    "Actual": {f"2026-{m:02d}" for m in range(1, 7)},
    "Budget": {f"2026-{m:02d}" for m in range(1, 13)},
    "Forecast": {f"2026-{m:02d}" for m in range(7, 13)},
}

# Months whose source GL holds only summary postings: target month -> month whose detail mix is used.
DETAIL_FROM_MONTH = {
    "Actual": {"2026-06": "2026-05"},
    "Budget": {},
    "Forecast": {},
}

FORECAST_TEMPLATE_MONTH = "2026-06"


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


def rebuild(version: str, gl_rows: list[dict[str, str]], summary_rows: list[dict[str, str]]):
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
    template_rows = [r for r in actual_rows if r["period"][:7] == FORECAST_TEMPLATE_MONTH and r["statement"] != "Balance Sheet"]
    for target in sorted(REBUILD_PERIODS["Forecast"]):
        for r in template_rows:
            nr = _clone_to(r, target, FORECAST_TEMPLATE_MONTH)
            nr["version"] = "Forecast"
            nr["amount"] = f"{-Decimal(r['amount']):.2f}"
            nr["notes"] = f"Forecast {target} built from {FORECAST_TEMPLATE_MONTH} actual account and team mix, sized to forecast summary"
            seed.append(nr)
    return seed


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
        rows, log = rebuild(version, gl, summary)
        rebuilt[version] = rows
        all_log.extend(log)
        rows.sort(key=lambda r: (r["period"], r["statement"], r["department"], r["account_number"], r["cost_center"]))
        with open(os.path.join(dst, f"{version}_gl_detail.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
    with open(os.path.join(dst, "gl_rebuild_log.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["version", "period", "line", "action", "detail", "amount"])
        w.writeheader()
        w.writerows(all_log)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
