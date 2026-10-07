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
    return [
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


def assumption_map(assumptions: list[DriverAssumption]) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for item in assumptions:
        value = item.forecast_value if item.forecast_value is not None else item.actual_value
        if value is not None:
            out[item.assumption_name] = value
    return out
