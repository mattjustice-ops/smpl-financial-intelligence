"""Bookings forecast orchestration: load → forecast → metrics."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping, Optional

from sqlalchemy.orm import Session

from app.services.bookings.engine import (
    BookingsForecast,
    ForecastMethod,
    ScenarioFactors,
    WinRates,
    compute_forecast,
)
from app.services.bookings.metrics import ForecastConfidence, coverage_ratio, forecast_confidence
from app.services.bookings.repository import (
    compute_historical_win_rates,
    load_open_opportunities,
)
from app.services.workforce.engine import q_money
from app.services.workforce.integration import load_gtm_quota_capacity


@dataclass(frozen=True)
class BookingsForecastResult:
    forecast: BookingsForecast
    confidence: ForecastConfidence
    coverage_ratio: Optional[Decimal]
    win_rates_used: WinRates

    def as_dict(self) -> dict[str, object]:
        return {
            "forecast": self.forecast.as_dict(),
            "confidence": self.confidence.as_dict(),
            "coverage_ratio": self.coverage_ratio,
            "win_rates_used": {
                "by_stage": dict(self.win_rates_used.by_stage),
                "by_segment": dict(self.win_rates_used.by_segment),
                "overall": self.win_rates_used.overall,
            },
        }


def run_bookings_forecast(
    session: Session,
    organization_id: uuid.UUID,
    *,
    period_start: date,
    period_end: date,
    method: ForecastMethod = ForecastMethod.WEIGHTED,
    scenario_factors: Optional[ScenarioFactors] = None,
    target_bookings: Optional[Decimal] = None,
    win_rates_override: Optional[WinRates] = None,
    win_rates_by_stage_override: Optional[Mapping[str, Decimal]] = None,
    win_rates_by_segment_override: Optional[Mapping[str, Decimal]] = None,
) -> BookingsForecastResult:
    """End-to-end: load opportunities, derive (or take) win rates, forecast."""
    opps = load_open_opportunities(
        session,
        organization_id,
        period_start=period_start,
        period_end=period_end,
    )

    if target_bookings is None:
        gtm_rows = load_gtm_quota_capacity(
            session,
            organization_id,
            scenario="Forecast",
            start_period=period_start,
            end_period=period_end,
        )
        quota_total = sum((q_money(r.get("productive_quota_capacity_arr") or 0) for r in gtm_rows), Decimal("0"))
        if quota_total > 0:
            target_bookings = quota_total

    if win_rates_override is not None:
        rates = win_rates_override
    else:
        base = compute_historical_win_rates(session, organization_id)
        rates = WinRates(
            by_stage=dict(win_rates_by_stage_override or base.by_stage),
            by_segment=dict(win_rates_by_segment_override or base.by_segment),
            overall=base.overall,
        )

    forecast = compute_forecast(
        opps,
        period_start=period_start,
        period_end=period_end,
        win_rates=rates,
        method=method,
        scenario_factors=scenario_factors,
    )
    conf = forecast_confidence(opps, rates)
    cov = coverage_ratio(forecast, target_bookings)
    return BookingsForecastResult(
        forecast=forecast,
        confidence=conf,
        coverage_ratio=cov,
        win_rates_used=rates,
    )
