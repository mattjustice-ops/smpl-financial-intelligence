"""Period slices for Management P&L — FY outlook vs full-year budget."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.services.reporting.period_utils import period_range, prior_period, to_period


def month_start(value: date | str) -> date:
    p = to_period(value) if isinstance(value, str) else to_period(value.isoformat())
    return date(int(p[:4]), int(p[5:7]), 1)


def default_as_of_cutover(fiscal_year: int) -> str:
    """Last closed actual month for demo dataset (aligns with board close)."""
    return f"{fiscal_year:04d}-05"


@dataclass(frozen=True)
class PeriodContext:
    fiscal_year: int
    as_of_period: str
    fy_periods: tuple[str, ...]
    closed_periods: tuple[str, ...]
    open_periods: tuple[str, ...]
    current_month: tuple[str, ...]
    prior_month: tuple[str, ...]
    qtd_periods: tuple[str, ...]
    ytd_periods: tuple[str, ...]

    @property
    def as_of_date(self) -> date:
        return month_start(self.as_of_period)


def build_period_context(
    *,
    fiscal_year: int,
    as_of_period: str,
    period_mode: str = "month",
) -> PeriodContext:
    fy_start = f"{fiscal_year:04d}-01"
    fy_end = f"{fiscal_year:04d}-12"
    fy = tuple(period_range(fy_start, fy_end))
    as_of = to_period(as_of_period)
    closed = tuple(p for p in fy if p <= as_of)
    open_ = tuple(p for p in fy if p > as_of)
    prior = (prior_period(as_of),) if as_of != fy[0] else ()
    q = (month_start(as_of).month - 1) // 3 + 1
    q_start = (q - 1) * 3 + 1
    qtd = tuple(p for p in fy if int(p[5:7]) >= q_start and int(p[5:7]) < q_start + 3)
    ytd = closed
    if period_mode == "qtd":
        current = qtd
    elif period_mode == "ytd":
        current = ytd
    elif period_mode == "fy":
        current = fy
    else:
        current = (as_of,)
    return PeriodContext(
        fiscal_year=fiscal_year,
        as_of_period=as_of,
        fy_periods=fy,
        closed_periods=closed,
        open_periods=open_,
        current_month=(as_of,),
        prior_month=prior,
        qtd_periods=qtd,
        ytd_periods=ytd,
    )


def sum_metric(
    by_period: dict[str, dict[str, Decimal]],
    periods: tuple[str, ...] | list[str],
    key: str,
) -> Decimal:
    total = Decimal("0")
    for p in periods:
        total += by_period.get(p, {}).get(key, Decimal("0"))
    return total


def fy_outlook(
    actual: dict[str, dict[str, Decimal]],
    forecast: dict[str, dict[str, Decimal]],
    ctx: PeriodContext,
    key: str,
) -> Decimal:
    return sum_metric(actual, ctx.closed_periods, key) + sum_metric(forecast, ctx.open_periods, key)


def fy_budget(budget: dict[str, dict[str, Decimal]], ctx: PeriodContext, key: str) -> Decimal:
    return sum_metric(budget, ctx.fy_periods, key)


def variance(outlook: Decimal, budget: Decimal) -> tuple[Decimal, Decimal | None]:
    var = outlook - budget
    pct = (var / abs(budget)).quantize(Decimal("0.0001")) if budget != 0 else None
    return var, pct
