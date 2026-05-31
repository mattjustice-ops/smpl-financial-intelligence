"""Normalized attribution views for expandable waterfalls."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import fetch_scenario_rows, str_any, value_any
from app.services.dashboard.schemas import WaterfallAttributionRow


def arr_waterfall_attribution_view(db: Session, organization_id: uuid.UUID, **params) -> list[WaterfallAttributionRow]:
    rows: list[WaterfallAttributionRow] = []
    for scenario, period, table_name, raw in fetch_scenario_rows(db, organization_id, suffix="mrr_waterfall", fallback="mrr_waterfall", **params):
        metrics = {
            "beginning": value_any(raw, "beginning_arr", "beginning_mrr") * (Decimal("12") if raw.get("beginning_arr") in (None, "") else Decimal("1")),
            "new_business": value_any(raw, "new_business_arr", "new_mrr") * (Decimal("12") if raw.get("new_business_arr") in (None, "") else Decimal("1")),
            "expansion": value_any(raw, "expansion_arr", "expansion_mrr") * (Decimal("12") if raw.get("expansion_arr") in (None, "") else Decimal("1")),
            "contraction": -abs(value_any(raw, "contraction_arr", "contraction_mrr") * (Decimal("12") if raw.get("contraction_arr") in (None, "") else Decimal("1"))),
            "churn": -abs(value_any(raw, "churn_arr", "churn_mrr") * (Decimal("12") if raw.get("churn_arr") in (None, "") else Decimal("1"))),
            "reactivation": value_any(raw, "reactivation_arr", "reactivation_mrr") * (Decimal("12") if raw.get("reactivation_arr") in (None, "") else Decimal("1")),
            "ending": value_any(raw, "ending_arr", "ending_mrr") * (Decimal("12") if raw.get("ending_arr") in (None, "") else Decimal("1")),
        }
        for waterfall_type, amount in metrics.items():
            if amount == 0 and waterfall_type not in {"beginning", "ending"}:
                continue
            rows.append(
                WaterfallAttributionRow(
                    organization_id=str(organization_id),
                    scenario=scenario,
                    period=period,
                    waterfall_type=waterfall_type,
                    customer_id=str_any(raw, "customer_id"),
                    customer_name=str_any(raw, "customer_name"),
                    segment=str_any(raw, "segment"),
                    arr_impact=amount,
                    mrr_impact=amount / Decimal("12"),
                    amount=amount,
                    source_table=table_name,
                    raw={k: str(v) for k, v in raw.items() if v is not None},
                )
            )
    return rows


def pipeline_waterfall_attribution_view(db: Session, organization_id: uuid.UUID, **params) -> list[WaterfallAttributionRow]:
    rows: list[WaterfallAttributionRow] = []
    explicit_keys: set[tuple[str, str, str | None]] = set()
    explicit_periods: set[tuple[str, str]] = set()
    actual_jan_beginning_by_channel: dict[str | None, Decimal] = {}
    for scenario, period, table_name, raw in fetch_scenario_rows(db, organization_id, suffix="pipeline_waterfall", fallback=None, **params):
        channel = str_any(raw, "marketing_channel")
        explicit_keys.add((scenario, period, channel))
        explicit_periods.add((scenario, period))
        if scenario == "Actual" and period == "2026-01":
            actual_jan_beginning_by_channel[channel] = value_any(raw, "beginning_pipeline_arr")
        metrics = {
            "beginning_pipeline": value_any(raw, "beginning_pipeline_arr"),
            "pipeline_created": value_any(raw, "pipeline_arr_created"),
            "closed_won": -abs(value_any(raw, "closed_won_arr", "expected_closed_won_arr")),
            "closed_lost": -abs(value_any(raw, "closed_lost_arr")),
            "slipped_pipeline": -abs(value_any(raw, "slipped_pipeline_arr")),
            "ending_pipeline": value_any(raw, "ending_pipeline_arr"),
        }
        for waterfall_type, amount in metrics.items():
            rows.append(
                WaterfallAttributionRow(
                    organization_id=str(organization_id),
                    scenario=scenario,
                    period=period,
                    waterfall_type=waterfall_type,
                    marketing_channel=channel,
                    amount=amount,
                    arr_impact=amount,
                    source_table=table_name,
                    raw={k: str(v) for k, v in raw.items() if v is not None},
                )
            )

    running_ending_by_channel: dict[tuple[str, str | None], Decimal] = {}
    fallback_rows = sorted(
        fetch_scenario_rows(db, organization_id, suffix="marketing_pipeline", **params),
        key=lambda item: (item[0], str_any(item[3], "marketing_channel") or "", item[1]),
    )
    for scenario, period, table_name, raw in fallback_rows:
        channel = str_any(raw, "marketing_channel")
        if (scenario, period) in explicit_periods:
            continue
        if (scenario, period, channel) in explicit_keys:
            continue
        pipeline_created = value_any(raw, "pipeline_arr_created")
        closed_won = value_any(raw, "closed_won_arr", "expected_closed_won_arr")
        closed_lost = value_any(raw, "closed_lost_arr")
        slipped = value_any(raw, "slipped_pipeline_arr")
        beginning = value_any(raw, "beginning_pipeline_arr")
        if scenario == "Budget" and period == "2026-01" and beginning == 0:
            beginning = actual_jan_beginning_by_channel.get(channel, Decimal("0"))
        if beginning == 0:
            beginning = running_ending_by_channel.get((scenario, channel), Decimal("0"))
        ending = value_any(raw, "ending_pipeline_arr")
        if ending == 0:
            ending = beginning + pipeline_created - closed_won - closed_lost - slipped
        running_ending_by_channel[(scenario, channel)] = ending
        for waterfall_type, amount in {
            "beginning_pipeline": beginning,
            "pipeline_created": pipeline_created,
            "closed_won": -abs(closed_won),
            "closed_lost": -abs(closed_lost),
            "slipped_pipeline": -abs(slipped),
            "ending_pipeline": ending,
        }.items():
            rows.append(
                WaterfallAttributionRow(
                    organization_id=str(organization_id),
                    scenario=scenario,
                    period=period,
                    waterfall_type=waterfall_type,
                    marketing_channel=channel,
                    amount=amount,
                    arr_impact=amount,
                    source_table=table_name,
                    raw={k: str(v) for k, v in raw.items() if v is not None},
                )
            )
    return rows


def deferred_revenue_attribution_view(db: Session, organization_id: uuid.UUID, **params) -> list[WaterfallAttributionRow]:
    rows: list[WaterfallAttributionRow] = []
    deferred_rows = fetch_scenario_rows(db, organization_id, suffix="deferred_revenue_waterfall", **params)
    forecast_deferred_runoff: dict[str, Decimal] = {}
    forecast_rows = sorted(
        [(period, raw) for scenario, period, _table_name, raw in deferred_rows if scenario == "Forecast"],
        key=lambda item: item[0],
    )
    if forecast_rows:
        # Treat the opening forecast deferred balance as a static revenue source
        # and run it down over the remaining forecast months. New/renewal/expansion
        # activity is layered separately below instead of grouped into deferred.
        opening_deferred_balance = value_any(forecast_rows[0][1], "beginning_deferred_revenue")
        total_weight = sum(range(1, len(forecast_rows) + 1))
        for index, (period, _raw) in enumerate(forecast_rows):
            weight = len(forecast_rows) - index
            forecast_deferred_runoff[period] = opening_deferred_balance * Decimal(weight) / Decimal(total_weight)

    for scenario, period, table_name, raw in deferred_rows:
        revenue_recognized = value_any(raw, "revenue_recognized")
        deferred_revenue_recognized = forecast_deferred_runoff.get(period, revenue_recognized) if scenario == "Forecast" else revenue_recognized
        for waterfall_type, amount in {
            "beginning_deferred_revenue": value_any(raw, "beginning_deferred_revenue"),
            "new_billings": value_any(raw, "new_billings", "billings"),
            "revenue_recognized": -abs(revenue_recognized),
            "deferred_revenue_recognized": deferred_revenue_recognized,
            "ending_deferred_revenue": value_any(raw, "ending_deferred_revenue"),
        }.items():
            rows.append(
                WaterfallAttributionRow(
                    organization_id=str(organization_id),
                    scenario=scenario,
                    period=period,
                    waterfall_type=waterfall_type,
                    customer_id=str_any(raw, "customer_id"),
                    customer_name=str_any(raw, "customer_name"),
                    amount=amount,
                    revenue_impact=amount if waterfall_type == "deferred_revenue_recognized" else Decimal("0"),
                    source_table=table_name,
                    raw={k: str(v) for k, v in raw.items() if v is not None},
                )
            )

    # GAAP revenue-by-source rows are applied on summarized waterfall rows via
    # gaap_revenue_forecast_service (MRR carry-forward for forecast months).
    return rows


def cash_flow_attribution_view(db: Session, organization_id: uuid.UUID, **params) -> list[WaterfallAttributionRow]:
    rows: list[WaterfallAttributionRow] = []
    for scenario, period, table_name, raw in fetch_scenario_rows(db, organization_id, suffix="cash_flow_bridge", **params):
        metrics = {
            "beginning_cash": value_any(raw, "beginning_cash"),
            "cash_collections": value_any(raw, "cash_collections_from_invoices", "cash_collections", "collections"),
            "payroll_cash_out": -abs(value_any(raw, "payroll_cash_out")),
            "commission_cash_out": -abs(value_any(raw, "commission_cash_out")),
            "vendor_cash_out": -abs(value_any(raw, "vendor_cash_out_n30", "vendor_cash_out")),
            "tax_cash_out": -abs(value_any(raw, "tax_cash_out")),
            "capex": -abs(value_any(raw, "capex", "capital_expenditures")),
            "financing": value_any(raw, "financing_to_maintain_cash_floor", "financing", "debt_issuance_repayment"),
            "ending_cash": value_any(raw, "ending_cash"),
        }
        for waterfall_type, amount in metrics.items():
            rows.append(
                WaterfallAttributionRow(
                    organization_id=str(organization_id),
                    scenario=scenario,
                    period=period,
                    waterfall_type=waterfall_type,
                    amount=amount,
                    cash_impact=amount,
                    source_table=table_name,
                    raw={k: str(v) for k, v in raw.items() if v is not None},
                )
            )
    return rows
