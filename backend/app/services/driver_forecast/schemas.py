"""Frontend-ready response schemas for driver-based forecasting."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


class ChartPoint(BaseModel):
    period: date
    value: Decimal
    period_type: str = Field(description="actual or forecast")
    series: Optional[str] = None


class TableRow(BaseModel):
    period: date
    period_type: str
    values: dict[str, Decimal | str | None]


class ForecastScheduleResponse(BaseModel):
    organization_id: str
    scenario: str
    start_period: date
    end_period: date
    schedule_name: str
    actual_periods: list[date]
    forecast_periods: list[date]
    rows: list[TableRow]
    charts: dict[str, list[ChartPoint]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DriverAssumption(BaseModel):
    assumption_name: str
    assumption_category: str
    actual_value: Optional[Decimal] = None
    forecast_value: Optional[Decimal] = None
    effective_period: date
    scenario_name: str


class DriverSummaryResponse(BaseModel):
    organization_id: str
    scenario: str
    start_period: date
    end_period: date
    actual_periods: list[date]
    forecast_periods: list[date]
    kpis: dict[str, Decimal]
    schedules: dict[str, ForecastScheduleResponse]
    dbt_models: list[str]
    frontend_visualizations: dict[str, list[str]]
