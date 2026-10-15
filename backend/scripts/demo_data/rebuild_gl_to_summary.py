"""Rebuild the demo GL so actuals, budget and forecast tie to the P&L summary and the subledgers.

Writes new files only (never touches the database):
  <out>/Actual_gl_detail.csv, <out>/Budget_gl_detail.csv, <out>/Forecast_gl_detail.csv,
  <out>/gl_rebuild_log.csv, <out>/gl_balance_sheet_check.csv and the vendor files of vendor_model.write_files

Rules (agreed with Matt, Oct 5-9 2026):
  * Revenue, S&M, D&A and interest add up to the summary total for each month (build_workforce.py adds stock comp
    to the summary lines, so it does not displace marketing programs). Income tax is recomputed on the rebuilt
    pre-tax income: INCOME_TAX_RATE of cumulative pre-tax income since January 2024 when positive (losses carry
    forward; losses before 2024 are not known). Cost of revenue, R&D and G&A are what the subledgers book (payroll,
    stock comp, vendor bills including the usage meters for hosting, third-party product services and development
    cloud, and prepaid amortization); sync_v5_statements.py rewrites the income statement files from the GL.
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
      - bad debt expense (6560, Revenue Accounting) = the provision for credit losses in
        <version>_allowance_for_doubtful_accounts.csv (G&A);
      - vendor spend (vendor_model.py): seat-priced and fixed contracts, straight-line office lease cost
        (ASC 842), per-hire fees, the corporate card, audit and tax fees, and amortization of annual contracts
        paid up front. Expense is booked in the month of service, whenever the bill comes.
        Actual rows are one per bill line (per accrued line for services not billed by the close; per
        contract and lease for amortization and lease cost) with the vendor;
        Budget and Forecast rows are one per account and cost center a month
        (<version>_vendor_spend_plan.csv has the vendors).
  * Actual marketing programs (6300-6340) are booked, not sized to the summary's S&M. January-May 2026
    keeps the source spend. 2024-2025 and June 2026 have no program detail: January-May copy that calendar
    month of 2026, and June-December (including June 2026) are the January-May 2026 average. Those rows are
    flagged as generated. Budget and Forecast still size program spend to their summaries. The rows are billed
    by the account's vendors (vendor_model.USAGE_SHARES). Every other source row in S&M, and every source row
    in cost of revenue, R&D and G&A, is removed. Hosting (5000), third-party product services (5030) and
    development cloud (6410) are billed by the vendor model's usage meters, priced on the source GL's spend
    on those accounts.
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
    the AP, prepaid, accrued expense and lease subledgers (build_gl_balance_sheet.py). gl_balance_sheet_check.csv compares the
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
from build_gl_balance_sheet import (AP_SOURCE, AR_SOURCE, COMMISSION_SOURCE, EQUITY_SOURCE,  # noqa: E402
                                    FIXED_ASSET_SOURCE, JOURNAL_SOURCE, REVENUE_SOURCE, balances,
                                    build_balance_sheet_rows, check_against_statements)
from stock_comp import COGS_COST_CENTERS, SBC_ACCOUNTS, by_cost_center  # noqa: E402
from vendor_model import (BALANCE_SHEET_LINE_ACCOUNTS, CLOSE, LEASE_COST_CENTER, LEASE_DEPARTMENT,  # noqa: E402
                          LEASES, RENT_ACCOUNT, USAGE_ACCOUNTS, VENDORS, Ledger, VendorModel, last_day, month,
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
PAYROLL_SOURCE = "Payroll"
# The subledger or journal that posts the source rows each line keeps (the usage line keeps only vendor-billed
# accounts).
SOURCE_BY_LINE = {
    "revenue": REVENUE_SOURCE,
    "sales_and_marketing": AP_SOURCE,
    "depreciation_and_amortization": FIXED_ASSET_SOURCE,
    "interest_expense": JOURNAL_SOURCE,
    "tax_expense": JOURNAL_SOURCE,
}
# Lines sized to the summary; in the usage line only USAGE_ACCOUNTS source rows are sized (the rest of the line).
SIZED_LINES = ("revenue", "sales_and_marketing", "depreciation_and_amortization", "interest_expense", "tax_expense")
USAGE_LINES = frozenset({"sales_and_marketing"})
BOTTOM_UP_LINES = frozenset({"cost_of_revenue", "research_and_development", "general_and_administrative"})
BOTTOM_UP_REASON = "cost of revenue, R&D and G&A are booked from payroll, stock comp, vendor bills and usage meters"
if set(SOURCE_BY_LINE) != set(SIZED_LINES):
    raise ValueError("every sized line needs the source that posts its rows")
# Federal 21% plus state, net of the federal benefit.
INCOME_TAX_RATE = Decimal("0.25")

HISTORY_MONTHS = [f"{y}-{m:02d}" for y in (2024, 2025) for m in range(1, 13)]
MARKETING_PROGRAM_ACCOUNTS = frozenset({"6300", "6310", "6320", "6330", "6340"})
SOURCE_PROGRAM_MONTHS = [f"2026-{m:02d}" for m in range(1, 6)]
GENERATED_PROGRAM_MONTHS = set(HISTORY_MONTHS) | {"2026-06"}
GENERATED_PROGRAM_NOTE = (
    "generated from January-May 2026 marketing program spend; "
    "the source GL has no program detail for this month"
)

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
ALLOWANCE_SUFFIX = "_allowance_for_doubtful_accounts.csv"
BAD_DEBT_ACCOUNT = "6560"
BAD_DEBT_COST_CENTER = "FIN-REV"
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
        return BOTTOM_UP_REASON
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
        if version == "Actual" and row["account_number"] in MARKETING_PROGRAM_ACCOUNTS:
            continue
        reason = _drop_reason(row)
        line = _line(row)
        if reason:
            log.append({"version": version, "period": period, "line": line or "", "action": "removed",
                        "detail": f"{row['department']} / {row['cost_center']} / {row['account_name']} ({reason})",
                        "amount": row["amount"]})
            continue
        by_period_line[(period, line)].append(row)

    for target, template in fill.items():
        for (period, line), rows in list(by_period_line.items()):
            if period == template:
                by_period_line[(target, line)] = [_clone_to(r, target, template) for r in rows]

    for period in sorted(periods):
        for line in SIZED_LINES:
            if version == "Actual" and line == "sales_and_marketing":
                continue
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
                out.append({**rows[0], "amount": f"{want:.2f}", "source_system": SOURCE_BY_LINE[line]})
                log.append({"version": version, "period": period, "line": line, "action": "set",
                            "detail": "single account was 0; set to summary", "amount": f"{target:.2f}"})
                continue
            factor = target / current
            for r, amt in zip(rows, _scale(rows, factor, want)):
                out.append({**r, "amount": f"{amt:.2f}", "source_system": SOURCE_BY_LINE[line]})
            log.append({"version": version, "period": period, "line": line, "action": "scaled",
                        "detail": f"{len(rows)} rows; factor {factor:.4f}", "amount": f"{target:.2f}"})
    return out, log


def _program_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (row["account_number"], row["department"], row["cost_center"], row.get("notes") or "")


def _program_row(row: dict[str, str], period: str, amount: Decimal, notes: str) -> dict[str, str]:
    nr = dict(row)
    nr["period"] = period
    nr["amount"] = f"{amount:.2f}"
    nr["notes"] = notes
    nr["source_system"] = AP_SOURCE
    record = row.get("source_record_id") or _program_key(row)[3]
    src_period = row["period"][:7]
    nr["source_record_id"] = record.replace(src_period, period) if src_period in record else f"{record}-{period}"
    return nr


def actual_marketing_program_rows(gl_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Actual marketing programs, debit-positive.

    January-May 2026 is the source spend. A later or earlier month with no source detail copies that
    calendar month when it falls in January-May, and otherwise the average of those five months.
    Generated rows carry GENERATED_PROGRAM_NOTE. Returns the rows and the log.
    """
    source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in gl_rows:
        period = row["period"][:7]
        if period in SOURCE_PROGRAM_MONTHS and row.get("statement") != "Balance Sheet" \
                and row["account_number"] in MARKETING_PROGRAM_ACCOUNTS:
            source[period].append(row)
    missing = [p for p in SOURCE_PROGRAM_MONTHS if not source[p]]
    if missing:
        raise ValueError(f"Actual GL has no marketing program spend for {', '.join(missing)}")

    by_key: dict[tuple[str, str, str, str], dict[str, Decimal]] = defaultdict(dict)
    templates: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for period, rows in source.items():
        for row in rows:
            key = _program_key(row)
            by_key[key][period] = by_key[key].get(period, ZERO) + Decimal(row["amount"])
            templates.setdefault(key, row)

    out: list[dict[str, str]] = []
    log: list[dict[str, str]] = []

    def emit(period: str, row: dict[str, str], credit: Decimal, generated: bool) -> None:
        amount = (-credit).quantize(CENT, ROUND_HALF_UP)
        if amount == 0:
            return
        notes = row.get("notes") or ""
        if generated:
            notes = f"{notes}; {GENERATED_PROGRAM_NOTE}" if notes else GENERATED_PROGRAM_NOTE
        out.append(_program_row(row, period, amount, notes))

    for period in SOURCE_PROGRAM_MONTHS:
        for row in source[period]:
            emit(period, row, Decimal(row["amount"]), False)
        total = sum((Decimal(r["amount"]) for r in out if r["period"] == period), ZERO)
        log.append({"version": "Actual", "period": period, "line": "sales_and_marketing", "action": "booked",
                    "detail": "marketing program spend booked from the source GL, not scaled to the S&M summary",
                    "amount": f"{total:.2f}"})

    same_month = {p[5:7] for p in SOURCE_PROGRAM_MONTHS}
    for period in sorted(GENERATED_PROGRAM_MONTHS):
        month = period[5:7]
        if month in same_month:
            template_period = f"2026-{month}"
            for row in source[template_period]:
                emit(period, row, Decimal(row["amount"]), True)
            detail = f"copied from {template_period} source marketing program spend; {GENERATED_PROGRAM_NOTE}"
        else:
            pieces: list[tuple[dict[str, str], Decimal]] = []
            for key, amounts in by_key.items():
                credit = sum((amounts.get(p, ZERO) for p in SOURCE_PROGRAM_MONTHS), ZERO) / Decimal(len(SOURCE_PROGRAM_MONTHS))
                pieces.append((templates[key], (-credit).quantize(CENT, ROUND_HALF_UP)))
            want = (-sum((sum(amounts.get(p, ZERO) for p in SOURCE_PROGRAM_MONTHS) for amounts in by_key.values()), ZERO)
                    / Decimal(len(SOURCE_PROGRAM_MONTHS))).quantize(CENT, ROUND_HALF_UP)
            if pieces:
                largest = max(range(len(pieces)), key=lambda i: abs(pieces[i][1]))
                row, amount = pieces[largest]
                pieces[largest] = (row, amount + want - sum((a for _, a in pieces), ZERO))
            for row, amount in pieces:
                if amount == 0:
                    continue
                notes = row.get("notes") or ""
                notes = f"{notes}; {GENERATED_PROGRAM_NOTE}" if notes else GENERATED_PROGRAM_NOTE
                out.append(_program_row(row, period, amount, notes))
            detail = f"average of {SOURCE_PROGRAM_MONTHS[0]} to {SOURCE_PROGRAM_MONTHS[-1]} source marketing program spend; {GENERATED_PROGRAM_NOTE}"
        total = sum((Decimal(r["amount"]) for r in out if r["period"] == period), ZERO)
        log.append({"version": "Actual", "period": period, "line": "sales_and_marketing", "action": "generated",
                    "detail": detail, "amount": f"{total:.2f}"})
    return out, log


def actual_program_month_totals(gl_rows: list[dict[str, str]]) -> dict[str, Decimal]:
    """Debit-positive Actual marketing program totals the rebuild books, by month."""
    rows, _ = actual_marketing_program_rows(gl_rows)
    out: dict[str, Decimal] = defaultdict(Decimal)
    for row in rows:
        out[row["period"][:7]] += Decimal(row["amount"])
    return out


def summary_sized_sm(version: str, gl_rows: list[dict[str, str]], summary_rows: list[dict[str, str]],
                     payroll: dict[tuple[str, str], Decimal]) -> list[dict[str, str]]:
    """The S&M line's non-payroll source rows sized to the summary S&M less payroll and stock comp (``payroll``,
    debit-positive), as the GL was booked before the commission rollforward existed. Its 6200 rows are the
    commissions that build replaces."""
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
            "currency": "USD", "subsidiary": "US Parent", "source_system": REVENUE_SOURCE,
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
            "currency": "USD", "subsidiary": "US Parent", "source_system": REVENUE_SOURCE,
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
        ("-clawback_amortization_reversal", "6200", "Sales Commissions", "Sales Expense", "Commissions", "Sales",
         "SALES-AE", "Account Executives", "no-start commission clawed back: amortization to date reversed "
                                           "(Actual_commission_clawbacks.csv)"),
        ("commission_write_downs", "6200", "Sales Commissions", "Sales Expense", "Commissions", "Sales", "SALES-AE",
         "Account Executives", "no-start outside the clawback window: unamortized commission written down "
                               "(Actual_commission_clawbacks.csv)"),
        ("expensed_commissions", "6210", "Sales Commissions - Expensed", "Sales Expense", "Commissions",
         "Customer Success", "CS-RENEW", "Renewals", "renewal commissions expensed when paid (12-month term)"),
        ("payroll_tax_on_commissions", "6110", "Payroll Taxes", "Labor", "Payroll Taxes", "Sales", "SALES-AE",
         "Account Executives", "employer payroll tax on commission payouts, expensed when paid"),
    )
    rows = []
    for r in _read(path):
        period = r["period"][:7]
        for col, number, name, group, etype, dept, cc, sub, note in lines:
            sign, col = (-1, col[1:]) if col.startswith("-") else (1, col)
            amount = sign * Decimal(r.get(col) or "0")
            if not amount:
                continue
            rows.append({
                **{k: "" for k in template},
                "organization_id": template["organization_id"], "version": version, "period": period,
                "account_number": number, "account_name": name, "statement": "Income Statement",
                "statement_category": "Operating Expense", "account_group": group, "expense_type": etype,
                "department": dept, "cost_center": cc, "sub_department": sub, "source_file": source,
                "source_record_id": f"{version}-{period}-{number}-{col}", "amount": f"{amount:.2f}",
                "currency": "USD", "subsidiary": "US Parent", "source_system": COMMISSION_SOURCE, "notes": note,
            })
    return rows


def bad_debt_rows(src: str, version: str, template: dict[str, str], accts: Accounts) -> list[dict[str, str]]:
    """6560 Bad Debt Expense (Revenue Accounting) = the month's provision for credit losses in
    <version>_allowance_for_doubtful_accounts.csv, when the file exists."""
    source = f"{version}{ALLOWANCE_SUFFIX}"
    path = os.path.join(src, source)
    if not os.path.exists(path):
        return []
    rows = []
    for r in _read(path):
        amount = Decimal(r["provision_for_credit_losses"])
        if amount:
            period = r["period"][:7]
            rows.append(accts.row(template, period, BAD_DEBT_ACCOUNT, "Finance", BAD_DEBT_COST_CENTER, amount,
                                  source_file=source, record_id=f"{version}-{period}-{BAD_DEBT_ACCOUNT}",
                                  source_system=AR_SOURCE,
                                  notes=f"provision for credit losses: allowance {Decimal(r['beginning_allowance']):,.2f} "
                                        f"-> {Decimal(r['ending_allowance']):,.2f}, write-offs "
                                        f"{Decimal(r['write_offs']):,.2f}"))
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
                "currency": "USD", "subsidiary": "US Parent", "source_system": PAYROLL_SOURCE,
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
                                  record_id=f"{version}-{period}-{cc}-{account}", source_system=EQUITY_SOURCE,
                                  notes="stock comp: equity_sbc_annual / 12 for days employed (non-cash)"))
    return rows


def model_fixed_by_line(model: VendorModel, version: str, accts: Accounts) -> dict[tuple[str, str], Decimal]:
    """Vendor expense that does not depend on the P&L summary, by month and line: every bill line except usage and
    lease payments, plus prepaid amortization and straight-line lease cost."""
    out: dict[tuple[str, str], Decimal] = defaultdict(Decimal)

    def add(p, account, dept, amount):
        cat = accts.coa[account]["statement_category"]
        line = LINE_BY_DEPARTMENT[dept] if cat == "Operating Expense" else LINE_BY_CATEGORY[cat]
        out[(p, line)] += amount

    periods = sorted(REBUILD_PERIODS[version])
    for p in periods:
        for ln in model.monthly_lines(version, p):
            if ln.account not in BALANCE_SHEET_LINE_ACCOUNTS:
                add(p, ln.account, ln.department, ln.amount)
        for _, ln in model.hire_bills(version, p):
            add(p, ln.account, ln.department, ln.amount)
        for lease in LEASES:
            if (m := lease.at(p)) is not None:
                add(p, RENT_ACCOUNT, LEASE_DEPARTMENT, m.straight_line_cost)
    for c in model.contracts(version):
        for p in periods:
            if c.amortization(p):
                add(p, c.account, c.department, c.amortization(p))
    return out


def _program_bill_note(version: str, period: str, line, note: str) -> str:
    """Generated Actual program months say so on the vendor bill that carries the spend."""
    if version == "Actual" and period in GENERATED_PROGRAM_MONTHS and line.account in MARKETING_PROGRAM_ACCOUNTS \
            and line.description == "Usage":
        return f"{note}; {GENERATED_PROGRAM_NOTE}"
    return note


def vendor_rows(ledger: Ledger, template: dict[str, str], accts: Accounts) -> list[dict[str, str]]:
    """P&L rows from the vendor ledger: Actual per bill line (services not billed by the close: per accrued line),
    per contract month and per lease month with the vendor; Budget and Forecast one row per month, account and cost
    center."""
    version = ledger.version
    periods = REBUILD_PERIODS[version]
    close = last_day(CLOSE)
    rows: list[dict[str, str]] = []
    plan: dict[tuple[str, str, str, str], Decimal] = defaultdict(Decimal)
    for b in ledger.bills:
        for i, ln in enumerate(b.lines, 1):
            p = month(ln.service_start)
            if ln.account in BALANCE_SHEET_LINE_ACCOUNTS or p not in periods:
                continue
            if version == "Actual" and b.bill_date > close:
                rows.append(accts.row(template, p, ln.account, ln.department, ln.cost_center, ln.amount,
                                      source_file="Actual_accrued_expenses_detail.csv",
                                      record_id=f"ACCR-{p.replace('-', '')}-{b.vendor}-{i}", source_system=AP_SOURCE,
                                      vendor_id=b.vendor,
                                      notes=_program_bill_note(version, p, ln, f"{ln.description}; accrued, not billed at the close")))
            elif version == "Actual":
                rows.append(accts.row(template, p, ln.account, ln.department, ln.cost_center, ln.amount,
                                      source_file="Actual_vendor_bills.csv", record_id=f"{b.id}-{i}",
                                      source_system=AP_SOURCE, vendor_id=b.vendor,
                                      notes=_program_bill_note(version, p, ln, f"{ln.description}; bill {b.number} dated {b.bill_date.isoformat()}")))
            else:
                plan[(p, ln.account, ln.department, ln.cost_center)] += ln.amount
    for lease in LEASES:
        for p in sorted(periods):
            m = lease.at(p)
            if m is None:
                continue
            if version == "Actual":
                rows.append(accts.row(template, p, RENT_ACCOUNT, LEASE_DEPARTMENT, LEASE_COST_CENTER,
                                      m.straight_line_cost, source_file="Actual_operating_lease_schedule.csv",
                                      record_id=f"{lease.id}-{p}", source_system=AP_SOURCE, vendor_id=lease.vendor,
                                      notes=f"{lease.description}: straight-line lease cost (ASC 842)"))
            else:
                plan[(p, RENT_ACCOUNT, LEASE_DEPARTMENT, LEASE_COST_CENTER)] += m.straight_line_cost
    for c in ledger.contracts:
        for p in sorted(periods):
            amount = c.amortization(p)
            if not amount:
                continue
            if version == "Actual":
                rows.append(accts.row(template, p, c.account, c.department, c.cost_center, amount,
                                      source_file="Actual_Prepaid_Amortization_Schedule.csv",
                                      record_id=f"{c.id}-{p}", source_system=AP_SOURCE, vendor_id=c.vendor,
                                      notes=f"{c.description}: amortization of the {c.start} prepaid"))
            else:
                plan[(p, c.account, c.department, c.cost_center)] += amount
    for (p, account, dept, cc), amount in sorted(plan.items()):
        rows.append(accts.row(template, p, account, dept, cc, amount,
                              source_file=f"{version}_vendor_spend_plan.csv",
                              record_id=f"{version}-{p}-{cc}-{account}-vendors", source_system=AP_SOURCE,
                              notes="vendor spend plan, including amortization of prepaid contracts"))
    return rows


def recompute_income_tax(rebuilt: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    """Set each month's tax row to INCOME_TAX_RATE x cumulative pre-tax income since the GL start when positive, less
    what earlier months booked (losses carry forward; Budget and Forecast continue from the Actual months before
    them). Returns the log."""
    pretax: dict[str, dict[str, Decimal]] = {v: defaultdict(Decimal) for v in VERSIONS}
    for v, rows in rebuilt.items():
        for r in rows:
            if r["statement"] != "Balance Sheet" and r["statement_category"] != "Taxes":
                pretax[v][r["period"][:7]] -= Decimal(r["amount"])
    log = []
    for v in VERSIONS:
        months = sorted(REBUILD_PERIODS[v])
        cum = sum((x for p, x in pretax["Actual"].items() if p < months[0] and p in REBUILD_PERIODS["Actual"]), ZERO)
        booked = (INCOME_TAX_RATE * max(cum, ZERO)).quantize(CENT, ROUND_HALF_UP)
        tax_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
        for r in rebuilt[v]:
            if r["statement_category"] == "Taxes" and r["period"][:7] in REBUILD_PERIODS[v]:
                tax_rows[r["period"][:7]].append(r)
        total = ZERO
        for p in months:
            if len(tax_rows[p]) != 1:
                raise ValueError(f"{v} {p}: {len(tax_rows[p])} tax rows; expected one")
            cum += pretax[v][p]
            due = (INCOME_TAX_RATE * max(cum, ZERO)).quantize(CENT, ROUND_HALF_UP)
            row = tax_rows[p][0]
            row["amount"] = f"{due - booked:.2f}"
            row["notes"] = (f"income tax: {INCOME_TAX_RATE:.0%} of cumulative pre-tax income since January 2024 "
                            f"({cum:,.2f}) when positive, less earlier months")
            total += due - booked
            booked = due
        log.append({"version": v, "period": "", "line": "tax_expense", "action": "recomputed",
                    "detail": f"{INCOME_TAX_RATE:.0%} of positive cumulative pre-tax income; cumulative at "
                              f"{months[-1]}: {cum:,.2f}", "amount": f"{total:.2f}"})
    return log


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
        sbc = stock_comp_rows(src, version, template, accts[version])
        bad = bad_debt_rows(src, version, template, accts[version])
        if not comm:
            if version == "Forecast" and "Actual" not in summary_sm:
                raise ValueError("Forecast has no commission rollforward but Actual does")
            sm_source = forecast_seed(summary_sm["Actual"]) if version == "Forecast" else gl
            summary_sm[version] = summary_sized_sm(version, sm_source, summary, by_line(pay + sbc))
            comm = [{**r, "source_system": COMMISSION_SOURCE,
                     "notes": "commissions as the summary S&M held them (sized with the line's other non-payroll "
                              "source rows); replaced by the commission rollforward"}
                    for r in summary_sm[version] if r["account_number"] == COMMISSION_ACCOUNT]
        fixed[version] = model_fixed_by_line(model, version, accts[version])
        booked: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
        for r in impl + rsvc:
            booked[(r["period"], "revenue")] -= Decimal(r["amount"])
        for key, amount in by_line(comm + pay + sbc).items():
            booked[key] += amount
        for key, amount in fixed[version].items():
            booked[key] += amount
        rows, log = rebuild(version, gl, summary, booked)
        if version == "Actual":
            prog, prog_log = actual_marketing_program_rows(gl)
            rows.extend(prog)
            log = prog_log + log
        old_bs = [r for r in rows if r["statement"] == "Balance Sheet"]
        if old_bs:
            log.append({"version": version, "period": "", "line": "balance sheet", "action": "replaced",
                        "detail": f"{len(old_bs)} month-end balance rows replaced by opening balances and monthly activity",
                        "amount": ""})
        sized[version] = [r for r in rows if r["statement"] != "Balance Sheet"]
        booked_rows[version] = impl + rsvc + comm + pay + sbc + bad
        for r in sized[version]:
            if r["account_number"] in USAGE_ACCOUNTS and r["period"][:7] in REBUILD_PERIODS[version]:
                model.add_usage(version, r["period"][:7], r["account_number"], r["department"], r["cost_center"],
                                Decimal(r["amount"]))
        for name, rws in (("payroll", pay), ("commissions", comm), ("stock comp", sbc), ("bad debt", bad),
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
        check_vendor_rows(version, vend, usage_rows, fixed[version], ledgers[version], accts[version], model)
        keep = [r for r in sized[version] if not (r["account_number"] in USAGE_ACCOUNTS
                                                  and r["period"][:7] in REBUILD_PERIODS[version])]
        rebuilt[version] = keep + booked_rows[version] + vend
        all_log.append({"version": version, "period": "", "line": "vendors", "action": "booked",
                        "detail": f"{len(vend)} rows from the vendor ledger ({len(ledgers[version].bills)} bills, "
                                  f"{len(ledgers[version].contracts)} prepaid contracts)",
                        "amount": f"{sum(Decimal(r['amount']) for r in vend):.2f}"})

    all_log.extend(recompute_income_tax(rebuilt))
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
                      fixed: dict[tuple[str, str], Decimal], ledger: Ledger, accts: Accounts,
                      model: VendorModel) -> None:
    """The ledger's rows on usage accounts are the sized usage rows, the usage meters' readings and the
    amortization of prepaid contracts on those accounts (by month, account and cost center); its other rows are the
    rest of the fixed spend the lines were sized around."""
    want: dict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
    for r in usage_rows:
        want[(r["period"][:7], r["account_number"], r["cost_center"])] += Decimal(r["amount"])
    for p in REBUILD_PERIODS[version]:
        for m in model.meters.readings(version, p):
            want[(p, m.meter.account, m.cost_center)] += m.amount
    fixed = dict(fixed)
    for c in ledger.contracts:
        if c.account not in USAGE_ACCOUNTS:
            continue
        cat = accts.coa[c.account]["statement_category"]
        line = LINE_BY_DEPARTMENT[c.department] if cat == "Operating Expense" else LINE_BY_CATEGORY[cat]
        for p in REBUILD_PERIODS[version]:
            if c.amortization(p):
                want[(p, c.account, c.cost_center)] += c.amortization(p)
                fixed[(p, line)] = fixed.get((p, line), ZERO) - c.amortization(p)
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
