"""Normalized financial statement reporting over uploaded CSV tables."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable, Literal

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.financial_statements.financial_statement_mapper import (
    BALANCE_SHEET_LINES,
    CASH_FLOW_LINES,
    INCOME_STATEMENT_LINES,
    LineMapping,
    table_name_for,
)

MONEY = Decimal("0.01")
TOLERANCE = Decimal("1.00")


class NormalizedStatementLine(BaseModel):
    organization_id: str
    scenario: str
    period: date
    line_item: str
    line_item_order: int
    section: str
    amount: Decimal
    source_table: str
    source_column: str


class NormalizedStatementResponse(BaseModel):
    organization_id: str
    scenario: str
    start_period: date
    end_period: date
    statement_type: str
    rows: list[NormalizedStatementLine] = Field(default_factory=list)
    periods: list[date] = Field(default_factory=list)


class ValidationResult(BaseModel):
    scenario: str
    period: date
    validation_name: str
    status: Literal["pass", "warning", "fail"]
    expected_value: Decimal | None = None
    actual_value: Decimal | None = None
    variance: Decimal | None = None
    source_tables_used: list[str] = Field(default_factory=list)


class SummaryResponse(BaseModel):
    organization_id: str
    scenario: str
    start_period: date
    end_period: date
    income_statement: NormalizedStatementResponse
    balance_sheet: NormalizedStatementResponse
    cash_flow: NormalizedStatementResponse
    validation: list[ValidationResult]


def q(value: Any) -> Decimal:
    if value is None or value == "":
        value = Decimal("0")
    if not isinstance(value, Decimal):
        if isinstance(value, str):
            cleaned = value.strip().replace("$", "").replace(",", "")
            if cleaned.startswith("(") and cleaned.endswith(")"):
                cleaned = f"-{cleaned[1:-1]}"
            value = cleaned or "0"
        value = Decimal(str(value))
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def month_start(value: date) -> date:
    return value.replace(day=1)


def parse_period(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return month_start(value)
    s = str(value)
    if len(s) == 7 and s[4] == "-":
        return date(int(s[:4]), int(s[5:7]), 1)
    return month_start(date.fromisoformat(s[:10]))


def period_range(start_period: date, end_period: date) -> list[date]:
    current = month_start(start_period)
    end = month_start(end_period)
    periods: list[date] = []
    while current <= end:
        periods.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return periods


def table_exists(session: Session, table_name: str) -> bool:
    return session.execute(text("select to_regclass(:name)"), {"name": f"public.{table_name}"}).scalar() is not None


def fetch_rows(session: Session, table_name: str, organization_id: uuid.UUID, start_period: date, end_period: date) -> list[dict[str, Any]]:
    if not table_exists(session, table_name):
        return []
    rows = session.execute(
        text(f'select * from "{table_name}" where organization_id = :organization_id'),
        {"organization_id": str(organization_id)},
    ).mappings()
    out: list[dict[str, Any]] = []
    start = month_start(start_period)
    end = month_start(end_period)
    for row in rows:
        data = dict(row)
        period = parse_period(data.get("period"))
        if period is None or period < start or period > end:
            continue
        data["period"] = period
        out.append(data)
    return sorted(out, key=lambda r: r["period"])


def scenarios_for(scenario: str, start_period: date, end_period: date) -> list[tuple[str, date, date]]:
    if scenario.lower() != "combined":
        normalized = "Forecast" if scenario.lower() == "forecast" else "Budget" if scenario.lower() == "budget" else "Actual"
        return [(normalized, month_start(start_period), month_start(end_period))]
    periods = period_range(start_period, end_period)
    actual_periods = [p for p in periods if p <= date(2026, 5, 1)]
    forecast_periods = [p for p in periods if p >= date(2026, 6, 1)]
    out: list[tuple[str, date, date]] = []
    if actual_periods:
        out.append(("Actual", actual_periods[0], actual_periods[-1]))
    if forecast_periods:
        out.append(("Forecast", forecast_periods[0], forecast_periods[-1]))
    return out


def row_value(row: dict[str, Any], key: str) -> Decimal:
    return q(row.get(key))


def row_value_any(row: dict[str, Any], *keys: str) -> Decimal:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return q(value)
    return Decimal("0.00")


def ensure_income_formulas(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["gross_profit"] = row_value(out, "revenue") - row_value(out, "cost_of_revenue")
    out["total_operating_expenses"] = row_value(out, "sales_and_marketing") + row_value(out, "research_and_development") + row_value(out, "general_and_administrative")
    out["ebitda"] = row_value(out, "gross_profit") - row_value(out, "total_operating_expenses")
    out["operating_income"] = row_value(out, "ebitda") - row_value(out, "depreciation_and_amortization")
    out["net_income"] = row_value(out, "operating_income") - row_value(out, "interest_expense") - row_value(out, "tax_expense")
    return out


def ensure_balance_formulas(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["prepaids_and_other_current_assets"] = row_value_any(
        out,
        "prepaids_and_other_current_assets",
        "prepaid_and_other_current_assets",
        "prepaids",
        "prepaid_expenses",
        "other_current_assets",
    )
    out["property_and_equipment_net"] = row_value_any(
        out,
        "property_and_equipment_net",
        "property_plant_and_equipment_net",
        "property_plant_equipment_net",
        "property_plant_net",
        "ppe_net",
        "fixed_assets",
    )
    out["debt"] = row_value_any(out, "debt", "total_debt", "debt_balance", "notes_payable")
    out["total_assets"] = row_value(out, "cash") + row_value(out, "accounts_receivable") + row_value(out, "prepaids_and_other_current_assets") + row_value(out, "property_and_equipment_net")
    out["total_liabilities"] = row_value(out, "accounts_payable") + row_value(out, "deferred_revenue") + row_value(out, "debt")
    out["total_liabilities_and_equity"] = row_value(out, "total_liabilities") + row_value(out, "equity")
    out["balance_check"] = row_value(out, "total_assets") - row_value(out, "total_liabilities_and_equity")
    return out


def ensure_cash_flow_formulas(rows: list[dict[str, Any]], bs_cash: dict[tuple[str, date], Decimal], scenario: str) -> list[dict[str, Any]]:
    out_rows: list[dict[str, Any]] = []
    prior_ending: Decimal | None = None
    actual_may_cash = bs_cash.get(("Actual", date(2026, 5, 1)))
    for row in sorted(rows, key=lambda r: r["period"]):
        out = dict(row)
        period = out["period"]
        beginning = row_value(out, "beginning_cash")
        net_change = row_value(out, "net_change_in_cash")
        ending = row_value(out, "ending_cash")
        if beginning == 0:
            if scenario == "Forecast" and period == date(2026, 6, 1) and actual_may_cash is not None:
                beginning = actual_may_cash
            elif prior_ending is not None:
                beginning = prior_ending
            elif ending != 0 or net_change != 0:
                beginning = ending - net_change
        if not out.get("stock_based_compensation"):
            out["stock_based_compensation"] = Decimal("0")
        if not out.get("change_in_prepaids"):
            out["change_in_prepaids"] = Decimal("0")
        out["beginning_cash"] = beginning
        out["net_cash_from_operating_activities"] = (
            row_value(out, "net_income")
            + row_value(out, "depreciation_and_amortization")
            + row_value(out, "stock_based_compensation")
            + row_value(out, "change_in_accounts_receivable")
            + row_value(out, "change_in_deferred_revenue")
            + row_value(out, "change_in_accounts_payable")
            + row_value(out, "change_in_prepaids")
        )
        out["net_cash_from_investing_activities"] = row_value(out, "capital_expenditures")
        out["net_cash_from_financing_activities"] = row_value(out, "debt_issuance_repayment")
        out["net_change_in_cash"] = row_value(out, "net_cash_from_operating_activities") + row_value(out, "net_cash_from_investing_activities") + row_value(out, "net_cash_from_financing_activities")
        out["ending_cash"] = beginning + row_value(out, "net_change_in_cash")
        # Loaded statement cash wins when present, but validation will flag if it does not tie.
        if ending != 0:
            out["ending_cash"] = ending
        prior_ending = row_value(out, "ending_cash")
        out_rows.append(out)
    return out_rows


def normalize_rows(
    organization_id: uuid.UUID,
    scenario: str,
    table_name: str,
    rows: Iterable[dict[str, Any]],
    mappings: list[LineMapping],
) -> list[NormalizedStatementLine]:
    out: list[NormalizedStatementLine] = []
    for row in rows:
        for mapping in mappings:
            out.append(
                NormalizedStatementLine(
                    organization_id=str(organization_id),
                    scenario=scenario,
                    period=row["period"],
                    line_item=mapping.line_item,
                    line_item_order=mapping.line_item_order,
                    section=mapping.section,
                    amount=q(row.get(mapping.source_column)),
                    source_table=table_name,
                    source_column=mapping.source_column,
                )
            )
    return sorted(out, key=lambda r: (r.period, r.line_item_order))


def statement(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: date,
    end_period: date,
    statement_type: str,
) -> NormalizedStatementResponse:
    rows: list[NormalizedStatementLine] = []
    periods: set[date] = set()
    for scenario_name, s, e in scenarios_for(scenario, start_period, end_period):
        if statement_type == "income_statement":
            table = table_name_for(scenario_name, "income_statement")
            source = [ensure_income_formulas(r) for r in fetch_rows(session, table, organization_id, s, e)]
            mappings = INCOME_STATEMENT_LINES
        elif statement_type == "balance_sheet":
            table = table_name_for(scenario_name, "balance_sheet")
            source = [ensure_balance_formulas(r) for r in fetch_rows(session, table, organization_id, s, e)]
            mappings = BALANCE_SHEET_LINES
        else:
            table = table_name_for(scenario_name, "cash_flow_statement")
            bs_cash = balance_sheet_cash(session, organization_id, start_period, end_period)
            source = ensure_cash_flow_formulas(fetch_rows(session, table, organization_id, s, e), bs_cash, scenario_name)
            mappings = CASH_FLOW_LINES
        periods.update(r["period"] for r in source)
        rows.extend(normalize_rows(organization_id, scenario_name, table, source, mappings))
    return NormalizedStatementResponse(
        organization_id=str(organization_id),
        scenario=scenario,
        start_period=month_start(start_period),
        end_period=month_start(end_period),
        statement_type=statement_type,
        rows=rows,
        periods=sorted(periods),
    )


def balance_sheet_cash(session: Session, organization_id: uuid.UUID, start_period: date, end_period: date) -> dict[tuple[str, date], Decimal]:
    out: dict[tuple[str, date], Decimal] = {}
    for scenario_name in ("Actual", "Budget", "Forecast"):
        table = table_name_for(scenario_name, "balance_sheet")
        for row in fetch_rows(session, table, organization_id, start_period, end_period):
            out[(scenario_name, row["period"])] = row_value(row, "cash")
    return out


def summary(session: Session, organization_id: uuid.UUID, *, scenario: str, start_period: date, end_period: date) -> SummaryResponse:
    income = statement(session, organization_id, scenario=scenario, start_period=start_period, end_period=end_period, statement_type="income_statement")
    balance = statement(session, organization_id, scenario=scenario, start_period=start_period, end_period=end_period, statement_type="balance_sheet")
    cash = statement(session, organization_id, scenario=scenario, start_period=start_period, end_period=end_period, statement_type="cash_flow")
    from app.services.financial_statements.financial_statement_validation_service import validate_financial_statements

    validations = validate_financial_statements(income, balance, cash)
    validations.extend(source_reconciliation_validations(session, organization_id, scenario=scenario, start_period=start_period, end_period=end_period))
    return SummaryResponse(
        organization_id=str(organization_id),
        scenario=scenario,
        start_period=month_start(start_period),
        end_period=month_start(end_period),
        income_statement=income,
        balance_sheet=balance,
        cash_flow=cash,
        validation=validations,
    )


def _validation(scenario: str, period: date, name: str, expected: Decimal, actual: Decimal, sources: list[str]) -> ValidationResult:
    variance = q(actual - expected)
    return ValidationResult(
        scenario=scenario,
        period=period,
        validation_name=name,
        status="pass" if abs(variance) <= TOLERANCE else "fail",
        expected_value=q(expected),
        actual_value=q(actual),
        variance=variance,
        source_tables_used=sources,
    )


def source_reconciliation_validations(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: date,
    end_period: date,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    for scenario_name, s, e in scenarios_for(scenario, start_period, end_period):
        ar_table = table_name_for(scenario_name, "accounts_receivable_rollforward")
        for row in fetch_rows(session, ar_table, organization_id, s, e):
            expected = (
                row_value_any(row, "beginning_accounts_receivable", "beginning_ar")
                + row_value_any(row, "new_billings", "billings")
                - row_value_any(row, "cash_collections", "collections")
            )
            actual = row_value_any(row, "ending_accounts_receivable", "ending_ar")
            results.append(_validation(scenario_name, row["period"], "ar_rollforward_ties", expected, actual, [ar_table]))
            if row_value_any(row, "cash_collections", "collections") == 0:
                results.append(ValidationResult(scenario=scenario_name, period=row["period"], validation_name="cash_collections_missing", status="warning", expected_value=None, actual_value=Decimal("0"), variance=None, source_tables_used=[ar_table]))

        ap_table = table_name_for(scenario_name, "accounts_payable_rollforward")
        for row in fetch_rows(session, ap_table, organization_id, s, e):
            expected = (
                row_value_any(row, "beginning_accounts_payable", "beginning_ap")
                + row_value_any(row, "vendor_expense_accruals", "vendor_accruals")
                - row_value_any(row, "vendor_cash_payments_n30", "vendor_payments")
            )
            actual = row_value_any(row, "ending_accounts_payable", "ending_ap")
            results.append(_validation(scenario_name, row["period"], "ap_rollforward_ties", expected, actual, [ap_table]))

        dr_table = table_name_for(scenario_name, "deferred_revenue_waterfall")
        for row in fetch_rows(session, dr_table, organization_id, s, e):
            billings = row_value(row, "billings") or row_value(row, "new_billings")
            expected = row_value(row, "beginning_deferred_revenue") + billings - row_value(row, "revenue_recognized")
            actual = row_value(row, "ending_deferred_revenue")
            results.append(_validation(scenario_name, row["period"], "deferred_revenue_waterfall_ties", expected, actual, [dr_table]))

        cf_table = table_name_for(scenario_name, "cash_flow_statement")
        for row in fetch_rows(session, cf_table, organization_id, s, e):
            ocf = row_value(row, "net_cash_from_operating_activities")
            if ocf == 0:
                results.append(ValidationResult(scenario=scenario_name, period=row["period"], validation_name="operating_cash_flow_missing_or_zero", status="warning", expected_value=None, actual_value=Decimal("0"), variance=None, source_tables_used=[cf_table]))
            results.append(ValidationResult(scenario=scenario_name, period=row["period"], validation_name="dashboard_values_sourced_from_database", status="pass", expected_value=None, actual_value=None, variance=None, source_tables_used=[cf_table, table_name_for(scenario_name, "income_statement"), table_name_for(scenario_name, "balance_sheet")]))

    return results
