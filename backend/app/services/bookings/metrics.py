"""Forecast confidence + pipeline coverage ratio.

Confidence (0..1): weighted average of probability and stage maturity.
  - avg_probability: mean of opportunity.probability across in-window pipeline
  - stage_maturity:  mean of the (historical) win rate for each opportunity's
                     stage — using `win_rates.by_stage` if present, else 0.5
                     (neutral) so unseen stages don't drag the score to 0.
  - blended:         (avg_probability + stage_maturity) / 2

Coverage ratio: total_pipeline_amount / target_bookings (or vs total_forecast
when no target is supplied). Returns None if the denominator is 0.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, Optional

from app.services.bookings.engine import (
    BookingsForecast,
    Opportunity,
    OpportunityForecast,
    WinRates,
)

ZERO = Decimal("0")
ONE = Decimal("1")
TWO = Decimal("2")
NEUTRAL = Decimal("0.5")
RATE = Decimal("0.0001")
MONEY = Decimal("0.01")


def _q_rate(v: Decimal) -> Decimal:
    return v.quantize(RATE, rounding=ROUND_HALF_UP)


def _to_decimal(value: object, default: Decimal = ZERO) -> Decimal:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True)
class ForecastConfidence:
    """Heuristic confidence in the forecast.

    `band` is a coarse label for dashboards:
      score < 0.3   -> "low"
      0.3..0.6      -> "medium"
      >= 0.6        -> "high"
    """

    score: Decimal
    avg_probability: Decimal
    stage_maturity_score: Decimal
    sample_size: int
    band: str

    def as_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "avg_probability": self.avg_probability,
            "stage_maturity_score": self.stage_maturity_score,
            "sample_size": self.sample_size,
            "band": self.band,
        }


def _band(score: Decimal) -> str:
    if score < Decimal("0.3"):
        return "low"
    if score < Decimal("0.6"):
        return "medium"
    return "high"


def forecast_confidence(
    opportunities: Iterable[Opportunity], win_rates: WinRates
) -> ForecastConfidence:
    opps = list(opportunities)
    n = len(opps)
    if n == 0:
        return ForecastConfidence(
            score=ZERO,
            avg_probability=ZERO,
            stage_maturity_score=ZERO,
            sample_size=0,
            band="low",
        )

    avg_prob = sum((_to_decimal(o.probability) for o in opps), ZERO) / Decimal(n)
    stage_maturity = sum(
        (_to_decimal(win_rates.by_stage.get(o.stage, NEUTRAL)) for o in opps), ZERO
    ) / Decimal(n)
    score = (avg_prob + stage_maturity) / TWO

    return ForecastConfidence(
        score=_q_rate(score),
        avg_probability=_q_rate(avg_prob),
        stage_maturity_score=_q_rate(stage_maturity),
        sample_size=n,
        band=_band(score),
    )


def coverage_ratio(
    forecast: BookingsForecast, target_bookings: Optional[Decimal] = None
) -> Optional[Decimal]:
    """pipeline / target — i.e. how many "X" of pipeline you have vs goal.

    Common SaaS rule of thumb is 3x pipeline coverage. With no target given,
    coverage is measured against `total_forecast` (so a healthy forecast
    coverage > 1 means there's more pipeline than expected to close).
    """
    if target_bookings is not None:
        denom = _to_decimal(target_bookings)
    else:
        denom = forecast.total_forecast
    if denom == ZERO:
        return None
    return _q_rate(forecast.total_pipeline / denom)
