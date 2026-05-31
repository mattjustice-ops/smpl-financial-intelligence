"""Line-item mappings for normalized financial statement reporting."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LineMapping:
    source_column: str
    line_item: str
    line_item_order: int
    section: str


INCOME_STATEMENT_LINES: list[LineMapping] = [
    LineMapping("revenue", "Revenue", 100, "Revenue"),
    LineMapping("cost_of_revenue", "Cost of Revenue", 200, "Gross Profit"),
    LineMapping("gross_profit", "Gross Profit", 300, "Gross Profit"),
    LineMapping("sales_and_marketing", "Sales and Marketing", 400, "Operating Expenses"),
    LineMapping("research_and_development", "Research and Development", 500, "Operating Expenses"),
    LineMapping("general_and_administrative", "General and Administrative", 600, "Operating Expenses"),
    LineMapping("total_operating_expenses", "Total Operating Expenses", 700, "Operating Expenses"),
    LineMapping("ebitda", "EBITDA", 800, "Profitability"),
    LineMapping("depreciation_and_amortization", "Depreciation and Amortization", 900, "Profitability"),
    LineMapping("operating_income", "Operating Income", 1000, "Profitability"),
    LineMapping("interest_expense", "Interest Expense", 1100, "Other Income / Expense"),
    LineMapping("tax_expense", "Tax Expense", 1200, "Other Income / Expense"),
    LineMapping("net_income", "Net Income", 1300, "Net Income"),
]


BALANCE_SHEET_LINES: list[LineMapping] = [
    LineMapping("cash", "Cash", 100, "Assets"),
    LineMapping("accounts_receivable", "Accounts Receivable", 200, "Assets"),
    LineMapping("prepaids_and_other_current_assets", "Prepaids and Other Current Assets", 300, "Assets"),
    LineMapping("property_and_equipment_net", "Property and Equipment, Net", 400, "Assets"),
    LineMapping("total_assets", "Total Assets", 500, "Assets"),
    LineMapping("accounts_payable", "Accounts Payable", 600, "Liabilities"),
    LineMapping("deferred_revenue", "Deferred Revenue", 700, "Liabilities"),
    LineMapping("debt", "Debt", 800, "Liabilities"),
    LineMapping("total_liabilities", "Total Liabilities", 900, "Liabilities"),
    LineMapping("equity", "Equity", 1000, "Equity"),
    LineMapping("total_liabilities_and_equity", "Total Liabilities and Equity", 1100, "Equity"),
    LineMapping("balance_check", "Balance Check", 1200, "Checks"),
]


CASH_FLOW_LINES: list[LineMapping] = [
    LineMapping("beginning_cash", "Beginning Cash Balance", 100, "Beginning Cash"),
    LineMapping("net_income", "Net Income", 200, "Operating Activities"),
    LineMapping("depreciation_and_amortization", "Depreciation and Amortization", 300, "Operating Activities"),
    LineMapping("stock_based_compensation", "Stock-Based Compensation", 400, "Operating Activities"),
    LineMapping("change_in_accounts_receivable", "Change in Accounts Receivable", 500, "Operating Activities"),
    LineMapping("change_in_deferred_revenue", "Change in Deferred Revenue", 600, "Operating Activities"),
    LineMapping("change_in_accounts_payable", "Change in Accounts Payable", 700, "Operating Activities"),
    LineMapping("change_in_prepaids", "Change in Prepaids", 800, "Operating Activities"),
    LineMapping("net_cash_from_operating_activities", "Net Cash Provided by Operating Activities", 900, "Operating Activities"),
    LineMapping("capital_expenditures", "Capital Expenditures", 1000, "Investing Activities"),
    LineMapping("net_cash_from_investing_activities", "Net Cash Used in Investing Activities", 1100, "Investing Activities"),
    LineMapping("debt_issuance_repayment", "Debt Issuance / Repayment", 1200, "Financing Activities"),
    LineMapping("net_cash_from_financing_activities", "Net Cash Provided by Financing Activities", 1300, "Financing Activities"),
    LineMapping("net_change_in_cash", "Net Change in Cash", 1400, "Net Change in Cash"),
    LineMapping("ending_cash", "Ending Cash Balance", 1500, "Ending Cash"),
]


STATEMENT_CONFIG = {
    "income_statement": {
        "table_suffix": "income_statement",
        "lines": INCOME_STATEMENT_LINES,
    },
    "balance_sheet": {
        "table_suffix": "balance_sheet",
        "lines": BALANCE_SHEET_LINES,
    },
    "cash_flow": {
        "table_suffix": "cash_flow_statement",
        "lines": CASH_FLOW_LINES,
    },
}


def table_name_for(scenario: str, table_suffix: str) -> str:
    return f"{scenario.lower()}_{table_suffix}"
