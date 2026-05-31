"""Driver-based billings forecast."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.driver_forecast.common import month_range, period_type, q_money
from app.services.driver_forecast.repository import decimal_value, fetch_period_rows


def build_billing_forecast(
    session: Session,
    organization_id,
    *,
    start_period: date,
    end_period: date,
) -> dict[date, Decimal]:
    """Billings from forecast revenue schedule plus weighted forecast opportunities."""
    out = {p: Decimal("0") for p in month_range(start_period, end_period)}

    for row in fetch_period_rows(
        session,
        table_name="forecast_revenue_schedule",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    ):
        out[row["period"]] = out.get(row["period"], Decimal("0")) + decimal_value(row, "billings")

    for row in fetch_period_rows(
        session,
        table_name="forecast_opportunities",
        organization_id=organization_id,
        period_column="forecast_period",
        start_period=start_period,
        end_period=end_period,
    ):
        # Forecast opportunity billings are probability weighted and assumed to bill in close month.
        period = row["forecast_period"]
        weighted_arr = decimal_value(row, "weighted_arr") or (
            decimal_value(row, "amount_arr") * decimal_value(row, "probability")
        )
        if period_type(period) == "forecast":
            out[period] = out.get(period, Decimal("0")) + (weighted_arr / Decimal("12"))

    return {p: q_money(v) for p, v in out.items()}
