"""Cash collections forecast from billings and DSO assumptions."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.driver_forecast.billing_forecast_engine import build_billing_forecast
from app.services.driver_forecast.common import add_months, month_range, period_type, q_money
from app.services.driver_forecast.repository import decimal_value, fetch_period_rows


def build_cash_collections_forecast(
    session: Session,
    organization_id,
    *,
    start_period: date,
    end_period: date,
    assumptions: dict[str, Decimal],
) -> dict[date, Decimal]:
    out = {p: Decimal("0") for p in month_range(start_period, end_period)}

    actual_invoices = fetch_period_rows(
        session,
        table_name="actual_invoices",
        organization_id=organization_id,
        period_column="invoice_period",
        start_period=start_period,
        end_period=end_period,
    )
    for row in actual_invoices:
        if str(row.get("payment_status") or "").lower() == "paid":
            out[row["invoice_period"]] += decimal_value(row, "invoice_amount")

    billings = build_billing_forecast(
        session,
        organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    modeled = {p: Decimal("0") for p in month_range(start_period, end_period)}
    lag_months = max(0, int((assumptions.get("dso", Decimal("42")) / Decimal("30")).to_integral_value()))
    for period, amount in billings.items():
        collection_period = add_months(period, lag_months)
        if start_period <= collection_period <= end_period:
            modeled[collection_period] += amount

    # Uploaded forecast collections are used, but modeled collections from billings
    # act as a floor so new billings/opportunities reach the cash forecast.
    explicit = fetch_period_rows(
        session,
        table_name="forecast_cash_collections",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    explicit_by_period = {
        row["period"]: decimal_value(row, "cash_collections") or decimal_value(row, "collections")
        for row in explicit
    }
    for period in out:
        if period_type(period) == "forecast":
            out[period] = max(explicit_by_period.get(period, Decimal("0")), modeled.get(period, Decimal("0")))

    return {p: q_money(v) for p, v in out.items()}
