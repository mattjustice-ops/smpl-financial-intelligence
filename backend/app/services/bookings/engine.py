"""Pure bookings forecast engine.

No DB or framework dependencies. The repository layer translates rows from the
`opportunities` table into `Opportunity` dataclasses, the service layer plugs
in historical win rates, and `compute_forecast(...)` returns a full
`BookingsForecast` dataclass.

Forecast methods:
  - WEIGHTED:        amount * probability         (the deal owner's own forecast)
  - STAGE_ADJUSTED:  amount * win_rate_by_stage   (historical conversion at stage)
  - HISTORICAL:      amount * blend(stage, segment) win rates
Scenarios are applied as multipliers on top of the chosen method's totals
(default conservative=0.8, base=1.0, upside=1.2), with `upside` capped at the
total unweighted pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Iterable, Mapping, Optional

ZERO = Decimal("0")
ONE = Decimal("1")
TWO = Decimal("2")
MONEY = Decimal("0.01")
RATE = Decimal("0.0001")


def _q_money(v: Decimal) -> Decimal:
    return v.quantize(MONEY, rounding=ROUND_HALF_UP)


def _q_rate(v: Decimal) -> Decimal:
    return v.quantize(RATE, rounding=ROUND_HALF_UP)


def _to_decimal(value: object, default: Decimal = ZERO) -> Decimal:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class ForecastMethod(str, Enum):
    WEIGHTED = "weighted"
    STAGE_ADJUSTED = "stage_adjusted"
    HISTORICAL = "historical"


@dataclass(frozen=True)
class Opportunity:
    """Open opportunity input. All money values in the engine's reporting currency."""

    opportunity_id: str
    customer_id: str
    stage: str
    amount: Decimal
    probability: Decimal  # 0..1
    expected_close_date: date
    rep_id: Optional[str] = None
    segment: Optional[str] = None
    pipeline_created_date: Optional[date] = None


@dataclass(frozen=True)
class WinRates:
    """Historical win rates. Values are 0..1 (e.g. 0.35 == 35%)."""

    by_stage: Mapping[str, Decimal] = field(default_factory=dict)
    by_segment: Mapping[str, Decimal] = field(default_factory=dict)
    overall: Decimal = Decimal("0.25")


@dataclass(frozen=True)
class ScenarioFactors:
    conservative: Decimal = Decimal("0.8")
    base: Decimal = Decimal("1.0")
    upside: Decimal = Decimal("1.2")


@dataclass(frozen=True)
class OpportunityForecast:
    opportunity_id: str
    customer_id: str
    rep_id: Optional[str]
    segment: Optional[str]
    stage: str
    amount: Decimal
    probability: Decimal
    expected_close_date: date
    forecast_value: Decimal
    method: ForecastMethod

    def as_dict(self) -> dict[str, object]:
        return {
            "opportunity_id": self.opportunity_id,
            "customer_id": self.customer_id,
            "rep_id": self.rep_id,
            "segment": self.segment,
            "stage": self.stage,
            "amount": self.amount,
            "probability": self.probability,
            "expected_close_date": self.expected_close_date,
            "forecast_value": self.forecast_value,
            "method": self.method.value,
        }


@dataclass(frozen=True)
class BookingsForecast:
    method: ForecastMethod
    period_start: date
    period_end: date
    total_pipeline: Decimal
    total_forecast: Decimal
    by_month: dict[date, Decimal]
    by_quarter: dict[str, Decimal]
    by_rep: dict[str, Decimal]
    by_segment: dict[str, Decimal]
    by_customer: dict[str, Decimal]
    scenarios: dict[str, Decimal]
    opportunity_forecasts: list[OpportunityForecast]

    def as_dict(self) -> dict[str, object]:
        return {
            "method": self.method.value,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "total_pipeline": self.total_pipeline,
            "total_forecast": self.total_forecast,
            "by_month": {k.isoformat(): v for k, v in self.by_month.items()},
            "by_quarter": dict(self.by_quarter),
            "by_rep": dict(self.by_rep),
            "by_segment": dict(self.by_segment),
            "by_customer": dict(self.by_customer),
            "scenarios": dict(self.scenarios),
            "opportunity_forecasts": [r.as_dict() for r in self.opportunity_forecasts],
        }


# ---------------------------------------------------------------------------
# Forecast value functions (per opportunity)
# ---------------------------------------------------------------------------


def weighted_forecast_value(opp: Opportunity) -> Decimal:
    """amount * probability — the deal owner's own forecast."""
    return _q_money(_to_decimal(opp.amount) * _to_decimal(opp.probability))


def stage_adjusted_forecast_value(opp: Opportunity, win_rates: WinRates) -> Decimal:
    """amount * historical win rate at this stage (falls back to overall)."""
    rate = win_rates.by_stage.get(opp.stage, win_rates.overall)
    return _q_money(_to_decimal(opp.amount) * _to_decimal(rate))


def historical_forecast_value(opp: Opportunity, win_rates: WinRates) -> Decimal:
    """amount * blended(stage, segment) win rate.

    Blend = mean of stage rate and segment rate, each falling back to overall.
    """
    stage_rate = _to_decimal(win_rates.by_stage.get(opp.stage, win_rates.overall))
    seg_key = opp.segment or ""
    seg_rate = _to_decimal(win_rates.by_segment.get(seg_key, win_rates.overall))
    blended = (stage_rate + seg_rate) / TWO
    return _q_money(_to_decimal(opp.amount) * blended)


_METHOD_FN: dict[ForecastMethod, object] = {
    ForecastMethod.WEIGHTED: weighted_forecast_value,
    ForecastMethod.STAGE_ADJUSTED: stage_adjusted_forecast_value,
    ForecastMethod.HISTORICAL: historical_forecast_value,
}


def forecast_value_for(opp: Opportunity, method: ForecastMethod, win_rates: WinRates) -> Decimal:
    if method is ForecastMethod.WEIGHTED:
        return weighted_forecast_value(opp)
    if method is ForecastMethod.STAGE_ADJUSTED:
        return stage_adjusted_forecast_value(opp, win_rates)
    return historical_forecast_value(opp, win_rates)


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _quarter_label(d: date) -> str:
    q = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{q}"


def filter_to_period(
    opps: Iterable[Opportunity], period_start: date, period_end: date
) -> list[Opportunity]:
    return [o for o in opps if period_start <= o.expected_close_date <= period_end]


def _bucket_sum(
    rows: Iterable[OpportunityForecast], key_fn
) -> dict:
    out: dict = {}
    for r in rows:
        k = key_fn(r)
        if k is None or k == "":
            k = "(unassigned)"
        out[k] = _q_money(out.get(k, ZERO) + r.forecast_value)
    return out


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------


def compute_forecast(
    opportunities: Iterable[Opportunity],
    *,
    period_start: date,
    period_end: date,
    win_rates: WinRates,
    method: ForecastMethod = ForecastMethod.WEIGHTED,
    scenario_factors: Optional[ScenarioFactors] = None,
) -> BookingsForecast:
    """Compute a full bookings forecast for a given window and method."""
    factors = scenario_factors or ScenarioFactors()
    in_window = filter_to_period(opportunities, period_start, period_end)

    forecasts: list[OpportunityForecast] = []
    for opp in in_window:
        fv = forecast_value_for(opp, method, win_rates)
        forecasts.append(
            OpportunityForecast(
                opportunity_id=opp.opportunity_id,
                customer_id=opp.customer_id,
                rep_id=opp.rep_id,
                segment=opp.segment,
                stage=opp.stage,
                amount=_q_money(_to_decimal(opp.amount)),
                probability=_q_rate(_to_decimal(opp.probability)),
                expected_close_date=opp.expected_close_date,
                forecast_value=fv,
                method=method,
            )
        )

    total_pipeline = _q_money(sum((f.amount for f in forecasts), ZERO))
    total_forecast = _q_money(sum((f.forecast_value for f in forecasts), ZERO))

    by_month_raw: dict[date, Decimal] = {}
    for f in forecasts:
        m = _month_start(f.expected_close_date)
        by_month_raw[m] = _q_money(by_month_raw.get(m, ZERO) + f.forecast_value)
    by_month = dict(sorted(by_month_raw.items()))

    by_quarter_raw: dict[str, Decimal] = {}
    for f in forecasts:
        q = _quarter_label(f.expected_close_date)
        by_quarter_raw[q] = _q_money(by_quarter_raw.get(q, ZERO) + f.forecast_value)
    by_quarter = dict(sorted(by_quarter_raw.items()))

    by_rep = _bucket_sum(forecasts, lambda r: r.rep_id)
    by_segment = _bucket_sum(forecasts, lambda r: r.segment)
    by_customer = _bucket_sum(forecasts, lambda r: r.customer_id)

    upside_cap = total_pipeline
    scenarios = {
        "conservative": _q_money(total_forecast * factors.conservative),
        "base": _q_money(total_forecast * factors.base),
        "upside": _q_money(min(total_forecast * factors.upside, upside_cap)),
    }

    return BookingsForecast(
        method=method,
        period_start=period_start,
        period_end=period_end,
        total_pipeline=total_pipeline,
        total_forecast=total_forecast,
        by_month=by_month,
        by_quarter=by_quarter,
        by_rep=by_rep,
        by_segment=by_segment,
        by_customer=by_customer,
        scenarios=scenarios,
        opportunity_forecasts=forecasts,
    )
