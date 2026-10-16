"""Forecast months follow the close and the fiscal year end."""

from app.services.reporting.fiscal_year import (
    forecast_open_periods,
    forecast_periods_after_close,
)
from app.services.reporting.period_utils import next_period


def test_next_period_crosses_the_year() -> None:
    assert next_period("2026-06") == "2026-07"
    assert next_period("2026-12") == "2027-01"


def test_calendar_year_forecast_is_the_months_after_the_close() -> None:
    assert forecast_open_periods("2026-06") == [
        "2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12",
    ]
    assert forecast_open_periods("2026-11") == ["2026-12"]


def test_close_on_the_fiscal_year_end_opens_the_next_year() -> None:
    assert forecast_open_periods("2026-12") == [f"2027-{m:02d}" for m in range(1, 13)]


def test_fiscal_year_that_does_not_end_in_december() -> None:
    # Year ends in January: February through the January after the close.
    assert forecast_open_periods("2026-11", fiscal_year_end_month=1) == ["2026-12", "2027-01"]
    assert forecast_open_periods("2027-01", fiscal_year_end_month=1) == [
        f"2027-{m:02d}" for m in range(2, 13)
    ] + ["2028-01"]


def test_reporting_window_uses_the_same_rule() -> None:
    assert forecast_periods_after_close("2026-06", "2026-12") == forecast_open_periods("2026-06")
    assert forecast_periods_after_close("2026-12", "2026-12") == forecast_open_periods("2026-12")
    assert forecast_periods_after_close("2027-01", "2027-01") == forecast_open_periods(
        "2027-01", fiscal_year_end_month=1
    )
