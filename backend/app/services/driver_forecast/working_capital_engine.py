"""Working capital forecast schedules."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.driver_forecast.cash_collections_forecast import build_cash_collections_forecast
from app.services.driver_forecast.common import month_range, period_type, q_money
from app.services.driver_forecast.repository import decimal_value, fetch_period_rows


def build_working_capital_forecast(
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
    bs_rows = fetch_period_rows(
        session,
        table_name="forecast_balance_sheet",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    bs_by_period = {r["period"]: r for r in bs_rows}
    actual_bs_rows = fetch_period_rows(
        session,
        table_name="actual_balance_sheet",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    actual_bs_by_period = {r["period"]: r for r in actual_bs_rows}
    actual_invoice_rows = fetch_period_rows(
        session,
        table_name="actual_invoices",
        organization_id=organization_id,
        period_column="invoice_period",
        start_period=start_period,
        end_period=end_period,
    )
    actual_collections: dict[date, Decimal] = {}
    for r in actual_invoice_rows:
        if str(r.get("payment_status") or "").lower() == "paid":
            actual_collections[r["invoice_period"]] = actual_collections.get(r["invoice_period"], Decimal("0")) + decimal_value(r, "invoice_amount")
    rows: list[dict[str, Decimal | date]] = []
    for period in periods:
        row = actual_bs_by_period.get(period, {}) if period_type(period) == "actual" else bs_by_period.get(period, {})
        ar = decimal_value(row, "accounts_receivable")
        deferred = decimal_value(row, "deferred_revenue")
        ap = decimal_value(row, "accounts_payable")
        period_collections = (
            actual_collections.get(period, Decimal("0"))
            if period_type(period) == "actual"
            else collections.get(period, Decimal("0"))
        )
        rows.append(
            {
                "period": period,
                "dso": assumptions.get("dso", Decimal("42")),
                "dpo": assumptions.get("dpo", Decimal("32")),
                "dio": assumptions.get("dio", Decimal("0")),
                "accounts_receivable": q_money(ar),
                "deferred_revenue": q_money(deferred),
                "accounts_payable": q_money(ap),
                "collections": q_money(period_collections),
            }
        )
    return rows
