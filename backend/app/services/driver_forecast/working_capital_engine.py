"""Working capital schedules from loaded balance sheets, collections and assumptions."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.driver_forecast.cash_collections_forecast import build_cash_collections_forecast
from app.services.driver_forecast.common import month_range, period_type, q_opt
from app.services.driver_forecast.repository import loaded_value
from app.services.financial_statements.financial_statement_service import gl_balance_rows


def build_working_capital_forecast(
    session: Session,
    organization_id,
    *,
    start_period: date,
    end_period: date,
    assumptions: dict[str, Decimal],
) -> list[dict[str, Decimal | date | None]]:
    periods = month_range(start_period, end_period)
    collections = build_cash_collections_forecast(
        session,
        organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    bs_by_period = {r["period"]: r for r in gl_balance_rows(session, organization_id, "Forecast", start_period, end_period)}
    actual_bs_by_period = {r["period"]: r for r in gl_balance_rows(session, organization_id, "Actual", start_period, end_period)}
    rows: list[dict[str, Decimal | date | None]] = []
    for period in periods:
        row = actual_bs_by_period.get(period) if period_type(period) == "actual" else bs_by_period.get(period)
        rows.append(
            {
                "period": period,
                "dso": assumptions.get("dso"),
                "dpo": assumptions.get("dpo"),
                "dio": assumptions.get("dio"),
                "accounts_receivable": q_opt(loaded_value(row, "accounts_receivable")),
                "deferred_revenue": q_opt(loaded_value(row, "deferred_revenue")),
                "accounts_payable": q_opt(loaded_value(row, "accounts_payable")),
                "collections": collections.get(period),
            }
        )
    return rows
