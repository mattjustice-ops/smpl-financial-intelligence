"""Shared reporting foundation tests."""

from __future__ import annotations

from decimal import Decimal

from app.services.reporting.marketing_metrics_service import (
    calculate_pipeline_per_spend,
    calculate_pipeline_waterfall,
    calculate_win_rate_on_pipeline_created,
)
from app.services.reporting.period_utils import period_range, scenario_periods, to_period


def test_period_utils_use_yyyy_mm_and_combined_logic() -> None:
    assert to_period("2026-01-15") == "2026-01"
    assert period_range("2026-01", "2026-03") == ["2026-01", "2026-02", "2026-03"]
    assert scenario_periods("Combined", "2026-05", "2026-06") == [
        ("Actual", "2026-05"),
        ("Forecast", "2026-06"),
    ]


def test_marketing_metric_formulas() -> None:
    assert calculate_pipeline_per_spend(Decimal("500"), Decimal("100")) == Decimal("5.0000")
    assert calculate_win_rate_on_pipeline_created(Decimal("25"), Decimal("100")) == Decimal("0.2500")
    assert (
        calculate_pipeline_waterfall(
            Decimal("1000"),
            Decimal("500"),
            Decimal("200"),
            Decimal("100"),
            Decimal("50"),
        )
        == Decimal("1150")
    )
