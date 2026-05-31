"""Operating cash flow bridge forecast."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.driver_forecast.common import month_range, period_type, q_money
from app.services.driver_forecast.repository import decimal_value, fetch_period_rows


def build_operating_cash_bridge(
    session: Session,
    organization_id,
    *,
    start_period: date,
    end_period: date,
    assumptions: dict[str, Decimal],
) -> list[dict[str, Decimal | date]]:
    periods = month_range(start_period, end_period)
    income_rows = fetch_period_rows(
        session,
        table_name="forecast_income_statement",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    cf_rows = fetch_period_rows(
        session,
        table_name="forecast_cash_flow_statement",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    income_by_period = {r["period"]: r for r in income_rows}
    cf_by_period = {r["period"]: r for r in cf_rows}
    actual_income_rows = fetch_period_rows(
        session,
        table_name="actual_income_statement",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    actual_cf_rows = fetch_period_rows(
        session,
        table_name="actual_cash_flow_statement",
        organization_id=organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    actual_income_by_period = {r["period"]: r for r in actual_income_rows}
    actual_cf_by_period = {r["period"]: r for r in actual_cf_rows}
    rows: list[dict[str, Decimal | date]] = []
    for period in periods:
        income = actual_income_by_period.get(period, {}) if period_type(period) == "actual" else income_by_period.get(period, {})
        cf = actual_cf_by_period.get(period, {}) if period_type(period) == "actual" else cf_by_period.get(period, {})
        net_income = decimal_value(cf, "net_income") or decimal_value(income, "net_income")
        da = decimal_value(cf, "depreciation_and_amortization")
        sbc = abs(decimal_value(income, "sales_and_marketing")) * assumptions.get("sbc_pct_of_payroll", Decimal("0.05"))
        if period_type(period) == "actual":
            sbc = Decimal("0")
        ar = decimal_value(cf, "change_in_accounts_receivable")
        deferred = decimal_value(cf, "change_in_deferred_revenue")
        ap = decimal_value(cf, "change_in_accounts_payable")
        prepaids = Decimal("0")
        other = Decimal("0")
        ocf = decimal_value(cf, "net_cash_from_operating_activities") or (
            net_income + da + sbc + ar + deferred + ap + prepaids + other
        )
        rows.append(
            {
                "period": period,
                "net_income": q_money(net_income),
                "depreciation_and_amortization": q_money(da),
                "stock_based_compensation": q_money(sbc),
                "noncash_items": q_money(Decimal("0")),
                "change_in_accounts_receivable": q_money(ar),
                "change_in_deferred_revenue": q_money(deferred),
                "change_in_accounts_payable": q_money(ap),
                "change_in_prepaids": q_money(prepaids),
                "change_in_other_working_capital": q_money(other),
                "net_cash_from_operating_activities": q_money(ocf),
            }
        )
    return rows
