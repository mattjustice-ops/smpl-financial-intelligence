"""Unit tests for bookings confidence + coverage ratio."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.bookings.engine import (
    ForecastMethod,
    Opportunity,
    WinRates,
    compute_forecast,
)
from app.services.bookings.metrics import coverage_ratio, forecast_confidence


def _d(v) -> Decimal:
    return Decimal(str(v))


def _opp(
    oid: str = "OPP",
    *,
    stage: str = "Proposal",
    amount: str = "1000",
    probability: str = "0.5",
    close: date = date(2026, 2, 1),
) -> Opportunity:
    return Opportunity(
        opportunity_id=oid,
        customer_id="C",
        stage=stage,
        amount=_d(amount),
        probability=_d(probability),
        expected_close_date=close,
        rep_id="R",
        segment="Enterprise",
    )


def test_confidence_is_zero_for_empty_pipeline() -> None:
    c = forecast_confidence([], WinRates())
    assert c.score == _d("0")
    assert c.sample_size == 0
    assert c.band == "low"


def test_confidence_blends_probability_and_stage_maturity() -> None:
    opps = [_opp(stage="Proposal", probability="0.6"), _opp("O2", stage="Proposal", probability="0.4")]
    rates = WinRates(by_stage={"Proposal": _d("0.8")})
    c = forecast_confidence(opps, rates)
    # avg_probability = 0.5
    # stage_maturity  = 0.8
    # score           = 0.65 -> "high"
    assert c.avg_probability == _d("0.5000")
    assert c.stage_maturity_score == _d("0.8000")
    assert c.score == _d("0.6500")
    assert c.band == "high"


def test_unknown_stages_use_neutral_maturity_05() -> None:
    opps = [_opp(stage="Mystery", probability="0.5")]
    c = forecast_confidence(opps, WinRates())
    # avg_probability=0.5, stage_maturity=0.5 (neutral fallback) -> score 0.5
    assert c.score == _d("0.5000")
    assert c.band == "medium"


def test_coverage_against_explicit_target() -> None:
    opps = [_opp(amount="3000", probability="1")]  # pipeline = 3000
    f = compute_forecast(
        opps,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        win_rates=WinRates(),
        method=ForecastMethod.WEIGHTED,
    )
    assert coverage_ratio(f, target_bookings=_d("1000")) == _d("3.0000")


def test_coverage_against_forecast_when_no_target() -> None:
    # pipeline=2000, forecast=1000, coverage = 2.0
    opps = [_opp(amount="2000", probability="0.5")]
    f = compute_forecast(
        opps,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        win_rates=WinRates(),
        method=ForecastMethod.WEIGHTED,
    )
    assert coverage_ratio(f) == _d("2.0000")


def test_coverage_with_zero_denominator_returns_none() -> None:
    f = compute_forecast(
        [],
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        win_rates=WinRates(),
    )
    assert coverage_ratio(f) is None
    assert coverage_ratio(f, target_bookings=_d("0")) is None
