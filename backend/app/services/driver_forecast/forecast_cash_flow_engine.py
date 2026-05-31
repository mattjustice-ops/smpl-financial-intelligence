"""Driver-based 3-statement cash flow forecast."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.driver_forecast.cash_collections_forecast import build_cash_collections_forecast
from app.services.driver_forecast.common import month_range, period_type, q_money
from app.services.driver_forecast.operating_cash_bridge import build_operating_cash_bridge
from app.services.driver_forecast.repository import decimal_value, fetch_period_rows
from app.services.workforce.integration import resolve_payroll_cash_out


def build_cash_flow_forecast(
    session: Session,
    organization_id,
    *,
    start_period: date,
    end_period: date,
    assumptions: dict[str, Decimal],
) -> list[dict[str, Decimal | date]]:
    periods = month_range(start_period, end_period)
    collections = build_cash_collections_forecast(
        session,
        organization_id,
        start_period=start_period,
        end_period=end_period,
        assumptions=assumptions,
    )
    ocf_rows = build_operating_cash_bridge(
        session,
        organization_id,
        start_period=start_period,
        end_period=end_period,
        assumptions=assumptions,
    )
    ocf_by_period = {r["period"]: r for r in ocf_rows}
    explicit = fetch_period_rows(
        session,
        table_name="forecast_cash_collections",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    explicit_by_period = {r["period"]: r for r in explicit}
    income_rows = fetch_period_rows(
        session,
        table_name="forecast_income_statement",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    revenue_by_period = {r["period"]: decimal_value(r, "revenue") for r in income_rows}
    actual_rows = fetch_period_rows(
        session,
        table_name="actual_cash_flow_statement",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    actual_by_period = {r["period"]: r for r in actual_rows}
    actual_bs_rows = fetch_period_rows(
        session,
        table_name="actual_balance_sheet",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    actual_cash_by_period = {r["period"]: decimal_value(r, "cash") for r in actual_bs_rows}

    beginning_cash = Decimal("0")
    rows: list[dict[str, Decimal | date]] = []
    for period in periods:
        if period_type(period) == "actual" and period in actual_by_period:
            actual = actual_by_period[period]
            ending_cash = decimal_value(actual, "ending_cash") or actual_cash_by_period.get(period, Decimal("0"))
            net_change = decimal_value(actual, "net_change_in_cash")
            if beginning_cash == 0:
                beginning_cash = ending_cash - net_change
            operating = decimal_value(actual, "net_cash_from_operating_activities")
            investing = decimal_value(actual, "net_cash_from_investing_activities") or decimal_value(actual, "capital_expenditures")
            financing = decimal_value(actual, "net_cash_from_financing_activities")
            rows.append(
                {
                    "period": period,
                    "beginning_cash": q_money(beginning_cash),
                    "cash_collections": q_money(collections.get(period, Decimal("0"))),
                    "operating_cash_flow": q_money(operating),
                    "investing_cash_flow": q_money(investing),
                    "financing_cash_flow": q_money(financing),
                    "ending_cash": q_money(ending_cash),
                }
            )
            beginning_cash = ending_cash
            continue

        explicit_row = explicit_by_period.get(period, {})
        if explicit_row and beginning_cash == 0:
            beginning_cash = decimal_value(explicit_row, "beginning_cash") or beginning_cash
        manual_payroll = decimal_value(explicit_row, "payroll_cash_out")
        payroll_cash_out, payroll_source = resolve_payroll_cash_out(
            session,
            organization_id,
            period=period,
            manual_value=manual_payroll if manual_payroll else None,
        )
        cash_outflows = (
            payroll_cash_out
            + decimal_value(explicit_row, "commission_cash_out")
            + decimal_value(explicit_row, "vendor_cash_out")
            + decimal_value(explicit_row, "marketing_cash_out")
        )
        if explicit_row:
            operating = collections.get(period, Decimal("0")) - cash_outflows
        else:
            operating = decimal_value(ocf_by_period.get(period, {}), "net_cash_from_operating_activities")
            if payroll_cash_out > 0:
                operating -= payroll_cash_out
        capex = -(revenue_by_period.get(period, Decimal("0")) * assumptions.get("capex_pct_of_revenue", Decimal("0.02")))
        financing = Decimal("0")
        ending_cash = beginning_cash + operating + capex + financing
        rows.append(
            {
                "period": period,
                "beginning_cash": q_money(beginning_cash),
                "cash_collections": q_money(collections.get(period, Decimal("0"))),
                "payroll_cash_out": q_money(-payroll_cash_out),
                "payroll_source": payroll_source,
                "operating_cash_flow": q_money(operating),
                "investing_cash_flow": q_money(capex),
                "financing_cash_flow": q_money(financing),
                "ending_cash": q_money(ending_cash),
            }
        )
        beginning_cash = ending_cash
    return rows
