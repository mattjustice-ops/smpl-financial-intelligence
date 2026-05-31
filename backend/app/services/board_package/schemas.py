"""Pydantic models for board reporting inputs and the canonical slide package.

`BoardPackageInputs` is what callers POST. It mirrors the outputs of the MRR,
ARR bridge, bookings, KPI, and commentary engines.

`BoardPackage` is the rendered, slide-by-slide representation. The pptx builder
and Google Slides emitter both consume `BoardPackage` — so they always render
the same data.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.services.commentary.schemas import CommentaryOutput


class _ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


# ---------------------------------------------------------------------------
# Input sub-schemas
# ---------------------------------------------------------------------------


class CompanyKpiSummary(_ApiModel):
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
    gross_mrr_churn_rate: Optional[Decimal] = None
    logo_churn_rate: Optional[Decimal] = None
    net_mrr_churn_rate: Optional[Decimal] = None


class MrrWaterfallSlide(_ApiModel):
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


class ArrBridge(_ApiModel):
    period: date
    beginning_arr: Decimal
    new_arr: Decimal = Decimal("0")
    expansion_arr: Decimal = Decimal("0")
    contraction_arr: Decimal = Decimal("0")
    churn_arr: Decimal = Decimal("0")
    reactivation_arr: Decimal = Decimal("0")
    ending_arr: Decimal


class BookingsForecastSlide(_ApiModel):
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
    total_pipeline: Optional[Decimal] = None


class RevenueForecastSlide(_ApiModel):
    period_start: date
    period_end: date
    forecasted_revenue: Decimal
    actual_revenue: Optional[Decimal] = None
    prior_period_revenue: Optional[Decimal] = None
    growth_rate: Optional[Decimal] = None
    variance_vs_plan: Optional[Decimal] = None


class CashForecastSlide(_ApiModel):
    period_start: date
    period_end: date
    forecasted_collections: Decimal
    open_ar_balance: Optional[Decimal] = None
    expected_dso: Optional[Decimal] = None
    cash_position: Optional[Decimal] = None
    runway_months: Optional[Decimal] = None
    aging_buckets: dict[str, Decimal] = Field(default_factory=dict)


class SalesEfficiencySlide(_ApiModel):
    new_bookings_arr: Decimal
    sales_marketing_expense: Decimal
    sales_efficiency: Optional[Decimal] = None
    magic_number: Optional[Decimal] = None
    cac: Optional[Decimal] = None
    cac_payback_months: Optional[Decimal] = None


class QuotaAttainmentRow(_ApiModel):
    rep_id: str
    rep_name: Optional[str] = None
    segment: Optional[str] = None
    quota_period: Optional[str] = None
    quota_arr: Decimal
    closed_won_arr: Decimal
    attainment_rate: Optional[Decimal] = None


class ChurnExpansionAnalysis(_ApiModel):
    period: date
    expansion_mrr: Decimal = Decimal("0")
    contraction_mrr: Decimal = Decimal("0")
    churn_mrr: Decimal = Decimal("0")
    reactivation_mrr: Decimal = Decimal("0")
    new_customers: int = 0
    churned_customers: int = 0
    expanded_customers: int = 0
    contracted_customers: int = 0
    reactivated_customers: int = 0
    notable_movements: list[str] = Field(default_factory=list)


class BoardPackageInputs(_ApiModel):
    """All inputs a caller can supply to the board package generator."""

    period_label: str
    organization_name: str = "Company"
    currency: str = "USD"
    prepared_for: str = "Board of Directors"
    prepared_date: Optional[date] = None

    kpi_summary: Optional[CompanyKpiSummary] = None
    mrr_waterfall: Optional[MrrWaterfallSlide] = None
    arr_bridge: Optional[ArrBridge] = None
    bookings_forecast: Optional[BookingsForecastSlide] = None
    revenue_forecast: Optional[RevenueForecastSlide] = None
    cash_forecast: Optional[CashForecastSlide] = None
    sales_efficiency: Optional[SalesEfficiencySlide] = None
    quota_attainment: list[QuotaAttainmentRow] = Field(default_factory=list)
    churn_expansion: Optional[ChurnExpansionAnalysis] = None
    commentary: Optional[CommentaryOutput] = None


# ---------------------------------------------------------------------------
# Canonical slide representation
# ---------------------------------------------------------------------------


class TableSpec(_ApiModel):
    headers: list[str]
    rows: list[list[str]]


class KpiCard(_ApiModel):
    """Executive KPI callout for board slides."""

    label: str
    value: str
    subtext: str | None = None
    tone: Literal["favorable", "unfavorable", "neutral", "watch"] | None = "neutral"
    group: Literal["growth", "profitability", "liquidity", "gtm", "efficiency"] | None = None
    direction: Literal["up", "down", "flat"] | None = None


class CalloutBlock(_ApiModel):
    """Structured win / risk / action callout."""

    kind: Literal["win", "risk", "action"]
    text: str
    owner: str | None = None


class ChartSpec(_ApiModel):
    """Lightweight chart description — the pptx renderer turns this into a real chart.

    For the Google Slides emitter, this becomes a textual chart placeholder
    that callers can replace with a real chart later via the Sheets/Charts API.
    """

    chart_type: Literal["bar", "column", "waterfall", "line"] = "column"
    archetype: str | None = None
    title: str
    categories: list[str]
    series: dict[str, list[float]] = Field(default_factory=dict)
    y_axis_label: str | None = None
    max_categories: int = 8


class SlideContent(_ApiModel):
    """Canonical slide. Used by both the pptx and Google Slides emitters."""

    slide_id: str
    title: str
    subtitle: Optional[str] = None
    layout: Literal[
        "executive_scorecard",
        "executive_dashboard",
        "executive_ytd",
        "story_slide",
        "mda_narrative",
        "chart_primary",
        "dual_metric",
        "spotlight",
        "compact_table",
        "narrative",
        "narrative_table_split",
        "marketing_source",
        "section_divider",
        "section_transition",
        "cash_trend",
        "risk_matrix",
    ] = "chart_primary"
    key_takeaway: Optional[str] = None
    section_label: Optional[str] = None
    commentary_heading: Optional[str] = None
    narrative: Optional[str] = None
    bullets: list[str] = Field(default_factory=list)
    callouts: list[CalloutBlock] = Field(default_factory=list)
    kpi_cards: list[KpiCard] = Field(default_factory=list)
    spotlight_cards: list[KpiCard] = Field(default_factory=list)
    table: Optional[TableSpec] = None
    chart: Optional[ChartSpec] = None
    secondary_chart: Optional[ChartSpec] = None
    footnote: Optional[str] = None
    max_table_rows: int = 6


class BoardPackage(_ApiModel):
    period_label: str
    organization_name: str
    prepared_for: str
    prepared_date: date
    currency: str
    slides: list[SlideContent]
