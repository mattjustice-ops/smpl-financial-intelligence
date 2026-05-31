"""Management P&L API models — demo-ready operating statement."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Tone = Literal["pos", "neg", "neu"]


class MetricSlice(BaseModel):
    actual: Decimal = Decimal("0")
    budget: Decimal = Decimal("0")
    forecast: Decimal = Decimal("0")
    outlook: Decimal = Decimal("0")
    variance: Decimal = Decimal("0")
    variance_pct: Decimal | None = None
    pct_of_revenue: Decimal | None = None
    ytd_actual: Decimal = Decimal("0")
    ytd_budget: Decimal = Decimal("0")
    ytd_variance: Decimal = Decimal("0")


class PlLine(BaseModel):
    id: str
    label: str
    line_type: Literal["header", "section", "detail", "subdetail", "total", "margin"]
    section_key: str
    indent: int = 0
    expandable: bool = False
    is_bold: bool = False
    is_ebitda: bool = False
    metrics: MetricSlice
    children: list["PlLine"] = Field(default_factory=list)
    driver: str = ""


class KpiCard(BaseModel):
    key: str
    label: str
    value: Decimal
    value_format: Literal["currency", "percent", "multiple", "text"] = "currency"
    compare_value: Decimal | None = None
    compare_label: str = "vs FY Budget"
    delta_label: str = ""
    tone: Tone = "neu"
    sparkline: list[Decimal] = Field(default_factory=list)


class MonthlySeries(BaseModel):
    period: str
    label: str
    is_closed: bool = False
    revenue_actual: Decimal = Decimal("0")
    revenue_forecast: Decimal = Decimal("0")
    revenue_budget: Decimal = Decimal("0")
    revenue_outlook: Decimal = Decimal("0")
    cogs_outlook: Decimal = Decimal("0")
    cogs_budget: Decimal = Decimal("0")
    gross_profit_actual: Decimal = Decimal("0")
    gross_profit_forecast: Decimal = Decimal("0")
    gross_profit_budget: Decimal = Decimal("0")
    gross_profit_outlook: Decimal = Decimal("0")
    ebitda_actual: Decimal = Decimal("0")
    ebitda_forecast: Decimal = Decimal("0")
    ebitda_outlook: Decimal = Decimal("0")
    total_opex: Decimal = Decimal("0")
    opex_stack_sm: Decimal = Decimal("0")
    opex_stack_rd: Decimal = Decimal("0")
    opex_stack_ga: Decimal = Decimal("0")
    sm: Decimal = Decimal("0")
    rd: Decimal = Decimal("0")
    ga: Decimal = Decimal("0")
    cs: Decimal = Decimal("0")
    gm_pct_actual: Decimal = Decimal("0")
    gm_pct_budget: Decimal = Decimal("0")
    ebitda_margin_actual: Decimal = Decimal("0")
    ebitda_margin_budget: Decimal = Decimal("0")


class WaterfallStep(BaseModel):
    label: str
    value: Decimal
    running_total: Decimal
    step_type: Literal["add", "subtract", "total"] = "add"


class DepartmentVariance(BaseModel):
    department: str
    outlook: Decimal
    budget: Decimal
    variance: Decimal
    variance_pct: Decimal | None = None
    pct_of_opex: Decimal | None = None


class DepartmentSummaryRow(BaseModel):
    department: str
    headcount: Decimal = Decimal("0")
    period_actual: Decimal = Decimal("0")
    period_budget: Decimal = Decimal("0")
    variance: Decimal = Decimal("0")
    variance_pct: Decimal | None = None
    ytd_actual: Decimal = Decimal("0")
    ytd_budget: Decimal = Decimal("0")
    ytd_variance: Decimal = Decimal("0")


class GlAccountRow(BaseModel):
    account: str
    account_group: str
    outlook: Decimal
    budget: Decimal
    variance: Decimal
    variance_pct: Decimal | None = None
    ytd_outlook: Decimal = Decimal("0")
    ytd_variance: Decimal = Decimal("0")
    h2_forecast: Decimal = Decimal("0")
    is_non_recurring: bool = False


class ValidationWarning(BaseModel):
    code: str
    message: str
    severity: Literal["warning", "fail"] = "warning"


class CommentaryBlock(BaseModel):
    section: str
    observation: str
    implication: str
    recommendation: str


PlLine.model_rebuild()


class ManagementPlDashboardResponse(BaseModel):
    organization_id: str
    as_of_period: str
    period_mode: str
    view_mode: Literal["management", "accounting"]
    department_filter: str
    outlook_label: str

    kpis: list[KpiCard] = Field(default_factory=list)
    monthly_series: list[MonthlySeries] = Field(default_factory=list)
    pl_lines: list[PlLine] = Field(default_factory=list)
    ebitda_waterfall: list[WaterfallStep] = Field(default_factory=list)
    department_variances: list[DepartmentVariance] = Field(default_factory=list)
    department_summary: list[DepartmentSummaryRow] = Field(default_factory=list)
    gl_by_department: dict[str, list[GlAccountRow]] = Field(default_factory=dict)
    commentary: list[CommentaryBlock] = Field(default_factory=list)
    validations: list[ValidationWarning] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
