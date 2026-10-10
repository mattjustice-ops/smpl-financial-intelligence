"""Stock-based compensation from the HRIS roster: each employee's equity_sbc_annual, expensed for the days employed.

Used by build_workforce.py ({V}_SBC_Schedule.csv) and rebuild_gl_to_summary.py (GL rows by cost center), so the
schedule and the GL come from the same roster.
"""

from __future__ import annotations

import calendar
import csv
import datetime as dt
import os
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ZERO = Decimal("0")
CLOSE = "2026-06"
# Cost centers whose people are cost of revenue (rebuild_gl_to_summary.COGS_PAYROLL).
COGS_COST_CENTERS = frozenset({"SUP-TIER1", "CS-IMPL"})
LINE_BY_DEPARTMENT = {"Sales": "sm", "Marketing": "sm", "Customer Success": "sm", "Engineering": "rd", "Product": "rd",
                      "Finance": "ga", "G&A": "ga", "Support": "ga"}
SBC_ACCOUNTS = {
    "cogs": ("5040", "Stock-Based Compensation COGS", "Cost of Revenue", "COGS"),
    "opex": ("6140", "Stock-Based Compensation", "Operating Expense", "Stock Compensation"),
}
SBC_EXPENSE_TYPE = "Stock-Based Compensation"
SCHEDULE_FIELDS = ["organization_id", "version", "period", "headcount", "total_sbc", "cogs_sbc", "sm_sbc", "rd_sbc",
                   "ga_sbc", "notes"]


def q(x: Decimal) -> Decimal:
    return x.quantize(CENT, ROUND_HALF_UP)


def _date(text: str) -> dt.date | None:
    return dt.date.fromisoformat(text) if text else None


def _days(hire: dt.date, exit_: dt.date | None, p: str) -> int:
    y, m = int(p[:4]), int(p[5:7])
    first, last = dt.date(y, m, 1), dt.date(y, m, calendar.monthrange(y, m)[1])
    start, end = max(hire, first), min(exit_ or last, last)
    return max(0, (end - start).days + 1)


def line_of(department: str, cost_center: str) -> str:
    return "cogs" if cost_center in COGS_COST_CENTERS else LINE_BY_DEPARTMENT[department]


def roster_for(src: str, version: str, period: str) -> str:
    """The roster that holds ``period``: the version's own from its first month, the Actual roster before it."""
    start = {"Actual": "0000-00", "Budget": "2026-01", "Forecast": "2026-07"}[version]
    return os.path.join(src, f"{version if period >= start else 'Actual'}_Employees.csv")


def by_cost_center(src: str, version: str, periods: list[str]) -> dict[str, dict[tuple[str, str], Decimal]]:
    """{period: {(department, cost_center): stock comp}} rounded to cents per cost center."""
    cache: dict[str, list[dict[str, str]]] = {}
    out: dict[str, dict[tuple[str, str], Decimal]] = {}
    for p in periods:
        path = roster_for(src, version, p)
        if path not in cache:
            with open(path, newline="", encoding="utf-8-sig") as f:
                cache[path] = list(csv.DictReader(f))
        full = Decimal(calendar.monthrange(int(p[:4]), int(p[5:7]))[1])
        acc: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
        for e in cache[path]:
            days = _days(_date(e["hire_date"]), _date(e["termination_date"]), p)
            if days:
                acc[(e["department"], e["cost_center"])] += Decimal(e["equity_sbc_annual"] or "0") / 12 * days / full
        out[p] = {k: q(v) for k, v in acc.items() if q(v)}
    return out


def heads(src: str, version: str, p: str) -> int:
    y, m = int(p[:4]), int(p[5:7])
    last = dt.date(y, m, calendar.monthrange(y, m)[1])
    with open(roster_for(src, version, p), newline="", encoding="utf-8-sig") as f:
        return sum(1 for e in csv.DictReader(f)
                   if _date(e["hire_date"]) <= last and (not e["termination_date"] or _date(e["termination_date"]) > last))


def schedule_rows(src: str, org: str, version: str, periods: list[str]) -> list[dict]:
    rows = []
    for p, ccs in by_cost_center(src, version, periods).items():
        lines = {k: ZERO for k in ("cogs", "sm", "rd", "ga")}
        for (dept, cc), amt in ccs.items():
            lines[line_of(dept, cc)] += amt
        rows.append({"organization_id": org, "version": version, "period": p, "headcount": str(heads(src, version, p)),
                     "total_sbc": sum(lines.values(), ZERO), "cogs_sbc": lines["cogs"], "sm_sbc": lines["sm"],
                     "rd_sbc": lines["rd"], "ga_sbc": lines["ga"],
                     "notes": f"{os.path.basename(roster_for(src, version, p))}: equity_sbc_annual / 12 for days "
                              f"employed; COGS = {', '.join(sorted(COGS_COST_CENTERS))}"})
    return rows
