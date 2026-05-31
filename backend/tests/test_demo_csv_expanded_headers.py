"""Expanded warehouse CSV profiles."""

from __future__ import annotations

from app.services.demo_csv.detector import detect_csv_kind
from app.services.demo_csv.loader import (
    _apply_physical_required_aliases,
    _canonicalize_row,
    _is_skippable_physical_row,
    _kind_from_filename,
    _physical_version_table_name,
)


def test_detects_forecast_gl_detail_profile() -> None:
    headers = [
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
    ]
    assert detect_csv_kind(headers) == "forecast_gl_detail"


def test_detects_expanded_gl_actuals_profile() -> None:
    headers = [
        "organization_id",
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
    ]
    assert detect_csv_kind(headers) == "gl_actuals"


def test_canonicalizes_expanded_core_columns() -> None:
    customer = _canonicalize_row(
        "customers",
        {"customer_start_date": "2026-01-01", "billing_terms": "Net 30"},
    )
    subscription = _canonicalize_row(
        "subscriptions",
        {"contract_start_date": "2026-01-01", "contract_end_date": "2026-12-31"},
    )
    opportunity = _canonicalize_row("opportunities", {"owner_rep_id": "REP-001"})
    gl = _canonicalize_row("gl_actuals", {"statement_category": "Revenue"})

    assert customer["start_date"] == "2026-01-01"
    assert customer["payment_terms"] == "Net 30"
    assert subscription["start_date"] == "2026-01-01"
    assert subscription["end_date"] == "2026-12-31"
    assert opportunity["rep_id"] == "REP-001"
    assert gl["category"] == "Revenue"


def test_detects_forecast_csv_profiles() -> None:
    assert (
        detect_csv_kind(
            [
                "organization_id",
                "version",
                "period",
                "gross_bookings_arr",
                "weighted_pipeline_arr",
                "pipeline_coverage_ratio",
                "new_business_arr",
                "renewal_arr",
                "expansion_arr",
            ]
        )
        == "forecast_bookings_summary"
    )
    assert (
        detect_csv_kind(
            [
                "organization_id",
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
            ]
        )
        == "forecast_opportunities"
    )


def test_routes_version_prefixed_filenames() -> None:
    assert _kind_from_filename("Actual_customers.csv") == "customers"
    assert _kind_from_filename("Budget_customers.csv") == "budget_customers"
    assert _kind_from_filename("Forecast_customers.csv") == "forecast_customers"
    assert _kind_from_filename("Actual_gl_detail.csv") == "gl_actuals"
    assert _kind_from_filename("Budget_gl_detail.csv") == "gl_actuals"
    assert _kind_from_filename("Forecast_gl_detail.csv") == "forecast_gl_detail"
    assert _kind_from_filename("Forecast_income_statement.csv") == "forecast_income_statement"
    assert _kind_from_filename("Budget_income_statement.csv") == "budget_income_statement"


def test_detects_versioned_opportunity_profile() -> None:
    headers = [
        "organization_id",
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
    ]
    assert detect_csv_kind(headers) == "opportunities"


def test_forecast_opportunities_alias_period_to_forecast_period() -> None:
    row_payload: dict[str, object] = {"period": "2026-06"}
    raw = {"period": "2026-06"}
    _apply_physical_required_aliases(
        "forecast_opportunities",
        row_payload,
        raw,
        column_types={"forecast_period": "date"},
        required_columns={"forecast_period"},
        version_hint="Forecast",
    )
    assert row_payload["forecast_period"] == "2026-06-01"


def test_versioned_opportunity_filenames_use_physical_tables() -> None:
    assert _physical_version_table_name("Actual_opportunities.csv") == "actual_opportunities"
    assert _physical_version_table_name("Budget_opportunities.csv") == "budget_opportunities"
    assert _physical_version_table_name("Forecast_opportunities.csv") == "forecast_opportunities"
    assert _kind_from_filename("Actual_opportunities.csv") == "actual_opportunities"
    assert _kind_from_filename("Budget_opportunities.csv") == "budget_opportunities"
    assert _kind_from_filename("Forecast_opportunities.csv") == "forecast_opportunities"


def test_physical_table_names_for_versioned_files() -> None:
    assert _physical_version_table_name("Actual_customers.csv") == "actual_customers"
    assert _physical_version_table_name("Actuals_customers.csv") == "actual_customers"
    assert _physical_version_table_name("Actual_marketing_pipeline.csv") == "actual_marketing_pipeline"
    assert _physical_version_table_name("Budget_income_statement.csv") == "budget_income_statement"
    assert _physical_version_table_name("Forecast_income_statement.csv") == "forecast_income_statement"
    assert _physical_version_table_name("Forecast_cash_flow_bridge.csv") == "forecast_cash_flow_bridge"
    assert _physical_version_table_name("Forecast_MRR_Waterfall.csv") == "forecast_mrr_waterfall"


def test_skips_blank_physical_mrr_waterfall_rows() -> None:
    required = {"organization_id", "version", "period", "source_row_number"}
    assert _is_skippable_physical_row(
        {"version": None, "period": None},
        required_columns=required,
    )
    # Version from filename hint but no period — still skip (trailing blank rows).
    assert _is_skippable_physical_row(
        {"version": "Forecast", "period": None},
        required_columns=required,
    )
    assert not _is_skippable_physical_row(
        {"version": "Forecast", "period": "2026-06-01"},
        required_columns=required,
    )


def test_detects_expanded_forecast_mrr_waterfall_headers() -> None:
    headers = [
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
    ]
    assert detect_csv_kind(headers) == "forecast_mrr_waterfall"


def test_detects_workforce_employee_profile() -> None:
    assert (
        detect_csv_kind(
            [
                "version",
                "employee_id",
                "department",
                "role",
                "hire_date",
                "employment_status",
                "salary_annual",
            ]
        )
        == "workforce_employees"
    )


def test_workforce_kind_from_typo_filename() -> None:
    from app.services.demo_csv.workforce_csv import workforce_kind_from_filename

    assert workforce_kind_from_filename("compensations_bands.csv") == "workforce_compensation_bands"
    assert workforce_kind_from_filename("Compensation_Bands.csv") == "workforce_compensation_bands"


def test_detects_simple_csvs_compensation_bands() -> None:
    assert (
        detect_csv_kind(
            [
                "department",
                "role",
                "level",
                "salary_midpoint",
                "salary_low",
                "salary_high",
                "variable_comp_target",
                "equity_sbc_annual",
                "benefits_load_pct",
                "fully_loaded_cash_cost_midpoint",
                "fully_loaded_gaap_cost_midpoint",
                "quota_carrying",
                "annual_quota_arr",
                "productivity_ramp_months",
            ]
        )
        == "workforce_compensation_bands"
    )


def test_detects_simple_csvs_hiring_ramp() -> None:
    assert (
        detect_csv_kind(
            ["ramp_months", "month_after_start", "productivity_pct", "applies_to"]
        )
        == "workforce_hiring_ramp_assumptions"
    )


def test_detects_workforce_open_requisition_profile() -> None:
    assert (
        detect_csv_kind(
            [
                "version",
                "req_id",
                "role",
                "department",
                "planned_start_date",
                "approved_status",
                "requisition_type",
            ]
        )
        == "workforce_open_requisitions"
    )
