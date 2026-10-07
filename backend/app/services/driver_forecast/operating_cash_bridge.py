"""Operating cash flow bridge from the loaded cash flow and income statements."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.driver_forecast.common import month_range, period_type, q_opt
from app.services.driver_forecast.repository import loaded_value
from app.services.financial_statements.financial_statement_service import gl_cash_flow_rows, gl_income_rows

# Net income to operating cash flow; ``bridge_check`` is operating cash flow less these lines.
BRIDGE_LINES = (
    "net_income",
    "depreciation_and_amortization",
    "stock_based_compensation",
    "other_non_cash",
    "change_in_accounts_receivable",
    "change_in_prepaids",
    "change_in_deferred_commissions",
    "change_in_accounts_payable",
    "change_in_deferred_revenue",
    "change_in_other_liabilities",
    "unclassified",
)

def build_operating_cash_bridge(
    session: Session,
    organization_id,
    *,
    start_period: date,
    end_period: date,
    assumptions: dict[str, Decimal] | None = None,
) -> list[dict[str, Decimal | date | None]]:
    periods = month_range(start_period, end_period)
    income_by_scenario = {
        s: {r["period"]: r for r in gl_income_rows(session, organization_id, s, start_period, end_period)}
        for s in ("Actual", "Forecast")
    }
    cf_by_scenario = {
        s: {r["period"]: r for r in gl_cash_flow_rows(session, organization_id, s, start_period, end_period)}
        for s in ("Actual", "Forecast")
    }
    rows: list[dict[str, Decimal | date | None]] = []
    for period in periods:
        scenario = "Actual" if period_type(period) == "actual" else "Forecast"
        income = income_by_scenario[scenario].get(period)
        cf = cf_by_scenario[scenario].get(period)
        row: dict[str, Decimal | date | None] = {
            "period": period,
            "net_income": q_opt(loaded_value(cf, "net_income") or loaded_value(income, "net_income")),
        }
        row.update({line: q_opt(loaded_value(cf, line)) for line in BRIDGE_LINES[1:]})
        ocf = loaded_value(cf, "net_cash_from_operating_activities")
        row["net_cash_from_operating_activities"] = q_opt(ocf)
        lines = [row[line] for line in BRIDGE_LINES]
        row["bridge_check"] = (
            None if ocf is None or any(v is None for v in lines) else q_opt(ocf - sum(lines, Decimal("0")))
        )
        rows.append(row)
    return rows
