"""Module Capability Registry (MCR) and onboarding questionnaire catalog for the Readiness Score.

Module definitions follow SKA Section 8.2.3 (Tier 1 MCR) plus the Management P&L, which SMPL
reports alongside the Income Statement. Assessment logic lives in ``engine.py`` (CAL.4–CAL.7);
this module only declares what each module needs.

Module weights are SMPL defaults — SOF Section 7.2 defines the formula but not the weights.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CONNECTOR_TYPES: dict[str, str] = {
    "ERP": "ERP / general ledger (NetSuite, QuickBooks Online, Sage Intacct)",
    "BUDGET": "Budget / forecast upload or FP&A tool",
    "BILLING": "Billing (Stripe, Chargebee, Recurly, Zuora)",
    "CRM": "CRM (Salesforce, HubSpot)",
    "MARKETING": "Marketing automation (HubSpot, Marketo)",
    "HRIS": "HRIS / payroll (Rippling, Workday, BambooHR + Gusto)",
    "CS": "Customer success tool (Gainsight, ChurnZero)",
    "COMP": "Commission / comp tool (CaptivateIQ, Spiff, Xactly) or payroll export",
}

VERSIONS: tuple[str, ...] = ("Actual", "Budget", "Forecast")


@dataclass(frozen=True)
class SourceFile:
    """One upload file: ``{Version}_{base}.csv`` for each version, or ``{base}.csv`` when versions is empty."""

    base: str
    versions: tuple[str, ...] = VERSIONS


def files(*bases: str, versions: tuple[str, ...] = VERSIONS) -> tuple[SourceFile, ...]:
    return tuple(SourceFile(b, versions) for b in bases)


@dataclass(frozen=True)
class CanonicalObject:
    id: str
    name: str
    connector: str
    # Warehouse tables that can supply the object; any populated table satisfies presence.
    tables: tuple[str, ...]
    # Reporting window used to score period coverage: "actual" (FY start → close month),
    # "budget" (full FY), "forecast" (after close month → FY end), or None (presence only).
    period_scope: str | None = None
    # Upload manifest (manifest.py): the files that supply the object, the load tier (dimensions
    # before ledgers, ledgers before subledgers, schedules last) and the questionnaire question
    # that says whether the customer has it.
    files: tuple[SourceFile, ...] = ()
    tier: int = 0
    question: str | None = None


A, B, F = ("Actual",), ("Budget",), ("Forecast",)
SHARED: tuple[str, ...] = ()

# Load tiers for the upload manifest.
DIMENSION, LEDGER, SUBLEDGER, OPERATIONAL, SCHEDULE, STATEMENT = 1, 2, 3, 4, 5, 6

OBJECTS: dict[str, CanonicalObject] = {
    o.id: o
    for o in (
        CanonicalObject("gl_account", "GL Account", "ERP", ("actual_chart_of_accounts",),
                        files=files("chart_of_accounts"), tier=DIMENSION),
        CanonicalObject("journal_entry", "Journal Entry (GL activity)", "ERP", ("gl_actuals#Actual", "actual_gl_detail"), "actual",
                        files=files("gl_detail", versions=A), tier=LEDGER),
        CanonicalObject("income_statement", "Income Statement", "ERP", ("gl_actuals#Actual",), "actual",
                        files=files("income_statement"), tier=STATEMENT),
        CanonicalObject("balance_sheet", "Balance Sheet", "ERP", ("gl_actuals#Actual",), "actual",
                        files=files("balance_sheet"), tier=STATEMENT),
        CanonicalObject("cash_flow_statement", "Cash Flow Statement", "ERP", ("gl_actuals#Actual",), "actual",
                        files=files("cash_flow_statement", "cash_flow_bridge"), tier=STATEMENT),
        CanonicalObject("cash_position", "Cash Position", "ERP", ("gl_actuals#Actual",), "actual"),
        CanonicalObject("legal_entity", "Legal Entity", "ERP", ("@organization",)),
        CanonicalObject("department", "Department / Cost Center", "ERP", ("actual_department_cost_centers",),
                        files=files("department_cost_centers"), tier=DIMENSION),
        CanonicalObject("vendor", "Vendor", "ERP", ("actual_vendor_master",),
                        files=files("vendor_master", versions=A), tier=DIMENSION, question="7.33"),
        CanonicalObject("vendor_bill", "Vendor Bill (AP subledger)", "ERP", ("actual_vendor_bills",),
                        files=files("vendor_bills", versions=A), tier=SUBLEDGER, question="7.33"),
        CanonicalObject("vendor_payment", "Vendor Payment", "ERP", ("actual_vendor_payments",),
                        files=files("vendor_payments", versions=A), tier=SUBLEDGER, question="7.33"),
        CanonicalObject("ap_aging", "AP Aging", "ERP", ("actual_ap_aging",),
                        files=files("AP_Aging", versions=A), tier=SCHEDULE, question="7.33"),
        CanonicalObject("ap_rollforward", "AP Rollforward", "ERP", ("actual_accounts_payable_rollforward",), "actual",
                        files=files("accounts_payable_rollforward"), tier=SCHEDULE),
        CanonicalObject("ar_rollforward", "AR Rollforward", "ERP", ("actual_accounts_receivable_rollforward",), "actual",
                        files=files("accounts_receivable_rollforward"), tier=SCHEDULE),
        CanonicalObject("allowance_for_doubtful_accounts", "Allowance for Doubtful Accounts (reserve and write-offs)",
                        "ERP", ("actual_allowance_for_doubtful_accounts",), "actual",
                        files=files("allowance_for_doubtful_accounts"), tier=SCHEDULE, question="7.35"),
        CanonicalObject("prepaid_schedule", "Prepaid Schedule", "ERP", ("actual_prepaids_rollforward",),
                        files=files("Prepaids_Rollforward", "Prepaid_Amortization_Schedule"), tier=SCHEDULE,
                        question="7.35"),
        CanonicalObject("accrued_expenses", "Accrued Expenses (services received, not yet billed)", "ERP",
                        ("actual_accrued_expenses_rollforward",), "actual",
                        files=(*files("accrued_expenses_rollforward"), *files("accrued_expenses_detail", versions=A)),
                        tier=SCHEDULE, question="7.35"),
        CanonicalObject("lease_schedule", "Operating Lease Schedule (ASC 842)", "ERP",
                        ("actual_operating_lease_schedule",), files=files("operating_lease_schedule"), tier=SCHEDULE,
                        question="7.35"),
        CanonicalObject("fixed_asset", "Fixed Asset Register", "ERP", ("actual_fixed_asset_register",),
                        files=files("fixed_asset_register", versions=A), tier=SUBLEDGER, question="7.35"),
        CanonicalObject("debt_schedule", "Debt Schedule", "ERP", ("actual_debt_schedule",),
                        files=files("debt_schedule", versions=A), tier=SUBLEDGER, question="7.35"),
        CanonicalObject("budget_scenario", "Scenario — Budget", "BUDGET", ("gl_actuals#Budget",), "budget"),
        CanonicalObject("budget_line", "Budget Line", "BUDGET", ("gl_actuals#Budget", "budget_gl_detail"), "budget",
                        files=files("gl_detail", versions=B), tier=LEDGER),
        CanonicalObject("vendor_spend_plan", "Vendor Spend Plan", "BUDGET",
                        ("budget_vendor_spend_plan", "forecast_vendor_spend_plan"),
                        files=files("vendor_spend_plan", versions=B + F), tier=OPERATIONAL),
        CanonicalObject("forecast_scenario", "Scenario — Forecast", "BUDGET", ("gl_actuals#Forecast",), "forecast"),
        CanonicalObject("forecast_line", "Forecast Line", "BUDGET", ("gl_actuals#Forecast", "forecast_gl_detail"), "forecast",
                        files=files("gl_detail", versions=F), tier=LEDGER),
        CanonicalObject("assumption_driver", "Assumption Driver", "BUDGET", ("forecast_assumptions", "forecast_driver_assumptions"),
                        files=(*files("assumptions", "working_capital_metrics", versions=F),
                               *files("cash_flow_driver_assumptions", "Working_Capital_Driver_Summary")),
                        tier=SCHEDULE),
        CanonicalObject("headcount_plan", "Headcount Plan", "BUDGET", ("actual_headcount_plan",),
                        files=files("Headcount_Plan"), tier=SCHEDULE),
        CanonicalObject("hiring_plan_input", "Hiring Plan Inputs (comp bands, ramp, allocations)", "BUDGET",
                        ("workforce_compensation_bands", "workforce_hiring_ramp_assumptions",
                         "workforce_department_allocation_rules"),
                        files=files("Compensation_Bands", "Hiring_Ramp_Assumptions", "Department_Allocation_Rules",
                                    versions=SHARED), tier=OPERATIONAL),
        CanonicalObject("customer", "Customer", "BILLING", ("actual_customers",),
                        files=files("customers"), tier=SUBLEDGER),
        CanonicalObject("subscription", "Subscription", "BILLING", ("actual_invoice_billing_schedule", "actual_revenue_recognition"),
                        files=files("invoice_billing_schedule", "revenue_recognition"), tier=SUBLEDGER),
        CanonicalObject("arr_movement", "ARR Movement", "BILLING", ("actual_mrr_waterfall",), "actual",
                        files=files("customer_arr_history"), tier=SUBLEDGER),
        CanonicalObject("arr_waterfall", "ARR Waterfall", "BILLING", ("actual_mrr_waterfall",), "actual",
                        files=files("MRR_Waterfall"), tier=SCHEDULE),
        CanonicalObject("invoice", "Invoice", "BILLING", ("actual_invoices",),
                        files=files("invoices"), tier=SUBLEDGER),
        CanonicalObject("payment", "Payment", "BILLING", ("actual_cash_collections",), "actual",
                        files=files("cash_collections"), tier=SUBLEDGER),
        CanonicalObject("customer_payment", "Customer Payment (applied to invoices)", "BILLING",
                        ("actual_customer_payments",), "actual",
                        files=files("customer_payments", versions=A), tier=SUBLEDGER, question="7.37"),
        CanonicalObject("ar_aging", "AR Aging", "BILLING", ("actual_ar_aging",),
                        files=files("AR_Aging", versions=A), tier=SCHEDULE, question="7.37"),
        CanonicalObject("collections_case", "Collections Cases and Dunning Log", "BILLING",
                        ("actual_collections_cases", "actual_collections_activity"),
                        files=files("collections_cases", "collections_activity", versions=A), tier=OPERATIONAL,
                        question="7.38"),
        CanonicalObject("revenue_schedule", "Revenue Schedule", "BILLING", ("actual_revenue_recognition",),
                        files=files("revenue_schedule", versions=F), tier=SCHEDULE),
        CanonicalObject("services_schedule", "Implementation / Services Schedule", "BILLING",
                        ("actual_implementation_schedule", "actual_recurring_services_schedule"),
                        files=files("implementation_schedule", "recurring_services_schedule"), tier=SUBLEDGER),
        CanonicalObject("deferred_revenue", "Deferred Revenue Waterfall", "BILLING", ("actual_deferred_revenue_waterfall",), "actual",
                        files=files("deferred_revenue_waterfall"), tier=SCHEDULE),
        CanonicalObject("opportunity", "Opportunity", "CRM", ("actual_opportunities",),
                        files=files("opportunities", "opportunity_movements"), tier=OPERATIONAL),
        CanonicalObject("renewal_pipeline", "Renewal Pipeline", "CRM", ("actual_renewal_pipeline",),
                        files=files("renewal_pipeline", versions=A + F), tier=OPERATIONAL),
        CanonicalObject("pipeline_waterfall", "Pipeline Waterfall and Bookings", "CRM", ("actual_pipeline_waterfall",),
                        files=(*files("pipeline_waterfall"), *files("bookings_summary", versions=B + F)), tier=SCHEDULE),
        CanonicalObject("sales_quota", "Sales Reps and Quotas", "CRM", ("actual_sales_quotas", "actual_sales_reps"),
                        files=(*files("sales_reps"), *files("Sales_Quotas", versions=A + B),
                               *files("quota_capacity", versions=F)), tier=SUBLEDGER),
        CanonicalObject("campaign", "Campaign / Channel", "MARKETING", ("actual_marketing_spend_by_channel",), "actual",
                        files=files("marketing_spend_by_channel", versions=A), tier=OPERATIONAL),
        CanonicalObject("mql", "MQL", "MARKETING", ("actual_marketing_pipeline",), "actual",
                        files=(*files("marketing_pipeline"), *files("funnel_conversion_rates", versions=A),
                               *files("marketing_pipeline_summary", versions=F)), tier=OPERATIONAL),
        CanonicalObject("employee", "Employee", "HRIS", ("actual_employees", "workforce_employees"),
                        files=files("Employees"), tier=DIMENSION, question="7.32"),
        CanonicalObject("payroll_policy", "Payroll Policy (tax, benefits, 401(k), bonus timing)", "HRIS",
                        ("actual_payroll_policies",), files=files("payroll_policies"), tier=DIMENSION, question="7.31"),
        CanonicalObject("payroll_line", "Payroll Line", "HRIS",
                        ("actual_payroll_register", "actual_headcount_plan", "workforce_period_summary"),
                        files=files("payroll_register"), tier=SUBLEDGER, question="7.30"),
        CanonicalObject("open_requisition", "Open Requisition", "HRIS", ("actual_open_requisitions",),
                        files=files("Open_Requisitions"), tier=OPERATIONAL),
        CanonicalObject("sbc_schedule", "Stock-Based Compensation Schedule", "HRIS", ("actual_sbc_schedule",),
                        files=files("SBC_Schedule"), tier=SCHEDULE, question="7.36"),
        CanonicalObject("commission_plan", "Commission Plan", "COMP", ("actual_commission_plans",),
                        files=files("commission_plans"), tier=DIMENSION, question="7.20"),
        CanonicalObject("commission_payout", "Commission Payout", "COMP",
                        ("actual_commission_payouts", "actual_renewal_commissions"), "actual",
                        files=files("commission_payouts", "renewal_commissions", "commission_clawbacks", versions=A),
                        tier=SUBLEDGER,
                        question="7.20"),
        CanonicalObject("commission_schedule", "Commission Schedule (capitalized / expensed)", "COMP",
                        ("actual_commission_schedule",), "actual",
                        files=files("commission_schedule"), tier=SCHEDULE, question="7.14"),
        CanonicalObject("deferred_commission", "Deferred Commissions Rollforward (ASC 340-40)", "COMP",
                        ("actual_deferred_commissions_rollforward",), "actual",
                        files=files("deferred_commissions_rollforward"), tier=SCHEDULE, question="7.14"),
        CanonicalObject("health_score", "Health Score", "CS", ()),
    )
}


@dataclass(frozen=True)
class Module:
    id: str
    name: str
    required_objects: tuple[str, ...]
    ready_threshold: float
    weight: float
    partial_threshold: float = 0.30
    # Normalization gates that must be resolved before the module can be READY.
    gates: tuple[str, ...] = ()
    # Score inputs (questionnaire 7.7–7.13) that limit this module when answered "no".
    policy_inputs: tuple[str, ...] = ()


MODULES: tuple[Module, ...] = (
    Module("financial_statements", "Financial Statements (P&L, Balance Sheet, Cash Flow)",
           ("gl_account", "journal_entry", "income_statement", "balance_sheet", "cash_flow_statement",
            "legal_entity", "department", "budget_scenario"), 0.92, 3),
    Module("management_pl", "Management P&L",
           ("gl_account", "journal_entry", "income_statement", "department"), 0.90, 2,
           policy_inputs=("7.7", "7.8", "7.9")),
    Module("budget_vs_actual", "Budget vs Actual Variance",
           ("gl_account", "journal_entry", "budget_line", "budget_scenario", "department"), 0.90, 3,
           policy_inputs=("7.10", "7.11", "7.12")),
    Module("board_reporting", "Board Reporting",
           ("income_statement", "balance_sheet", "cash_flow_statement", "arr_waterfall", "opportunity",
            "cash_position", "employee"), 0.85, 2,
           gates=("subscription", "crm_stage", "commission_policy"), policy_inputs=("7.13",)),
    Module("executive_dashboards", "Executive Dashboards",
           ("arr_waterfall", "income_statement", "cash_position", "employee"), 0.88, 2,
           gates=("subscription",)),
    Module("arr_analytics", "ARR Analytics",
           ("customer", "subscription", "arr_movement", "arr_waterfall", "budget_scenario"), 0.90, 2,
           partial_threshold=0.65, gates=("subscription",)),
    Module("cash_forecasting", "Cash Forecasting",
           ("cash_position", "payment", "invoice", "payroll_line"), 0.88, 2,
           gates=("commission_policy",)),
    Module("executive_briefings", "Executive Briefings",
           ("arr_waterfall", "income_statement", "cash_position", "employee"), 0.82, 1,
           gates=("subscription",), policy_inputs=("7.10",)),
    Module("variance_analysis", "Variance Analysis",
           ("gl_account", "journal_entry", "budget_line", "budget_scenario", "department", "arr_waterfall"), 0.88, 1,
           gates=("subscription",), policy_inputs=("7.10", "7.11", "7.12")),
    Module("workforce_planning", "Workforce Planning",
           ("employee", "department", "payroll_line", "budget_line", "budget_scenario"), 0.82, 1),
    Module("revenue_forecasting", "Revenue Forecasting",
           ("opportunity", "arr_waterfall", "revenue_schedule", "subscription", "forecast_scenario"), 0.80, 1,
           gates=("subscription", "crm_stage")),
    Module("pipeline_forecasting", "Pipeline Forecasting",
           ("opportunity", "customer", "arr_movement", "forecast_scenario"), 0.80, 1,
           gates=("crm_stage",)),
    Module("renewal_analytics", "Renewal Analytics",
           ("subscription", "customer", "health_score", "arr_movement", "opportunity"), 0.78, 1,
           gates=("subscription",)),
    Module("gtm_analytics", "GTM Analytics",
           ("opportunity", "campaign", "mql", "customer", "department"), 0.76, 1,
           gates=("crm_stage",)),
    Module("scenario_planning", "Scenario Planning",
           ("budget_scenario", "forecast_scenario", "budget_line", "forecast_line", "assumption_driver"), 0.75, 1,
           gates=("commission_policy",)),
)

MODULES_BY_ID: dict[str, Module] = {m.id: m for m in MODULES}


# ── Questionnaire catalog (docs/onboarding/Customer_Onboarding_Discovery_Call_Sheet.md) ──

YES_NO = ("yes", "no")


@dataclass(frozen=True)
class Question:
    id: str
    section: str
    prompt: str
    choices: tuple[str, ...] = YES_NO
    # Score inputs only: effect when answered "no".
    effect: str | None = None  # "cap_partial" | "confidence_penalty"
    penalty: float = 1.0
    consequence: str = ""
    customer_action: str = ""


READINESS_GATES: tuple[Question, ...] = (
    Question("0.1", "gate", "Books kept on an accrual basis (not cash or tax basis)"),
    Question("0.2", "gate", "One named book of record (GAAP books) with a named owner"),
    Question("0.3", "gate", "Books closed monthly with a named close owner and target close day"),
    Question("0.4", "gate", "Finance lead can walk through last month's income statement and explain material lines"),
    Question("0.5", "gate", "Customer accepts the data-ownership terms"),
)

SUBSCRIPTION_GATE: tuple[Question, ...] = (
    Question("4.1", "subscription", "Trialing subscriptions in ARR", ("include", "exclude")),
    Question("4.2", "subscription", "Past-due / unpaid subscriptions in ARR", ("include", "exclude")),
    Question("4.3", "subscription", "Usage-based ARR policy",
             ("not_applicable", "committed_minimums_only", "committed_and_overages")),
)

# The ARR engine reads these to label returning customers. No module is gated on them yet;
# unanswered, every return stays Reactivation with an unknown return type.
CUSTOMER_RETURNS: tuple[Question, ...] = (
    Question("4.10", "customer_returns",
             "Winback window: a customer who ended their contract and returns within this many months is a "
             "winback (Reactivation); a later return is new business",
             ("3", "6", "12", "no_window")),
    Question("4.11", "customer_returns", "Paused subscriptions in ARR",
             ("removes_arr", "keeps_arr", "not_offered")),
)

CRM_STAGE_GATE: tuple[Question, ...] = (
    Question("9.1", "crm_stage", "CRM stage normalization (ambiguous stages mapped)",
             ("resolved", "not_applicable", "unresolved")),
)

AMORTIZATION_MONTHS = ("12", "24", "36", "48", "60", "72", "84", "not_applicable")
# Customer returns: on ARR above the customer's ARR before leaving, on all returned ARR, or none.
RETURN_COMMISSION = ("above_prior_arr", "full_amount", "not_paid")

# ASC 340-40: the engines read this policy (they never let a user change it) and the
# readiness checks compare it with the GL.
COMMISSION_POLICY_GATE: tuple[Question, ...] = (
    Question("7.14", "commission_policy",
             "Sales commissions on new and expansion contracts (incremental costs of obtaining a contract)",
             ("capitalized", "expensed", "no_commissions", "not_sure")),
    Question("7.15", "commission_policy",
             "Amortization period for capitalized new-business commissions, in months (including expected renewals)",
             AMORTIZATION_MONTHS),
    Question("7.16", "commission_policy", "Amortization period for capitalized expansion commissions, in months",
             AMORTIZATION_MONTHS),
    Question("7.17", "commission_policy",
             "Renewal commissions (expensed under the 12-month practical expedient, or capitalized)",
             ("expensed", "capitalized", "not_paid")),
    Question("7.18", "commission_policy", "When commissions are paid",
             ("month_of_booking", "month_after_booking", "quarter_after_booking", "on_customer_payment")),
    Question("7.19", "commission_policy", "Employer payroll taxes on commissions", ("expensed", "capitalized")),
    Question("7.20", "commission_policy", "System of record for commission payouts",
             ("comp_tool", "payroll_export", "spreadsheet", "none")),
    Question("7.21", "commission_policy",
             "Commissions on winbacks (a customer who ended their contract returns within the winback window)",
             RETURN_COMMISSION),
    Question("7.22", "commission_policy", "Commissions on restarts after a pause", RETURN_COMMISSION),
    Question("7.23", "commission_policy", "Rate paid on commissionable winback and restart ARR",
             ("new_business_rate", "expansion_rate")),
    Question("7.24", "commission_policy",
             "Commissions on expansion after a contraction (only above the customer's prior level, or all of it)",
             ("above_prior_level", "all_expansion")),
)

ATTAINMENT_PCT = tuple(str(p) for p in range(50, 125, 5))

# Sales hiring and commission planning inputs; checked against the loaded quotas, opportunities, payouts
# and employees (sales_plan_inputs.py). No module is gated on them.
SALES_PLAN: tuple[Question, ...] = (
    Question("7.25", "sales_plan",
             "Expected quota attainment used to plan sales hiring, as a percent of ramped quota",
             ATTAINMENT_PCT),
    Question("7.26", "sales_plan", "What counts toward a closer's quota",
             ("new_business_arr", "new_and_expansion_arr", "net_new_arr")),
    Question("7.27", "sales_plan", "Period over which quota attainment and accelerators are measured",
             ("monthly", "quarterly", "annual")),
    Question("7.28", "sales_plan", "Who owns and is paid on expansion deals",
             ("account_executives", "account_managers", "customer_success", "not_paid")),
    Question("7.29", "sales_plan",
             "Sales variable pay in the HRIS (commission target): paid through the commission plan, or a bonus in "
             "addition to commissions",
             ("through_commission_plan", "bonus_in_addition")),
)

# Which source files and subledgers the customer can export; the upload manifest links each object to
# its question (CanonicalObject.question). No module is gated on them.
DATA_SOURCES: tuple[Question, ...] = (
    Question("7.30", "data_sources",
             "Payroll register export (Gusto, ADP, Rippling, Paylocity): by employee and pay period, by department, "
             "summary only, or none",
             ("by_employee", "by_department", "summary_only", "none")),
    Question("7.31", "data_sources",
             "Payroll policies documented: employer tax rates, benefits, 401(k) match and bonus payout timing"),
    Question("7.32", "data_sources", "HRIS export includes terminated employees with termination dates"),
    Question("7.33", "data_sources",
             "AP subledger exportable from the ERP: vendor bills (vendor, bill date, due date, amount, GL account) "
             "and bill payments"),
    Question("7.34", "data_sources", "Standard vendor payment terms",
             ("net_15", "net_30", "net_45", "net_60", "mixed")),
    Question("7.35", "data_sources",
             "Supporting schedules kept outside the GL: prepaid, accrued expense, lease (ASC 842), fixed asset, "
             "debt and allowance for doubtful accounts schedules",
             ("all", "some", "none")),
    Question("7.36", "data_sources", "Equity grant / stock-based compensation schedule (Carta, Shareworks)"),
    Question("7.37", "data_sources",
             "AR subledger exportable from billing or the ERP: customer payments applied to invoices (payment date "
             "and amount) and AR aging"),
    Question("7.38", "data_sources",
             "Collections history kept: dunning steps, service suspensions and write-offs by customer, with the "
             "reason"),
)

SCORE_INPUTS: tuple[Question, ...] = (
    Question("7.7", "score_input", "Cost of revenue policy documented and approved",
             effect="cap_partial",
             consequence="Management P&L gross margin is PARTIAL — gross margin shows only as booked",
             customer_action="Document and approve the cost of revenue policy"),
    Question("7.8", "score_input", "Payroll posted by department / cost center",
             effect="cap_partial",
             consequence="Labor can't be split between cost of revenue and OpEx; gross margin stays PARTIAL",
             customer_action="Post payroll journal entries by department"),
    Question("7.9", "score_input", "Shared-cost allocations booked as journal entries",
             effect="confidence_penalty", penalty=0.9,
             consequence="Allocations outside the GL can't be shown; costs are presented where booked",
             customer_action="Book allocations as journal entries each month"),
    Question("7.10", "score_input", "Expenses accrued monthly",
             effect="confidence_penalty", penalty=0.85,
             consequence="Monthly variances swing on timing; commentary confidence lowered",
             customer_action="Accrue expenses monthly"),
    Question("7.11", "score_input", "Accruals reverse and actuals post to the same account and department",
             effect="confidence_penalty", penalty=0.9,
             consequence="Missing or mismatched accrual legs are reported as data gaps, not narrated",
             customer_action="Reverse accruals consistently and code actuals to the same account and department"),
    Question("7.12", "score_input", "Usage-based vendors accrued on estimate and trued up",
             effect="confidence_penalty", penalty=0.9,
             consequence="True-ups show as unexplained swings until all legs are present",
             customer_action="Document the usage estimate and true-up practice"),
    Question("7.13", "score_input", "Documented treatment for year-end audit adjustments",
             effect="cap_partial",
             consequence="Board history is PARTIAL — reported periods may change without an agreed treatment",
             customer_action="Choose and document an audit-adjustment policy"),
)

ALL_QUESTIONS: dict[str, Question] = {
    q.id: q
    for q in (*READINESS_GATES, *SUBSCRIPTION_GATE, *CUSTOMER_RETURNS, *CRM_STAGE_GATE, *COMMISSION_POLICY_GATE,
              *SALES_PLAN, *DATA_SOURCES, *SCORE_INPUTS)
}

NORMALIZATION_GATES: dict[str, dict[str, object]] = {
    "subscription": {
        "name": "Subscription Normalization Gate",
        "questions": SUBSCRIPTION_GATE,
        "resolved_values": None,  # any answer resolves each question
    },
    "customer_returns": {
        "name": "Customer Returns (winbacks and restarts)",
        "questions": CUSTOMER_RETURNS,
        "resolved_values": None,
    },
    "crm_stage": {
        "name": "CRM Stage Normalization Gate",
        "questions": CRM_STAGE_GATE,
        "resolved_values": ("resolved", "not_applicable"),
    },
    "commission_policy": {
        "name": "Commission Policy Gate (ASC 340-40)",
        "questions": COMMISSION_POLICY_GATE,
        "resolved_values": None,
        "unresolved_values": ("not_sure",),
        # question → (question, answers that make it required); "not_applicable" does not resolve it then.
        "required_if": {
            "7.15": ("7.14", ("capitalized",)),
            "7.16": ("7.14", ("capitalized",)),
            "7.17": ("7.14", ("capitalized", "expensed")),
            "7.18": ("7.14", ("capitalized", "expensed")),
            "7.19": ("7.14", ("capitalized", "expensed")),
            "7.20": ("7.14", ("capitalized", "expensed")),
            "7.21": ("7.14", ("capitalized", "expensed")),
            "7.22": ("7.14", ("capitalized", "expensed")),
            "7.23": ("7.14", ("capitalized", "expensed")),
            "7.24": ("7.14", ("capitalized", "expensed")),
        },
    },
    "sales_plan": {
        "name": "Sales Quota and Comp Plan",
        "questions": SALES_PLAN,
        "resolved_values": None,
        "required_if": {
            "7.27": ("7.14", ("capitalized", "expensed")),
            "7.28": ("7.14", ("capitalized", "expensed")),
            "7.29": ("7.14", ("capitalized", "expensed")),
        },
    },
    "data_sources": {
        "name": "Data Sources and Subledgers",
        "questions": DATA_SOURCES,
        "resolved_values": None,
        "required_if": {
            "7.34": ("7.33", ("yes",)),
        },
    },
}


def catalog() -> dict[str, object]:
    """Question catalog for the questionnaire UI."""

    def q(x: Question) -> dict[str, object]:
        out: dict[str, object] = {"id": x.id, "section": x.section, "prompt": x.prompt, "choices": list(x.choices)}
        if x.effect:
            out.update(effect=x.effect, consequence=x.consequence, customer_action=x.customer_action)
        return out

    return {
        "readiness_gates": [q(x) for x in READINESS_GATES],
        "normalization_gates": [
            {"id": gid, "name": g["name"], "questions": [q(x) for x in g["questions"]]}  # type: ignore[union-attr]
            for gid, g in NORMALIZATION_GATES.items()
        ],
        "score_inputs": [q(x) for x in SCORE_INPUTS],
    }


@dataclass
class ObjectEvidence:
    present: bool
    confidence: float
    rows: int = 0
    sources: list[str] = field(default_factory=list)
    structural: bool = False
    missing_periods: list[str] = field(default_factory=list)
