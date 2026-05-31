"""Tests for Actual + Forecast period display logic."""

from __future__ import annotations

from decimal import Decimal

from app.services.reporting.export.effective_periods import period_display_values
from app.services.reporting.export.period_column_layout import build_display_by_period


def test_closed_month_omits_zero_forecast() -> None:
    display = period_display_values(
        Decimal("100"),
        Decimal("90"),
        Decimal("0"),
        period="2026-05",
        as_of_period="2026-05",
        has_actual_rows=True,
        has_budget_rows=True,
        has_forecast_rows=True,
    )
    assert display["actual"] == Decimal("100")
    assert display["forecast"] == Decimal("0")
    assert display["budget"] == Decimal("90")


def test_open_month_uses_forecast_outlook() -> None:
    display = period_display_values(
        Decimal("0"),
        Decimal("80"),
        Decimal("120"),
        period="2026-06",
        as_of_period="2026-05",
        has_actual_rows=False,
        has_budget_rows=True,
        has_forecast_rows=True,
    )
    assert display["actual"] is None
    assert display["forecast"] == Decimal("120")
    assert display["outlook"] == Decimal("120")


def test_build_display_by_period_variance_only_when_both_present() -> None:
    periods = ["2026-05"]
    presence = {"2026-05": {"actual": True, "budget": True, "forecast": True}}
    raw = {"2026-05": {"actual": Decimal("110"), "budget": Decimal("100"), "forecast": Decimal("0")}}
    out = build_display_by_period(raw, periods, presence, "2026-05")
    assert out["2026-05"]["var_bud"] == Decimal("10")
