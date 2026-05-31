"""Forecast driver assumptions layer."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.demo_finance import ForecastDriverAssumption
from app.services.driver_forecast.common import month_start
from app.services.driver_forecast.schemas import DriverAssumption


DEFAULT_ASSUMPTIONS: dict[str, tuple[str, Decimal]] = {
    "dso": ("working_capital", Decimal("42")),
    "dpo": ("working_capital", Decimal("32")),
    "dio": ("working_capital", Decimal("0")),
    "deferred_revenue_days": ("working_capital", Decimal("180")),
    "billing_cadence_months": ("billings", Decimal("1")),
    "renewal_probability": ("renewals", Decimal("0.92")),
    "pipeline_conversion": ("pipeline", Decimal("0.35")),
    "collections_timing_days": ("collections", Decimal("42")),
    "commission_payout_timing_days": ("cash_outflows", Decimal("30")),
    "payroll_timing_days": ("cash_outflows", Decimal("15")),
    "vendor_payment_timing_days": ("cash_outflows", Decimal("32")),
    "sbc_pct_of_payroll": ("noncash", Decimal("0.05")),
    "capex_pct_of_revenue": ("investing", Decimal("0.02")),
}


def fetch_driver_assumptions(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: date,
    end_period: date,
) -> list[DriverAssumption]:
    stmt = (
        select(ForecastDriverAssumption)
        .where(
            ForecastDriverAssumption.organization_id == organization_id,
            ForecastDriverAssumption.scenario_name == scenario,
            ForecastDriverAssumption.effective_period >= month_start(start_period),
            ForecastDriverAssumption.effective_period <= month_start(end_period),
        )
        .order_by(ForecastDriverAssumption.effective_period, ForecastDriverAssumption.assumption_name)
    )
    rows = [
        DriverAssumption(
            assumption_name=r.assumption_name,
            assumption_category=r.assumption_category or "general",
            actual_value=r.actual_value,
            forecast_value=r.forecast_value,
            effective_period=r.effective_period,
            scenario_name=r.scenario_name,
        )
        for r in session.scalars(stmt).all()
    ]
    if rows:
        return rows
    return [
        DriverAssumption(
            assumption_name=name,
            assumption_category=category,
            actual_value=None,
            forecast_value=value,
            effective_period=month_start(start_period),
            scenario_name=scenario,
        )
        for name, (category, value) in DEFAULT_ASSUMPTIONS.items()
    ]


def assumption_map(assumptions: list[DriverAssumption]) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for item in assumptions:
        value = item.forecast_value if item.forecast_value is not None else item.actual_value
        if value is not None:
            out[item.assumption_name] = value
    for name, (_, value) in DEFAULT_ASSUMPTIONS.items():
        out.setdefault(name, value)
    return out
