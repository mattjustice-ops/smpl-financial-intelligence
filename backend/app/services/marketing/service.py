"""Marketing performance reporting service."""

from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.marketing.schemas import ActualBudgetForecastResponse, ChartSeries, MarketingMetricRow, MarketingResponse
from app.services.reporting.marketing_metrics_service import (
    calculate_cost_per_mql,
    calculate_cost_per_sql,
    calculate_marketing_cac_proxy,
    calculate_pipeline_coverage,
    calculate_pipeline_per_spend,
    calculate_pipeline_waterfall,
    calculate_win_rate_on_pipeline_created,
    q_money,
)
from app.services.reporting.period_utils import period_range, scenario_periods, to_period
from app.services.reporting.validation_service import ValidationCheck, compare_values, warning

SCENARIO_TABLE = {
    "Actual": "actual_marketing_pipeline",
    "Budget": "budget_marketing_pipeline",
    "Forecast": "forecast_marketing_pipeline",
}


def _decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, str):
        cleaned = value.strip().replace("$", "").replace(",", "")
        if not cleaned:
            return Decimal("0")
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = f"-{cleaned[1:-1]}"
        if cleaned.endswith("%"):
            return Decimal(cleaned[:-1]) / Decimal("100")
        value = cleaned
    return Decimal(str(value))


def _table_exists(db: Session, table_name: str) -> bool:
    return db.execute(text("select to_regclass(:name)"), {"name": f"public.{table_name}"}).scalar() is not None


def _fetch_rows(db: Session, table_name: str, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    if not _table_exists(db, table_name):
        return []
    rows = db.execute(
        text(f'select * from "{table_name}" where organization_id = :organization_id'),
        {"organization_id": str(organization_id)},
    ).mappings()
    return [dict(row) for row in rows]


def _value(row: dict[str, Any], *keys: str) -> Decimal:
    for key in keys:
        if row.get(key) not in (None, ""):
            return _decimal(row.get(key))
    return Decimal("0")


def _normalize_row(organization_id: uuid.UUID, scenario: str, table_name: str, row: dict[str, Any]) -> MarketingMetricRow:
    period = to_period(row.get("period") or row.get("forecast_period"))
    marketing_spend = _value(row, "marketing_spend", "spend")
    mqls = _value(row, "mqls")
    sqls = _value(row, "sqls")
    sals = _value(row, "sals")
    opportunities_created = _value(row, "opportunities_created", "opportunities")
    pipeline_arr_created = _value(row, "pipeline_arr_created")
    closed_won_arr = _value(row, "closed_won_arr", "expected_closed_won_arr")
    closed_lost_arr = _value(row, "closed_lost_arr")
    slipped_pipeline_arr = _value(row, "slipped_pipeline_arr")
    beginning_pipeline_arr = _value(row, "beginning_pipeline_arr")
    ending_pipeline_arr = _value(row, "ending_pipeline_arr")
    return MarketingMetricRow(
        organization_id=str(organization_id),
        scenario=scenario,
        period=period,
        marketing_channel=str(row.get("marketing_channel") or "Unassigned"),
        marketing_spend=q_money(marketing_spend),
        mqls=mqls,
        sqls=sqls,
        sals=sals,
        opportunities_created=opportunities_created,
        pipeline_arr_created=q_money(pipeline_arr_created),
        closed_won_arr=q_money(closed_won_arr),
        closed_lost_arr=q_money(closed_lost_arr),
        slipped_pipeline_arr=q_money(slipped_pipeline_arr),
        beginning_pipeline_arr=q_money(beginning_pipeline_arr),
        ending_pipeline_arr=q_money(ending_pipeline_arr),
        cost_per_mql=calculate_cost_per_mql(marketing_spend, mqls),
        cost_per_sql=calculate_cost_per_sql(marketing_spend, sqls),
        pipeline_per_dollar_spend=calculate_pipeline_per_spend(pipeline_arr_created, marketing_spend),
        marketing_cac_proxy=calculate_marketing_cac_proxy(marketing_spend, closed_won_arr),
        pipeline_coverage_ratio=calculate_pipeline_coverage(pipeline_arr_created, closed_won_arr),
        win_rate_on_pipeline_created=calculate_win_rate_on_pipeline_created(closed_won_arr, pipeline_arr_created),
        source_table=table_name,
    )


def _load_marketing_rows(
    db: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: str,
    end_period: str,
    marketing_channel: str | None = None,
) -> list[MarketingMetricRow]:
    wanted = set(scenario_periods(scenario, start_period, end_period))
    rows: list[MarketingMetricRow] = []
    for source_scenario in sorted({item[0] for item in wanted}):
        table_name = SCENARIO_TABLE[source_scenario]
        for raw in _fetch_rows(db, table_name, organization_id):
            period = to_period(raw.get("period") or raw.get("forecast_period"))
            if (source_scenario, period) not in wanted:
                continue
            normalized = _normalize_row(organization_id, source_scenario, table_name, raw)
            if marketing_channel and normalized.marketing_channel != marketing_channel:
                continue
            rows.append(normalized)
    return sorted(rows, key=lambda row: (row.period, row.marketing_channel or ""))


def _aggregate(rows: list[MarketingMetricRow], *, by_channel: bool) -> list[MarketingMetricRow]:
    grouped: dict[tuple[str, str, str | None], list[MarketingMetricRow]] = defaultdict(list)
    for row in rows:
        channel = row.marketing_channel if by_channel else None
        grouped[(row.scenario, row.period, channel)].append(row)

    out: list[MarketingMetricRow] = []
    for (scenario, period, channel), items in grouped.items():
        marketing_spend = sum((r.marketing_spend for r in items), Decimal("0"))
        mqls = sum((r.mqls for r in items), Decimal("0"))
        sqls = sum((r.sqls for r in items), Decimal("0"))
        sals = sum((r.sals for r in items), Decimal("0"))
        opportunities_created = sum((r.opportunities_created for r in items), Decimal("0"))
        pipeline_arr_created = sum((r.pipeline_arr_created for r in items), Decimal("0"))
        closed_won_arr = sum((r.closed_won_arr for r in items), Decimal("0"))
        closed_lost_arr = sum((r.closed_lost_arr for r in items), Decimal("0"))
        slipped_pipeline_arr = sum((r.slipped_pipeline_arr for r in items), Decimal("0"))
        beginning_pipeline_arr = sum((r.beginning_pipeline_arr for r in items), Decimal("0"))
        ending_pipeline_arr = sum((r.ending_pipeline_arr for r in items), Decimal("0"))
        out.append(
            MarketingMetricRow(
                organization_id=items[0].organization_id,
                scenario=scenario,
                period=period,
                marketing_channel=channel,
                marketing_spend=q_money(marketing_spend),
                mqls=mqls,
                sqls=sqls,
                sals=sals,
                opportunities_created=opportunities_created,
                pipeline_arr_created=q_money(pipeline_arr_created),
                closed_won_arr=q_money(closed_won_arr),
                closed_lost_arr=q_money(closed_lost_arr),
                slipped_pipeline_arr=q_money(slipped_pipeline_arr),
                beginning_pipeline_arr=q_money(beginning_pipeline_arr),
                ending_pipeline_arr=q_money(ending_pipeline_arr),
                cost_per_mql=calculate_cost_per_mql(marketing_spend, mqls),
                cost_per_sql=calculate_cost_per_sql(marketing_spend, sqls),
                pipeline_per_dollar_spend=calculate_pipeline_per_spend(pipeline_arr_created, marketing_spend),
                marketing_cac_proxy=calculate_marketing_cac_proxy(marketing_spend, closed_won_arr),
                pipeline_coverage_ratio=calculate_pipeline_coverage(pipeline_arr_created, closed_won_arr),
                win_rate_on_pipeline_created=calculate_win_rate_on_pipeline_created(closed_won_arr, pipeline_arr_created),
                source_table=", ".join(sorted({r.source_table for r in items})),
            )
        )
    return sorted(out, key=lambda row: (row.period, row.marketing_channel or ""))


def _chart(rows: list[MarketingMetricRow], metric_names: list[str], *, series_by_channel: bool = False) -> dict[str, list[ChartSeries]]:
    charts: dict[str, list[ChartSeries]] = {}
    for metric in metric_names:
        series: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            name = row.marketing_channel or row.scenario if series_by_channel else row.scenario
            series[name].append({"period": row.period, "value": getattr(row, metric), "marketing_channel": row.marketing_channel, "scenario": row.scenario})
        charts[metric] = [ChartSeries(series_name=name, points=points) for name, points in sorted(series.items())]
    return charts


def _actual_closed_won_by_channel(db: Session, organization_id: uuid.UUID, start_period: str, end_period: str) -> dict[tuple[str, str], Decimal]:
    table_name = "actual_opportunities" if _table_exists(db, "actual_opportunities") else "opportunities"
    if not _table_exists(db, table_name):
        return {}
    out: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for raw in _fetch_rows(db, table_name, organization_id):
        if str(raw.get("stage") or "").lower() != "closed won":
            continue
        period_source = raw.get("close_date") or raw.get("forecast_period") or raw.get("expected_close_date")
        if not period_source:
            continue
        period = to_period(period_source)
        if period < start_period or period > end_period:
            continue
        channel = str(raw.get("marketing_channel") or "Unassigned")
        out[(period, channel)] += _value(raw, "amount_arr", "closed_won_arr")
    return out


def _validate(
    db: Session,
    organization_id: uuid.UUID,
    rows: list[MarketingMetricRow],
    *,
    scenario: str,
    start_period: str,
    end_period: str,
) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []
    actual_closed_won = _actual_closed_won_by_channel(db, organization_id, start_period, end_period)
    for row in rows:
        if row.beginning_pipeline_arr or row.ending_pipeline_arr:
            expected = calculate_pipeline_waterfall(
                row.beginning_pipeline_arr,
                row.pipeline_arr_created,
                row.closed_won_arr,
                row.closed_lost_arr,
                row.slipped_pipeline_arr,
            )
            checks.append(
                compare_values(
                    scenario=row.scenario,
                    period=row.period,
                    validation_name="pipeline_waterfall_ties",
                    expected_value=expected,
                    actual_value=row.ending_pipeline_arr,
                    source_tables_used=[row.source_table],
                )
            )
        if row.marketing_spend == 0 or row.mqls == 0 or row.sqls == 0 or row.pipeline_arr_created == 0:
            checks.append(
                warning(
                    scenario=row.scenario,
                    period=row.period,
                    validation_name="missing_active_channel_marketing_metrics",
                    actual_value=Decimal("0"),
                    source_tables_used=[row.source_table],
                )
            )
        if row.scenario == "Actual" and row.marketing_channel and (row.period, row.marketing_channel) in actual_closed_won:
            checks.append(
                compare_values(
                    scenario=row.scenario,
                    period=row.period,
                    validation_name="actual_marketing_closed_won_arr_ties_to_actual_opportunities",
                    expected_value=actual_closed_won[(row.period, row.marketing_channel)],
                    actual_value=row.closed_won_arr,
                    source_tables_used=[row.source_table, "actual_opportunities"],
                )
            )
    if scenario.lower() == "combined":
        for source_scenario, period in scenario_periods("Combined", start_period, end_period):
            matching = [r for r in rows if r.period == period]
            if matching and any(r.scenario != source_scenario for r in matching):
                checks.append(
                    warning(
                        scenario="Combined",
                        period=period,
                        validation_name="combined_scenario_period_source_mismatch",
                        source_tables_used=sorted({r.source_table for r in matching}),
                    )
                )
    return checks


def performance_summary(db: Session, organization_id: uuid.UUID, *, scenario: str, start_period: str, end_period: str, marketing_channel: str | None = None) -> MarketingResponse:
    rows = _aggregate(_load_marketing_rows(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period, marketing_channel=marketing_channel), by_channel=False)
    return MarketingResponse(organization_id=str(organization_id), scenario=scenario, start_period=start_period, end_period=end_period, rows=rows, charts=_chart(rows, ["marketing_spend", "pipeline_arr_created", "closed_won_arr"]), validation=_validate(db, organization_id, rows, scenario=scenario, start_period=start_period, end_period=end_period), metadata={"grain": "period"})


def channel_performance(db: Session, organization_id: uuid.UUID, *, scenario: str, start_period: str, end_period: str, marketing_channel: str | None = None) -> MarketingResponse:
    rows = _aggregate(_load_marketing_rows(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period, marketing_channel=marketing_channel), by_channel=True)
    return MarketingResponse(organization_id=str(organization_id), scenario=scenario, start_period=start_period, end_period=end_period, rows=rows, charts=_chart(rows, ["pipeline_arr_created", "marketing_spend", "closed_won_arr"], series_by_channel=True), validation=_validate(db, organization_id, rows, scenario=scenario, start_period=start_period, end_period=end_period), metadata={"grain": "period_channel"})


def pipeline_waterfall(db: Session, organization_id: uuid.UUID, *, scenario: str, start_period: str, end_period: str, marketing_channel: str | None = None) -> MarketingResponse:
    return channel_performance(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period, marketing_channel=marketing_channel)


def funnel_conversion(db: Session, organization_id: uuid.UUID, *, scenario: str, start_period: str, end_period: str, marketing_channel: str | None = None) -> MarketingResponse:
    rows = performance_summary(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period, marketing_channel=marketing_channel).rows
    return MarketingResponse(organization_id=str(organization_id), scenario=scenario, start_period=start_period, end_period=end_period, rows=rows, charts=_chart(rows, ["mqls", "sqls", "sals", "opportunities_created", "closed_won_arr"]), validation=_validate(db, organization_id, rows, scenario=scenario, start_period=start_period, end_period=end_period), metadata={"visualization": "funnel"})


def spend_efficiency(db: Session, organization_id: uuid.UUID, *, scenario: str, start_period: str, end_period: str, marketing_channel: str | None = None) -> MarketingResponse:
    rows = channel_performance(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period, marketing_channel=marketing_channel).rows
    return MarketingResponse(organization_id=str(organization_id), scenario=scenario, start_period=start_period, end_period=end_period, rows=rows, charts=_chart(rows, ["cost_per_mql", "cost_per_sql", "pipeline_per_dollar_spend", "marketing_cac_proxy"], series_by_channel=True), validation=_validate(db, organization_id, rows, scenario=scenario, start_period=start_period, end_period=end_period), metadata={"section": "efficiency"})


def actual_budget_forecast(db: Session, organization_id: uuid.UUID, *, start_period: str, end_period: str, marketing_channel: str | None = None) -> ActualBudgetForecastResponse:
    actual = performance_summary(db, organization_id, scenario="Actual", start_period=start_period, end_period=end_period, marketing_channel=marketing_channel).rows
    budget = performance_summary(db, organization_id, scenario="Budget", start_period=start_period, end_period=end_period, marketing_channel=marketing_channel).rows
    forecast = performance_summary(db, organization_id, scenario="Forecast", start_period=start_period, end_period=end_period, marketing_channel=marketing_channel).rows
    combined_response = performance_summary(db, organization_id, scenario="Combined", start_period=start_period, end_period=end_period, marketing_channel=marketing_channel)
    return ActualBudgetForecastResponse(organization_id=str(organization_id), start_period=start_period, end_period=end_period, actual=actual, budget=budget, forecast=forecast, combined=combined_response.rows, validation=combined_response.validation)
