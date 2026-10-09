"""Rebuild the demo GL so actuals, budget and forecast tie to the P&L summary and the subledgers.

Writes new files only (never touches the database):
  <out>/Actual_gl_detail.csv, <out>/Budget_gl_detail.csv, <out>/Forecast_gl_detail.csv,
  <out>/gl_rebuild_log.csv, <out>/gl_balance_sheet_check.csv and the vendor files of vendor_model.write_files

Rules (agreed with Matt, Oct 5-9 2026):
  * Revenue, cost of revenue, S&M, D&A, interest and tax add up to the summary total for each month.
    R&D and G&A are what the subledgers book (payroll, stock comp, vendor bills and prepaid
    amortization); sync_v5_statements.py rewrites the income statement files from the GL.
  * Booked from the subledgers, by cost center:
      - payroll from <version>_payroll_register.csv: 5010 / 5020 one fully loaded row for Tier 1
        Support / Implementation, other cost centers one row per account (wages 6100, bonus 6105,
        payroll tax 6110, 401(k) match 6115, benefits 6120, severance 6125);
      - sales commissions from <version>_deferred_commissions_rollforward.csv: 6200 amortization of
        deferred commissions, 6210 commissions expensed when paid, 6110 payroll tax on the payouts.
        Before that file exists (the first pass, which add_commission_capitalization.py reads), the
        source 6200 rows are sized with the S&M line's other non-payroll source rows to the summary
        S&M less payroll, so the commission build replaces exactly what the summary held;
      - stock comp from the roster's equity grants (stock_comp.py): 5040 for cost-of-revenue cost
        centers, 6140 for the rest;
      - vendor spend (vendor_model.py): seat-priced and fixed contracts, rent, per-hire fees, the
        corporate card, audit and tax fees, and amortization of annual contracts paid up front.
        Actual rows are one per bill line (and per contract for amortization) with the vendor;
        Budget and Forecast rows are one per account and cost center a month
        (<version>_vendor_spend_plan.csv has the vendors).
  * The rest of cost of revenue (hosting, third-party product fees: 5000, 5030) and of S&M (marketing
    programs: 6300-6340) is usage: the source rows of those accounts keep their mix, are sized to the
    rest of the line, and are billed by the account's vendors (vendor_model.USAGE_SHARES). Every other
    source row in those lines, and every source row in R&D and G&A, is removed.
  * The "Accounting True-Up" plug is removed. Customer Success and Support labor posted to
    cost-of-revenue accounts stays there; the duplicate opex payroll for those cost centers is removed.
    Customer Success is part of Sales (S&M). Remaining Support stays in opex (G&A).
  * Months whose source GL holds only summary postings get account and team mix from a month that
    has it (same rows, relabeled and noted): June 2026 from May 2026, every 2024 and 2025 month from
    January 2026. The July-December forecast starts from June's actual mix.
  * Implementation & Onboarding revenue (4100) comes from <version>_implementation_schedule.csv and
    Recurring Services revenue (4200) from <version>_recurring_services_schedule.csv; subscription
    revenue is the summary revenue less those two.
  * Amounts are debit-positive (expenses positive, revenue negative), matching the rest of the GL.
  * Balance sheet: opening balances at Jan 2024 and monthly activity from the dataset's schedules and
    the AP and prepaid subledgers (build_gl_balance_sheet.py). gl_balance_sheet_check.csv compares the
    GL balances with the balance sheet files.

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
from stock_comp import COGS_COST_CENTERS, SBC_ACCOUNTS, by_cost_center  # noqa: E402
from vendor_model import (PREPAID_ACCOUNT, USAGE_ACCOUNTS, VENDORS, Ledger, VendorModel, month,  # noqa: E402
                          write_files)

CENT = Decimal("0.01")
ZERO = Decimal("0")
VERSIONS = ("Actual", "Budget", "Forecast")

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
# Lines sized to the summary; in the usage lines only USAGE_ACCOUNTS source rows are sized (the rest of the line).
SIZED_LINES = ("revenue", "cost_of_revenue", "sales_and_marketing", "depreciation_and_amortization",
               "interest_expense", "tax_expense")
USAGE_LINES = frozenset({"cost_of_revenue", "sales_and_marketing"})
BOTTOM_UP_LINES = frozenset({"research_and_development", "general_and_administrative"})

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
COMMISSION_SOURCE_SUFFIX = "_deferred_commissions_rollforward.csv"
PAYROLL_REGISTER_SUFFIX = "_payroll_register.csv"
# register column, account, account name, expense type
PAYROLL_COLUMNS = (
    ("regular_wages", "6100", "Base Salaries", "Salaries and Wages"),
    ("bonus", "6105", "Bonuses", "Bonus"),
    ("employer_payroll_tax", "6110", "Payroll Taxes", "Payroll Taxes"),
    ("retirement_match", "6115", "401(k) Employer Match", "Retirement Match"),
    ("health_benefits", "6120", "Employee Benefits", "Benefits"),
    ("severance", "6125", "Severance", "Severance"),
)
# Cost centers whose payroll is cost of revenue: one fully loaded row per month.
COGS_PAYROLL = {"SUP-TIER1": ("5010", "Customer Support Labor COGS"), "CS-IMPL": ("5020", "Customer Success Labor COGS")}
PAYROLL_ACCOUNTS = {a for _, a, _, _ in PAYROLL_COLUMNS} | {a for a, _ in COGS_PAYROLL.values()}
COMMISSION_ACCOUNT = "6200"
if set(COGS_PAYROLL) != COGS_COST_CENTERS:
    raise ValueError("stock_comp.COGS_COST_CENTERS must be the cost-of-revenue payroll cost centers")


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


def _drop_reason(row: dict[str, str]) -> str:
    if row["account_name"] in DROP_ACCOUNTS:
        return "plug removed"
    if row["statement_category"] == "Operating Expense" and row["cost_center"] in DUPLICATE_OPEX_COST_CENTERS:
        return "duplicate of the cost-of-revenue payroll"
    line = _line(row)
    if line in BOTTOM_UP_LINES:
        return "R&D and G&A are booked from payroll, stock comp and vendor bills"
    if line in USAGE_LINES and row["account_number"] not in USAGE_ACCOUNTS:
        return "booked from the payroll register, commission schedule, stock comp or vendor bills"
    return ""


def _scale(rows: list[dict[str, str]], factor: Decimal, want: Decimal) -> list[Decimal]:
    """Scale source rows (credit-positive) by ``factor`` into debit-positive cents that add up to ``want``;
    the rounding drift goes to the largest row."""
    new_amounts = [(Decimal(r["amount"]) * factor * Decimal("-1")).quantize(CENT, ROUND_HALF_UP) for r in rows]
    largest = max(range(len(rows)), key=lambda i: abs(new_amounts[i]))
    new_amounts[largest] += want - sum(new_amounts, ZERO)
    return new_amounts


def _read(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def rebuild(version: str, gl_rows: list[dict[str, str]], summary_rows: list[dict[str, str]],
            booked: dict[tuple[str, str], Decimal]):
    """Size each SIZED_LINES line's kept source rows to the summary less ``booked`` (by month and line: revenue
    from the revenue schedules, expense from the subledgers). Returns the GL rows (source rows outside the rebuilt
    months and balance sheet rows pass through) and the log."""
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
        reason = _drop_reason(row)
        if reason:
            log.append({"version": version, "period": period, "line": _line(row) or "", "action": "removed",
                        "detail": f"{row['department']} / {row['cost_center']} / {row['account_name']} ({reason})",
                        "amount": row["amount"]})
            continue
        by_period_line[(period, _line(row))].append(row)

    for target, template in fill.items():
        for (period, line), rows in list(by_period_line.items()):
            if period == template:
                by_period_line[(target, line)] = [_clone_to(r, target, template) for r in rows]

    for period in sorted(periods):
        for line in SIZED_LINES:
            rows = by_period_line.get((period, line), [])
            target = Decimal(str(summary[period][line] or 0)) - booked.get((period, line), ZERO)
            if line in USAGE_LINES and target < 0:
                raise ValueError(f"{version} {period} {line}: the subledgers book {-target:,.2f} more than the summary")
            if not rows:
                if target:
                    raise ValueError(f"{version} {period} {line}: {target:,.2f} left for the line but the GL has no rows")
                continue
            posted = sum((Decimal(r["amount"]) for r in rows), ZERO)
            # Source P&L rows are credit-positive: revenue +, expenses -.
            current = posted if line == "revenue" else -posted
            want = -target if line == "revenue" else target
            if current == 0:
                if len(rows) != 1:
                    raise ValueError(f"{version} {period} {line}: {len(rows)} zero rows cannot carry {target}")
                out.append({**rows[0], "amount": f"{want:.2f}"})
                log.append({"version": version, "period": period, "line": line, "action": "set",
                            "detail": "single account was 0; set to summary", "amount": f"{target:.2f}"})
                continue
            factor = target / current
            for r, amt in zip(rows, _scale(rows, factor, want)):
                out.append({**r, "amount": f"{amt:.2f}"})
            log.append({"version": version, "period": period, "line": line, "action": "scaled",
                        "detail": f"{len(rows)} rows; factor {factor:.4f}", "amount": f"{target:.2f}"})
    return out, log


def summary_sized_sm(version: str, gl_rows: list[dict[str, str]], summary_rows: list[dict[str, str]],
                     payroll: dict[tuple[str, str], Decimal]) -> list[dict[str, str]]:
    """The S&M line's non-payroll source rows sized to the summary S&M less payroll (debit-positive), as the GL was
    booked before the commission rollforward existed. Its 6200 rows are the commissions that build replaces."""
    summary = {r["period"][:7]: r for r in summary_rows}
    periods = REBUILD_PERIODS[version]
    fill = DETAIL_FROM_MONTH[version]
    by_period: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in gl_rows:
        p = row["period"][:7]
        if p not in periods or p in fill or row["statement"] == "Balance Sheet" or _line(row) != "sales_and_marketing":
            continue
        if row["account_name"] in DROP_ACCOUNTS or row["cost_center"] in DUPLICATE_OPEX_COST_CENTERS \
                or row["account_number"] in PAYROLL_ACCOUNTS:
            continue
        by_period[p].append(row)
    for target, template in fill.items():
        by_period[target] = [_clone_to(r, target, template) for r in by_period.get(template, [])]
    out = []
    for p, rows in sorted(by_period.items()):
        want = Decimal(str(summary[p]["sales_and_marketing"])) - payroll.get((p, "sales_and_marketing"), ZERO)
        current = -sum((Decimal(r["amount"]) for r in rows), ZERO)
        out += [{**r, "amount": f"{amt:.2f}"} for r, amt in zip(rows, _scale(rows, want / current, want))]
    return out


def forecast_seed(actual_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Forecast months start from the last actual month's sized source rows, in the source sign convention."""
    seed: list[dict[str, str]] = []
    template_rows = [r for r in actual_rows if r["period"][:7] == FORECAST_TEMPLATE_MONTH
                     and r["statement"] != "Balance Sheet"]
    for target in sorted(REBUILD_PERIODS["Forecast"]):
        for r in template_rows:
            nr = _clone_to(r, target, FORECAST_TEMPLATE_MONTH)
            nr["version"] = "Forecast"
            nr["amount"] = f"{-Decimal(r['amount']):.2f}"
            nr["notes"] = f"Forecast {target} built from {FORECAST_TEMPLATE_MONTH} actual account and team mix, sized to forecast summary"
            seed.append(nr)
    return seed


class Accounts:
    """Account names and classes from <version>_chart_of_accounts.csv; teams from <version>_department_cost_centers.csv."""

    def __init__(self, src: str, version: str):
        self.coa = {r["account_number"]: r for r in _read(os.path.join(src, f"{version}_chart_of_accounts.csv"))}
        self.sub = {r["cost_center"]: r["sub_department"]
                    for r in _read(os.path.join(src, f"{version}_department_cost_centers.csv"))}
        self.version = version

    def row(self, template: dict[str, str], period: str, account: str, department: str, cost_center: str,
            amount: Decimal, *, source_file: str, record_id: str, source_system: str, notes: str,
            vendor_id: str = "") -> dict[str, str]:
        if account not in self.coa:
            raise ValueError(f"{self.version}_chart_of_accounts.csv has no account {account}")
        if cost_center not in self.sub:
            raise ValueError(f"{self.version}_department_cost_centers.csv has no cost center {cost_center}")
        a = self.coa[account]
        return {
            **{k: "" for k in template},
            "organization_id": template["organization_id"], "version": self.version, "period": period,
            "account_number": account, "account_name": a["account_name"], "statement": "Income Statement",
            "statement_category": a["statement_category"], "account_group": a["account_group"],
            "expense_type": a["expense_type"], "department": department, "cost_center": cost_center,
            "sub_department": self.sub[cost_center], "vendor_id": vendor_id,
            "vendor_name": VENDORS[vendor_id].name if vendor_id else "", "source_file": source_file,
            "source_record_id": record_id, "amount": f"{amount:.2f}", "currency": "USD", "subsidiary": "US Parent",
            "source_system": source_system, "notes": notes,
        }


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
            "source_record_id": f"{version}-{period}-{IMPLEMENTATION_ACCOUNT}", "amount": f"{-sum(fees, ZERO):.2f}",
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


def commission_rows(src: str, version: str, template: dict[str, str]) -> list[dict[str, str]]:
    """6200 amortization, 6210 expensed commissions and 6110 payroll tax on payouts, from the
    version's deferred commissions rollforward, when the file exists."""
    source = f"{version}{COMMISSION_SOURCE_SUFFIX}"
    path = os.path.join(src, source)
    if not os.path.exists(path):
        return []
    lines = (
        ("commission_amortization", "6200", "Sales Commissions", "Sales Expense", "Commissions", "Sales", "SALES-AE",
         "Account Executives", "amortization of deferred commissions (ASC 340-40, straight-line from the payout month)"),
        ("expensed_commissions", "6210", "Sales Commissions - Expensed", "Sales Expense", "Commissions",
         "Customer Success", "CS-RENEW", "Renewals", "renewal commissions expensed when paid (12-month term)"),
        ("payroll_tax_on_commissions", "6110", "Payroll Taxes", "Labor", "Payroll Taxes", "Sales", "SALES-AE",
         "Account Executives", "employer payroll tax on commission payouts, expensed when paid"),
    )
    rows = []
    for r in _read(path):
        period = r["period"][:7]
        for col, number, name, group, etype, dept, cc, sub, note in lines:
            amount = Decimal(r[col] or "0")
            if not amount:
                continue
            rows.append({
                **{k: "" for k in template},
                "organization_id": template["organization_id"], "version": version, "period": period,
                "account_number": number, "account_name": name, "statement": "Income Statement",
                "statement_category": "Operating Expense", "account_group": group, "expense_type": etype,
                "department": dept, "cost_center": cc, "sub_department": sub, "source_file": source,
                "source_record_id": f"{version}-{period}-{number}-{col}", "amount": f"{amount:.2f}",
                "currency": "USD", "subsidiary": "US Parent", "source_system": "Demo Model", "notes": note,
            })
    return rows


def payroll_rows(src: str, version: str, template: dict[str, str]) -> list[dict[str, str]]:
    """GL payroll rows from <version>_payroll_register.csv by month and cost center."""
    source = f"{version}{PAYROLL_REGISTER_SUFFIX}"
    path = os.path.join(src, source)
    if not os.path.exists(path):
        raise FileNotFoundError(f"{source} is missing; build_workforce.py writes it")
    sub = {r["cost_center"]: r["sub_department"] for r in _read(os.path.join(src, f"{version}_department_cost_centers.csv"))}
    totals: dict[tuple[str, str, str], dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    heads: dict[tuple[str, str, str], int] = defaultdict(int)
    for r in _read(path):
        key = (r["period"][:7], r["department"], r["cost_center"])
        if r["cost_center"] not in sub:
            raise ValueError(f"{source}: cost center {r['cost_center']} is not in {version}_department_cost_centers.csv")
        for col, *_ in PAYROLL_COLUMNS:
            totals[key][col] += Decimal(r[col])
        totals[key]["total"] += Decimal(r["total_payroll_cost"])
        heads[key] += 1
    rows = []
    for (period, dept, cc), t in sorted(totals.items()):
        if cc in COGS_PAYROLL:
            number, name = COGS_PAYROLL[cc]
            lines = [(number, name, "Cost of Revenue", "COGS", "Labor", t["total"])]
        else:
            lines = [(number, name, "Operating Expense", "Labor", etype, t[col]) for col, number, name, etype in PAYROLL_COLUMNS]
        for number, name, category, group, etype, amount in lines:
            if not amount:
                continue
            rows.append({
                **{k: "" for k in template},
                "organization_id": template["organization_id"], "version": version, "period": period,
                "account_number": number, "account_name": name, "statement": "Income Statement",
                "statement_category": category, "account_group": group, "expense_type": etype,
                "department": dept, "cost_center": cc, "sub_department": sub[cc], "source_file": source,
                "source_record_id": f"{version}-{period}-{cc}-{number}", "amount": f"{amount:.2f}",
                "currency": "USD", "subsidiary": "US Parent", "source_system": "Payroll",
                "notes": f"{heads[(period, dept, cc)]} employees on the {period} payroll register",
            })
    return rows


def stock_comp_rows(src: str, version: str, template: dict[str, str], accts: Accounts) -> list[dict[str, str]]:
    """5040 / 6140 by month and cost center from the roster's equity grants (the same figures as <version>_SBC_Schedule.csv)."""
    rows = []
    for period, ccs in by_cost_center(src, version, sorted(REBUILD_PERIODS[version])).items():
        for (dept, cc), amount in sorted(ccs.items()):
            account = SBC_ACCOUNTS["cogs" if cc in COGS_COST_CENTERS else "opex"][0]
            rows.append(accts.row(template, period, account, dept, cc, amount,
                                  source_file=f"{version}_SBC_Schedule.csv",
                                  record_id=f"{version}-{period}-{cc}-{account}", source_system="Equity",
                                  notes="stock comp: equity_sbc_annual / 12 for days employed (non-cash)"))
    return rows


def model_fixed_by_line(model: VendorModel, version: str, accts: Accounts) -> dict[tuple[str, str], Decimal]:
    """Vendor expense that does not depend on the P&L summary, by month and line: every bill line except usage,
    plus prepaid amortization."""
    out: dict[tuple[str, str], Decimal] = defaultdict(Decimal)

    def add(p, account, dept, amount):
        cat = accts.coa[account]["statement_category"]
        line = LINE_BY_DEPARTMENT[dept] if cat == "Operating Expense" else LINE_BY_CATEGORY[cat]
        out[(p, line)] += amount

    periods = sorted(REBUILD_PERIODS[version])
    for p in periods:
        for ln in model.monthly_lines(version, p):
            add(p, ln.account, ln.department, ln.amount)
        for _, ln in model.hire_bills(version, p):
            add(p, ln.account, ln.department, ln.amount)
    for c in model.contracts(version):
        for p in periods:
            if c.amortization(p):
                add(p, c.account, c.department, c.amortization(p))
    return out


def vendor_rows(ledger: Ledger, template: dict[str, str], accts: Accounts) -> list[dict[str, str]]:
    """P&L rows from the vendor ledger: Actual per bill line and per contract month with the vendor; Budget and
    Forecast one row per month, account and cost center."""
    version = ledger.version
    periods = REBUILD_PERIODS[version]
    rows: list[dict[str, str]] = []
    plan: dict[tuple[str, str, str, str], Decimal] = defaultdict(Decimal)
    for b in ledger.bills:
        for i, ln in enumerate(b.lines, 1):
            p = month(ln.service_start)
            if ln.account == PREPAID_ACCOUNT or p not in periods:
                continue
            if version == "Actual":
                rows.append(accts.row(template, p, ln.account, ln.department, ln.cost_center, ln.amount,
                                      source_file="Actual_vendor_bills.csv", record_id=f"{b.id}-{i}",
                                      source_system="AP", vendor_id=b.vendor,
                                      notes=f"{ln.description}; bill {b.number} dated {b.bill_date.isoformat()}"))
            else:
                plan[(p, ln.account, ln.department, ln.cost_center)] += ln.amount
    for c in ledger.contracts:
        for p in sorted(periods):
            amount = c.amortization(p)
            if not amount:
                continue
            if version == "Actual":
                rows.append(accts.row(template, p, c.account, c.department, c.cost_center, amount,
                                      source_file="Actual_Prepaid_Amortization_Schedule.csv",
                                      record_id=f"{c.id}-{p}", source_system="AP", vendor_id=c.vendor,
                                      notes=f"{c.description}: amortization of the {c.start} prepaid"))
            else:
                plan[(p, c.account, c.department, c.cost_center)] += amount
    for (p, account, dept, cc), amount in sorted(plan.items()):
        rows.append(accts.row(template, p, account, dept, cc, amount,
                              source_file=f"{version}_vendor_spend_plan.csv",
                              record_id=f"{version}-{p}-{cc}-{account}-vendors", source_system="Demo Model",
                              notes="vendor spend plan, including amortization of prepaid contracts"))
    return rows


def by_line(rows: list[dict[str, str]]) -> dict[tuple[str, str], Decimal]:
    out: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for r in rows:
        out[(r["period"][:7], _line(r))] += Decimal(r["amount"])
    return out


def main(src: str, dst: str) -> None:
    os.makedirs(dst, exist_ok=True)
    all_log: list[dict[str, str]] = []
    fieldnames: list[str] = []
    model = VendorModel(src)
    sized: dict[str, list[dict[str, str]]] = {}
    summary_sm: dict[str, list[dict[str, str]]] = {}
    booked_rows: dict[str, list[dict[str, str]]] = {}
    fixed: dict[str, dict[tuple[str, str], Decimal]] = {}
    accts = {v: Accounts(src, v) for v in VERSIONS}
    for version in VERSIONS:
        if version == "Forecast":
            gl = forecast_seed(sized["Actual"])
        else:
            gl = _read(os.path.join(src, f"{version}_gl_detail.csv"))
            fieldnames = fieldnames or list(gl[0].keys())
        template = gl[0]
        summary = _read(os.path.join(src, f"{version}_income_statement.csv"))
        impl = implementation_rows(src, version, template)
        rsvc = recurring_services_rows(src, version, template)
        comm = commission_rows(src, version, template)
        pay = payroll_rows(src, version, template)
        if not comm:
            if version == "Forecast" and "Actual" not in summary_sm:
                raise ValueError("Forecast has no commission rollforward but Actual does")
            sm_source = forecast_seed(summary_sm["Actual"]) if version == "Forecast" else gl
            summary_sm[version] = summary_sized_sm(version, sm_source, summary, by_line(pay))
            comm = [{**r, "notes": "commissions as the summary S&M held them (sized with the line's other non-payroll "
                                   "source rows); replaced by the commission rollforward"}
                    for r in summary_sm[version] if r["account_number"] == COMMISSION_ACCOUNT]
        sbc = stock_comp_rows(src, version, template, accts[version])
        fixed[version] = model_fixed_by_line(model, version, accts[version])
        booked: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
        for r in impl + rsvc:
            booked[(r["period"], "revenue")] -= Decimal(r["amount"])
        for key, amount in by_line(comm + pay + sbc).items():
            booked[key] += amount
        for key, amount in fixed[version].items():
            booked[key] += amount
        rows, log = rebuild(version, gl, summary, booked)
        old_bs = [r for r in rows if r["statement"] == "Balance Sheet"]
        if old_bs:
            log.append({"version": version, "period": "", "line": "balance sheet", "action": "replaced",
                        "detail": f"{len(old_bs)} month-end balance rows replaced by opening balances and monthly activity",
                        "amount": ""})
        sized[version] = [r for r in rows if r["statement"] != "Balance Sheet"]
        booked_rows[version] = impl + rsvc + comm + pay + sbc
        for r in sized[version]:
            if r["account_number"] in USAGE_ACCOUNTS and r["period"][:7] in REBUILD_PERIODS[version]:
                model.add_usage(version, r["period"][:7], r["account_number"], r["department"], r["cost_center"],
                                Decimal(r["amount"]))
        for name, rws in (("payroll", pay), ("commissions", comm), ("stock comp", sbc),
                          ("implementation revenue", impl), ("recurring services revenue", rsvc)):
            if rws:
                log.append({"version": version, "period": "", "line": name, "action": "booked",
                            "detail": f"{len(rws)} rows from {rws[0]['source_file']}",
                            "amount": f"{sum(Decimal(r['amount']) for r in rws):.2f}"})
        all_log.extend(log)

    ledgers = {"Actual": model.ledger("Actual")}
    for version in ("Budget", "Forecast"):
        ledgers[version] = model.ledger(version, ledgers["Actual"])

    rebuilt: dict[str, list[dict[str, str]]] = {}
    for version in VERSIONS:
        vend = vendor_rows(ledgers[version], sized[version][0], accts[version])
        usage_rows = [r for r in sized[version]
                      if r["account_number"] in USAGE_ACCOUNTS and r["period"][:7] in REBUILD_PERIODS[version]]
        check_vendor_rows(version, vend, usage_rows, fixed[version])
        keep = [r for r in sized[version] if not (r["account_number"] in USAGE_ACCOUNTS
                                                  and r["period"][:7] in REBUILD_PERIODS[version])]
        rebuilt[version] = keep + booked_rows[version] + vend
        all_log.append({"version": version, "period": "", "line": "vendors", "action": "booked",
                        "detail": f"{len(vend)} rows from the vendor ledger ({len(ledgers[version].bills)} bills, "
                                  f"{len(ledgers[version].contracts)} prepaid contracts)",
                        "amount": f"{sum(Decimal(r['amount']) for r in vend):.2f}"})

    bs_rows, bs_log = build_balance_sheet_rows(src, rebuilt, ledgers)
    all_log.extend(bs_log)
    for version, rows in rebuilt.items():
        rows = rows + bs_rows[version]
        rows.sort(key=lambda r: (r["period"], r["statement"], r["department"], r["account_number"], r["cost_center"],
                                 r["source_record_id"]))
        with open(os.path.join(dst, f"{version}_gl_detail.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
    org = rebuilt["Actual"][0]["organization_id"]
    for note in write_files(dst, org, model, ledgers):
        all_log.append({"version": "", "period": "", "line": "vendors", "action": "file", "detail": note, "amount": ""})
    with open(os.path.join(dst, "gl_rebuild_log.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["version", "period", "line", "action", "detail", "amount"])
        w.writeheader()
        w.writerows(all_log)
    check = check_against_statements(src, balances(bs_rows, rebuilt))
    with open(os.path.join(dst, "gl_balance_sheet_check.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["version", "period", "line", "gl", "statement", "difference"])
        w.writeheader()
        w.writerows(check)


def check_vendor_rows(version: str, vend: list[dict[str, str]], usage_rows: list[dict[str, str]],
                      fixed: dict[tuple[str, str], Decimal]) -> None:
    """The ledger's usage rows are the sized usage rows (by month, account and cost center); its other rows are the
    fixed spend the lines were sized around."""
    want: dict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
    for r in usage_rows:
        want[(r["period"][:7], r["account_number"], r["cost_center"])] += Decimal(r["amount"])
    got: dict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
    rest: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for r in vend:
        if r["account_number"] in USAGE_ACCOUNTS:
            got[(r["period"], r["account_number"], r["cost_center"])] += Decimal(r["amount"])
        else:
            rest[(r["period"], _line(r))] += Decimal(r["amount"])
    for key in set(want) | set(got):
        if want[key] != got[key]:
            raise ValueError(f"{version} {key}: usage billed {got[key]:,.2f}, sized {want[key]:,.2f}")
    for key in set(rest) | set(fixed):
        if rest[key] != fixed.get(key, ZERO):
            raise ValueError(f"{version} {key}: vendor rows {rest[key]:,.2f}, sized around {fixed.get(key, ZERO):,.2f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
