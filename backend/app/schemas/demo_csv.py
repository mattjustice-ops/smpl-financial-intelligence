"""Pydantic rows for demo CSV validation (headers must match loader expectations)."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from typing_extensions import Annotated


_NUMBER_RE = re.compile(r"-?\d+(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?")


def _coerce_decimal(v: Any) -> Any:
    """Accept common spreadsheet values: $1,200, 10%, 1.5x, (500), '100% quota'."""
    if v is None or isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s or s.lower() in {"n/a", "na", "none", "null", "-"}:
            return None
        is_negative = s.startswith("(") and s.endswith(")")
        match = _NUMBER_RE.search(s.replace("$", "").replace("€", "").replace("£", ""))
        if match is None:
            return None
        value = Decimal(match.group(0).replace(",", ""))
        if "%" in s:
            value = value / Decimal("100")
        if is_negative:
            value = -value
        return value
    return v


def _coerce_probability(v: Any) -> Any:
    """Like _coerce_decimal but normalizes plain '70' to 0.70 (treated as percent)."""
    parsed = _coerce_decimal(v)
    if parsed is None:
        return None
    if isinstance(parsed, Decimal):
        if parsed > Decimal("1"):
            return parsed / Decimal("100")
        if parsed < Decimal("0"):
            return Decimal("0")
    return parsed


def _coerce_date(v: Any) -> Any:
    """Accept full ISO dates and common US spreadsheet dates."""
    if v is None or v == "":
        return v
    if isinstance(v, (date, datetime)):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        for fmt in ("%m/%d/%Y", "%m/%d/%y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                pass
    return v


def _coerce_period(v: Any) -> Any:
    """Accept YYYY-MM, YYYYMM, ISO dates, and US spreadsheet dates (e.g. 1/1/2026).

    Period columns are normalized to the first day of the month.
    """
    if v is None or v == "":
        return v
    if isinstance(v, datetime):
        return v.date().replace(day=1)
    if isinstance(v, date):
        return v.replace(day=1)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        if len(s) == 7 and s[4] == "-" and s[:4].isdigit() and s[5:].isdigit():
            return f"{s}-01"
        if len(s) == 6 and s[:4].isdigit() and s[4:].isdigit():
            return f"{s[:4]}-{s[4:]}-01"
        # M/D/YYYY, MM/DD/YYYY, etc. (same as other date columns)
        parsed = _coerce_date(s)
        if isinstance(parsed, date):
            return parsed.replace(day=1)
    return v


DateValue = Annotated[date, BeforeValidator(_coerce_date)]
FlexibleDecimal = Annotated[Decimal, BeforeValidator(_coerce_decimal)]
ProbabilityDecimal = Annotated[Decimal, BeforeValidator(_coerce_probability)]
PeriodDate = Annotated[date, BeforeValidator(_coerce_period)]


class CustomerRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: str = Field(max_length=128)
    customer_name: str
    segment: Optional[str] = None
    industry: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[DateValue] = None
    billing_cadence: Optional[str] = None
    payment_terms: Optional[str] = None
    source_crm: Optional[str] = None
    netsuite_customer_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None


class SubscriptionRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    subscription_id: str
    customer_id: str
    product: Optional[str] = None
    billing_cadence: Optional[str] = None
    start_date: Optional[DateValue] = None
    end_date: Optional[DateValue] = None
    current_mrr: Optional[FlexibleDecimal] = None
    current_arr: Optional[FlexibleDecimal] = None
    status: Optional[str] = None
    currency: Optional[str] = None


class OpportunityRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    opportunity_id: str
    customer_id: str
    opportunity_name: str
    opportunity_type: Optional[str] = None
    stage: Optional[str] = None
    amount_arr: Optional[FlexibleDecimal] = None
    expected_close_date: Optional[DateValue] = None
    probability: Optional[ProbabilityDecimal] = None
    segment: Optional[str] = None
    owner: Optional[str] = None
    rep_id: Optional[str] = None
    forecast_period: Optional[str] = None
    source_crm: Optional[str] = None


class InvoiceRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    invoice_id: str
    customer_id: str
    invoice_period: Optional[str] = None
    invoice_date: Optional[DateValue] = None
    due_date: Optional[DateValue] = None
    invoice_amount: Optional[FlexibleDecimal] = None
    payment_status: Optional[str] = None
    billing_cadence: Optional[str] = None
    currency: Optional[str] = None


class PaymentRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    payment_id: str
    invoice_id: str
    customer_id: str
    payment_date: Optional[DateValue] = None
    payment_amount: Optional[FlexibleDecimal] = None
    payment_method: Optional[str] = None
    currency: Optional[str] = None


class ForecastGlDetailRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    scenario: Optional[str] = None
    version: Optional[str] = None  # alias accepted in file; stored as scenario
    period: PeriodDate
    line_type: Optional[str] = None
    statement_category: Optional[str] = None
    department: Optional[str] = None
    sub_department: Optional[str] = None
    account_group: Optional[str] = None
    expense_type: Optional[str] = None
    gl_account: str
    management_view_include: Optional[str] = None
    accounting_view_include: Optional[str] = None
    sbc_flag: Optional[str] = None
    one_time_flag: Optional[str] = None
    non_cash_flag: Optional[str] = None
    forecast_amount: Optional[FlexibleDecimal] = None
    source: Optional[str] = None
    notes: Optional[str] = None


class GlActualRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    period: PeriodDate
    version: Optional[str] = None
    account_number: str
    account_name: Optional[str] = None
    statement: Optional[str] = None
    category: Optional[str] = None
    statement_category: Optional[str] = None
    account_group: Optional[str] = None
    expense_type: Optional[str] = None
    department: Optional[str] = None
    cost_center: Optional[str] = None
    sub_department: Optional[str] = None
    vendor_id: Optional[str] = None
    vendor_name: Optional[str] = None
    source_file: Optional[str] = None
    source_record_id: Optional[str] = None
    amount: Optional[FlexibleDecimal] = None
    currency: Optional[str] = None
    subsidiary: Optional[str] = None
    source_system: Optional[str] = None
    notes: Optional[str] = None


class HeadcountPlanRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: Optional[str] = None
    period: PeriodDate
    department: str
    headcount: Optional[FlexibleDecimal] = None
    headcount_ending: Optional[FlexibleDecimal] = None
    headcount_beginning: Optional[FlexibleDecimal] = None
    monthly_payroll_cost: Optional[FlexibleDecimal] = None
    payroll_tax_rate: Optional[FlexibleDecimal] = None
    benefits_rate: Optional[FlexibleDecimal] = None
    total_people_cost: Optional[FlexibleDecimal] = None

    def model_post_init(self, __context: object) -> None:
        if self.headcount is None and self.headcount_ending is not None:
            object.__setattr__(self, "headcount", self.headcount_ending)


class VendorContractRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    vendor_id: str
    vendor_name: Optional[str] = None
    service_category: Optional[str] = None
    contract_start: Optional[DateValue] = None
    contract_end: Optional[DateValue] = None
    annual_contract_value: Optional[FlexibleDecimal] = None
    billing_cadence: Optional[str] = None
    payment_terms: Optional[str] = None
    expense_category: Optional[str] = None


class SalesQuotaRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    rep_id: str
    rep_name: Optional[str] = None
    segment: Optional[str] = ""
    quota_period: str
    quota_arr: Optional[FlexibleDecimal] = None
    closed_won_arr_to_date: Optional[FlexibleDecimal] = None


class CommissionPlanRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    plan_id: str
    role: Optional[str] = None
    eligible_opportunity_type: Optional[str] = None
    base_commission_rate: Optional[FlexibleDecimal] = None
    accelerator_multiplier: Optional[FlexibleDecimal] = None
    accelerator_threshold: Optional[FlexibleDecimal] = None
    accelerated_rate: Optional[FlexibleDecimal] = None
    clawback_window: Optional[str] = None


class MrrWaterfallRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    period: PeriodDate
    customer_id: str
    beginning_mrr: Optional[FlexibleDecimal] = None
    new_mrr: Optional[FlexibleDecimal] = None
    expansion_mrr: Optional[FlexibleDecimal] = None
    contraction_mrr: Optional[FlexibleDecimal] = None
    churn_mrr: Optional[FlexibleDecimal] = None
    reactivation_mrr: Optional[FlexibleDecimal] = None
    ending_mrr: Optional[FlexibleDecimal] = None
    movement_type: str


class ForecastAssumptionRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    assumption: str
    value: Optional[str] = None


class ForecastBookingsSummaryRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: Optional[str] = None
    period: PeriodDate
    gross_bookings_arr: Optional[FlexibleDecimal] = None
    weighted_pipeline_arr: Optional[FlexibleDecimal] = None
    pipeline_coverage_ratio: Optional[FlexibleDecimal] = None
    new_business_arr: Optional[FlexibleDecimal] = None
    renewal_arr: Optional[FlexibleDecimal] = None
    expansion_arr: Optional[FlexibleDecimal] = None


class ForecastCashCollectionsRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: Optional[str] = None
    period: PeriodDate
    beginning_cash: Optional[FlexibleDecimal] = None
    collections: Optional[FlexibleDecimal] = None
    payroll_cash_out: Optional[FlexibleDecimal] = None
    commission_cash_out: Optional[FlexibleDecimal] = None
    vendor_cash_out: Optional[FlexibleDecimal] = None
    marketing_cash_out: Optional[FlexibleDecimal] = None
    ending_cash: Optional[FlexibleDecimal] = None


class ForecastCashFlowStatementRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: Optional[str] = None
    period: PeriodDate
    net_income: Optional[FlexibleDecimal] = None
    change_in_accounts_receivable: Optional[FlexibleDecimal] = None
    change_in_deferred_revenue: Optional[FlexibleDecimal] = None
    capital_expenditures: Optional[FlexibleDecimal] = None
    net_cash_from_operating_activities: Optional[FlexibleDecimal] = None
    ending_cash: Optional[FlexibleDecimal] = None


class ForecastBalanceSheetRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: Optional[str] = None
    period: PeriodDate
    cash: Optional[FlexibleDecimal] = None
    accounts_receivable: Optional[FlexibleDecimal] = None
    deferred_revenue: Optional[FlexibleDecimal] = None
    accounts_payable: Optional[FlexibleDecimal] = None
    total_assets: Optional[FlexibleDecimal] = None
    total_liabilities: Optional[FlexibleDecimal] = None
    equity: Optional[FlexibleDecimal] = None


class ForecastIncomeStatementRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: Optional[str] = None
    period: PeriodDate
    revenue: Optional[FlexibleDecimal] = None
    cost_of_revenue: Optional[FlexibleDecimal] = None
    gross_profit: Optional[FlexibleDecimal] = None
    sales_and_marketing: Optional[FlexibleDecimal] = None
    research_and_development: Optional[FlexibleDecimal] = None
    general_and_administrative: Optional[FlexibleDecimal] = None
    ebitda: Optional[FlexibleDecimal] = None
    net_income: Optional[FlexibleDecimal] = None


class ForecastHeadcountPlanRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: Optional[str] = None
    period: PeriodDate
    department: str
    headcount: Optional[FlexibleDecimal] = None
    headcount_ending: Optional[FlexibleDecimal] = None
    headcount_beginning: Optional[FlexibleDecimal] = None
    monthly_payroll_cost: Optional[FlexibleDecimal] = None
    total_people_cost: Optional[FlexibleDecimal] = None

    def model_post_init(self, __context: object) -> None:
        if self.headcount is None and self.headcount_ending is not None:
            object.__setattr__(self, "headcount", self.headcount_ending)


class WorkforceEmployeeRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True, extra="ignore")

    version: Optional[str] = None
    employee_id: str
    department: str
    sub_department: Optional[str] = None
    role: str
    level: Optional[str] = None
    region: Optional[str] = None
    hire_date: Optional[DateValue] = None
    termination_date: Optional[DateValue] = None
    employment_status: str = "Active"
    salary_annual: Optional[FlexibleDecimal] = None
    bonus_annual: Optional[FlexibleDecimal] = None
    commission_annual: Optional[FlexibleDecimal] = None
    equity_sbc_annual: Optional[FlexibleDecimal] = None
    benefits_load_pct: Optional[FlexibleDecimal] = None
    quota_capacity_arr: Optional[FlexibleDecimal] = None
    productivity_ramp_pct: Optional[FlexibleDecimal] = None
    months_to_full_productivity: Optional[int] = None


class WorkforceOpenRequisitionRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    version: Optional[str] = None
    req_id: str
    role: str
    department: str
    sub_department: Optional[str] = None
    hiring_manager: Optional[str] = None
    target_hire_date: Optional[DateValue] = None
    planned_start_date: Optional[DateValue] = None
    priority: Optional[str] = None
    approved_status: str = "Approved"
    requisition_type: str = "new"
    level: Optional[str] = None
    region: Optional[str] = None
    salary_annual_override: Optional[FlexibleDecimal] = None
    quota_capacity_arr_override: Optional[FlexibleDecimal] = None


class WorkforceHiringRampAssumptionRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    version: Optional[str] = None
    department: str
    role: str
    level: str = ""
    month_offset: int
    productivity_pct: FlexibleDecimal
    notes: Optional[str] = None


class WorkforceCompensationBandRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    version: Optional[str] = None
    department: str
    role: str
    level: str = ""
    region: str = ""
    base_salary_annual: FlexibleDecimal
    bonus_target_pct: Optional[FlexibleDecimal] = None
    commission_annual: Optional[FlexibleDecimal] = None
    equity_sbc_annual: Optional[FlexibleDecimal] = None
    benefits_load_pct: Optional[FlexibleDecimal] = None
    default_quota_capacity_arr: Optional[FlexibleDecimal] = None


class WorkforceDepartmentAllocationRuleRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    version: Optional[str] = None
    rule_id: str
    department: str
    pnl_line: str
    allocation_pct: FlexibleDecimal
    effective_start: Optional[DateValue] = None
    effective_end: Optional[DateValue] = None
    notes: Optional[str] = None


class ForecastMarketingPipelineRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: Optional[str] = None
    period: PeriodDate
    marketing_channel: str
    mqls: Optional[FlexibleDecimal] = None
    sqls: Optional[FlexibleDecimal] = None
    pipeline_arr_created: Optional[FlexibleDecimal] = None
    expected_closed_won_arr: Optional[FlexibleDecimal] = None
    marketing_spend: Optional[FlexibleDecimal] = None
    cost_per_sql: Optional[FlexibleDecimal] = None


class ForecastMrrWaterfallRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: Optional[str] = None
    period: PeriodDate
    beginning_arr: Optional[FlexibleDecimal] = None
    renewal_arr: Optional[FlexibleDecimal] = None
    renewal_uplift_arr: Optional[FlexibleDecimal] = None
    new_business_arr: Optional[FlexibleDecimal] = None
    expansion_arr: Optional[FlexibleDecimal] = None
    reactivation_arr: Optional[FlexibleDecimal] = None
    contraction_arr: Optional[FlexibleDecimal] = None
    churn_arr: Optional[FlexibleDecimal] = None
    ending_arr: Optional[FlexibleDecimal] = None
    forecasted_nrr: Optional[FlexibleDecimal] = None


class ForecastOpportunityRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: Optional[str] = None
    forecast_period: PeriodDate
    opportunity_id: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    segment: Optional[str] = None
    region: Optional[str] = None
    marketing_channel: Optional[str] = None
    opportunity_type: Optional[str] = None
    stage: Optional[str] = None
    amount_arr: Optional[FlexibleDecimal] = None
    probability: Optional[ProbabilityDecimal] = None
    weighted_arr: Optional[FlexibleDecimal] = None
    billing_cadence: Optional[str] = None
    billing_terms: Optional[str] = None
    historical_nrr_assumption: Optional[FlexibleDecimal] = None


class ForecastQuotaCapacityRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: Optional[str] = None
    period: PeriodDate
    region: str
    quota_carrying_reps: Optional[FlexibleDecimal] = None
    quota_capacity_arr: Optional[FlexibleDecimal] = None
    expected_bookings_arr: Optional[FlexibleDecimal] = None


class ForecastRevenueScheduleRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: Optional[str] = None
    period: PeriodDate
    recognized_revenue: Optional[FlexibleDecimal] = None
    billings: Optional[FlexibleDecimal] = None
    deferred_revenue_ending: Optional[FlexibleDecimal] = None
    historical_dso: Optional[FlexibleDecimal] = None
    expected_collections: Optional[FlexibleDecimal] = None


class ForecastWorkingCapitalMetricsRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: Optional[str] = None
    period: PeriodDate
    dso: Optional[FlexibleDecimal] = None
    dpo: Optional[FlexibleDecimal] = None
    accounts_receivable: Optional[FlexibleDecimal] = None
    deferred_revenue: Optional[FlexibleDecimal] = None


DemoCsvKind = Literal[
    "customers",
    "subscriptions",
    "opportunities",
    "invoices",
    "payments",
    "gl_actuals",
    "headcount_plan",
    "vendor_contracts",
    "sales_quotas",
    "commission_plans",
    "mrr_waterfall",
    "forecast_assumptions",
    "forecast_balance_sheet",
    "forecast_bookings_summary",
    "forecast_cash_collections",
    "forecast_cash_flow_statement",
    "forecast_headcount_plan",
    "forecast_income_statement",
    "forecast_marketing_pipeline",
    "forecast_mrr_waterfall",
    "forecast_opportunities",
    "forecast_quota_capacity",
    "forecast_revenue_schedule",
    "forecast_working_capital_metrics",
    "forecast_gl_detail",
    "workforce_employees",
    "workforce_open_requisitions",
    "workforce_hiring_ramp_assumptions",
    "workforce_compensation_bands",
    "workforce_department_allocation_rules",
]

ROW_MODELS: dict[str, type[BaseModel]] = {
    "customers": CustomerRow,
    "subscriptions": SubscriptionRow,
    "opportunities": OpportunityRow,
    "invoices": InvoiceRow,
    "payments": PaymentRow,
    "gl_actuals": GlActualRow,
    "headcount_plan": HeadcountPlanRow,
    "vendor_contracts": VendorContractRow,
    "sales_quotas": SalesQuotaRow,
    "commission_plans": CommissionPlanRow,
    "mrr_waterfall": MrrWaterfallRow,
    "forecast_assumptions": ForecastAssumptionRow,
    "forecast_balance_sheet": ForecastBalanceSheetRow,
    "forecast_bookings_summary": ForecastBookingsSummaryRow,
    "forecast_cash_collections": ForecastCashCollectionsRow,
    "forecast_cash_flow_statement": ForecastCashFlowStatementRow,
    "forecast_headcount_plan": ForecastHeadcountPlanRow,
    "forecast_income_statement": ForecastIncomeStatementRow,
    "forecast_marketing_pipeline": ForecastMarketingPipelineRow,
    "forecast_mrr_waterfall": ForecastMrrWaterfallRow,
    "forecast_opportunities": ForecastOpportunityRow,
    "forecast_quota_capacity": ForecastQuotaCapacityRow,
    "forecast_revenue_schedule": ForecastRevenueScheduleRow,
    "forecast_working_capital_metrics": ForecastWorkingCapitalMetricsRow,
    "forecast_gl_detail": ForecastGlDetailRow,
    "workforce_employees": WorkforceEmployeeRow,
    "workforce_open_requisitions": WorkforceOpenRequisitionRow,
    "workforce_hiring_ramp_assumptions": WorkforceHiringRampAssumptionRow,
    "workforce_compensation_bands": WorkforceCompensationBandRow,
    "workforce_department_allocation_rules": WorkforceDepartmentAllocationRuleRow,
}
