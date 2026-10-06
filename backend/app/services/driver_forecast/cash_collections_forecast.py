"""Cash collections from paid invoices (actual) and the loaded forecast collections."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.driver_forecast.common import period_type, q_money
from app.services.driver_forecast.repository import decimal_value, fetch_period_rows


def build_cash_collections_forecast(
    session: Session,
    organization_id,
    *,
    start_period: date,
    end_period: date,
    assumptions: dict[str, Decimal] | None = None,
) -> dict[date, Decimal]:
    """Collections by period; months with nothing loaded are absent, not zero."""
    out: dict[date, Decimal] = {}

    for row in fetch_period_rows(
        session,
        table_name="actual_invoices",
        organization_id=organization_id,
        period_column="invoice_period",
        start_period=start_period,
        end_period=end_period,
    ):
        period = row["invoice_period"]
        if period_type(period) != "actual":
            continue
        if str(row.get("payment_status") or "").lower() == "paid":
            out[period] = out.get(period, Decimal("0")) + decimal_value(row, "invoice_amount")

    for row in fetch_period_rows(
        session,
        table_name="forecast_cash_collections",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    ):
        period = row["period"]
        if period_type(period) != "forecast":
            continue
        key = "cash_collections" if row.get("cash_collections") not in (None, "") else "collections"
        if row.get(key) in (None, ""):
            continue
        out[period] = out.get(period, Decimal("0")) + decimal_value(row, key)

    return {p: q_money(v) for p, v in out.items()}
