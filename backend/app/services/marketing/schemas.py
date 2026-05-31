"""Marketing performance API schemas."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.services.reporting.validation_service import ValidationCheck


class MarketingMetricRow(BaseModel):
    organization_id: str
    scenario: str
    period: str
    marketing_channel: str | None = None
    marketing_spend: Decimal = Decimal("0")
    mqls: Decimal = Decimal("0")
    sqls: Decimal = Decimal("0")
    sals: Decimal = Decimal("0")
    opportunities_created: Decimal = Decimal("0")
    pipeline_arr_created: Decimal = Decimal("0")
    closed_won_arr: Decimal = Decimal("0")
    closed_lost_arr: Decimal = Decimal("0")
    slipped_pipeline_arr: Decimal = Decimal("0")
    beginning_pipeline_arr: Decimal = Decimal("0")
    ending_pipeline_arr: Decimal = Decimal("0")
    cost_per_mql: Decimal = Decimal("0")
    cost_per_sql: Decimal = Decimal("0")
    pipeline_per_dollar_spend: Decimal = Decimal("0")
    marketing_cac_proxy: Decimal = Decimal("0")
    pipeline_coverage_ratio: Decimal = Decimal("0")
    win_rate_on_pipeline_created: Decimal = Decimal("0")
    source_table: str


class ChartSeries(BaseModel):
    series_name: str
    points: list[dict[str, Any]] = Field(default_factory=list)


class MarketingResponse(BaseModel):
    organization_id: str
    scenario: str
    start_period: str
    end_period: str
    rows: list[MarketingMetricRow] = Field(default_factory=list)
    charts: dict[str, list[ChartSeries]] = Field(default_factory=dict)
    validation: list[ValidationCheck] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActualBudgetForecastResponse(BaseModel):
    organization_id: str
    start_period: str
    end_period: str
    actual: list[MarketingMetricRow] = Field(default_factory=list)
    budget: list[MarketingMetricRow] = Field(default_factory=list)
    forecast: list[MarketingMetricRow] = Field(default_factory=list)
    combined: list[MarketingMetricRow] = Field(default_factory=list)
    validation: list[ValidationCheck] = Field(default_factory=list)
