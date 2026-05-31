"""Structured input and output schemas for the AI commentary service.

The input schema mirrors the outputs of the MRR, bookings, KPI engines plus a
few raw aggregates a finance team would normally hand to the LLM. The output
schema constrains the model to a fixed shape: every section is named and every
risk / opportunity / follow-up question is captured separately so callers can
render them however they want.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class _ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


# ---------------------------------------------------------------------------
# Input sub-schemas
# ---------------------------------------------------------------------------


class MrrWaterfallSummary(_ApiModel):
    period: date
    beginning_mrr: Decimal
    new_mrr: Decimal = Decimal("0")
    expansion_mrr: Decimal = Decimal("0")
    contraction_mrr: Decimal = Decimal("0")
    churn_mrr: Decimal = Decimal("0")
    reactivation_mrr: Decimal = Decimal("0")
    ending_mrr: Decimal
    nrr: Optional[Decimal] = None
    grr: Optional[Decimal] = None
    gross_mrr_churn_rate: Optional[Decimal] = None


class BookingsForecastInput(_ApiModel):
    period_start: date
    period_end: date
    total_forecast: Decimal
    weighted_forecast: Optional[Decimal] = None
    stage_adjusted_forecast: Optional[Decimal] = None
    historical_forecast: Optional[Decimal] = None
    conservative: Optional[Decimal] = None
    base: Optional[Decimal] = None
    upside: Optional[Decimal] = None
    confidence_score: Optional[Decimal] = None
    confidence_band: Optional[str] = None
    coverage_ratio: Optional[Decimal] = None
    target_bookings: Optional[Decimal] = None


class RevenueForecastInput(_ApiModel):
    period_start: date
    period_end: date
    forecasted_revenue: Decimal
    prior_period_revenue: Optional[Decimal] = None
    growth_rate: Optional[Decimal] = None
    method: Optional[str] = None


class CashCollectionsForecastInput(_ApiModel):
    period_start: date
    period_end: date
    forecasted_collections: Decimal
    open_ar_balance: Optional[Decimal] = None
    expected_dso: Optional[Decimal] = None
    aging_buckets: dict[str, Decimal] = Field(default_factory=dict)


class KpiTrend(_ApiModel):
    period_label: str
    arr: Optional[Decimal] = None
    mrr: Optional[Decimal] = None
    nrr: Optional[Decimal] = None
    grr: Optional[Decimal] = None
    rule_of_40: Optional[Decimal] = None
    magic_number: Optional[Decimal] = None
    cac: Optional[Decimal] = None
    cac_payback_months: Optional[Decimal] = None
    ltv: Optional[Decimal] = None
    ltv_to_cac: Optional[Decimal] = None
    burn_multiple: Optional[Decimal] = None
    sales_efficiency: Optional[Decimal] = None
    pipeline_coverage: Optional[Decimal] = None


class VarianceRow(_ApiModel):
    metric: str
    actual: Decimal
    forecast: Decimal
    variance_absolute: Decimal
    variance_percent: Optional[Decimal] = None
    direction: Optional[Literal["favorable", "unfavorable", "neutral"]] = None


class PipelineChange(_ApiModel):
    label: str  # e.g. "Enterprise stage 4 -> 5", "SMB pipeline created"
    delta_arr: Decimal
    delta_count: Optional[int] = None
    note: Optional[str] = None


class CustomerMovementSummary(_ApiModel):
    new_customers: int = 0
    churned_customers: int = 0
    expanded_customers: int = 0
    contracted_customers: int = 0
    reactivated_customers: int = 0
    notable_customers: list[str] = Field(default_factory=list)


class QuotaAttainment(_ApiModel):
    rep_id: str
    rep_name: Optional[str] = None
    segment: Optional[str] = None
    quota_period: Optional[str] = None
    quota_arr: Decimal
    closed_won_arr: Decimal
    attainment_rate: Optional[Decimal] = None


class SalesEfficiencyInput(_ApiModel):
    new_bookings_arr: Decimal
    sales_marketing_expense: Decimal
    sales_efficiency: Optional[Decimal] = None
    magic_number: Optional[Decimal] = None
    cac_payback_months: Optional[Decimal] = None


class CommentaryInputs(_ApiModel):
    """All structured inputs the model is allowed to reason over."""

    period_label: str = Field(description="Human-readable period, e.g. 'May 2026' or 'Q2 2026'")
    organization_name: Optional[str] = None
    currency: str = "USD"

    mrr_waterfall: Optional[MrrWaterfallSummary] = None
    bookings_forecast: Optional[BookingsForecastInput] = None
    revenue_forecast: Optional[RevenueForecastInput] = None
    cash_forecast: Optional[CashCollectionsForecastInput] = None
    kpi_trends: list[KpiTrend] = Field(default_factory=list)
    actuals_vs_forecast: list[VarianceRow] = Field(default_factory=list)
    pipeline_changes: list[PipelineChange] = Field(default_factory=list)
    customer_movement: Optional[CustomerMovementSummary] = None
    quota_attainment: list[QuotaAttainment] = Field(default_factory=list)
    sales_efficiency: Optional[SalesEfficiencyInput] = None
    additional_notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Output sub-schemas
# ---------------------------------------------------------------------------


class Citation(_ApiModel):
    label: str = Field(description="Short description of the metric being cited")
    value: str = Field(description="Verbatim value from the input data, e.g. '$1.2M ARR'")


class CommentarySection(_ApiModel):
    title: str
    narrative: str = Field(description="3-6 sentence executive-grade prose")
    citations: list[Citation] = Field(default_factory=list)


class RiskOpportunity(_ApiModel):
    type: Literal["risk", "opportunity"]
    description: str
    evidence: str = Field(description="Specific data point(s) supporting the call-out")
    severity: Optional[Literal["low", "medium", "high"]] = None


class FollowupQuestion(_ApiModel):
    question: str
    rationale: str = Field(description="Why this question matters given the data")


class DataGap(_ApiModel):
    topic: str
    data_needed: str = Field(description="Specific input that would let us draw a stronger conclusion")


class CommentaryOutput(_ApiModel):
    period_label: str
    executive_summary: CommentarySection
    revenue_commentary: CommentarySection
    mrr_waterfall_commentary: CommentarySection
    bookings_forecast_commentary: CommentarySection
    cash_forecast_commentary: CommentarySection
    risks_and_opportunities: list[RiskOpportunity] = Field(default_factory=list)
    followup_questions: list[FollowupQuestion] = Field(default_factory=list)
    data_gaps: list[DataGap] = Field(default_factory=list)
