"""Validation checks for normalized financial statements."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.financial_statements.financial_statement_service import (
    NormalizedStatementResponse,
    ValidationResult,
    q,
)

TOLERANCE = Decimal("1.00")


def _index(stmt: NormalizedStatementResponse) -> dict[tuple[str, date, str], Decimal]:
    return {(r.scenario, r.period, r.line_item): r.amount for r in stmt.rows}


def _result(scenario: str, period: date, name: str, expected: Decimal, actual: Decimal, sources: list[str]) -> ValidationResult:
    variance = q(actual - expected)
    status = "pass" if abs(variance) <= TOLERANCE else "fail"
    return ValidationResult(
        scenario=scenario,
        period=period,
        validation_name=name,
        status=status,
        expected_value=q(expected),
        actual_value=q(actual),
        variance=variance,
        source_tables_used=sources,
    )


def validate_financial_statements(
    income: NormalizedStatementResponse,
    balance: NormalizedStatementResponse,
    cash_flow: NormalizedStatementResponse,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    inc = _index(income)
    bs = _index(balance)
    cf = _index(cash_flow)
    keys = sorted({(r.scenario, r.period) for r in [*income.rows, *balance.rows, *cash_flow.rows]})

    for scenario, period in keys:
        sources = [f"{scenario.lower()}_income_statement"]
        gp = inc.get((scenario, period, "Revenue"), Decimal("0")) - inc.get((scenario, period, "Cost of Revenue"), Decimal("0"))
        results.append(_result(scenario, period, "income_statement_gross_profit", gp, inc.get((scenario, period, "Gross Profit"), Decimal("0")), sources))
        opex = inc.get((scenario, period, "Sales and Marketing"), Decimal("0")) + inc.get((scenario, period, "Research and Development"), Decimal("0")) + inc.get((scenario, period, "General and Administrative"), Decimal("0"))
        results.append(_result(scenario, period, "income_statement_total_opex", opex, inc.get((scenario, period, "Total Operating Expenses"), Decimal("0")), sources))
        ebitda = inc.get((scenario, period, "Gross Profit"), Decimal("0")) - inc.get((scenario, period, "Total Operating Expenses"), Decimal("0"))
        results.append(_result(scenario, period, "income_statement_ebitda", ebitda, inc.get((scenario, period, "EBITDA"), Decimal("0")), sources))
        op_income = inc.get((scenario, period, "EBITDA"), Decimal("0")) - inc.get((scenario, period, "Depreciation and Amortization"), Decimal("0"))
        results.append(_result(scenario, period, "income_statement_operating_income", op_income, inc.get((scenario, period, "Operating Income"), Decimal("0")), sources))
        net_income = inc.get((scenario, period, "Operating Income"), Decimal("0")) - inc.get((scenario, period, "Interest Expense"), Decimal("0")) - inc.get((scenario, period, "Tax Expense"), Decimal("0"))
        results.append(_result(scenario, period, "income_statement_net_income", net_income, inc.get((scenario, period, "Net Income"), Decimal("0")), sources))

        bs_sources = [f"{scenario.lower()}_balance_sheet"]
        assets = bs.get((scenario, period, "Cash"), Decimal("0")) + bs.get((scenario, period, "Accounts Receivable"), Decimal("0")) + bs.get((scenario, period, "Prepaids and Other Current Assets"), Decimal("0")) + bs.get((scenario, period, "Property and Equipment, Net"), Decimal("0"))
        results.append(_result(scenario, period, "balance_sheet_total_assets", assets, bs.get((scenario, period, "Total Assets"), Decimal("0")), bs_sources))
        liabilities = bs.get((scenario, period, "Accounts Payable"), Decimal("0")) + bs.get((scenario, period, "Deferred Revenue"), Decimal("0")) + bs.get((scenario, period, "Debt"), Decimal("0"))
        results.append(_result(scenario, period, "balance_sheet_total_liabilities", liabilities, bs.get((scenario, period, "Total Liabilities"), Decimal("0")), bs_sources))
        lie = bs.get((scenario, period, "Total Liabilities"), Decimal("0")) + bs.get((scenario, period, "Equity"), Decimal("0"))
        results.append(_result(scenario, period, "balance_sheet_liabilities_and_equity", lie, bs.get((scenario, period, "Total Liabilities and Equity"), Decimal("0")), bs_sources))
        results.append(_result(scenario, period, "balance_sheet_balances", Decimal("0"), bs.get((scenario, period, "Balance Check"), Decimal("0")), bs_sources))

        cf_sources = [f"{scenario.lower()}_cash_flow_statement", f"{scenario.lower()}_balance_sheet"]
        ocf = (
            cf.get((scenario, period, "Net Income"), Decimal("0"))
            + cf.get((scenario, period, "Depreciation and Amortization"), Decimal("0"))
            + cf.get((scenario, period, "Stock-Based Compensation"), Decimal("0"))
            + cf.get((scenario, period, "Change in Accounts Receivable"), Decimal("0"))
            + cf.get((scenario, period, "Change in Deferred Revenue"), Decimal("0"))
            + cf.get((scenario, period, "Change in Accounts Payable"), Decimal("0"))
            + cf.get((scenario, period, "Change in Prepaids"), Decimal("0"))
        )
        results.append(_result(scenario, period, "cash_flow_operating_cash_flow", ocf, cf.get((scenario, period, "Net Cash Provided by Operating Activities"), Decimal("0")), cf_sources))
        net_change = cf.get((scenario, period, "Net Cash Provided by Operating Activities"), Decimal("0")) + cf.get((scenario, period, "Net Cash Used in Investing Activities"), Decimal("0")) + cf.get((scenario, period, "Net Cash Provided by Financing Activities"), Decimal("0"))
        results.append(_result(scenario, period, "cash_flow_net_change", net_change, cf.get((scenario, period, "Net Change in Cash"), Decimal("0")), cf_sources))
        ending = cf.get((scenario, period, "Beginning Cash Balance"), Decimal("0")) + cf.get((scenario, period, "Net Change in Cash"), Decimal("0"))
        results.append(_result(scenario, period, "cash_flow_ending_cash_rolls", ending, cf.get((scenario, period, "Ending Cash Balance"), Decimal("0")), cf_sources))
        results.append(_result(scenario, period, "cash_flow_ending_cash_equals_balance_sheet_cash", bs.get((scenario, period, "Cash"), Decimal("0")), cf.get((scenario, period, "Ending Cash Balance"), Decimal("0")), cf_sources))

    actual_may = cf.get(("Actual", date(2026, 5, 1), "Ending Cash Balance"))
    forecast_june = cf.get(("Forecast", date(2026, 6, 1), "Beginning Cash Balance"))
    if actual_may is not None and forecast_june is not None:
        results.append(_result("Combined", date(2026, 6, 1), "forecast_opening_cash_equals_actual_ending_cash", actual_may, forecast_june, ["actual_cash_flow_statement", "forecast_cash_flow_statement"]))

    return results
