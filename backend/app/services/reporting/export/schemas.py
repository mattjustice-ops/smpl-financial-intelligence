"""Schemas for reporting export bundles and commentary templates."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.commentary.schemas import CommentaryOutput
from app.services.dashboard.schemas import (
    ExecutiveFlowResponse,
    WaterfallAttributionRow,
    WaterfallSummaryRow,
    WaterfallResponse,
)
from app.services.financial_statements.financial_statement_service import SummaryResponse
from app.services.marketing.schemas import ActualBudgetForecastResponse
from app.services.reporting.validation_service import ValidationCheck


class CommentaryField(BaseModel):
    """Editable CFO commentary cell for Excel variance tabs."""

    section: str
    period: str | None = None
    line_item: str | None = None
    what_changed: str = ""
    variance_driver: str = ""
    favorable: str = ""
    unfavorable: str = ""
    leadership_attention: str = ""
    recommended_actions: str = ""
    owner: str = ""
    metric_context: str = Field(
        default="",
        description="Auto-filled Actual / Budget / Forecast metrics for this section (from API).",
    )
    source: Literal["template", "metrics", "ai", "user"] = "template"


class ExportValidationSummary(BaseModel):
    status: Literal["pass", "warning", "fail"]
    checks: list[ValidationCheck] = Field(default_factory=list)
    failed_count: int = 0
    warning_count: int = 0
    passed_count: int = 0


class GlDetailRow(BaseModel):
    scenario: str
    period: str
    department: str | None = None
    account: str | None = None
    account_group: str | None = None
    expense_type: str | None = None
    amount: Decimal = Decimal("0")
    source_table: str = ""


class DataGapNote(BaseModel):
    """Documents missing or partial export data and where to load it."""

    section: str
    scenario: str
    status: Literal["ok", "partial", "missing"]
    expected_source: str
    message: str
    action: str


class HeadcountRow(BaseModel):
    scenario: str
    period: str
    department: str | None = None
    headcount: Decimal | None = None
    open_roles: Decimal | None = None
    hiring_plan: Decimal | None = None
    source_table: str = ""


class ReportingBundle(BaseModel):
    """All data required to render Excel / PowerPoint exports (API-sourced only)."""

    organization_id: str
    organization_name: str | None = None
    scenario: str
    start_period: str
    end_period: str
    as_of_period: str
    period_label: str
    currency: str = "USD"

    executive_flow: ExecutiveFlowResponse
    financial_statements: SummaryResponse | None = None
    comparison_waterfalls: dict[str, list[WaterfallSummaryRow]] = Field(default_factory=dict)
    comparison_financial_statements: SummaryResponse | None = None
    marketing_comparison: ActualBudgetForecastResponse | None = None
    gl_detail: list[GlDetailRow] = Field(default_factory=list)
    headcount: list[HeadcountRow] = Field(default_factory=list)
    pipeline_drilldown: dict[str, Any] = Field(default_factory=dict)
    opportunity_attribution: list[WaterfallAttributionRow] = Field(default_factory=list)
    mda_commentary: list[CommentaryField] = Field(default_factory=list)
    data_gaps: list[DataGapNote] = Field(default_factory=list)

    commentary: CommentaryOutput | None = None
    commentary_fields: list[CommentaryField] = Field(default_factory=list)
    validation: ExportValidationSummary = Field(default_factory=lambda: ExportValidationSummary(status="pass"))

    model_config = {"arbitrary_types_allowed": True}


class ComparisonColumn(BaseModel):
    key: str
    label: str
    periods: list[str] = Field(default_factory=list)


class ComparisonMatrixRow(BaseModel):
    line_item: str
    section: str | None = None
    values: dict[str, Decimal | None] = Field(default_factory=dict)
    variance_dollar: dict[str, Decimal | None] = Field(default_factory=dict)
    variance_percent: dict[str, Decimal | None] = Field(default_factory=dict)


def waterfall_by_type(waterfall: WaterfallResponse, waterfall_type: str, period: str) -> Decimal:
    for row in waterfall.rows:
        if row.waterfall_type == waterfall_type and row.period == period:
            return row.amount
    return Decimal("0")


def statement_amount_by_line(
    summary: SummaryResponse | None,
    statement: Literal["income_statement", "balance_sheet", "cash_flow"],
    line_item: str,
    scenario: str,
    period: date,
) -> Decimal:
    if summary is None:
        return Decimal("0")
    block = getattr(summary, statement)
    for row in block.rows:
        if row.line_item == line_item and row.scenario == scenario and row.period == period:
            return row.amount
    return Decimal("0")
