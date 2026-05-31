"""Balance sheet forecast tied to P&L, cash flow, and working capital schedules."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.driver_forecast.common import month_range, period_type, q_money
from app.services.driver_forecast.deferred_revenue_waterfall import build_deferred_revenue_waterfall
from app.services.driver_forecast.forecast_cash_flow_engine import build_cash_flow_forecast
from app.services.driver_forecast.repository import decimal_value, fetch_period_rows


def decimal_value_any(row: dict, *keys: str) -> Decimal:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return decimal_value(row, key)
    return Decimal("0")


def build_balance_sheet_forecast(
    session: Session,
    organization_id,
    *,
    start_period: date,
    end_period: date,
    assumptions: dict[str, Decimal],
) -> list[dict[str, Decimal | date]]:
    periods = month_range(start_period, end_period)
    explicit = fetch_period_rows(
        session,
        table_name="forecast_balance_sheet",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    explicit_by_period = {r["period"]: r for r in explicit}
    actual_rows = fetch_period_rows(
        session,
        table_name="actual_balance_sheet",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    actual_by_period = {r["period"]: r for r in actual_rows}
    cash_rows = {r["period"]: r for r in build_cash_flow_forecast(session, organization_id, start_period=start_period, end_period=end_period, assumptions=assumptions)}
    deferred_rows = {r["period"]: r for r in build_deferred_revenue_waterfall(session, organization_id, start_period=start_period, end_period=end_period)}

    rows: list[dict[str, Decimal | date]] = []
    equity = Decimal("0")
    carried_prepaids = Decimal("0")
    carried_fixed_assets = Decimal("0")
    carried_debt = Decimal("0")
    for period in periods:
        row = actual_by_period.get(period, {}) if period_type(period) == "actual" else explicit_by_period.get(period, {})
        cash = decimal_value(row, "cash") or decimal_value(cash_rows.get(period, {}), "ending_cash")
        ar = decimal_value(row, "accounts_receivable")
        deferred = decimal_value(row, "deferred_revenue") or decimal_value(deferred_rows.get(period, {}), "ending_deferred_revenue")
        ap = decimal_value(row, "accounts_payable")
        prepaids = decimal_value_any(
            row,
            "prepaids_and_other_current_assets",
            "prepaid_and_other_current_assets",
            "prepaids",
            "prepaid_expenses",
            "other_current_assets",
        )
        fixed_assets = decimal_value_any(
            row,
            "property_and_equipment_net",
            "property_plant_and_equipment_net",
            "property_plant_equipment_net",
            "property_plant_net",
            "ppe_net",
            "fixed_assets",
        )
        debt = decimal_value_any(row, "debt", "total_debt", "debt_balance", "notes_payable")
        if prepaids:
            carried_prepaids = prepaids
        else:
            prepaids = carried_prepaids
        if fixed_assets:
            carried_fixed_assets = fixed_assets
        else:
            fixed_assets = carried_fixed_assets
        if debt:
            carried_debt = debt
        else:
            debt = carried_debt
        total_assets = cash + ar + prepaids + fixed_assets
        total_liabilities = ap + deferred + debt
        equity = decimal_value(row, "equity") or (total_assets - total_liabilities)
        rows.append(
            {
                "period": period,
                "cash": q_money(cash),
                "accounts_receivable": q_money(ar),
                "prepaids_and_other_current_assets": q_money(prepaids),
                "property_and_equipment_net": q_money(fixed_assets),
                "deferred_revenue": q_money(deferred),
                "accounts_payable": q_money(ap),
                "prepaids": q_money(prepaids),
                "fixed_assets": q_money(fixed_assets),
                "debt": q_money(debt),
                "equity": q_money(equity),
                "total_assets": q_money(total_assets),
                "total_liabilities": q_money(total_liabilities),
                "total_liabilities_and_equity": q_money(total_liabilities + equity),
                "balance_check": q_money(total_assets - total_liabilities - equity),
            }
        )
    return rows
