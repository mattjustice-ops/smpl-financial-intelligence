"""GAAP revenue forecast rows (deferred + monthly MRR waterfall sources)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import fetch_scenario_rows, value_any
from app.services.dashboard.schemas import WaterfallSummaryRow
from app.services.reporting.period_utils import combined_scenario_for_period, period_range, to_period

# Forecast-only MRR source lines in section 5 (monthly recognition from MRR waterfall).
GAAP_FORECAST_SOURCE_TYPES: tuple[str, ...] = (
    "renewal_revenue",
    "new_business_revenue",
    "expansion_revenue",
    "reactivation_revenue",
)

GAAP_COMPONENT_TYPES: frozenset[str] = frozenset(GAAP_FORECAST_SOURCE_TYPES)


def _row_with_amount(row: WaterfallSummaryRow, amount: Decimal, *, source_table: str | None = None) -> WaterfallSummaryRow:
    if hasattr(row, "model_copy"):
        updates: dict[str, object] = {"amount": amount}
        if source_table is not None:
            updates["source_table"] = source_table
        return row.model_copy(update=updates)
    payload = row.model_dump() if hasattr(row, "model_dump") else row.dict()
    payload["amount"] = amount
    if source_table is not None:
        payload["source_table"] = source_table
    return WaterfallSummaryRow(**payload)


MRR_BOOKING_KEYS: dict[str, tuple[str, ...]] = {
    "renewal_revenue": ("renewal_mrr", "renewal_arr", "renewal_uplift_arr"),
    "new_business_revenue": ("new_business_mrr", "new_mrr", "new_business_arr"),
    "expansion_revenue": ("expansion_mrr", "expansion_arr"),
    "reactivation_revenue": ("reactivation_mrr", "reactivation_arr"),
}


def is_actual_period(period: str) -> bool:
    return combined_scenario_for_period(period) == "Actual"


def mrr_monthly_amount(raw: dict, *keys: str) -> Decimal:
    """Prefer explicit MRR columns; convert ARR to monthly MRR when needed."""
    for key in keys:
        if key.endswith("_mrr") and raw.get(key) not in (None, ""):
            return value_any(raw, key)
    total = Decimal("0")
    for key in keys:
        if key.endswith("_arr") and raw.get(key) not in (None, ""):
            total += value_any(raw, key) / Decimal("12")
    return total


def monthly_bookings_by_type(
    db: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: str,
    end_period: str,
) -> dict[str, dict[str, Decimal]]:
    """Sum new MRR bookings by revenue source and period (forecast MRR waterfall only)."""
    bookings: dict[str, dict[str, Decimal]] = {
        revenue_type: defaultdict(Decimal) for revenue_type in GAAP_FORECAST_SOURCE_TYPES
    }
    for src_scenario, period, _table_name, raw in fetch_scenario_rows(
        db,
        organization_id,
        scenario=scenario,
        suffix="mrr_waterfall",
        fallback="mrr_waterfall",
        start_period=start_period,
        end_period=end_period,
    ):
        if is_actual_period(period) or src_scenario != "Forecast":
            continue
        period_key = to_period(period)
        for revenue_type, keys in MRR_BOOKING_KEYS.items():
            bookings[revenue_type][period_key] += mrr_monthly_amount(raw, *keys)
    return bookings


def carry_forward_monthly_revenue(
    bookings_by_period: dict[str, Decimal],
    periods: list[str],
) -> dict[str, Decimal]:
    """Once booked, MRR stacks and is recognized each month through the forecast window."""
    active: list[Decimal] = []
    recognized: dict[str, Decimal] = {}
    for period in periods:
        active.append(bookings_by_period.get(period, Decimal("0")))
        recognized[period] = sum(active, Decimal("0"))
    return recognized


def _income_statement_revenue_by_period(
    db: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: str,
    end_period: str,
    source_scenario: str,
    period_filter,
) -> dict[str, Decimal]:
    revenue: dict[str, Decimal] = defaultdict(Decimal)
    for src_scenario, period, _table_name, raw in fetch_scenario_rows(
        db,
        organization_id,
        scenario=scenario,
        suffix="income_statement",
        fallback=None,
        start_period=start_period,
        end_period=end_period,
    ):
        if src_scenario != source_scenario or not period_filter(period):
            continue
        revenue[to_period(period)] += value_any(raw, "revenue")
    return revenue


def forecast_income_statement_revenue_by_period(
    db: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: str,
    end_period: str,
) -> dict[str, Decimal]:
    return _income_statement_revenue_by_period(
        db,
        organization_id,
        scenario=scenario,
        start_period=start_period,
        end_period=end_period,
        source_scenario="Forecast",
        period_filter=lambda period: not is_actual_period(period),
    )


def _expected_income_source_scenario(view_scenario: str, period: str) -> str | None:
    view = view_scenario.strip().lower()
    period_key = to_period(period)
    if view == "combined":
        return combined_scenario_for_period(period_key)
    if view == "actual":
        return "Actual" if is_actual_period(period_key) else None
    if view == "budget":
        return "Budget"
    if view == "forecast":
        return "Forecast" if not is_actual_period(period_key) else None
    normalized = view_scenario.strip()
    if normalized in {"Actual", "Budget", "Forecast"}:
        return normalized
    return None


def income_statement_gaap_revenue_by_period(
    db: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: str,
    end_period: str,
) -> dict[str, Decimal]:
    """Income statement revenue for Total GAAP (actual + forecast months in view)."""
    revenue: dict[str, Decimal] = defaultdict(Decimal)
    for src_scenario, period, _table_name, raw in fetch_scenario_rows(
        db,
        organization_id,
        scenario=scenario,
        suffix="income_statement",
        fallback=None,
        start_period=start_period,
        end_period=end_period,
    ):
        expected = _expected_income_source_scenario(scenario, period)
        if expected is None or src_scenario != expected:
            continue
        revenue[to_period(period)] += value_any(raw, "revenue")
    return revenue


def forecast_monthly_revenue_by_type(
    db: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: str,
    end_period: str,
) -> dict[tuple[str, str], Decimal]:
    """Each forecast month uses that month's MRR waterfall booking (not cumulative carry-forward)."""
    periods = period_range(start_period, end_period)
    forecast_periods = [period for period in periods if not is_actual_period(period)]
    bookings = monthly_bookings_by_type(
        db,
        organization_id,
        scenario=scenario,
        start_period=start_period,
        end_period=end_period,
    )
    monthly: dict[tuple[str, str], Decimal] = {}
    for revenue_type in GAAP_FORECAST_SOURCE_TYPES:
        for period in forecast_periods:
            period_key = to_period(period)
            monthly[(revenue_type, period_key)] = bookings[revenue_type].get(period_key, Decimal("0"))
    return monthly


def _component_sum_by_period(stacked: dict[tuple[str, str], Decimal]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for (_revenue_type, period), amount in stacked.items():
        totals[period] += amount
    return totals


def _deferred_revenue_for_period(
    forecast_income_revenue: dict[str, Decimal],
    component_sum: dict[str, Decimal],
    period: str,
) -> Decimal:
    """Deferred = income statement forecast revenue minus MRR source components."""
    period_key = to_period(period)
    return forecast_income_revenue.get(period_key, Decimal("0")) - component_sum.get(period_key, Decimal("0"))


def apply_gaap_revenue_forecast_rows(
    db: Session,
    organization_id: uuid.UUID,
    rows: list[WaterfallSummaryRow],
    *,
    scenario: str,
    start_period: str,
    end_period: str,
) -> tuple[list[WaterfallSummaryRow], dict[str, Decimal]]:
    """Build GAAP forecast rows: blank actual detail; forecast deferred ties to income statement."""
    income_statement_totals = income_statement_gaap_revenue_by_period(
        db,
        organization_id,
        scenario=scenario,
        start_period=start_period,
        end_period=end_period,
    )
    forecast_income_revenue = forecast_income_statement_revenue_by_period(
        db,
        organization_id,
        scenario=scenario,
        start_period=start_period,
        end_period=end_period,
    )
    monthly_by_type = forecast_monthly_revenue_by_type(
        db,
        organization_id,
        scenario=scenario,
        start_period=start_period,
        end_period=end_period,
    )
    component_sum = _component_sum_by_period(monthly_by_type)
    gaap_source = "forecast_income_statement, forecast_mrr_waterfall"

    updated: list[WaterfallSummaryRow] = []
    for row in rows:
        period = to_period(row.period)
        if row.waterfall_type == "total_gaap_revenue":
            continue
        if is_actual_period(period) and row.waterfall_type in {
            "deferred_revenue_recognized",
            *GAAP_COMPONENT_TYPES,
        }:
            continue
        if row.waterfall_type == "deferred_revenue_recognized":
            deferred = _deferred_revenue_for_period(forecast_income_revenue, component_sum, period)
            row = _row_with_amount(row, deferred, source_table=gaap_source)
        elif row.waterfall_type in GAAP_COMPONENT_TYPES:
            row = _row_with_amount(
                row,
                monthly_by_type.get((row.waterfall_type, period), row.amount),
                source_table="forecast_mrr_waterfall",
            )
        updated.append(row)

    existing = {(row.waterfall_type, to_period(row.period)) for row in updated}
    line_order = {
        "deferred_revenue_recognized": 310,
        "renewal_revenue": 320,
        "new_business_revenue": 330,
        "expansion_revenue": 340,
        "reactivation_revenue": 370,
    }
    for (revenue_type, period), amount in monthly_by_type.items():
        if (revenue_type, period) in existing:
            continue
        updated.append(
            WaterfallSummaryRow(
                organization_id=str(organization_id),
                scenario="Forecast",
                period=period,
                waterfall_name="deferred_revenue",
                waterfall_type=revenue_type,
                line_item=revenue_type.replace("_", " ").title().replace("Arr", "ARR"),
                line_item_order=line_order[revenue_type],
                amount=amount,
                source_table="forecast_mrr_waterfall",
                detail_count=0,
            )
        )
        existing.add((revenue_type, period))

    for period in sorted(forecast_income_revenue):
        if ("deferred_revenue_recognized", period) in existing:
            continue
        deferred = _deferred_revenue_for_period(forecast_income_revenue, component_sum, period)
        updated.append(
            WaterfallSummaryRow(
                organization_id=str(organization_id),
                scenario="Forecast",
                period=period,
                waterfall_name="deferred_revenue",
                waterfall_type="deferred_revenue_recognized",
                line_item="Deferred Revenue Recognized",
                line_item_order=line_order["deferred_revenue_recognized"],
                amount=deferred,
                source_table=gaap_source,
                detail_count=0,
            )
        )

    return updated, income_statement_totals
