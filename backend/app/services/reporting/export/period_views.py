"""MoM, QTD, YTD and current-month rollups for export tabs."""

from __future__ import annotations

from decimal import Decimal

from app.services.reporting.export.period_comparisons import variance
from app.services.reporting.period_utils import period_range, prior_period, to_period

ZERO = Decimal("0")


def ytd_periods(as_of_period: str, *, fiscal_year: int | None = None) -> list[str]:
    year = fiscal_year or int(to_period(as_of_period)[:4])
    start = f"{year:04d}-01"
    return period_range(start, as_of_period)


def qtd_periods(as_of_period: str) -> list[str]:
    p = to_period(as_of_period)
    month = int(p[5:7])
    q_start_month = ((month - 1) // 3) * 3 + 1
    start = f"{p[:4]}-{q_start_month:02d}"
    return period_range(start, as_of_period)


def sum_field(
    by_period: dict[str, dict[str, Decimal | None]],
    periods: list[str],
    field: str,
) -> Decimal:
    total = ZERO
    for period in periods:
        raw = by_period.get(period, {}).get(field)
        if raw is not None:
            total += raw
    return total


def mom_change(
    by_period: dict[str, dict[str, Decimal | None]],
    as_of_period: str,
    field: str = "actual",
) -> tuple[Decimal, Decimal, Decimal | None]:
    current = by_period.get(as_of_period, {}).get(field) or ZERO
    prior = by_period.get(prior_period(as_of_period), {}).get(field) or ZERO
    delta = current - prior
    pct = (delta / prior) if prior != ZERO else None
    return current, prior, delta if pct is not None else delta


def build_summary_metrics(
    by_period: dict[str, dict[str, Decimal | None]],
    as_of_period: str,
) -> dict[str, dict[str, Decimal | None]]:
    """Current month, MoM, QTD, YTD for actual/budget/outlook."""
    ytd_p = ytd_periods(as_of_period)
    qtd_p = qtd_periods(as_of_period)
    prior = prior_period(as_of_period)

    def pack(field: str) -> dict[str, Decimal | None]:
        cm = by_period.get(as_of_period, {}).get(field)
        pm = by_period.get(prior, {}).get(field)
        delta = (cm - pm) if cm is not None and pm is not None else None
        return {
            "current_month": cm,
            "prior_month": pm,
            "mom_delta": delta,
            "qtd": sum_field(by_period, qtd_p, field) if qtd_p else None,
            "ytd": sum_field(by_period, ytd_p, field) if ytd_p else None,
        }

    return {
        "actual": pack("actual"),
        "budget": pack("budget"),
        "outlook": pack("outlook"),
        "forecast": pack("forecast"),
    }


def variance_pack(actual: Decimal | None, baseline: Decimal | None) -> dict[str, Decimal | None]:
    if actual is None or baseline is None:
        return {"var_d": None, "var_pct": None}
    a = actual or ZERO
    b = baseline or ZERO
    d, p = variance(a, b)
    return {"var_d": d, "var_pct": p}
