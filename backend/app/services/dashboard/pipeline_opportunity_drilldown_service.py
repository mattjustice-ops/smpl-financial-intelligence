"""Pipeline waterfall opportunity drilldown from versioned opportunity_movements tables."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import fetch_scenario_rows, str_any, value_any
from app.services.dashboard.schemas import PipelineDrilldownResponse, WaterfallAttributionRow
from app.services.reporting.period_utils import combined_scenario_for_period
from app.services.reporting.validation_service import ValidationCheck, compare_values

# Movement labels in CSV -> internal waterfall_type keys (pipeline summary rows).
PIPELINE_MOVEMENT_TO_WATERFALL: dict[str, str] = {
    "pipeline created": "pipeline_created",
    "pipeline_created": "pipeline_created",
    "closed won": "closed_won",
    "closed_won": "closed_won",
    "closed lost": "closed_lost",
    "closed_lost": "closed_lost",
    "slipped pipeline": "slipped_pipeline",
    "slipped_pipeline": "slipped_pipeline",
}

PIPELINE_DRILLDOWN_TYPES = frozenset(
    {
        "pipeline_created",
        "closed_won",
        "closed_lost",
        "slipped_pipeline",
    }
)


def normalize_pipeline_movement_type(raw: str | None) -> str | None:
    if not raw:
        return None
    normalized = raw.strip().lower().replace("_", " ")
    if normalized in PIPELINE_MOVEMENT_TO_WATERFALL:
        return PIPELINE_MOVEMENT_TO_WATERFALL[normalized]
    compact = raw.strip().lower()
    return PIPELINE_MOVEMENT_TO_WATERFALL.get(compact, compact.replace(" ", "_"))


def signed_pipeline_movement_amount(waterfall_type: str, amount: Decimal) -> Decimal:
    if waterfall_type in {"closed_won", "closed_lost", "slipped_pipeline"}:
        return -abs(amount)
    return amount


def _movement_row(
    organization_id: uuid.UUID,
    scenario: str,
    period: str,
    table_name: str,
    waterfall_type: str,
    raw: dict,
) -> WaterfallAttributionRow:
    amount = value_any(raw, "amount_arr")
    signed = signed_pipeline_movement_amount(waterfall_type, amount)
    weighted = value_any(raw, "weighted_arr")
    return WaterfallAttributionRow(
        organization_id=str(organization_id),
        scenario=scenario,
        period=period,
        waterfall_type=waterfall_type,
        customer_id=str_any(raw, "customer_id"),
        customer_name=str_any(raw, "customer_name"),
        opportunity_id=str_any(raw, "opportunity_id"),
        opportunity_name=str_any(raw, "opportunity_name"),
        owner=str_any(raw, "owner", "owner_rep_id"),
        region=str_any(raw, "region"),
        segment=str_any(raw, "segment"),
        marketing_channel=str_any(raw, "marketing_channel"),
        stage=str_any(raw, "stage"),
        probability=value_any(raw, "probability"),
        close_date=str_any(raw, "close_date", "actual_close_date", "expected_close_date"),
        contract_start_date=str_any(raw, "contract_start_date"),
        billing_cadence=str_any(raw, "billing_cadence"),
        payment_terms=str_any(raw, "payment_terms", "billing_terms"),
        amount=signed,
        arr_impact=amount,
        mrr_impact=amount / Decimal("12") if amount else Decimal("0"),
        source_table=table_name,
        raw={k: str(v) for k, v in raw.items() if v is not None},
    )


def pipeline_opportunity_movements(
    db: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: str,
    end_period: str,
    marketing_channel: str | None = None,
    region: str | None = None,
    segment: str | None = None,
    owner: str | None = None,
) -> list[WaterfallAttributionRow]:
    filters = {"marketing_channel": marketing_channel, "region": region, "segment": segment, "owner": owner}
    rows: list[WaterfallAttributionRow] = []
    for src_scenario, period, table_name, raw in fetch_scenario_rows(
        db,
        organization_id,
        scenario=scenario,
        suffix="opportunity_movements",
        fallback=None,
        start_period=start_period,
        end_period=end_period,
        period_key="period",
        filters=filters,
    ):
        movement_label = str_any(raw, "pipeline_movement_type", "waterfall_type")
        waterfall_type = normalize_pipeline_movement_type(movement_label)
        if waterfall_type not in PIPELINE_DRILLDOWN_TYPES:
            continue
        rows.append(_movement_row(organization_id, src_scenario, period, table_name, waterfall_type, raw))
    return rows


def pipeline_movement_detail_counts(
    db: Session,
    organization_id: uuid.UUID,
    **params,
) -> dict[tuple[str, str, str], int]:
    """Count opportunity movements per cell without building full attribution rows."""
    filters = {
        "marketing_channel": params.get("marketing_channel"),
        "region": params.get("region"),
        "segment": params.get("segment"),
        "owner": params.get("owner"),
    }
    counts: dict[tuple[str, str, str], int] = {}
    for src_scenario, period, _table_name, raw in fetch_scenario_rows(
        db,
        organization_id,
        scenario=params["scenario"],
        suffix="opportunity_movements",
        fallback=None,
        start_period=params["start_period"],
        end_period=params["end_period"],
        period_key="period",
        filters=filters,
    ):
        movement_label = str_any(raw, "pipeline_movement_type", "waterfall_type")
        waterfall_type = normalize_pipeline_movement_type(movement_label)
        if waterfall_type not in PIPELINE_DRILLDOWN_TYPES:
            continue
        key = (src_scenario, period, waterfall_type)
        counts[key] = counts.get(key, 0) + 1
    return counts


def pipeline_drilldown(
    db: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    period: str,
    waterfall_type: str,
    expected_amount: Decimal | None = None,
    marketing_channel: str | None = None,
    region: str | None = None,
    segment: str | None = None,
    owner: str | None = None,
) -> PipelineDrilldownResponse:
    if scenario == "Combined":
        source_scenario = combined_scenario_for_period(period)
    else:
        source_scenario = scenario
    filters = {"marketing_channel": marketing_channel, "region": region, "segment": segment, "owner": owner}
    opportunities: list[WaterfallAttributionRow] = []
    source_tables: set[str] = set()

    if waterfall_type not in PIPELINE_DRILLDOWN_TYPES:
        return PipelineDrilldownResponse(
            organization_id=str(organization_id),
            scenario=scenario,
            source_scenario=source_scenario,
            period=period,
            waterfall_type=waterfall_type,
            line_item=waterfall_type.replace("_", " ").title(),
            opportunities=[],
            opportunity_count=0,
            total_arr=Decimal("0"),
            signed_total=Decimal("0"),
            expected_amount=expected_amount,
            drilldown_available=False,
            message="Beginning and ending pipeline balances are roll-forward positions, not opportunity movements.",
        )

    for src_scenario, row_period, table_name, raw in fetch_scenario_rows(
        db,
        organization_id,
        scenario=scenario,
        suffix="opportunity_movements",
        fallback=None,
        start_period=period,
        end_period=period,
        period_key="period",
        filters=filters,
    ):
        if row_period != period or src_scenario != source_scenario:
            continue
        movement_label = str_any(raw, "pipeline_movement_type", "waterfall_type")
        row_type = normalize_pipeline_movement_type(movement_label)
        if row_type != waterfall_type:
            continue
        opportunities.append(_movement_row(organization_id, src_scenario, period, table_name, waterfall_type, raw))
        source_tables.add(table_name)

    signed_total = sum((row.amount for row in opportunities), Decimal("0"))
    total_arr = sum((row.arr_impact for row in opportunities), Decimal("0"))
    validation: list[ValidationCheck] = []
    if expected_amount is not None:
        validation.append(
            compare_values(
                scenario=source_scenario,
                period=period,
                validation_name="pipeline_cell_opportunities_tie",
                expected_value=expected_amount,
                actual_value=signed_total,
                source_tables_used=sorted(source_tables),
            )
        )

    return PipelineDrilldownResponse(
        organization_id=str(organization_id),
        scenario=scenario,
        source_scenario=source_scenario,
        period=period,
        waterfall_type=waterfall_type,
        line_item=waterfall_type.replace("_", " ").title().replace("Arr", "ARR"),
        opportunities=opportunities,
        opportunity_count=len(opportunities),
        total_arr=total_arr,
        signed_total=signed_total,
        expected_amount=expected_amount,
        drilldown_available=True,
        validation=validation,
        source_tables=sorted(source_tables),
    )
