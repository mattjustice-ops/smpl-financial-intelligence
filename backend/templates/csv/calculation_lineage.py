"""Exportable calculation lineage registry for SMPL calculated outputs.

Generates:
  - Calculation_Lineage_Registry.csv   (open in Excel — one row per calculated column)
  - Calculation_Lineage_Gaps.csv       (rows flagged missing / partial / undocumented)
  - Calculation_Dataset_Dependencies.csv (one row per output file)
  - calculation_lineage_manifest.json  (machine-readable full graph)
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REGISTRY_COLUMNS = [
    "output_dataset",
    "output_filename_pattern",
    "output_column",
    "column_role",
    "grain",
    "is_calculated",
    "calculation_rule",
    "formula",
    "source_layer",
    "source_datasets",
    "source_columns",
    "depends_on_calculated_outputs",
    "depends_on_calculated_columns",
    "board_reporting_uses",
    "prototype_upload_table",
    "target_calc_engine",
    "coverage_status",
    "gap_or_risk_notes",
]


@dataclass
class LineageRow:
    output_dataset: str
    output_filename_pattern: str
    output_column: str
    column_role: str
    grain: str
    is_calculated: str
    calculation_rule: str
    formula: str
    source_layer: str
    source_datasets: str
    source_columns: str
    depends_on_calculated_outputs: str
    depends_on_calculated_columns: str
    board_reporting_uses: str
    prototype_upload_table: str
    target_calc_engine: str
    coverage_status: str
    gap_or_risk_notes: str = ""


def _rows() -> list[LineageRow]:
    """Curated lineage for calculated reporting outputs (Actual/Forecast/Budget)."""
    r: list[LineageRow] = []

    def add(**kwargs: str) -> None:
        r.append(LineageRow(**kwargs))

    # --- MRR / ARR Waterfall ---
    ds = "mrr_waterfall"
    fn = "{Version}_MRR_Waterfall.csv"
    tbl = "{version}_mrr_waterfall"
    for col, role, calc, rule, formula, src_ds, src_cols, deps_out, deps_col, status, notes in [
        (
            "period",
            "key",
            "N",
            "Pass-through period key",
            "",
            "",
            "",
            "",
            "",
            "complete",
            "",
        ),
        (
            "beginning_arr",
            "measure",
            "Y",
            "Point-in-time opening ARR for the period",
            "prior_period.ending_arr OR SUM(customer.beginning_mrr)*12 at period start",
            "mrr_waterfall_customer_level; Billing_Subscription_Export",
            "period;ending_mrr;current_arr;start_date;end_date",
            "mrr_waterfall",
            "prior_period.ending_arr",
            "complete",
            "Do not sum beginning_arr across months for YTD subtotals",
        ),
        (
            "renewal_arr",
            "measure",
            "Y",
            "ARR retained from existing customers before expansion/contraction/churn",
            "SUM(customer renewal component) — often embedded in GRR/NRR rather than shown separately",
            "mrr_waterfall_customer_level; subscriptions",
            "ending_mrr;current_arr;status;contract_start_date",
            "mrr_waterfall",
            "beginning_arr",
            "partial",
            "Reference deck omits renewal line; expanded warehouse template includes it — align calc spec",
        ),
        (
            "new_business_arr",
            "measure",
            "Y",
            "New logo ARR added in period",
            "SUM(new_mrr)*12 WHERE movement_type=new OR first subscription in period",
            "mrr_waterfall_customer_level; Billing_Subscription_Export; CRM_Opportunity_Export",
            "new_mrr;movement_type;amount_arr;opportunity_type;close_date",
            "",
            "",
            "complete",
            "",
        ),
        (
            "expansion_arr",
            "measure",
            "Y",
            "Upsell / seat expansion from existing customers",
            "SUM(expansion_mrr)*12 from customer-level waterfall",
            "mrr_waterfall_customer_level; subscriptions",
            "expansion_mrr;current_mrr;movement_type",
            "",
            "",
            "complete",
            "Store as negative in some sources; display as positive absolute in UI",
        ),
        (
            "contraction_arr",
            "measure",
            "Y",
            "Downgrade ARR from existing customers",
            "SUM(contraction_mrr)*12 (negative in source data)",
            "mrr_waterfall_customer_level; subscriptions",
            "contraction_mrr;movement_type",
            "",
            "",
            "complete",
            "Display as positive absolute in board waterfall rows",
        ),
        (
            "churn_arr",
            "measure",
            "Y",
            "Full customer loss ARR",
            "SUM(churn_mrr)*12 (negative in source data)",
            "mrr_waterfall_customer_level; subscriptions; Billing_Subscription_Export",
            "churn_mrr;status;end_date;movement_type",
            "",
            "",
            "complete",
            "",
        ),
        (
            "reactivation_arr",
            "measure",
            "Y",
            "Reactivated churned customer ARR",
            "SUM(reactivation_mrr)*12",
            "mrr_waterfall_customer_level",
            "reactivation_mrr;movement_type",
            "",
            "",
            "complete",
            "",
        ),
        (
            "net_new_arr",
            "measure",
            "Y",
            "Net ARR movement excluding opening balance",
            "new_business_arr + expansion_arr + contraction_arr + churn_arr + reactivation_arr",
            "mrr_waterfall",
            "new_business_arr;expansion_arr;contraction_arr;churn_arr;reactivation_arr",
            "mrr_waterfall",
            "new_business_arr;expansion_arr;contraction_arr;churn_arr;reactivation_arr",
            "complete",
            "Summed across months for YTD net new; beginning/ending are point-in-time",
        ),
        (
            "ending_arr",
            "measure",
            "Y",
            "Point-in-time closing ARR",
            "beginning_arr + net_new_arr OR SUM(customer.ending_mrr)*12",
            "mrr_waterfall_customer_level; mrr_waterfall",
            "ending_mrr;beginning_arr;net_new_arr",
            "mrr_waterfall",
            "beginning_arr;net_new_arr",
            "complete",
            "Chains to next period beginning_arr",
        ),
        (
            "gross_retention_rate",
            "rate",
            "Y",
            "Gross dollar retention",
            "(beginning_arr + contraction_arr + churn_arr) / beginning_arr",
            "mrr_waterfall",
            "beginning_arr;contraction_arr;churn_arr",
            "mrr_waterfall",
            "beginning_arr;contraction_arr;churn_arr",
            "complete",
            "Denominator zero-guard required",
        ),
        (
            "net_dollar_retention_rate",
            "rate",
            "Y",
            "Net dollar retention (NRR)",
            "(beginning_arr + expansion_arr + contraction_arr + churn_arr) / beginning_arr",
            "mrr_waterfall",
            "beginning_arr;expansion_arr;contraction_arr;churn_arr",
            "mrr_waterfall",
            "beginning_arr;expansion_arr;contraction_arr;churn_arr",
            "complete",
            "Reference: (Expansion+Contraction+Churn)/Beginning + 1 when using decimal form",
        ),
        (
            "waterfall_check",
            "validation",
            "Y",
            "Reconciliation flag",
            "ABS(ending_arr - (beginning_arr + net_new_arr)) < tolerance",
            "mrr_waterfall",
            "ending_arr;beginning_arr;net_new_arr",
            "mrr_waterfall",
            "ending_arr;beginning_arr;net_new_arr",
            "complete",
            "Fail closed in calc engine when check fails",
        ),
    ]:
        add(
            output_dataset=ds,
            output_filename_pattern=fn,
            output_column=col,
            column_role=role,
            grain="period",
            is_calculated=calc,
            calculation_rule=rule,
            formula=formula,
            source_layer="operational_mart" if src_ds else "calculated",
            source_datasets=src_ds,
            source_columns=src_cols,
            depends_on_calculated_outputs=deps_out,
            depends_on_calculated_columns=deps_col,
            board_reporting_uses="ARR Waterfall tab; Executive Summary; Board deck",
            prototype_upload_table=tbl,
            target_calc_engine="FIE-003",
            coverage_status=status,
            gap_or_risk_notes=notes,
        )

    # --- Income Statement ---
    ds = "income_statement"
    fn = "{Version}_IncomeStatement.csv"
    tbl = "{version}_income_statement"
    is_lines = [
        ("period", "key", "N", "", "", "", "", "", "", "complete", ""),
        (
            "revenue",
            "measure",
            "Y",
            "GAAP revenue for period",
            "SUM(gl_actuals.amount WHERE statement=income AND category=revenue) OR revenue_schedule.recognized_revenue",
            "gl_actuals; forecast_revenue_schedule; Actual_DeferredRevenueWaterfall",
            "amount;statement_category;recognized_revenue;revenue_recognized",
            "deferred_revenue_waterfall;revenue_schedule",
            "revenue_recognized;recognized_revenue",
            "complete",
            "",
        ),
        (
            "cost_of_revenue",
            "measure",
            "Y",
            "COGS",
            "SUM(gl_actuals.amount WHERE category=cost_of_revenue)",
            "gl_actuals",
            "amount;statement_category;account_group",
            "",
            "",
            "complete",
            "",
        ),
        (
            "gross_profit",
            "measure",
            "Y",
            "Revenue minus COGS",
            "revenue - cost_of_revenue",
            "income_statement",
            "revenue;cost_of_revenue",
            "income_statement",
            "revenue;cost_of_revenue",
            "complete",
            "",
        ),
        (
            "gross_margin_percent",
            "rate",
            "Y",
            "Gross margin ratio",
            "gross_profit / revenue",
            "income_statement",
            "gross_profit;revenue",
            "income_statement",
            "gross_profit;revenue",
            "complete",
            "",
        ),
        (
            "sales_and_marketing",
            "measure",
            "Y",
            "S&M OpEx",
            "SUM(gl_actuals.amount WHERE department/function maps to S&M)",
            "gl_actuals; workforce_department_allocation_rules",
            "amount;department;statement_category;allocation_pct",
            "",
            "",
            "complete",
            "Requires department→P&L mapping table",
        ),
        (
            "research_and_development",
            "measure",
            "Y",
            "R&D OpEx",
            "SUM(gl_actuals.amount WHERE department/function maps to R&D)",
            "gl_actuals",
            "amount;department;statement_category",
            "",
            "",
            "complete",
            "",
        ),
        (
            "general_and_administrative",
            "measure",
            "Y",
            "G&A OpEx",
            "SUM(gl_actuals.amount WHERE department/function maps to G&A)",
            "gl_actuals",
            "amount;department;statement_category",
            "",
            "",
            "complete",
            "",
        ),
        (
            "total_opex",
            "measure",
            "Y",
            "Total operating expense",
            "sales_and_marketing + research_and_development + general_and_administrative",
            "income_statement",
            "sales_and_marketing;research_and_development;general_and_administrative",
            "income_statement",
            "sales_and_marketing;research_and_development;general_and_administrative",
            "complete",
            "",
        ),
        (
            "ebitda",
            "measure",
            "Y",
            "EBITDA",
            "gross_profit - total_opex (excl D&A below EBITDA line per policy)",
            "income_statement",
            "gross_profit;total_opex",
            "income_statement",
            "gross_profit;total_opex",
            "complete",
            "Confirm D&A treatment vs operating_income line",
        ),
        (
            "depreciation_amortization",
            "measure",
            "Y",
            "D&A add-back",
            "SUM(gl_actuals.amount WHERE account_group=D&A) OR non_cash_flag",
            "gl_actuals",
            "amount;account_group;non_cash_flag",
            "",
            "",
            "partial",
            "GL account mapping not yet codified in repo calc engine",
        ),
        (
            "operating_income",
            "measure",
            "Y",
            "Operating income",
            "ebitda - depreciation_amortization",
            "income_statement",
            "ebitda;depreciation_amortization",
            "income_statement",
            "ebitda;depreciation_amortization",
            "partial",
            "",
        ),
        (
            "net_income",
            "measure",
            "Y",
            "Bottom-line net income",
            "operating_income +/- interest/tax/other (policy-dependent)",
            "income_statement; gl_actuals",
            "operating_income;amount;statement_category",
            "income_statement",
            "operating_income",
            "gap",
            "Interest/tax lines not in template — extend IS or document as out of scope",
        ),
    ]
    for col, role, calc, rule, formula, src_ds, src_cols, deps_out, deps_col, status, notes in is_lines:
        add(
            output_dataset=ds,
            output_filename_pattern=fn,
            output_column=col,
            column_role=role,
            grain="period",
            is_calculated=calc,
            calculation_rule=rule,
            formula=formula,
            source_layer="operational_mart" if src_ds and "income_statement" not in src_ds else "calculated",
            source_datasets=src_ds,
            source_columns=src_cols,
            depends_on_calculated_outputs=deps_out,
            depends_on_calculated_columns=deps_col,
            board_reporting_uses="3-Statement tab; Management P&L; MDA Excel",
            prototype_upload_table=tbl,
            target_calc_engine="FIE-003",
            coverage_status=status,
            gap_or_risk_notes=notes,
        )

    # --- Balance Sheet ---
    ds = "balance_sheet"
    fn = "{Version}_BalanceSheet.csv"
    tbl = "{version}_balance_sheet"
    bs_lines = [
        ("period", "key", "N", "", "", "", "", "", "", "complete", ""),
        (
            "cash",
            "measure",
            "Y",
            "Cash balance at period end",
            "cash_flow_bridge.ending_cash for same period",
            "cash_flow_bridge",
            "ending_cash;period",
            "cash_flow_bridge",
            "ending_cash",
            "complete",
            "Must chain from bridge not forecast opening cash",
        ),
        (
            "accounts_receivable",
            "measure",
            "Y",
            "AR balance",
            "prior_ar + billings - collections OR revenue_schedule + DSO model",
            "invoices; payments; revenue_schedule; working_capital_metrics",
            "invoice_amount;payment_amount;billings;expected_collections;dso",
            "revenue_schedule;working_capital_metrics",
            "deferred_revenue_ending;expected_collections",
            "partial",
            "DSO-based roll-forward vs GL tie-out not fully specified",
        ),
        (
            "deferred_revenue",
            "measure",
            "Y",
            "Deferred revenue liability",
            "deferred_revenue_waterfall.ending_deferred",
            "deferred_revenue_waterfall",
            "ending_deferred",
            "deferred_revenue_waterfall",
            "ending_deferred",
            "complete",
            "",
        ),
        (
            "accounts_payable",
            "measure",
            "Y",
            "AP balance",
            "SUM(gl_actuals liability AP) OR vendor payment schedule",
            "gl_actuals; vendor_contracts",
            "amount;vendor_id;payment_terms",
            "",
            "",
            "partial",
            "Vendor cash timing model not in templates",
        ),
        (
            "prepaid_expenses",
            "measure",
            "Y",
            "Prepaid assets",
            "SUM(gl_actuals WHERE account_group=prepaid)",
            "gl_actuals",
            "amount;account_group",
            "",
            "",
            "gap",
            "No prepaid source mapping in operational marts yet",
        ),
        (
            "other_current_assets",
            "measure",
            "Y",
            "Other current assets",
            "SUM(gl_actuals WHERE balance_sheet bucket=other_current_assets)",
            "gl_actuals",
            "amount;statement_category",
            "",
            "",
            "gap",
            "",
        ),
        (
            "total_assets",
            "measure",
            "Y",
            "Total assets",
            "cash + accounts_receivable + deferred_revenue_asset_components + other assets",
            "balance_sheet",
            "cash;accounts_receivable;prepaid_expenses;other_current_assets",
            "balance_sheet",
            "cash;accounts_receivable;prepaid_expenses;other_current_assets",
            "partial",
            "Deferred revenue is liability — confirm asset composition policy",
        ),
        (
            "total_liabilities",
            "measure",
            "Y",
            "Total liabilities",
            "deferred_revenue + accounts_payable + other liabilities",
            "balance_sheet; gl_actuals",
            "deferred_revenue;accounts_payable",
            "balance_sheet",
            "deferred_revenue;accounts_payable",
            "partial",
            "",
        ),
        (
            "equity",
            "measure",
            "Y",
            "Total equity",
            "total_assets - total_liabilities",
            "balance_sheet",
            "total_assets;total_liabilities",
            "balance_sheet",
            "total_assets;total_liabilities",
            "complete",
            "",
        ),
        (
            "retained_earnings",
            "measure",
            "Y",
            "Retained earnings roll-forward",
            "prior_retained_earnings + net_income - dividends",
            "balance_sheet; income_statement",
            "net_income",
            "income_statement;balance_sheet",
            "net_income;equity",
            "gap",
            "Dividends / equity issuance not in source templates",
        ),
    ]
    for col, role, calc, rule, formula, src_ds, src_cols, deps_out, deps_col, status, notes in bs_lines:
        add(
            output_dataset=ds,
            output_filename_pattern=fn,
            output_column=col,
            column_role=role,
            grain="period",
            is_calculated=calc,
            calculation_rule=rule,
            formula=formula,
            source_layer="mixed",
            source_datasets=src_ds,
            source_columns=src_cols,
            depends_on_calculated_outputs=deps_out,
            depends_on_calculated_columns=deps_col,
            board_reporting_uses="3-Statement tab; Board deck",
            prototype_upload_table=tbl,
            target_calc_engine="FIE-003",
            coverage_status=status,
            gap_or_risk_notes=notes,
        )

    # --- Cash Flow Bridge (primary cash source for board) ---
    ds = "cash_flow_bridge"
    fn = "{Version}_CashFlowBridge.csv"
    tbl = "{version}_cash_flow_bridge"
    cfb = [
        ("period", "key", "N", "", "", "", "", "", "", "complete", ""),
        (
            "beginning_cash",
            "measure",
            "Y",
            "Opening cash",
            "prior_period.ending_cash (Actual chains to Forecast at handoff month)",
            "cash_flow_bridge",
            "ending_cash",
            "cash_flow_bridge",
            "prior_period.ending_cash",
            "complete",
            "Jul beginning_cash = Jun actual ending_cash — not forecast model opening",
        ),
        (
            "collections",
            "measure",
            "Y",
            "Cash collected",
            "SUM(payments.payment_amount) OR revenue_schedule.expected_collections",
            "payments; revenue_schedule; invoices",
            "payment_amount;payment_date;expected_collections",
            "revenue_schedule",
            "expected_collections",
            "complete",
            "",
        ),
        (
            "payroll_cash_out",
            "measure",
            "Y",
            "Payroll disbursements",
            "SUM(headcount_plan.total_people_cost) with payment lag policy",
            "headcount_plan; workforce_employees",
            "total_people_cost;monthly_payroll_cost;fully_loaded_cash_cost",
            "headcount_plan",
            "total_people_cost",
            "partial",
            "Payroll lag (N+1) not codified",
        ),
        (
            "commission_cash_out",
            "measure",
            "Y",
            "Commission payments",
            "bookings * commission_plans rates with payout timing",
            "commission_plans; opportunity_movements; sales_quotas",
            "base_commission_rate;amount_arr;closed_won_arr_to_date",
            "bookings_summary",
            "gross_bookings_arr",
            "gap",
            "Commission payout engine not built",
        ),
        (
            "vendor_cash_out_n30",
            "measure",
            "Y",
            "Vendor/AP payments",
            "SUM(vendor_contracts) by payment_terms lag",
            "vendor_contracts; gl_actuals",
            "annual_contract_value;payment_terms;amount",
            "",
            "",
            "gap",
            "",
        ),
        (
            "tax_cash_out",
            "measure",
            "Y",
            "Tax payments",
            "Policy-based % of operating income or GL tax accounts",
            "gl_actuals; income_statement",
            "amount;net_income",
            "income_statement",
            "net_income",
            "gap",
            "No tax schedule source file",
        ),
        (
            "interest_cash_out",
            "measure",
            "Y",
            "Interest paid",
            "GL interest expense cash-paid portion",
            "gl_actuals",
            "amount;account_group",
            "",
            "",
            "gap",
            "",
        ),
        (
            "other_operating_cash_out",
            "measure",
            "Y",
            "Other operating outflows",
            "Residual operating cash out per GL/management policy",
            "gl_actuals",
            "amount;statement_category",
            "",
            "",
            "gap",
            "Catch-all — define exclusion rules",
        ),
        (
            "capex",
            "measure",
            "Y",
            "Capital expenditures",
            "SUM(gl_actuals WHERE capex accounts) OR forecast assumption",
            "gl_actuals; forecast_assumptions",
            "amount;account_group;assumption",
            "",
            "",
            "partial",
            "",
        ),
        (
            "financing_to_maintain_cash_floor",
            "measure",
            "Y",
            "Financing draw if below floor",
            "MAX(0, cash_floor - projected_ending_cash_before_financing)",
            "cash_flow_bridge",
            "cash_floor;ending_cash",
            "cash_flow_bridge",
            "cash_floor",
            "complete",
            "Only non-zero when floor breached",
        ),
        (
            "ending_cash",
            "measure",
            "Y",
            "Closing cash",
            "beginning_cash + collections - outflows - capex + financing",
            "cash_flow_bridge",
            "beginning_cash;collections;payroll_cash_out;commission_cash_out;vendor_cash_out_n30",
            "cash_flow_bridge",
            "beginning_cash;collections;all_outflows",
            "complete",
            "Feeds balance_sheet.cash",
        ),
        (
            "cash_floor",
            "assumption",
            "Y",
            "Minimum operating cash policy",
            "forecast_assumptions or customer config",
            "forecast_assumptions",
            "assumption;value",
            "",
            "",
            "complete",
            "",
        ),
    ]
    for col, role, calc, rule, formula, src_ds, src_cols, deps_out, deps_col, status, notes in cfb:
        add(
            output_dataset=ds,
            output_filename_pattern=fn,
            output_column=col,
            column_role=role,
            grain="period",
            is_calculated=calc,
            calculation_rule=rule,
            formula=formula,
            source_layer="mixed",
            source_datasets=src_ds,
            source_columns=src_cols,
            depends_on_calculated_outputs=deps_out,
            depends_on_calculated_columns=deps_col,
            board_reporting_uses="Cash Forecast tab; 3-Statement cash tie",
            prototype_upload_table=tbl,
            target_calc_engine="FIE-003",
            coverage_status=status,
            gap_or_risk_notes=notes,
        )

    # --- Deferred Revenue Waterfall ---
    ds = "deferred_revenue_waterfall"
    for col, role, calc, rule, formula, src_ds, src_cols, deps_out, deps_col, status, notes in [
        ("period", "key", "N", "", "", "", "", "", "", "complete", ""),
        (
            "beginning_deferred",
            "measure",
            "Y",
            "Opening deferred revenue",
            "prior_period.ending_deferred",
            "deferred_revenue_waterfall",
            "ending_deferred",
            "deferred_revenue_waterfall",
            "prior_period.ending_deferred",
            "complete",
            "",
        ),
        (
            "billings",
            "measure",
            "Y",
            "New billings in period",
            "SUM(invoices.invoice_amount WHERE service_period in period)",
            "invoices; Billing_Invoice_Register",
            "invoice_amount;invoice_date;service_period_start;service_period_end",
            "",
            "",
            "complete",
            "",
        ),
        (
            "revenue_recognized",
            "measure",
            "Y",
            "GAAP revenue recognized",
            "SUM(gl_actuals revenue) OR subscription ratable schedule",
            "gl_actuals; subscriptions; invoices",
            "amount;current_arr;service_period_start",
            "income_statement",
            "revenue",
            "partial",
            "Rev rec policy (ratable vs milestone) not codified",
        ),
        (
            "ending_deferred",
            "measure",
            "Y",
            "Closing deferred revenue",
            "beginning_deferred + billings - revenue_recognized",
            "deferred_revenue_waterfall",
            "beginning_deferred;billings;revenue_recognized",
            "deferred_revenue_waterfall",
            "beginning_deferred;billings;revenue_recognized",
            "complete",
            "Feeds balance_sheet.deferred_revenue",
        ),
    ]:
        add(
            output_dataset=ds,
            output_filename_pattern="{Version}_DeferredRevenueWaterfall.csv",
            output_column=col,
            column_role=role,
            grain="period",
            is_calculated=calc,
            calculation_rule=rule,
            formula=formula,
            source_layer="mixed",
            source_datasets=src_ds,
            source_columns=src_cols,
            depends_on_calculated_outputs=deps_out,
            depends_on_calculated_columns=deps_col,
            board_reporting_uses="3-Statement; Revenue & ARR",
            prototype_upload_table="{version}_deferred_revenue_waterfall",
            target_calc_engine="FIE-003",
            coverage_status=status,
            gap_or_risk_notes=notes,
        )

    # --- Headcount Plan ---
    ds = "headcount_plan"
    for col, role, calc, rule, formula, src_ds, src_cols, status, notes in [
        ("period", "key", "N", "", "", "", "", "complete", ""),
        ("department", "key", "N", "", "", "", "", "complete", ""),
        (
            "headcount_beginning",
            "measure",
            "Y",
            "Opening headcount",
            "prior_period.headcount_ending for same department",
            "headcount_plan; workforce_employees",
            "headcount_ending;employment_status",
            "partial",
            "Known gap: actual HC file is month-start not month-end",
        ),
        (
            "new_hires",
            "measure",
            "Y",
            "Hires in period",
            "COUNT(workforce_employees WHERE hire_date in period)",
            "workforce_employees; HRIS_Employee_Roster",
            "hire_date;employment_status",
            "complete",
            "",
        ),
        (
            "attrition",
            "measure",
            "Y",
            "Departures in period",
            "COUNT(workforce_employees WHERE termination_date in period)",
            "workforce_employees",
            "termination_date;employment_status",
            "complete",
            "",
        ),
        (
            "headcount_ending",
            "measure",
            "Y",
            "Closing headcount",
            "headcount_beginning + new_hires - attrition",
            "headcount_plan",
            "headcount_beginning;new_hires;attrition",
            "complete",
            "",
        ),
        (
            "monthly_payroll_cost",
            "measure",
            "Y",
            "Monthly payroll cash cost",
            "SUM(workforce fully_loaded_cash_cost) for active employees in department",
            "workforce_employees; workforce_compensation_bands",
            "fully_loaded_cash_cost;base_salary;department",
            "partial",
            "",
        ),
        (
            "total_people_cost",
            "measure",
            "Y",
            "Fully loaded people cost incl taxes/benefits",
            "monthly_payroll_cost * (1 + payroll_tax_rate + benefits_rate)",
            "headcount_plan",
            "monthly_payroll_cost;payroll_tax_rate;benefits_rate",
            "complete",
            "",
        ),
        (
            "quota_capacity",
            "measure",
            "Y",
            "Sales quota capacity",
            "SUM(annual_quota_arr) for quota_carrying reps in period",
            "workforce_employees; forecast_quota_capacity",
            "quota_carrying;annual_quota_arr",
            "partial",
            "",
        ),
    ]:
        add(
            output_dataset=ds,
            output_filename_pattern="{Version}_Headcount_Plan.csv",
            output_column=col,
            column_role=role,
            grain="period+department",
            is_calculated=calc,
            calculation_rule=rule,
            formula=formula,
            source_layer="mixed",
            source_datasets=src_ds,
            source_columns=src_cols,
            depends_on_calculated_outputs="headcount_plan" if col not in {"period", "department"} else "",
            depends_on_calculated_columns="",
            board_reporting_uses="Workforce tab; Cash bridge payroll",
            prototype_upload_table="{version}_headcount_plan",
            target_calc_engine="FIE-003",
            coverage_status=status,
            gap_or_risk_notes=notes,
        )

    # --- Marketing Pipeline (sample grain) ---
    ds = "marketing_pipeline"
    mp = [
        ("period", "key", "N", "", "", "", "", "complete", ""),
        ("marketing_channel", "key", "N", "", "", "", "", "complete", ""),
        (
            "marketing_spend",
            "measure",
            "Y",
            "Channel spend",
            "SUM(gl_actuals marketing accounts) OR external ad export",
            "gl_actuals",
            "amount;department;marketing_channel",
            "partial",
            "No dedicated ad platform source template",
        ),
        (
            "mqls",
            "measure",
            "Y",
            "Marketing qualified leads",
            "COUNT/aggregate from CRM/marketing system",
            "CRM_Pipeline_Export",
            "stage;marketing_channel",
            "gap",
            "MQL definition not in CRM export template",
        ),
        (
            "sqls",
            "measure",
            "Y",
            "Sales qualified leads",
            "COUNT CRM leads at SQL stage",
            "CRM_Pipeline_Export",
            "stage",
            "gap",
            "",
        ),
        (
            "pipeline_arr_created",
            "measure",
            "Y",
            "Pipeline ARR created",
            "SUM(opportunity amount_arr created in period)",
            "opportunities; CRM_Opportunity_Export",
            "amount_arr;created_date",
            "complete",
            "",
        ),
        (
            "closed_won_arr",
            "measure",
            "Y",
            "Closed won ARR",
            "SUM(opportunity_movements.arr_impact WHERE close_status=Closed Won)",
            "opportunity_movements",
            "arr_impact;close_status",
            "complete",
            "",
        ),
        (
            "cost_per_mql",
            "rate",
            "Y",
            "Cost per MQL",
            "marketing_spend / mqls",
            "marketing_pipeline",
            "marketing_spend;mqls",
            "partial",
            "Depends on mqls gap",
        ),
    ]
    for col, role, calc, rule, formula, src_ds, src_cols, status, notes in mp:
        add(
            output_dataset=ds,
            output_filename_pattern="{Version}_MarketingPipeline.csv",
            output_column=col,
            column_role=role,
            grain="period+marketing_channel",
            is_calculated=calc,
            calculation_rule=rule,
            formula=formula,
            source_layer="mixed",
            source_datasets=src_ds,
            source_columns=src_cols,
            depends_on_calculated_outputs="marketing_pipeline" if col == "cost_per_mql" else "",
            depends_on_calculated_columns="marketing_spend;mqls" if col == "cost_per_mql" else "",
            board_reporting_uses="GTM/Marketing tab",
            prototype_upload_table="{version}_marketing_pipeline",
            target_calc_engine="FIE-003",
            coverage_status=status,
            gap_or_risk_notes=notes,
        )

    return r


def dataset_dependencies(rows: list[LineageRow]) -> list[dict[str, str]]:
    by_ds: dict[str, set[str]] = {}
    calc_cols: dict[str, set[str]] = {}
    gaps: dict[str, set[str]] = {}
    for row in rows:
        by_ds.setdefault(row.output_dataset, set())
        calc_cols.setdefault(row.output_dataset, set())
        gaps.setdefault(row.output_dataset, set())
        if row.is_calculated == "Y":
            calc_cols[row.output_dataset].add(row.output_column)
        if row.coverage_status in {"gap", "partial"}:
            gaps[row.output_dataset].add(row.output_column)
        for src in filter(None, row.source_datasets.split(";")):
            src = src.strip()
            if src and src != row.output_dataset:
                by_ds[row.output_dataset].add(src)
        for dep in filter(None, row.depends_on_calculated_outputs.split(";")):
            dep = dep.strip()
            if dep and dep != row.output_dataset:
                by_ds[row.output_dataset].add(dep)

    out: list[dict[str, str]] = []
    for ds in sorted(by_ds):
        out.append(
            {
                "output_dataset": ds,
                "output_filename_pattern": next(
                    (r.output_filename_pattern for r in rows if r.output_dataset == ds),
                    "",
                ),
                "direct_source_datasets": "; ".join(sorted(by_ds[ds])),
                "calculated_column_count": str(len(calc_cols.get(ds, set()))),
                "columns_with_gaps": "; ".join(sorted(gaps.get(ds, set()))),
                "gap_count": str(len(gaps.get(ds, set()))),
            }
        )
    return out


def source_coverage_audit(rows: list[LineageRow]) -> list[dict[str, str]]:
    """Sources referenced by lineage but without a defined downstream calc."""
    referenced: set[str] = set()
    for row in rows:
        for src in row.source_datasets.split(";"):
            s = src.strip()
            if s:
                referenced.add(s)
    # Known source-only templates from generate_templates.py
    source_only = {
        "Billing_Subscription_Export",
        "Billing_Invoice_Register",
        "Billing_Customer_Export",
        "CRM_Opportunity_Export",
        "CRM_Account_Export",
        "CRM_Pipeline_Export",
        "ERP_GL_Detail_Export",
        "ERP_Chart_of_Accounts_Export",
        "HRIS_Employee_Roster",
        "HRIS_Compensation_Export",
        "gl_actuals",
        "invoices",
        "payments",
        "subscriptions",
        "customers",
        "opportunities",
        "vendor_contracts",
        "commission_plans",
        "forecast_assumptions",
        "workforce_employees",
        "workforce_compensation_bands",
    }
    audit: list[dict[str, str]] = []
    for src in sorted(referenced | source_only):
        consumers = sorted({r.output_dataset for r in rows if src in r.source_datasets})
        audit.append(
            {
                "source_dataset": src,
                "consumed_by_outputs": "; ".join(consumers) if consumers else "",
                "has_downstream_calc": "Y" if consumers else "N",
                "status": "connected" if consumers else "orphan",
            }
        )
    return audit


def write_csv(path: Path, fieldnames: list[str], data: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def main() -> None:
    rows = _rows()
    registry = [asdict(r) for r in rows]
    gaps = [r for r in registry if r["coverage_status"] in {"gap", "partial"}]
    deps = dataset_dependencies(rows)
    source_audit = source_coverage_audit(rows)

    write_csv(ROOT / "Calculation_Lineage_Registry.csv", REGISTRY_COLUMNS, registry)
    write_csv(ROOT / "Calculation_Lineage_Gaps.csv", REGISTRY_COLUMNS, gaps)
    write_csv(
        ROOT / "Calculation_Dataset_Dependencies.csv",
        list(deps[0].keys()) if deps else [],
        deps,
    )
    write_csv(
        ROOT / "Calculation_Source_Coverage_Audit.csv",
        list(source_audit[0].keys()) if source_audit else [],
        source_audit,
    )

    manifest = {
        "version": "1.0",
        "description": "SMPL calculated output lineage — trace each column to sources and gaps",
        "generated_from": "backend/templates/csv/calculation_lineage.py",
        "summary": {
            "total_lineage_rows": len(registry),
            "calculated_columns": sum(1 for r in registry if r["is_calculated"] == "Y"),
            "gap_rows": sum(1 for r in registry if r["coverage_status"] == "gap"),
            "partial_rows": sum(1 for r in registry if r["coverage_status"] == "partial"),
            "output_datasets_documented": len(deps),
        },
        "coverage_by_dataset": deps,
        "source_audit": source_audit,
        "lineage": registry,
    }
    (ROOT / "calculation_lineage_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote exportable lineage files under:")
    print(f"  {ROOT}")
    print(f"  Calculation_Lineage_Registry.csv      ({len(registry)} rows)  <- open in Excel")
    print(f"  Calculation_Lineage_Gaps.csv          ({len(gaps)} rows)")
    print(f"  Calculation_Dataset_Dependencies.csv  ({len(deps)} datasets)")
    print(f"  Calculation_Source_Coverage_Audit.csv ({len(source_audit)} sources)")
    print(f"  calculation_lineage_manifest.json")


if __name__ == "__main__":
    main()
