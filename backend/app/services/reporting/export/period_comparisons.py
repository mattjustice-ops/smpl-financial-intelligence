"""Period rollups for month, quarter, YTD, and full-year reporting columns."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.services.reporting.period_utils import period_range, prior_period, to_period


def period_to_date(period: str) -> date:
    p = to_period(period)
    return date(int(p[:4]), int(p[5:7]), 1)


def fiscal_quarter(period: str) -> int:
    return (period_to_date(period).month - 1) // 3 + 1


def fiscal_year(period: str) -> int:
    return period_to_date(period).year


def quarter_start_period(as_of_period: str) -> str:
    p = period_to_date(as_of_period)
    q = fiscal_quarter(as_of_period)
    start_month = (q - 1) * 3 + 1
    return f"{p.year:04d}-{start_month:02d}"


def ytd_start_period(as_of_period: str) -> str:
    return f"{fiscal_year(as_of_period):04d}-01"


def fy_end_period(as_of_period: str) -> str:
    return f"{fiscal_year(as_of_period):04d}-12"


def periods_for_slice(
    start_period: str,
    end_period: str,
    as_of_period: str,
    slice_type: str,
) -> list[str]:
    as_of = to_period(as_of_period)
    start = to_period(start_period)
    end = min(to_period(end_period), as_of)
    if slice_type == "month":
        return [as_of] if start <= as_of <= end else []
    if slice_type == "qtd":
        q_start = quarter_start_period(as_of)
        return [p for p in period_range(max(start, q_start), as_of) if p <= end]
    if slice_type == "ytd":
        y_start = ytd_start_period(as_of)
        return [p for p in period_range(max(start, y_start), as_of) if p <= end]
    if slice_type == "fy":
        fy_start = ytd_start_period(as_of)
        fy_end = fy_end_period(as_of)
        return [p for p in period_range(max(start, fy_start), min(end, fy_end))]
    if slice_type == "range":
        return period_range(start, end)
    return period_range(start, as_of)


def sum_by_periods(values_by_period: dict[str, Decimal], periods: list[str]) -> Decimal:
    return sum((values_by_period.get(p, Decimal("0")) for p in periods), Decimal("0"))


def pivot_waterfall_rows(
    rows: list,
    *,
    line_key: str = "line_item",
    type_key: str = "waterfall_type",
    period_key: str = "period",
    amount_key: str = "amount",
    scenario_key: str = "scenario",
) -> dict[tuple[str, str], dict[str, Decimal]]:
    """(line_item, scenario) -> {period: amount}."""
    out: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for row in rows:
        line = getattr(row, line_key, None) or getattr(row, type_key, "")
        scenario = getattr(row, scenario_key, "Actual")
        period = to_period(getattr(row, period_key))
        amount = getattr(row, amount_key, Decimal("0"))
        out[(str(line), str(scenario))][period] += amount
    return dict(out)


def build_comparison_columns(as_of_period: str) -> list[tuple[str, str, list[str]]]:
    """Return (key, label, periods) comparison column definitions."""
    as_of = to_period(as_of_period)
    q_start = quarter_start_period(as_of)
    y_start = ytd_start_period(as_of)
    fy_start = y_start
    fy_end = fy_end_period(as_of)
    return [
        ("actual_mtd", f"Actual {as_of}", [as_of]),
        ("budget_mtd", f"Budget {as_of}", [as_of]),
        ("forecast_mtd", f"Forecast {as_of}", [as_of]),
        ("actual_qtd", f"Actual QTD", period_range(q_start, as_of)),
        ("budget_qtd", f"Budget QTD", period_range(q_start, as_of)),
        ("forecast_qtd", f"Forecast QTD", period_range(q_start, as_of)),
        ("actual_ytd", f"Actual YTD", period_range(y_start, as_of)),
        ("budget_ytd", f"Budget YTD", period_range(y_start, as_of)),
        ("forecast_ytd", f"Forecast YTD", period_range(y_start, as_of)),
        ("budget_fy", f"Budget FY", period_range(fy_start, fy_end)),
        ("forecast_fy", f"Forecast FY", period_range(fy_start, fy_end)),
    ]


def variance(actual: Decimal, baseline: Decimal) -> tuple[Decimal, Decimal | None]:
    diff = actual - baseline
    if baseline == 0:
        return diff, None
    return diff, (diff / baseline).quantize(Decimal("0.0001"))
