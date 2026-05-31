"""Waterfall summary services."""

from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import commentary_prompts
from app.services.dashboard.schemas import WaterfallAttributionRow, WaterfallResponse, WaterfallSummaryRow
from app.services.dashboard.gaap_revenue_forecast_service import (
    apply_gaap_revenue_forecast_rows,
    is_actual_period,
)
from app.services.dashboard.pipeline_opportunity_drilldown_service import (
    PIPELINE_DRILLDOWN_TYPES,
    pipeline_movement_detail_counts,
)
from app.services.dashboard.cash_flow_gl_drilldown_service import (
    CASH_BALANCE_TYPES,
    cash_flow_gl_detail_counts,
)
from app.services.dashboard.waterfall_attribution_service import (
    arr_waterfall_attribution_view,
    cash_flow_attribution_view,
    deferred_revenue_attribution_view,
    pipeline_waterfall_attribution_view,
)
from app.services.reporting.validation_service import ValidationCheck, compare_values, warning


LINE_ORDER = {
    "beginning": 100,
    "new_business": 200,
    "expansion": 300,
    "contraction": 500,
    "churn": 600,
    "reactivation": 700,
    "ending": 900,
    "beginning_pipeline": 100,
    "pipeline_created": 200,
    "closed_won": 300,
    "closed_lost": 400,
    "slipped_pipeline": 500,
    "ending_pipeline": 900,
    "beginning_deferred_revenue": 100,
    "new_billings": 200,
    "revenue_recognized": 300,
    "ending_deferred_revenue": 900,
    "deferred_revenue_recognized": 310,
    "renewal_revenue": 320,
    "new_business_revenue": 330,
    "expansion_revenue": 340,
    "contraction_revenue": 350,
    "churn_revenue": 360,
    "reactivation_revenue": 370,
    "total_gaap_revenue": 399,
    "beginning_cash": 100,
    "cash_collections": 200,
    "payroll_cash_out": 300,
    "commission_cash_out": 400,
    "vendor_cash_out": 500,
    "tax_cash_out": 600,
    "capex": 700,
    "financing": 800,
    "ending_cash": 900,
}


def _label(value: str) -> str:
    return value.replace("_", " ").title().replace("Arr", "ARR").replace("Mrr", "MRR")


def _summarize(organization_id: uuid.UUID, waterfall_name: str, attribution: list[WaterfallAttributionRow]) -> list[WaterfallSummaryRow]:
    grouped: dict[tuple[str, str, str, str], list[WaterfallAttributionRow]] = defaultdict(list)
    for row in attribution:
        grouped[(row.scenario, row.period, row.waterfall_type, row.source_table)].append(row)
    out: list[WaterfallSummaryRow] = []
    for (scenario, period, waterfall_type, source_table), rows in grouped.items():
        out.append(
            WaterfallSummaryRow(
                organization_id=str(organization_id),
                scenario=scenario,
                period=period,
                waterfall_name=waterfall_name,
                waterfall_type=waterfall_type,
                line_item=_label(waterfall_type),
                line_item_order=LINE_ORDER.get(waterfall_type, 999),
                amount=sum((r.amount for r in rows), Decimal("0")),
                source_table=source_table,
                detail_count=len(rows),
            )
        )
    if waterfall_name == "arr":
        _roll_arr_waterfall_balances(out, organization_id)
    return sorted(out, key=lambda r: (r.period, r.line_item_order))


def _add_total_gaap_revenue_rows(
    rows: list[WaterfallSummaryRow],
    organization_id: uuid.UUID,
    *,
    income_statement_revenue: dict[str, Decimal] | None = None,
) -> None:
    """Total GAAP equals income statement revenue (actual and forecast months)."""
    income_by_period = income_statement_revenue or {}

    for period, amount in sorted(income_by_period.items(), key=lambda item: item[0]):
        actual = is_actual_period(period)
        rows.append(
            WaterfallSummaryRow(
                organization_id=str(organization_id),
                scenario="Actual" if actual else "Forecast",
                period=period,
                waterfall_name="deferred_revenue",
                waterfall_type="total_gaap_revenue",
                line_item="Total GAAP Revenue",
                line_item_order=LINE_ORDER["total_gaap_revenue"],
                amount=amount,
                source_table="actual_income_statement" if actual else "forecast_income_statement",
                detail_count=0,
            )
        )


def _roll_arr_waterfall_balances(rows: list[WaterfallSummaryRow], organization_id: uuid.UUID) -> None:
    """Force ARR waterfall balances to roll from movements.

    Displayed ending ARR is calculated as:
    beginning + new business + expansion - contraction - churn + reactivation.
    Each next period's beginning ARR is then set to the prior calculated ending.
    """
    rows_by_key = {(row.scenario, row.period, row.waterfall_type): row for row in rows}
    source_by_scenario_period: dict[tuple[str, str], set[str]] = defaultdict(set)
    periods_by_scenario: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        periods_by_scenario[row.scenario].add(row.period)
        source_by_scenario_period[(row.scenario, row.period)].add(row.source_table)

    def ensure_row(scenario: str, period: str, waterfall_type: str) -> WaterfallSummaryRow:
        key = (scenario, period, waterfall_type)
        if key in rows_by_key:
            return rows_by_key[key]
        source_table = ", ".join(sorted(source_by_scenario_period[(scenario, period)])) or "calculated"
        row = WaterfallSummaryRow(
            organization_id=str(organization_id),
            scenario=scenario,
            period=period,
            waterfall_name="arr",
            waterfall_type=waterfall_type,
            line_item=_label(waterfall_type),
            line_item_order=LINE_ORDER.get(waterfall_type, 999),
            amount=Decimal("0"),
            source_table=source_table,
            detail_count=0,
        )
        rows_by_key[key] = row
        rows.append(row)
        return row

    combined_actual_forecast = set(periods_by_scenario).issubset({"Actual", "Forecast"}) and len(periods_by_scenario) > 1
    if combined_actual_forecast:
        sequences = {
            "Combined": sorted(
                ((scenario, period) for scenario, periods in periods_by_scenario.items() for period in periods),
                key=lambda item: item[1],
            )
        }
    else:
        sequences = {
            scenario: [(scenario, period) for period in sorted(periods)]
            for scenario, periods in periods_by_scenario.items()
        }

    for _sequence_name, sequence in sequences.items():
        prior_ending: Decimal | None = None
        for scenario, period in sequence:
            beginning_row = ensure_row(scenario, period, "beginning")
            if prior_ending is not None:
                beginning_row.amount = prior_ending

            beginning = beginning_row.amount
            new_business = rows_by_key.get((scenario, period, "new_business"))
            expansion = rows_by_key.get((scenario, period, "expansion"))
            contraction = rows_by_key.get((scenario, period, "contraction"))
            churn = rows_by_key.get((scenario, period, "churn"))
            reactivation = rows_by_key.get((scenario, period, "reactivation"))

            ending = (
                beginning
                + (new_business.amount if new_business else Decimal("0"))
                + (expansion.amount if expansion else Decimal("0"))
                + (reactivation.amount if reactivation else Decimal("0"))
                + (contraction.amount if contraction else Decimal("0"))
                + (churn.amount if churn else Decimal("0"))
            )

            ending_row = ensure_row(scenario, period, "ending")
            ending_row.amount = ending
            ending_row.source_table = f"{ending_row.source_table}, calculated_rollforward" if "calculated_rollforward" not in ending_row.source_table else ending_row.source_table
            prior_ending = ending


def _validate(rows: list[WaterfallSummaryRow], waterfall_name: str) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []
    by_period: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    source_by_period: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in rows:
        by_period[(row.scenario, row.period)][row.waterfall_type] += row.amount
        source_by_period[(row.scenario, row.period)].add(row.source_table)
    for (scenario, period), values in by_period.items():
        sources = sorted(source_by_period[(scenario, period)])
        if waterfall_name == "arr":
            expected = values["beginning"] + values["new_business"] + values["expansion"] + values["reactivation"] + values["contraction"] + values["churn"]
            actual = values["ending"]
            checks.append(compare_values(scenario=scenario, period=period, validation_name="arr_waterfall_ties", expected_value=expected, actual_value=actual, source_tables_used=sources))
        elif waterfall_name == "pipeline":
            balance_types = (
                "beginning_pipeline",
                "pipeline_created",
                "closed_won",
                "closed_lost",
                "slipped_pipeline",
                "ending_pipeline",
            )
            if all(balance_type in values for balance_type in balance_types):
                expected = (
                    values["beginning_pipeline"]
                    + values["pipeline_created"]
                    + values["closed_won"]
                    + values["closed_lost"]
                    + values["slipped_pipeline"]
                )
                actual = values["ending_pipeline"]
                checks.append(
                    compare_values(
                        scenario=scenario,
                        period=period,
                        validation_name="pipeline_waterfall_ties",
                        expected_value=expected,
                        actual_value=actual,
                        source_tables_used=sources,
                    )
                )
        elif waterfall_name == "deferred_revenue":
            balance_types = (
                "beginning_deferred_revenue",
                "new_billings",
                "revenue_recognized",
                "ending_deferred_revenue",
            )
            if all(balance_type in values for balance_type in balance_types):
                expected = (
                    values["beginning_deferred_revenue"]
                    + values["new_billings"]
                    + values["revenue_recognized"]
                )
                actual = values["ending_deferred_revenue"]
                checks.append(
                    compare_values(
                        scenario=scenario,
                        period=period,
                        validation_name="deferred_revenue_waterfall_ties",
                        expected_value=expected,
                        actual_value=actual,
                        source_tables_used=sources,
                    )
                )
        elif waterfall_name == "cash_flow":
            expected = values["beginning_cash"] + values["cash_collections"] + values["payroll_cash_out"] + values["commission_cash_out"] + values["vendor_cash_out"] + values["tax_cash_out"] + values["capex"] + values["financing"]
            actual = values["ending_cash"]
            checks.append(compare_values(scenario=scenario, period=period, validation_name="cash_bridge_ties", expected_value=expected, actual_value=actual, source_tables_used=sources))
    gaap_forecast_only_types = {
        "renewal_revenue",
        "new_business_revenue",
        "expansion_revenue",
        "reactivation_revenue",
        "total_gaap_revenue",
    }
    for row in rows:
        if row.detail_count == 0 and not (
            waterfall_name == "pipeline" and row.waterfall_type not in PIPELINE_DRILLDOWN_TYPES
        ) and not (
            waterfall_name == "deferred_revenue" and row.waterfall_type in gaap_forecast_only_types
        ) and not (
            waterfall_name == "cash_flow" and row.waterfall_type in CASH_BALANCE_TYPES
        ):
            checks.append(warning(scenario=row.scenario, period=row.period, validation_name="expandable_section_empty", source_tables_used=[row.source_table]))
    if waterfall_name == "arr":
        for scenario in sorted({scenario for scenario, _period in by_period}):
            scenario_periods = sorted(period for item_scenario, period in by_period if item_scenario == scenario)
            for current_period, next_period in zip(scenario_periods, scenario_periods[1:]):
                ending = by_period[(scenario, current_period)]["ending"]
                next_beginning = by_period[(scenario, next_period)]["beginning"]
                checks.append(
                    compare_values(
                        scenario=scenario,
                        period=next_period,
                        validation_name="arr_ending_balance_equals_next_beginning_balance",
                        expected_value=ending,
                        actual_value=next_beginning,
                        source_tables_used=sorted(source_by_period[(scenario, current_period)] | source_by_period[(scenario, next_period)]),
                    )
                )
    return checks


def waterfall_response(db: Session, organization_id: uuid.UUID, *, waterfall_name: str, **params) -> WaterfallResponse:
    if waterfall_name == "arr":
        attribution = arr_waterfall_attribution_view(db, organization_id, **params)
    elif waterfall_name == "pipeline":
        attribution = pipeline_waterfall_attribution_view(db, organization_id, **params)
    elif waterfall_name == "deferred_revenue":
        attribution = deferred_revenue_attribution_view(db, organization_id, **params)
    elif waterfall_name == "cash_flow":
        attribution = cash_flow_attribution_view(db, organization_id, **params)
    else:
        attribution = []
    if params.get("waterfall_type"):
        attribution = [row for row in attribution if row.waterfall_type == params["waterfall_type"]]
    rows = _summarize(organization_id, waterfall_name, attribution)
    if waterfall_name == "deferred_revenue":
        rows = [row for row in rows if row.waterfall_type != "total_gaap_revenue"]
        rows, income_statement_totals = apply_gaap_revenue_forecast_rows(
            db,
            organization_id,
            rows,
            scenario=params["scenario"],
            start_period=params["start_period"],
            end_period=params["end_period"],
        )
        _add_total_gaap_revenue_rows(rows, organization_id, income_statement_revenue=income_statement_totals)
    if waterfall_name == "pipeline":
        movement_counts = pipeline_movement_detail_counts(db, organization_id, **params)
        for row in rows:
            row.detail_count = movement_counts.get((row.scenario, row.period, row.waterfall_type), 0)
        attribution = []
    if waterfall_name == "cash_flow":
        detail_counts = cash_flow_gl_detail_counts(db, organization_id, **params)
        for row in rows:
            row.detail_count = detail_counts.get((row.scenario, row.period, row.waterfall_type), 0)
        attribution = []
    return WaterfallResponse(
        organization_id=str(organization_id),
        scenario=params["scenario"],
        start_period=params["start_period"],
        end_period=params["end_period"],
        waterfall_name=waterfall_name,
        rows=rows,
        attribution=attribution,
        validation=_validate(rows, waterfall_name),
        commentary_prompts=commentary_prompts(),
    )
