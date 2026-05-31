"""GAAP revenue forecast carry-forward tests."""

from __future__ import annotations

from decimal import Decimal

from app.services.dashboard.query_utils import decimal_value
from app.services.dashboard.gaap_revenue_forecast_service import (
    _deferred_revenue_for_period,
    carry_forward_monthly_revenue,
    mrr_monthly_amount,
)
from app.services.dashboard.schemas import WaterfallSummaryRow
from app.services.dashboard.waterfall_service import _add_total_gaap_revenue_rows, _validate


def test_carry_forward_matches_sample_renewal_shape() -> None:
    bookings = {
      "2026-01": Decimal("473958.3333"),
      "2026-02": Decimal("482236.8334"),
      "2026-03": Decimal("491747.5833"),
    }
    periods = ["2026-01", "2026-02", "2026-03"]
    recognized = carry_forward_monthly_revenue(bookings, periods)
    assert recognized["2026-01"] == Decimal("473958.3333")
    assert recognized["2026-02"] == Decimal("956195.1667")
    assert recognized["2026-03"] == Decimal("1447942.75")


def test_mrr_prefers_mrr_columns_over_arr() -> None:
    raw = {"renewal_mrr": "1000", "renewal_arr": "12000"}
    assert mrr_monthly_amount(raw, "renewal_mrr", "renewal_arr") == Decimal("1000")


def test_mrr_sums_multiple_arr_components() -> None:
    raw = {"renewal_arr": "12000", "renewal_uplift_arr": "6000"}
    assert mrr_monthly_amount(raw, "renewal_mrr", "renewal_arr", "renewal_uplift_arr") == Decimal("1500")


def test_arr_converted_to_mrr_when_only_arr_present() -> None:
    raw = {"new_business_arr": "12000"}
    assert mrr_monthly_amount(raw, "new_mrr", "new_business_arr") == Decimal("1000")


def test_deferred_validation_skips_periods_without_balance_rows() -> None:
    """GAAP source-only periods must not crash deferred waterfall validation."""
    rows = [
        WaterfallSummaryRow(
            organization_id="org",
            scenario="Forecast",
            period="2026-06",
            waterfall_name="deferred_revenue",
            waterfall_type="renewal_revenue",
            line_item="Renewal Revenue",
            line_item_order=320,
            amount=Decimal("1000"),
            source_table="forecast_mrr_waterfall",
            detail_count=0,
        ),
        WaterfallSummaryRow(
            organization_id="org",
            scenario="Forecast",
            period="2026-06",
            waterfall_name="deferred_revenue",
            waterfall_type="total_gaap_revenue",
            line_item="Total GAAP Revenue",
            line_item_order=399,
            amount=Decimal("1000"),
            source_table="forecast_mrr_waterfall",
            detail_count=0,
        ),
    ]
    checks = _validate(rows, "deferred_revenue")
    assert checks == []


def test_decimal_value_treats_invalid_strings_as_zero() -> None:
    assert decimal_value("N/A") == Decimal("0")
    assert decimal_value("not-a-number") == Decimal("0")


def test_deferred_revenue_is_income_statement_minus_components() -> None:
    forecast_income = {"2026-06": Decimal("1000000")}
    component_sum = {"2026-06": Decimal("250000") + Decimal("100000") + Decimal("50000") + Decimal("25000")}
    assert _deferred_revenue_for_period(forecast_income, component_sum, "2026-06") == Decimal("575000")


def test_total_gaap_includes_actual_and_forecast_income_statement() -> None:
    rows: list[WaterfallSummaryRow] = []
    income = {
        "2026-03": Decimal("500000"),
        "2026-06": Decimal("1000000"),
    }
    _add_total_gaap_revenue_rows(rows, "org", income_statement_revenue=income)
    by_period = {row.period: row for row in rows}
    assert by_period["2026-03"].scenario == "Actual"
    assert by_period["2026-03"].source_table == "actual_income_statement"
    assert by_period["2026-03"].amount == Decimal("500000")
    assert by_period["2026-06"].scenario == "Forecast"
    assert by_period["2026-06"].source_table == "forecast_income_statement"
    assert by_period["2026-06"].amount == Decimal("1000000")


def test_forecast_monthly_revenue_does_not_stack_bookings() -> None:
    """GAAP components use per-month MRR only (carry-forward is not applied in the waterfall)."""
    bookings = {
        "2026-01": Decimal("4513.916667"),
        "2026-02": Decimal("5000"),
    }
    recognized = carry_forward_monthly_revenue(bookings, ["2026-01", "2026-02"])
    assert recognized["2026-02"] == Decimal("9513.916667")
    assert bookings["2026-02"] == Decimal("5000")
