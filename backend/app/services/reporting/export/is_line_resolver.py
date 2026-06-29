"""Strict income-statement line matching — prevents COGS/revenue field swaps in deck payloads."""

from __future__ import annotations

from decimal import Decimal

from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.period_utils import to_period

ZERO = Decimal("0")

_REVENUE_TOTAL_LINES = frozenset(
    {
        "revenue",
        "total revenue",
        "gaap revenue",
        "total gaap revenue",
    }
)
_REVENUE_COMPONENT_LINES = frozenset(
    {
        "subscription revenue",
        "recurring revenue",
        "services revenue",
        "other revenue",
    }
)


def line_item_matches(field: str, line_item: str) -> bool:
    """Match IS rows to logical fields without COGS/revenue confusion."""
    li = line_item.lower().strip()
    if "deferred" in li:
        return False
    f = field.lower()
    if f == "revenue":
        if "cost" in li:
            return False
        return li in _REVENUE_TOTAL_LINES or li in _REVENUE_COMPONENT_LINES
    if f in ("cogs", "cost of revenue"):
        return ("cost" in li and "revenue" in li) or li in ("cogs", "cost of goods sold")
    if f == "gross profit":
        return "gross profit" in li
    if f == "ebitda":
        return "ebitda" in li and "margin" not in li
    if f == "net income":
        return li == "net income" or li.startswith("net income")
    return f in li


def fs_by_period(bundle: ReportingBundle, field: str, scenario: str) -> dict[str, Decimal]:
    """One amount per period for a logical IS field."""
    out: dict[str, Decimal] = {}
    components: dict[str, Decimal] = {}
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if not fs:
        return out
    f = field.lower()
    for row in fs.income_statement.rows:
        if row.scenario != scenario:
            continue
        if not line_item_matches(f, row.line_item):
            continue
        p = to_period(str(row.period)[:7])
        li = row.line_item.lower().strip()
        if f == "revenue":
            if li in _REVENUE_TOTAL_LINES:
                out[p] = row.amount
            else:
                components[p] = components.get(p, ZERO) + row.amount
        else:
            out[p] = row.amount
    for p, amt in components.items():
        if p not in out and amt:
            out[p] = amt
    return out


def fs_sum_periods(
    bundle: ReportingBundle,
    periods: list[str],
    scenario: str,
    field: str,
) -> Decimal:
    wanted = {to_period(p) for p in periods}
    by_p = fs_by_period(bundle, field, scenario)
    return sum(by_p.get(p, ZERO) for p in wanted)


def ending_cash_at(bundle: ReportingBundle, period: str, scenario: str) -> Decimal:
    """Ending cash — balance sheet is source of truth, waterfall fallback."""
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    p = to_period(period)
    if fs:
        for row in fs.balance_sheet.rows:
            if str(row.period)[:7] != p or row.scenario != scenario:
                continue
            li = row.line_item.lower()
            if li == "cash" or "cash and cash equivalents" in li:
                return row.amount
    from app.services.reporting.export.board_chart_service import _wf

    for wtype in ("ending_cash", "ending"):
        val = _wf(bundle, "cash_flow", wtype, p, scenario)
        if val:
            return val
    return ZERO
