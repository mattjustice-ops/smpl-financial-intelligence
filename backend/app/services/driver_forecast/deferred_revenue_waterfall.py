"""Deferred revenue waterfall from loaded billings, revenue and deferred balances."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.driver_forecast.billing_forecast_engine import build_billing_forecast
from app.services.driver_forecast.common import month_range, period_type, q_money, q_opt
from app.services.driver_forecast.repository import decimal_value, fetch_period_rows, loaded_value
from app.services.financial_statements.financial_statement_service import gl_balance_rows, gl_income_rows


def build_deferred_revenue_waterfall(
    session: Session,
    organization_id,
    *,
    start_period: date,
    end_period: date,
) -> list[dict[str, Decimal | date | None]]:
    """Balances are never back-solved: a month without a loaded deferred balance shows ``None``."""
    periods = month_range(start_period, end_period)
    forecast_billings = build_billing_forecast(
        session,
        organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    actual_billings: dict[date, Decimal] = {}
    for r in fetch_period_rows(
        session,
        table_name="actual_invoices",
        organization_id=organization_id,
        period_column="invoice_period",
        start_period=start_period,
        end_period=end_period,
    ):
        actual_billings[r["invoice_period"]] = actual_billings.get(r["invoice_period"], Decimal("0")) + decimal_value(r, "invoice_amount")
    revenue_by_scenario = {
        s: {r["period"]: loaded_value(r, "revenue") for r in gl_income_rows(session, organization_id, s, start_period, end_period)}
        for s in ("Actual", "Forecast")
    }
    deferred_by_scenario = {
        s: {r["period"]: loaded_value(r, "deferred_revenue") for r in gl_balance_rows(session, organization_id, s, start_period, end_period)}
        for s in ("Actual", "Forecast")
    }

    rows: list[dict[str, Decimal | date | None]] = []
    prior_ending: Decimal | None = None
    for period in periods:
        actual = period_type(period) == "actual"
        scenario = "Actual" if actual else "Forecast"
        billings = actual_billings.get(period) if actual else forecast_billings.get(period)
        revenue = revenue_by_scenario[scenario].get(period)
        ending = deferred_by_scenario[scenario].get(period)
        rows.append(
            {
                "period": period,
                "beginning_deferred_revenue": q_opt(prior_ending),
                "new_billings": q_money(billings) if billings is not None else None,
                "revenue_recognized": q_opt(revenue),
                "ending_deferred_revenue": q_opt(ending),
            }
        )
        prior_ending = ending
    return rows
