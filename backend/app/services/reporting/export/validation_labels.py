"""Plain-language labels for export validation checks (Close Peak §6c)."""

from __future__ import annotations

from typing import Literal

from app.services.reporting.export.schemas import ExportValidationSummary
from app.services.reporting.validation_service import ValidationCheck

TrustStatus = Literal["verified", "needs_review", "blocked"]

# Customer-facing catalog: internal validation_name -> (title, what this proves)
VALIDATION_LABEL_CATALOG: dict[str, tuple[str, str]] = {
    "arr_waterfall_ties": (
        "ARR rollforward ties",
        "Ending ARR equals beginning plus the period’s ARR movements.",
    ),
    "arr_ending_balance_equals_next_beginning_balance": (
        "ARR continuity across months",
        "Each month’s ending ARR matches the next month’s beginning ARR.",
    ),
    "actual_ending_balance_rolls_to_forecast_beginning": (
        "Actuals roll into forecast",
        "Last actual ending ARR rolls into the forecast beginning balance.",
    ),
    "pipeline_waterfall_ties": (
        "Pipeline rollforward ties",
        "Pipeline beginning plus wins/losses ties to ending pipeline.",
    ),
    "closed_won_arr_ties_mrr_new_business_arr": (
        "Closed-won ties to new ARR",
        "Closed-won pipeline ARR matches new-business ARR in the MRR bridge.",
    ),
    "actual_marketing_closed_won_arr_ties_to_actual_opportunities": (
        "Marketing closed-won ties to opportunities",
        "Marketing closed-won ARR matches opportunity closed-won ARR.",
    ),
    "cash_bridge_ties": (
        "Cash bridge ties",
        "Beginning cash plus cash movements equals ending cash.",
    ),
    "cash_bridge_ending_cash_ties_balance_sheet_cash": (
        "Ending cash matches the balance sheet",
        "Cash bridge ending cash matches cash on the balance sheet.",
    ),
    "deferred_revenue_waterfall_ties": (
        "Deferred revenue rollforward ties",
        "Beginning deferred + billings − recognized = ending deferred revenue.",
    ),
    "ar_rollforward_ties": (
        "Accounts receivable rollforward ties",
        "Beginning AR + billings − collections = ending AR.",
    ),
    "ap_rollforward_ties": (
        "Accounts payable rollforward ties",
        "Beginning AP + accruals − payments = ending AP.",
    ),
    "cash_collections_missing": (
        "Cash collections missing",
        "AR rollforward has no collections in this period — review source data.",
    ),
    "operating_cash_flow_missing_or_zero": (
        "Operating cash flow missing",
        "Operating cash flow is zero or missing for this period.",
    ),
    "dashboard_values_sourced_from_database": (
        "Statements sourced from warehouse",
        "Financial statement values are pulled from loaded warehouse tables.",
    ),
    "cash_cell_gl_lines_tie": (
        "Cash cells tie to GL lines",
        "Cash drill-down amounts match the underlying GL lines.",
    ),
    "pipeline_cell_opportunities_tie": (
        "Pipeline cells tie to opportunities",
        "Pipeline cell amounts match underlying opportunity detail.",
    ),
    "expandable_section_empty": (
        "Expandable detail empty",
        "A drill-down section expected detail rows but found none.",
    ),
    "combined_scenario_period_source_mismatch": (
        "Combined scenario source mismatch",
        "Combined scenario periods are not aligned across source tables.",
    ),
    "missing_active_channel_marketing_metrics": (
        "Marketing channel metrics missing",
        "Active marketing channels are missing expected metric rows.",
    ),
    "export_validation_no_checks": (
        "No validation checks available",
        "There was not enough loaded data to run tie-out checks yet.",
    ),
    "workforce_source_data_missing": (
        "Workforce source data missing",
        "Workforce / headcount source tables are not loaded.",
    ),
    "workforce_zero_payroll": (
        "Workforce payroll is zero",
        "Payroll appears as zero — confirm workforce cost inputs.",
    ),
    "workforce_payroll_derived": (
        "Workforce payroll derived",
        "Payroll was derived from headcount plan rather than payroll file.",
    ),
    "workforce_pnl_overlay_ready": (
        "Workforce P&L overlay ready",
        "Workforce costs are available to overlay onto the P&L.",
    ),
    "workforce_cash_payroll_vs_people_cost": (
        "Payroll vs people cost",
        "Cash payroll and people-cost views are within expected tolerance.",
    ),
    "gtm_quota_capacity_source": (
        "GTM quota capacity sourced",
        "Quota / capacity figures are sourced from the GTM plan tables.",
    ),
    "legacy_headcount_plan_in_use": (
        "Legacy headcount plan in use",
        "Board workforce view is using the legacy headcount plan.",
    ),
}

_STATUS_TO_TRUST: dict[str, tuple[TrustStatus, str]] = {
    "pass": ("verified", "Verified"),
    "warning": ("needs_review", "Needs review"),
    "fail": ("blocked", "Blocked"),
}


def customer_label_for(validation_name: str) -> tuple[str, str]:
    """Return (title, detail). Falls back to a readable title from the snake_case name."""
    keyed = VALIDATION_LABEL_CATALOG.get(validation_name)
    if keyed:
        return keyed
    title = validation_name.replace("_", " ").strip().capitalize() or "Validation check"
    return title, "Internal warehouse check."


def trust_status_for(status: str) -> tuple[TrustStatus, str]:
    return _STATUS_TO_TRUST.get(status, ("needs_review", "Needs review"))


def apply_customer_validation_labels(
    summary: ExportValidationSummary,
    *,
    as_of_period: str | None = None,
) -> ExportValidationSummary:
    """Attach plain-language labels and board trust status for customer UI."""
    labeled: list[ValidationCheck] = []
    for check in summary.checks:
        title, detail = customer_label_for(check.validation_name)
        labeled.append(
            check.model_copy(
                update={
                    "customer_label": title,
                    "customer_detail": detail,
                }
            )
        )
    trust_status, trust_label = trust_status_for(summary.status)
    return summary.model_copy(
        update={
            "checks": labeled,
            "as_of_period": as_of_period or summary.as_of_period,
            "trust_status": trust_status,
            "trust_label": trust_label,
        }
    )
