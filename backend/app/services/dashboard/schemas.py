"""Schemas for executive dashboard waterfalls and attribution."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.services.reporting.validation_service import ValidationCheck


class WaterfallSummaryRow(BaseModel):
    organization_id: str
    scenario: str
    period: str
    waterfall_name: str
    waterfall_type: str
    line_item: str
    line_item_order: int
    amount: Decimal = Decimal("0")
    source_table: str
    detail_count: int = 0


class WaterfallAttributionRow(BaseModel):
    organization_id: str
    scenario: str
    period: str
    waterfall_type: str
    customer_id: str | None = None
    customer_name: str | None = None
    opportunity_id: str | None = None
    opportunity_name: str | None = None
    owner: str | None = None
    region: str | None = None
    segment: str | None = None
    marketing_channel: str | None = None
    stage: str | None = None
    probability: Decimal = Decimal("0")
    close_date: str | None = None
    contract_start_date: str | None = None
    billing_cadence: str | None = None
    payment_terms: str | None = None
    amount: Decimal = Decimal("0")
    arr_impact: Decimal = Decimal("0")
    mrr_impact: Decimal = Decimal("0")
    revenue_impact: Decimal = Decimal("0")
    cash_impact: Decimal = Decimal("0")
    source_table: str
    raw: dict[str, Any] = Field(default_factory=dict)


class OpportunitySummaryRow(BaseModel):
    organization_id: str
    scenario: str
    period: str
    stage: str | None = None
    marketing_channel: str | None = None
    owner: str | None = None
    region: str | None = None
    segment: str | None = None
    opportunity_count: int = 0
    amount_arr: Decimal = Decimal("0")
    weighted_arr: Decimal = Decimal("0")
    source_table: str


class WaterfallResponse(BaseModel):
    organization_id: str
    scenario: str
    start_period: str
    end_period: str
    waterfall_name: str
    rows: list[WaterfallSummaryRow] = Field(default_factory=list)
    attribution: list[WaterfallAttributionRow] = Field(default_factory=list)
    validation: list[ValidationCheck] = Field(default_factory=list)
    commentary_prompts: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineDrilldownResponse(BaseModel):
    organization_id: str
    scenario: str
    source_scenario: str
    period: str
    waterfall_type: str
    line_item: str
    opportunities: list[WaterfallAttributionRow] = Field(default_factory=list)
    opportunity_count: int = 0
    total_arr: Decimal = Decimal("0")
    signed_total: Decimal = Decimal("0")
    expected_amount: Decimal | None = None
    drilldown_available: bool = True
    message: str | None = None
    validation: list[ValidationCheck] = Field(default_factory=list)
    source_tables: list[str] = Field(default_factory=list)


class CashFlowDrilldownLine(BaseModel):
    account_number: str | None = None
    account_name: str | None = None
    account_group: str | None = None
    department: str | None = None
    vendor_name: str | None = None
    amount: Decimal = Decimal("0")
    source_table: str = ""
    detail_type: str = "gl"
    notes: str | None = None


class CashFlowDrilldownResponse(BaseModel):
    organization_id: str
    scenario: str
    source_scenario: str
    period: str
    waterfall_type: str
    line_item: str
    lines: list[CashFlowDrilldownLine] = Field(default_factory=list)
    line_count: int = 0
    signed_total: Decimal = Decimal("0")
    expected_amount: Decimal | None = None
    drilldown_available: bool = True
    message: str | None = None
    validation: list[ValidationCheck] = Field(default_factory=list)
    source_tables: list[str] = Field(default_factory=list)


class OpportunityResponse(BaseModel):
    organization_id: str
    scenario: str
    start_period: str
    end_period: str
    rows: list[OpportunitySummaryRow] = Field(default_factory=list)
    attribution: list[WaterfallAttributionRow] = Field(default_factory=list)


class ExecutiveFlowResponse(BaseModel):
    organization_id: str
    scenario: str
    start_period: str
    end_period: str
    as_of_period: str
    marketing_summary: dict[str, Any] = Field(default_factory=dict)
    waterfalls: dict[str, WaterfallResponse] = Field(default_factory=dict)
    opportunities: dict[str, OpportunityResponse] = Field(default_factory=dict)
    validation: list[ValidationCheck] = Field(default_factory=list)
    commentary_prompts: dict[str, str] = Field(default_factory=dict)
