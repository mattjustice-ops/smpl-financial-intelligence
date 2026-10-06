"""Balance sheet schedule from the loaded Actual and Forecast balance sheets."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.driver_forecast.common import month_range, period_type, q_opt
from app.services.driver_forecast.repository import loaded_value
from app.services.financial_statements.financial_statement_service import gl_balance_rows

PREPAIDS_KEYS = (
    "prepaids_and_other_current",
    "prepaids_and_other_current_assets",
    "prepaid_and_other_current_assets",
    "prepaids",
    "prepaid_expenses",
    "other_current_assets",
)
FIXED_ASSET_KEYS = (
    "ppe_net",
    "property_and_equipment_net",
    "property_plant_and_equipment_net",
    "property_plant_equipment_net",
    "property_plant_net",
    "fixed_assets",
)
DEBT_KEYS = ("debt", "total_debt", "debt_balance", "notes_payable")


def build_balance_sheet_forecast(
    session: Session,
    organization_id,
    *,
    start_period: date,
    end_period: date,
    assumptions: dict[str, Decimal] | None = None,
) -> list[dict[str, Decimal | date | None]]:
    """No carry-forwards or equity plugs: missing lines stay ``None`` and totals that need them do too."""
    periods = month_range(start_period, end_period)
    by_scenario = {
        s: {r["period"]: r for r in gl_balance_rows(session, organization_id, s, start_period, end_period)}
        for s in ("Actual", "Forecast")
    }
    rows: list[dict[str, Decimal | date | None]] = []
    for period in periods:
        row = by_scenario["Actual" if period_type(period) == "actual" else "Forecast"].get(period)
        cash = loaded_value(row, "cash")
        ar = loaded_value(row, "accounts_receivable")
        prepaids = loaded_value(row, *PREPAIDS_KEYS)
        fixed_assets = loaded_value(row, *FIXED_ASSET_KEYS)
        deferred = loaded_value(row, "deferred_revenue")
        ap = loaded_value(row, "accounts_payable")
        debt = loaded_value(row, *DEBT_KEYS)
        equity = loaded_value(row, "equity", "total_equity")
        total_assets = loaded_value(row, "total_assets")
        total_liabilities = loaded_value(row, "total_liabilities")
        total_le = None if total_liabilities is None or equity is None else total_liabilities + equity
        rows.append(
            {
                "period": period,
                "cash": q_opt(cash),
                "accounts_receivable": q_opt(ar),
                "prepaids_and_other_current_assets": q_opt(prepaids),
                "property_and_equipment_net": q_opt(fixed_assets),
                "deferred_revenue": q_opt(deferred),
                "accounts_payable": q_opt(ap),
                "prepaids": q_opt(prepaids),
                "fixed_assets": q_opt(fixed_assets),
                "debt": q_opt(debt),
                "equity": q_opt(equity),
                "total_assets": q_opt(total_assets),
                "total_liabilities": q_opt(total_liabilities),
                "total_liabilities_and_equity": q_opt(total_le),
                "balance_check": q_opt(None if total_assets is None or total_le is None else total_assets - total_le),
            }
        )
    return rows
