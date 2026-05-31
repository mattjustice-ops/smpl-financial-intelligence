"""Unit tests for the pure bookings forecast engine."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.bookings.engine import (
    ForecastMethod,
    Opportunity,
    ScenarioFactors,
    WinRates,
    compute_forecast,
    historical_forecast_value,
    stage_adjusted_forecast_value,
    weighted_forecast_value,
)

PERIOD_START = date(2026, 1, 1)
PERIOD_END = date(2026, 3, 31)


def _d(v) -> Decimal:
    return Decimal(str(v))


def _opp(
    oid: str = "OPP-1",
    *,
    customer_id: str = "CUST-1",
    stage: str = "Proposal",
    amount: str = "10000",
    probability: str = "0.5",
    close: date = date(2026, 2, 15),
    rep_id: str | None = "REP-1",
    segment: str | None = "Enterprise",
) -> Opportunity:
    return Opportunity(
        opportunity_id=oid,
        customer_id=customer_id,
        stage=stage,
        amount=_d(amount),
        probability=_d(probability),
        expected_close_date=close,
        rep_id=rep_id,
        segment=segment,
    )


# ---------------------------------------------------------------------------
# Per-opportunity forecast values
# ---------------------------------------------------------------------------


def test_weighted_is_amount_times_probability() -> None:
    opp = _opp(amount="10000", probability="0.5")
    assert weighted_forecast_value(opp) == _d("5000.00")


def test_stage_adjusted_uses_stage_rate_with_overall_fallback() -> None:
    opp = _opp(stage="Proposal", amount="10000", probability="0.5")
    rates = WinRates(by_stage={"Proposal": _d("0.7")}, overall=_d("0.2"))
    assert stage_adjusted_forecast_value(opp, rates) == _d("7000.00")

    opp_unknown = _opp(stage="Mystery", amount="10000", probability="0.5")
    assert stage_adjusted_forecast_value(opp_unknown, rates) == _d("2000.00")


def test_historical_blends_stage_and_segment() -> None:
    opp = _opp(stage="Proposal", segment="Enterprise", amount="10000", probability="0.5")
    rates = WinRates(
        by_stage={"Proposal": _d("0.6")},
        by_segment={"Enterprise": _d("0.4")},
        overall=_d("0.25"),
    )
    # blend = (0.6 + 0.4) / 2 = 0.5; forecast = 10000 * 0.5 = 5000
    assert historical_forecast_value(opp, rates) == _d("5000.00")


def test_historical_falls_back_to_overall_when_missing() -> None:
    opp = _opp(stage="Unknown", segment=None, amount="1000", probability="0.5")
    rates = WinRates(overall=_d("0.5"))
    # blend = (0.5 + 0.5) / 2 = 0.5
    assert historical_forecast_value(opp, rates) == _d("500.00")


# ---------------------------------------------------------------------------
# Forecast period filter
# ---------------------------------------------------------------------------


def test_only_opportunities_inside_window_are_counted() -> None:
    opps = [
        _opp("IN", close=date(2026, 2, 1), amount="1000", probability="1"),
        _opp("BEFORE", close=date(2025, 12, 31), amount="9999", probability="1"),
        _opp("AFTER", close=date(2026, 4, 1), amount="9999", probability="1"),
    ]
    f = compute_forecast(
        opps,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        win_rates=WinRates(),
        method=ForecastMethod.WEIGHTED,
    )
    assert len(f.opportunity_forecasts) == 1
    assert f.opportunity_forecasts[0].opportunity_id == "IN"
    assert f.total_forecast == _d("1000.00")


# ---------------------------------------------------------------------------
# Aggregations
# ---------------------------------------------------------------------------


def test_aggregates_by_month_quarter_rep_segment_and_customer() -> None:
    opps = [
        _opp(
            "A",
            close=date(2026, 1, 15),
            rep_id="R1",
            segment="Enterprise",
            customer_id="C1",
            amount="1000",
            probability="0.5",
        ),
        _opp(
            "B",
            close=date(2026, 1, 20),
            rep_id="R2",
            segment="SMB",
            customer_id="C2",
            amount="2000",
            probability="0.5",
        ),
        _opp(
            "C",
            close=date(2026, 3, 10),
            rep_id="R1",
            segment="Enterprise",
            customer_id="C1",
            amount="4000",
            probability="0.5",
        ),
    ]
    f = compute_forecast(
        opps,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        win_rates=WinRates(),
        method=ForecastMethod.WEIGHTED,
    )
    # weighted: 500 + 1000 + 2000 = 3500
    assert f.total_forecast == _d("3500.00")
    assert f.by_month[date(2026, 1, 1)] == _d("1500.00")
    assert f.by_month[date(2026, 3, 1)] == _d("2000.00")
    assert f.by_quarter == {"2026-Q1": _d("3500.00")}
    assert f.by_rep == {"R1": _d("2500.00"), "R2": _d("1000.00")}
    assert f.by_segment == {"Enterprise": _d("2500.00"), "SMB": _d("1000.00")}
    assert f.by_customer == {"C1": _d("2500.00"), "C2": _d("1000.00")}


def test_unassigned_buckets_for_missing_rep_or_segment() -> None:
    opps = [_opp(rep_id=None, segment=None, amount="100", probability="1")]
    f = compute_forecast(
        opps,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        win_rates=WinRates(),
    )
    assert f.by_rep == {"(unassigned)": _d("100.00")}
    assert f.by_segment == {"(unassigned)": _d("100.00")}


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


def test_scenarios_apply_factors_and_cap_upside_at_pipeline() -> None:
    opps = [_opp(amount="1000", probability="0.5")]  # base forecast = 500, pipeline = 1000
    f = compute_forecast(
        opps,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        win_rates=WinRates(),
        scenario_factors=ScenarioFactors(
            conservative=_d("0.5"),
            base=_d("1.0"),
            upside=_d("10.0"),  # absurd multiplier
        ),
    )
    assert f.scenarios["conservative"] == _d("250.00")
    assert f.scenarios["base"] == _d("500.00")
    # capped at total pipeline (1000), not 5000
    assert f.scenarios["upside"] == _d("1000.00")


def test_empty_pipeline_produces_zeros_not_errors() -> None:
    f = compute_forecast(
        [],
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        win_rates=WinRates(),
    )
    assert f.total_pipeline == _d("0.00")
    assert f.total_forecast == _d("0.00")
    assert f.by_month == {}
    assert f.by_quarter == {}
    assert f.scenarios == {
        "conservative": _d("0.00"),
        "base": _d("0.00"),
        "upside": _d("0.00"),
    }


def test_method_selection_changes_total() -> None:
    opps = [_opp(stage="Proposal", amount="10000", probability="0.4")]
    rates = WinRates(by_stage={"Proposal": _d("0.7")}, overall=_d("0.2"))

    w = compute_forecast(opps, period_start=PERIOD_START, period_end=PERIOD_END, win_rates=rates,
                        method=ForecastMethod.WEIGHTED).total_forecast
    s = compute_forecast(opps, period_start=PERIOD_START, period_end=PERIOD_END, win_rates=rates,
                        method=ForecastMethod.STAGE_ADJUSTED).total_forecast
    assert w == _d("4000.00")
    assert s == _d("7000.00")
