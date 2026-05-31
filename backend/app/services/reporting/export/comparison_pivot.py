"""Pivot dashboard rows into Actual / Budget / Forecast comparison matrices."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.services.dashboard.schemas import WaterfallSummaryRow
from app.services.financial_statements.financial_statement_service import NormalizedStatementLine
from app.services.reporting.period_utils import to_period

SCENARIOS: tuple[str, ...] = ("Actual", "Budget", "Forecast")
ZERO = Decimal("0")


def _normalize_scenario(value: str) -> str:
    v = value.strip()
    if v in SCENARIOS:
        return v
    if v.lower() == "actual":
        return "Actual"
    if v.lower() == "budget":
        return "Budget"
    if v.lower() == "forecast":
        return "Forecast"
    return v


def pivot_waterfall_abc(
    rows: list[WaterfallSummaryRow],
    *,
    periods: list[str] | None = None,
) -> list[dict]:
    """One dict per (period, waterfall_type) with actual/budget/forecast amounts."""
    wanted = set(periods) if periods else None
    bucket: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    meta: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        period = to_period(row.period)
        if wanted is not None and period not in wanted:
            continue
        key = (period, row.waterfall_type)
        scenario = _normalize_scenario(row.scenario)
        bucket[key][scenario] += row.amount
        meta[key] = {"line_item": row.line_item, "line_item_order": str(row.line_item_order)}
    out: list[dict] = []
    for (period, waterfall_type), amounts in sorted(bucket.items(), key=lambda x: (x[0][0], x[0][1])):
        actual = amounts.get("Actual", Decimal("0"))
        budget = amounts.get("Budget", Decimal("0"))
        forecast = amounts.get("Forecast", Decimal("0"))
        out.append(
            {
                "period": period,
                "waterfall_type": waterfall_type,
                "line_item": meta[(period, waterfall_type)]["line_item"],
                "line_item_order": int(meta[(period, waterfall_type)]["line_item_order"]),
                "actual": actual,
                "budget": budget,
                "forecast": forecast,
            }
        )
    return sorted(out, key=lambda r: (r["period"], r["line_item_order"]))


def pivot_statement_abc(
    rows: list[NormalizedStatementLine],
    *,
    periods: list[str] | None = None,
) -> list[dict]:
    bucket: dict[tuple[str, str, str], dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    meta: dict[tuple[str, str, str], dict[str, object]] = {}
    for row in rows:
        period = to_period(str(row.period)[:7])
        if periods is not None and period not in periods:
            continue
        key = (period, row.section, row.line_item)
        scenario = _normalize_scenario(row.scenario)
        bucket[key][scenario] += row.amount
        meta[key] = {"line_item_order": row.line_item_order, "section": row.section}
    out: list[dict] = []
    for (period, section, line_item), amounts in sorted(
        bucket.items(), key=lambda x: (x[0][0], meta[x[0]]["line_item_order"])
    ):
        out.append(
            {
                "period": period,
                "section": section,
                "line_item": line_item,
                "line_item_order": meta[(period, section, line_item)]["line_item_order"],
                "actual": amounts.get("Actual", Decimal("0")),
                "budget": amounts.get("Budget", Decimal("0")),
                "forecast": amounts.get("Forecast", Decimal("0")),
            }
        )
    return out


def pivot_waterfall_wide(
    rows: list[WaterfallSummaryRow],
    periods: list[str],
) -> list[dict]:
    """One row per waterfall line; values keyed by period then scenario."""
    wanted = set(periods)
    bucket: dict[tuple[str, str, int], dict[str, dict[str, Decimal]]] = defaultdict(
        lambda: defaultdict(lambda: {"actual": ZERO, "budget": ZERO, "forecast": ZERO})
    )
    for row in rows:
        period = to_period(row.period)
        if period not in wanted:
            continue
        key = (row.waterfall_type, row.line_item, row.line_item_order)
        scenario = _normalize_scenario(row.scenario).lower()
        if scenario in bucket[key][period]:
            bucket[key][period][scenario] += row.amount
    out: list[dict] = []
    for (waterfall_type, line_item, line_item_order), by_period in sorted(
        bucket.items(), key=lambda x: (x[0][2], x[0][0])
    ):
        out.append(
            {
                "waterfall_type": waterfall_type,
                "line_item": line_item,
                "line_item_order": line_item_order,
                "by_period": dict(by_period),
            }
        )
    return out


def pivot_statement_wide(
    rows: list[NormalizedStatementLine],
    periods: list[str],
) -> list[dict]:
    wanted = set(periods)
    bucket: dict[tuple[str, str, int], dict[str, dict[str, Decimal]]] = defaultdict(
        lambda: defaultdict(lambda: {"actual": ZERO, "budget": ZERO, "forecast": ZERO})
    )
    for row in rows:
        period = to_period(str(row.period)[:7])
        if period not in wanted:
            continue
        key = (row.section, row.line_item, row.line_item_order)
        scenario = _normalize_scenario(row.scenario).lower()
        if scenario in bucket[key][period]:
            bucket[key][period][scenario] += row.amount
    out: list[dict] = []
    for (section, line_item, line_item_order), by_period in sorted(
        bucket.items(), key=lambda x: (x[0][2], x[0][0], x[0][1])
    ):
        out.append(
            {
                "section": section,
                "line_item": line_item,
                "line_item_order": line_item_order,
                "by_period": dict(by_period),
            }
        )
    return out
