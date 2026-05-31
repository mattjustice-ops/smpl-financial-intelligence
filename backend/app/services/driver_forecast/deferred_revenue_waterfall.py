"""Deferred revenue waterfall forecast."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.driver_forecast.billing_forecast_engine import build_billing_forecast
from app.services.driver_forecast.common import month_range, period_type, q_money
from app.services.driver_forecast.repository import decimal_value, fetch_period_rows


def build_deferred_revenue_waterfall(
    session: Session,
    organization_id,
    *,
    start_period: date,
    end_period: date,
) -> list[dict[str, Decimal | date | str]]:
    periods = month_range(start_period, end_period)
    billings = build_billing_forecast(
        session,
        organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    revenue_rows = fetch_period_rows(
        session,
        table_name="forecast_income_statement",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    revenue_by_period = {r["period"]: decimal_value(r, "revenue") for r in revenue_rows}
    balance_rows = fetch_period_rows(
        session,
        table_name="forecast_balance_sheet",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    explicit_deferred = {r["period"]: decimal_value(r, "deferred_revenue") for r in balance_rows}
    actual_income_rows = fetch_period_rows(
        session,
        table_name="actual_income_statement",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    actual_revenue_by_period = {r["period"]: decimal_value(r, "revenue") for r in actual_income_rows}
    actual_balance_rows = fetch_period_rows(
        session,
        table_name="actual_balance_sheet",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    actual_deferred = {r["period"]: decimal_value(r, "deferred_revenue") for r in actual_balance_rows}
    actual_invoice_rows = fetch_period_rows(
        session,
        table_name="actual_invoices",
        organization_id=organization_id,
        period_column="invoice_period",
        start_period=start_period,
        end_period=end_period,
    )
    actual_billings: dict[date, Decimal] = {}
    for r in actual_invoice_rows:
        actual_billings[r["invoice_period"]] = actual_billings.get(r["invoice_period"], Decimal("0")) + decimal_value(r, "invoice_amount")

    beginning = (
        actual_deferred.get(periods[0])
        or explicit_deferred.get(periods[0])
        or Decimal("0")
        if periods
        else Decimal("0")
    )
    rows: list[dict[str, Decimal | date | str]] = []
    for period in periods:
        if period_type(period) == "actual":
            new_billings = actual_billings.get(period, Decimal("0"))
            revenue = actual_revenue_by_period.get(period, Decimal("0"))
            ending = actual_deferred.get(period, beginning + new_billings - revenue)
            rows.append(
                {
                    "period": period,
                    "beginning_deferred_revenue": q_money(beginning),
                    "new_billings": q_money(new_billings),
                    "revenue_recognized": q_money(revenue),
                    "ending_deferred_revenue": q_money(ending),
                }
            )
            beginning = ending
            continue

        new_billings = billings.get(period, Decimal("0"))
        revenue = revenue_by_period.get(period, Decimal("0"))
        ending = explicit_deferred.get(period, beginning + new_billings - revenue)
        rows.append(
            {
                "period": period,
                "beginning_deferred_revenue": q_money(beginning),
                "new_billings": q_money(new_billings),
                "revenue_recognized": q_money(revenue),
                "ending_deferred_revenue": q_money(ending),
            }
        )
        beginning = ending
    return rows
