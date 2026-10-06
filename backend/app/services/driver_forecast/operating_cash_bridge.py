"""Operating cash flow bridge from the loaded cash flow and income statements."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.driver_forecast.common import month_range, period_type, q_opt
from app.services.driver_forecast.repository import loaded_value
from app.services.financial_statements.financial_statement_service import gl_cash_flow_rows, gl_income_rows


def build_operating_cash_bridge(
    session: Session,
    organization_id,
    *,
    start_period: date,
    end_period: date,
    assumptions: dict[str, Decimal] | None = None,
) -> list[dict[str, Decimal | date | None]]:
    periods = month_range(start_period, end_period)
    income_by_scenario = {
        s: {r["period"]: r for r in gl_income_rows(session, organization_id, s, start_period, end_period)}
        for s in ("Actual", "Forecast")
    }
    cf_by_scenario = {
        s: {r["period"]: r for r in gl_cash_flow_rows(session, organization_id, s, start_period, end_period)}
        for s in ("Actual", "Forecast")
    }
    rows: list[dict[str, Decimal | date | None]] = []
    for period in periods:
        scenario = "Actual" if period_type(period) == "actual" else "Forecast"
        income = income_by_scenario[scenario].get(period)
        cf = cf_by_scenario[scenario].get(period)
        rows.append(
            {
                "period": period,
                "net_income": q_opt(loaded_value(cf, "net_income") or loaded_value(income, "net_income")),
                "depreciation_and_amortization": q_opt(loaded_value(cf, "depreciation_and_amortization")),
                "stock_based_compensation": q_opt(loaded_value(cf, "stock_based_compensation")),
                "change_in_accounts_receivable": q_opt(loaded_value(cf, "change_in_accounts_receivable")),
                "change_in_deferred_revenue": q_opt(loaded_value(cf, "change_in_deferred_revenue")),
                "change_in_accounts_payable": q_opt(loaded_value(cf, "change_in_accounts_payable")),
                "net_cash_from_operating_activities": q_opt(loaded_value(cf, "net_cash_from_operating_activities")),
            }
        )
    return rows
