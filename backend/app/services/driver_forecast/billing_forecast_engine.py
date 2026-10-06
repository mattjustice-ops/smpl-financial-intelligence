"""Forecast billings from the loaded forecast revenue schedule."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.driver_forecast.common import q_money
from app.services.driver_forecast.repository import decimal_value, fetch_period_rows


def build_billing_forecast(
    session: Session,
    organization_id,
    *,
    start_period: date,
    end_period: date,
) -> dict[date, Decimal]:
    """Billings by period for the months the forecast revenue schedule has loaded."""
    out: dict[date, Decimal] = {}
    for row in fetch_period_rows(
        session,
        table_name="forecast_revenue_schedule",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    ):
        if row.get("billings") in (None, ""):
            continue
        out[row["period"]] = out.get(row["period"], Decimal("0")) + decimal_value(row, "billings")
    return {p: q_money(v) for p, v in out.items()}
