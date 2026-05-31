"""Exact-header CSV type detection for demo files."""

from __future__ import annotations

from typing import Optional

# DB-managed columns may appear if a user exports an app table. They are ignored
# during detection and load; organization_id comes from the selected org, and
# timestamps are managed by the database.
MANAGED_COLUMNS = frozenset({"organization_id", "created_at", "updated_at"})

# Headers must match a known CSV profile after removing managed columns; column
# order in file may vary. Some profiles include both the original compact demo
# headers and the expanded warehouse headers from `simple CSVS`.
EXPECTED: dict[str, frozenset[str]] = {
    "customers": frozenset(
        {
            "customer_id",
            "customer_name",
            "segment",
            "industry",
            "status",
            "start_date",
            "billing_cadence",
            "payment_terms",
            "source_crm",
            "netsuite_customer_id",
            "stripe_customer_id",
        }
    ),
    "subscriptions": frozenset(
        {
            "subscription_id",
            "customer_id",
            "product",
            "billing_cadence",
            "start_date",
            "end_date",
            "current_mrr",
            "current_arr",
            "status",
            "currency",
        }
    ),
    "opportunities": frozenset(
        {
            "opportunity_id",
            "customer_id",
            "opportunity_name",
            "opportunity_type",
            "stage",
            "amount_arr",
            "expected_close_date",
            "probability",
            "segment",
            "owner",
            "rep_id",
            "forecast_period",
            "source_crm",
        }
    ),
    "invoices": frozenset(
        {
            "invoice_id",
            "customer_id",
            "invoice_period",
            "invoice_date",
            "due_date",
            "invoice_amount",
            "payment_status",
            "billing_cadence",
            "currency",
        }
    ),
    "payments": frozenset(
        {
            "payment_id",
            "invoice_id",
            "customer_id",
            "payment_date",
            "payment_amount",
            "payment_method",
            "currency",
        }
    ),
    "gl_actuals": frozenset(
        {
            "period",
            "account_number",
            "account_name",
            "statement",
            "category",
            "amount",
            "currency",
            "subsidiary",
            "source_system",
        }
    ),
    "headcount_plan": frozenset(
        {
            "period",
            "department",
            "headcount",
            "monthly_payroll_cost",
        }
    ),
    "vendor_contracts": frozenset(
        {
            "vendor_id",
            "vendor_name",
            "service_category",
            "contract_start",
            "contract_end",
            "annual_contract_value",
            "billing_cadence",
            "payment_terms",
            "expense_category",
        }
    ),
    "sales_quotas": frozenset(
        {
            "rep_id",
            "rep_name",
            "segment",
            "quota_period",
            "quota_arr",
            "closed_won_arr_to_date",
        }
    ),
    "commission_plans": frozenset(
        {
            "plan_id",
            "role",
            "eligible_opportunity_type",
            "base_commission_rate",
            "accelerator_multiplier",
            "accelerator_threshold",
            "accelerated_rate",
            "clawback_window",
        }
    ),
    "mrr_waterfall": frozenset(
        {
            "period",
            "customer_id",
            "beginning_mrr",
            "new_mrr",
            "expansion_mrr",
            "contraction_mrr",
            "churn_mrr",
            "reactivation_mrr",
            "ending_mrr",
            "movement_type",
        }
    ),
    "forecast_assumptions": frozenset({"assumption", "value"}),
    "forecast_bookings_summary": frozenset(
        {
            "version",
            "period",
            "gross_bookings_arr",
            "weighted_pipeline_arr",
            "pipeline_coverage_ratio",
            "new_business_arr",
            "renewal_arr",
            "expansion_arr",
        }
    ),
    "forecast_cash_collections": frozenset(
        {
            "version",
            "period",
            "beginning_cash",
            "collections",
            "payroll_cash_out",
            "commission_cash_out",
            "vendor_cash_out",
            "marketing_cash_out",
            "ending_cash",
        }
    ),
    "forecast_cash_flow_statement": frozenset(
        {
            "version",
            "period",
            "net_income",
            "change_in_accounts_receivable",
            "change_in_deferred_revenue",
            "capital_expenditures",
            "net_cash_from_operating_activities",
            "ending_cash",
        }
    ),
    "forecast_balance_sheet": frozenset(
        {
            "version",
            "period",
            "cash",
            "accounts_receivable",
            "deferred_revenue",
            "accounts_payable",
            "total_assets",
            "total_liabilities",
            "equity",
        }
    ),
    "forecast_income_statement": frozenset(
        {
            "version",
            "period",
            "revenue",
            "cost_of_revenue",
            "gross_profit",
            "sales_and_marketing",
            "research_and_development",
            "general_and_administrative",
            "ebitda",
            "net_income",
        }
    ),
    "forecast_headcount_plan": frozenset(
        {
            "version",
            "period",
            "department",
            "headcount",
            "monthly_payroll_cost",
            "total_people_cost",
        }
    ),
    "forecast_marketing_pipeline": frozenset(
        {
            "version",
            "period",
            "marketing_channel",
            "mqls",
            "sqls",
            "pipeline_arr_created",
            "expected_closed_won_arr",
            "marketing_spend",
            "cost_per_sql",
        }
    ),
    "forecast_mrr_waterfall": frozenset(
        {
            "version",
            "period",
            "beginning_arr",
            "renewal_arr",
            "renewal_uplift_arr",
            "new_business_arr",
            "expansion_arr",
            "reactivation_arr",
            "contraction_arr",
            "churn_arr",
            "ending_arr",
            "forecasted_nrr",
        }
    ),
    "forecast_opportunities": frozenset(
        {
            "version",
            "forecast_period",
            "opportunity_id",
            "customer_id",
            "customer_name",
            "segment",
            "region",
            "marketing_channel",
            "opportunity_type",
            "stage",
            "amount_arr",
            "probability",
            "weighted_arr",
            "billing_cadence",
            "billing_terms",
            "historical_nrr_assumption",
        }
    ),
    "forecast_quota_capacity": frozenset(
        {
            "version",
            "period",
            "region",
            "quota_carrying_reps",
            "quota_capacity_arr",
            "expected_bookings_arr",
        }
    ),
    "forecast_revenue_schedule": frozenset(
        {
            "version",
            "period",
            "recognized_revenue",
            "billings",
            "deferred_revenue_ending",
            "historical_dso",
            "expected_collections",
        }
    ),
    "forecast_working_capital_metrics": frozenset(
        {
            "version",
            "period",
            "dso",
            "dpo",
            "accounts_receivable",
            "deferred_revenue",
        }
    ),
    "forecast_gl_detail": frozenset(
        {
            "scenario",
            "period",
            "line_type",
            "statement_category",
            "department",
            "sub_department",
            "account_group",
            "expense_type",
            "gl_account",
            "management_view_include",
            "accounting_view_include",
            "sbc_flag",
            "one_time_flag",
            "non_cash_flag",
            "forecast_amount",
            "source",
            "notes",
        }
    ),
    "workforce_employees": frozenset(
        {
            "version",
            "employee_id",
            "department",
            "role",
            "hire_date",
            "employment_status",
            "salary_annual",
        }
    ),
    "workforce_open_requisitions": frozenset(
        {
            "version",
            "req_id",
            "role",
            "department",
            "planned_start_date",
            "approved_status",
            "requisition_type",
        }
    ),
    "workforce_hiring_ramp_assumptions": frozenset(
        {
            "version",
            "department",
            "role",
            "level",
            "month_offset",
            "productivity_pct",
        }
    ),
    "workforce_compensation_bands": frozenset(
        {
            "version",
            "department",
            "role",
            "level",
            "region",
            "base_salary_annual",
        }
    ),
    "workforce_department_allocation_rules": frozenset(
        {
            "version",
            "rule_id",
            "department",
            "pnl_line",
            "allocation_pct",
        }
    ),
}

EXPANDED_EXPECTED: dict[str, frozenset[str]] = {
    "customers": frozenset(
        {
            "customer_id",
            "customer_name",
            "segment",
            "industry",
            "status",
            "customer_start_date",
            "contract_start_date",
            "billing_cadence",
            "billing_terms",
            "billing_state",
            "source_crm",
            "netsuite_customer_id",
            "stripe_customer_id",
            "starting_mrr_jan_2026",
            "starting_arr_jan_2026",
            "currency",
        }
    ),
    "subscriptions": frozenset(
        {
            "subscription_id",
            "customer_id",
            "product",
            "billing_cadence",
            "contract_start_date",
            "contract_end_date",
            "current_mrr",
            "current_arr",
            "status",
            "source_opportunity_id",
            "currency",
            "version",
        }
    ),
    "opportunities": frozenset(
        {
            "opportunity_id",
            "customer_id",
            "customer_name",
            "opportunity_name",
            "opportunity_type",
            "stage",
            "amount_arr",
            "expected_close_date",
            "close_date",
            "contract_start_date",
            "probability",
            "segment",
            "owner_rep_id",
            "owner",
            "forecast_period",
            "source_crm",
            "marketing_channel",
            "version",
        }
    ),
    "versioned_opportunity_movements": frozenset(
        {
            "version",
            "period",
            "opportunity_id",
            "opportunity_name",
            "customer_id",
            "customer_name",
            "opportunity_type",
            "stage",
            "close_status",
            "created_date",
            "expected_close_date",
            "actual_close_date",
            "contract_start_date",
            "contract_end_date",
            "contract_term_months",
            "billing_cadence",
            "billing_terms",
            "customer_state",
            "region",
            "segment",
            "industry",
            "marketing_channel",
            "owner",
            "amount_arr",
            "weighted_arr",
            "probability",
            "waterfall_type",
            "pipeline_movement_type",
            "source_note",
        }
    ),
    "versioned_opportunities": frozenset(
        {
            "version",
            "period",
            "opportunity_id",
            "opportunity_name",
            "customer_id",
            "customer_name",
            "opportunity_type",
            "stage",
            "close_status",
            "created_date",
            "expected_close_date",
            "actual_close_date",
            "contract_start_date",
            "contract_end_date",
            "contract_term_months",
            "billing_cadence",
            "billing_terms",
            "customer_state",
            "region",
            "segment",
            "industry",
            "marketing_channel",
            "owner",
            "amount_arr",
            "weighted_arr",
            "probability",
            "waterfall_type",
            "pipeline_movement_type",
            "source_note",
        }
    ),
    "invoices": frozenset(
        {
            "version",
            "invoice_id",
            "customer_id",
            "customer_name",
            "invoice_period",
            "service_period_start",
            "service_period_end",
            "invoice_date",
            "due_date",
            "invoice_amount",
            "payment_status",
            "billing_cadence",
            "billing_terms",
            "currency",
        }
    ),
    "payments": frozenset(
        {
            "version",
            "payment_id",
            "invoice_id",
            "customer_id",
            "payment_date",
            "payment_amount",
            "payment_method",
            "currency",
        }
    ),
    "gl_actuals": frozenset(
        {
            "version",
            "period",
            "account_number",
            "account_name",
            "statement",
            "statement_category",
            "account_group",
            "expense_type",
            "department",
            "cost_center",
            "sub_department",
            "vendor_id",
            "vendor_name",
            "source_file",
            "source_record_id",
            "amount",
            "currency",
            "subsidiary",
            "source_system",
            "notes",
        }
    ),
    "headcount_plan": frozenset(
        {
            "version",
            "period",
            "department",
            "headcount",
            "monthly_payroll_cost",
            "payroll_tax_rate",
            "benefits_rate",
            "total_people_cost",
        }
    ),
    "sales_quotas": frozenset(
        {
            "rep_id",
            "rep_name",
            "role",
            "segment",
            "quota_period",
            "quota_arr",
            "closed_won_arr_to_date",
        }
    ),
    "commission_plans": frozenset(
        {
            "plan_id",
            "role",
            "eligible_opportunity_type",
            "base_commission_rate",
            "accelerator_multiplier",
            "accelerator_threshold",
            "accelerated_rate",
            "clawback_window_months",
        }
    ),
    "forecast_mrr_waterfall": frozenset(
        {
            "version",
            "period",
            "beginning_arr",
            "renewal_arr",
            "new_business_arr",
            "expansion_arr",
            "contraction_arr",
            "churn_arr",
            "reactivation_arr",
            "net_new_arr",
            "ending_arr",
            "gross_retention_rate",
            "net_dollar_retention_rate",
            "waterfall_check",
        }
    ),
}


def normalize_headers(raw: list[str]) -> list[str]:
    return [h.strip().lstrip("\ufeff") for h in raw]


def strip_managed_headers(headers: list[str]) -> list[str]:
    return [h for h in normalize_headers(headers) if h not in MANAGED_COLUMNS]


def detect_csv_kind(headers: list[str]) -> Optional[str]:
    hs = frozenset(strip_managed_headers(headers))
    from app.services.demo_csv.workforce_csv import detect_workforce_kind

    workforce_kind = detect_workforce_kind(hs)
    if workforce_kind is not None:
        return workforce_kind
    for kind, expected in EXPECTED.items():
        if hs == expected:
            return kind
    for kind, expected in EXPANDED_EXPECTED.items():
        if hs == expected:
            if kind in {"versioned_opportunities", "versioned_opportunity_movements"}:
                return "opportunities"
            return kind
    return None


def header_mismatch_report(headers: list[str]) -> dict[str, dict[str, list[str]]]:
    """For each known demo CSV profile, list missing and extra columns vs that expectation."""
    from app.services.demo_csv.workforce_csv import WORKFORCE_EXPANDED_HEADERS

    hs = frozenset(strip_managed_headers(headers))
    report: dict[str, dict[str, list[str]]] = {}
    merged = dict(EXPECTED)
    merged.update(EXPANDED_EXPECTED)
    merged.update(WORKFORCE_EXPANDED_HEADERS)
    for kind, expected in merged.items():
        best = expected
        missing = sorted(best - hs)
        extra = sorted(hs - best)
        report[kind] = {"missing": missing, "extra": extra}
    return report
