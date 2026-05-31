"""Service orchestration for institutional-style SaaS forecast schedules."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Callable

from sqlalchemy.orm import Session

from app.services.driver_forecast.assumptions import assumption_map, fetch_driver_assumptions
from app.services.driver_forecast.balance_sheet_forecast_engine import build_balance_sheet_forecast
from app.services.driver_forecast.common import month_range, period_type, q_money
from app.services.driver_forecast.deferred_revenue_waterfall import build_deferred_revenue_waterfall
from app.services.driver_forecast.forecast_cash_flow_engine import build_cash_flow_forecast
from app.services.driver_forecast.operating_cash_bridge import build_operating_cash_bridge
from app.services.driver_forecast.schemas import ChartPoint, DriverSummaryResponse, ForecastScheduleResponse, TableRow
from app.services.driver_forecast.working_capital_engine import build_working_capital_forecast


Builder = Callable[..., list[dict]]


def _response(
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: date,
    end_period: date,
    schedule_name: str,
    rows: list[dict],
    chart_fields: list[str],
    metadata: dict | None = None,
) -> ForecastScheduleResponse:
    periods = month_range(start_period, end_period)
    actual_periods = [p for p in periods if period_type(p) == "actual"]
    forecast_periods = [p for p in periods if period_type(p) == "forecast"]
    table_rows: list[TableRow] = []
    charts: dict[str, list[ChartPoint]] = {field: [] for field in chart_fields}
    for raw in rows:
        period = raw["period"]
        values = {k: v for k, v in raw.items() if k != "period"}
        table_rows.append(TableRow(period=period, period_type=period_type(period), values=values))
        for field in chart_fields:
            if field in values and isinstance(values[field], Decimal):
                charts[field].append(
                    ChartPoint(
                        period=period,
                        value=q_money(values[field]),
                        period_type=period_type(period),
                        series=field,
                    )
                )
    return ForecastScheduleResponse(
        organization_id=str(organization_id),
        scenario=scenario,
        start_period=start_period,
        end_period=end_period,
        schedule_name=schedule_name,
        actual_periods=actual_periods,
        forecast_periods=forecast_periods,
        rows=table_rows,
        charts=charts,
        metadata=metadata or {},
    )


def _assumptions(session: Session, organization_id: uuid.UUID, scenario: str, start_period: date, end_period: date) -> dict[str, Decimal]:
    return assumption_map(
        fetch_driver_assumptions(
            session,
            organization_id,
            scenario=scenario,
            start_period=start_period,
            end_period=end_period,
        )
    )


def cash_flow_schedule(session: Session, organization_id: uuid.UUID, *, scenario: str, start_period: date, end_period: date) -> ForecastScheduleResponse:
    assumptions = _assumptions(session, organization_id, scenario, start_period, end_period)
    rows = build_cash_flow_forecast(session, organization_id, start_period=start_period, end_period=end_period, assumptions=assumptions)
    return _response(organization_id, scenario=scenario, start_period=start_period, end_period=end_period, schedule_name="cash_flow", rows=rows, chart_fields=["ending_cash", "operating_cash_flow", "investing_cash_flow", "financing_cash_flow"], metadata={"method": "driver_based"})


def deferred_revenue_schedule(session: Session, organization_id: uuid.UUID, *, scenario: str, start_period: date, end_period: date) -> ForecastScheduleResponse:
    rows = build_deferred_revenue_waterfall(session, organization_id, start_period=start_period, end_period=end_period)
    return _response(organization_id, scenario=scenario, start_period=start_period, end_period=end_period, schedule_name="deferred_revenue_waterfall", rows=rows, chart_fields=["beginning_deferred_revenue", "new_billings", "revenue_recognized", "ending_deferred_revenue"])


def working_capital_schedule(session: Session, organization_id: uuid.UUID, *, scenario: str, start_period: date, end_period: date) -> ForecastScheduleResponse:
    assumptions = _assumptions(session, organization_id, scenario, start_period, end_period)
    rows = build_working_capital_forecast(session, organization_id, start_period=start_period, end_period=end_period, assumptions=assumptions)
    return _response(organization_id, scenario=scenario, start_period=start_period, end_period=end_period, schedule_name="working_capital", rows=rows, chart_fields=["accounts_receivable", "deferred_revenue", "accounts_payable", "collections"])


def operating_cash_bridge_schedule(session: Session, organization_id: uuid.UUID, *, scenario: str, start_period: date, end_period: date) -> ForecastScheduleResponse:
    assumptions = _assumptions(session, organization_id, scenario, start_period, end_period)
    rows = build_operating_cash_bridge(session, organization_id, start_period=start_period, end_period=end_period, assumptions=assumptions)
    return _response(organization_id, scenario=scenario, start_period=start_period, end_period=end_period, schedule_name="operating_cash_bridge", rows=rows, chart_fields=["net_income", "net_cash_from_operating_activities"])


def balance_sheet_schedule(session: Session, organization_id: uuid.UUID, *, scenario: str, start_period: date, end_period: date) -> ForecastScheduleResponse:
    assumptions = _assumptions(session, organization_id, scenario, start_period, end_period)
    rows = build_balance_sheet_forecast(session, organization_id, start_period=start_period, end_period=end_period, assumptions=assumptions)
    return _response(organization_id, scenario=scenario, start_period=start_period, end_period=end_period, schedule_name="balance_sheet", rows=rows, chart_fields=["cash", "accounts_receivable", "deferred_revenue", "accounts_payable", "equity", "total_assets"])


def assumptions_schedule(session: Session, organization_id: uuid.UUID, *, scenario: str, start_period: date, end_period: date) -> ForecastScheduleResponse:
    assumptions = fetch_driver_assumptions(session, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)
    rows = [
        {
            "period": a.effective_period,
            "assumption_name": a.assumption_name,
            "assumption_category": a.assumption_category,
            "actual_value": a.actual_value or Decimal("0"),
            "forecast_value": a.forecast_value or Decimal("0"),
        }
        for a in assumptions
    ]
    return _response(organization_id, scenario=scenario, start_period=start_period, end_period=end_period, schedule_name="assumptions", rows=rows, chart_fields=["forecast_value"], metadata={"grain": "assumption_period"})


def driver_summary(session: Session, organization_id: uuid.UUID, *, scenario: str, start_period: date, end_period: date) -> DriverSummaryResponse:
    cash = cash_flow_schedule(session, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)
    deferred = deferred_revenue_schedule(session, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)
    working_capital = working_capital_schedule(session, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)
    bridge = operating_cash_bridge_schedule(session, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)
    bs = balance_sheet_schedule(session, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)
    assumptions = assumptions_schedule(session, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)
    ending_cash = cash.rows[-1].values.get("ending_cash", Decimal("0")) if cash.rows else Decimal("0")
    ending_arr = Decimal("0")
    return DriverSummaryResponse(
        organization_id=str(organization_id),
        scenario=scenario,
        start_period=start_period,
        end_period=end_period,
        actual_periods=cash.actual_periods,
        forecast_periods=cash.forecast_periods,
        kpis={"ending_cash": ending_cash if isinstance(ending_cash, Decimal) else Decimal("0"), "ending_arr": ending_arr},
        schedules={"cash_flow": cash, "deferred_revenue_waterfall": deferred, "working_capital": working_capital, "operating_cash_bridge": bridge, "balance_sheet": bs, "assumptions": assumptions},
        dbt_models=["stg_actual_income_statement", "stg_forecast_opportunities", "int_billings_forecast", "int_deferred_revenue_waterfall", "fct_driver_cash_flow", "fct_forecast_balance_sheet"],
        frontend_visualizations={"line_charts": ["ending_cash", "accounts_receivable", "deferred_revenue"], "waterfalls": ["deferred_revenue_waterfall"], "bridges": ["operating_cash_bridge"], "tables": ["assumptions", "balance_sheet"]},
    )
