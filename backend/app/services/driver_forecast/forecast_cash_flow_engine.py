"""Cash flow schedule from the loaded Actual and Forecast cash flow statements."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.driver_forecast.cash_collections_forecast import build_cash_collections_forecast
from app.services.driver_forecast.common import month_range, period_type, q_money, q_opt
from app.services.driver_forecast.repository import decimal_value, fetch_period_rows, loaded_value
from app.services.financial_statements.financial_statement_service import gl_balance_rows, gl_cash_flow_rows
from app.services.workforce.integration import resolve_payroll_cash_out


def build_cash_flow_forecast(
    session: Session,
    organization_id,
    *,
    start_period: date,
    end_period: date,
    assumptions: dict[str, Decimal] | None = None,
) -> list[dict[str, Decimal | date | str | None]]:
    """One row per month; lines the dataset does not carry for a month stay ``None``."""
    periods = month_range(start_period, end_period)
    collections = build_cash_collections_forecast(
        session,
        organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    explicit_by_period = {
        r["period"]: r
        for r in fetch_period_rows(
            session,
            table_name="forecast_cash_collections",
            organization_id=organization_id,
            start_period=start_period,
            end_period=end_period,
        )
    }
    cf_by_scenario = {
        s: {r["period"]: r for r in gl_cash_flow_rows(session, organization_id, s, start_period, end_period)}
        for s in ("Actual", "Forecast")
    }
    bs_cash_by_scenario = {
        s: {r["period"]: loaded_value(r, "cash") for r in gl_balance_rows(session, organization_id, s, start_period, end_period)}
        for s in ("Actual", "Forecast")
    }

    rows: list[dict[str, Decimal | date | str | None]] = []
    prior_ending: Decimal | None = None
    for period in periods:
        actual = period_type(period) == "actual"
        scenario = "Actual" if actual else "Forecast"
        cf = cf_by_scenario[scenario].get(period)
        ending_cash = loaded_value(cf, "ending_cash")
        if ending_cash is None:
            ending_cash = bs_cash_by_scenario[scenario].get(period)
        beginning_cash = loaded_value(cf, "beginning_cash")
        if beginning_cash is None:
            beginning_cash = prior_ending
        row: dict[str, Decimal | date | str | None] = {
            "period": period,
            "beginning_cash": q_opt(beginning_cash),
            "cash_collections": collections.get(period),
            "operating_cash_flow": q_opt(loaded_value(cf, "net_cash_from_operating_activities")),
            "investing_cash_flow": q_opt(
                loaded_value(cf, "net_cash_from_investing_activities", "capital_expenditures")
            ),
            "financing_cash_flow": q_opt(loaded_value(cf, "net_cash_from_financing_activities")),
            "ending_cash": q_opt(ending_cash),
        }
        if not actual:
            manual_payroll = decimal_value(explicit_by_period.get(period, {}), "payroll_cash_out")
            payroll_cash_out, payroll_source = resolve_payroll_cash_out(
                session,
                organization_id,
                period=period,
                manual_value=manual_payroll if manual_payroll else None,
            )
            row["payroll_cash_out"] = q_money(-payroll_cash_out) if payroll_cash_out else None
            row["payroll_source"] = payroll_source
        rows.append(row)
        prior_ending = ending_cash
    return rows
