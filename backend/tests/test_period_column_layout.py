"""Period column layout for wide Excel exports."""

from __future__ import annotations

from types import SimpleNamespace

from app.services.reporting.export.effective_periods import include_forecast_column
from app.services.reporting.export.period_column_layout import (
    build_wide_period_layout,
    scenario_presence_by_period,
)


def test_jan_jun_actual_months_no_forecast_columns() -> None:
    periods = [f"2026-{m:02d}" for m in range(1, 7)]
    presence = {p: {"actual": True, "budget": True, "forecast": True} for p in periods}
    layout = build_wide_period_layout(periods, presence, as_of_period="2026-06")
    headers = layout.headers
    assert "Jan Actual" in headers
    assert "Jan Budget" in headers
    assert "Jan Fcst" not in headers
    assert "Feb Fcst" not in headers
    assert "Jun Fcst" in headers
    assert "Jun Act vs Fcst $" in headers


def test_open_month_shows_budget_and_forecast_only() -> None:
    presence = {
        "2026-07": {"actual": False, "budget": True, "forecast": True},
    }
    layout = build_wide_period_layout(["2026-07"], presence, as_of_period="2026-06")
    assert "Jul Budget" in layout.headers
    assert "Jul Outlook" in layout.headers
    assert "Jul Actual" not in layout.headers


def test_include_forecast_when_no_actuals() -> None:
    assert include_forecast_column(
        "2026-07",
        "2026-06",
        has_actual_rows=False,
        has_forecast_rows=True,
    )


def test_scenario_presence_from_rows() -> None:
    rows = [
        SimpleNamespace(period="2026-01", scenario="Actual"),
        SimpleNamespace(period="2026-01", scenario="Budget"),
    ]
    presence = scenario_presence_by_period(rows, ["2026-01"])
    assert presence["2026-01"]["actual"]
    assert presence["2026-01"]["budget"]
    assert not presence["2026-01"]["forecast"]
