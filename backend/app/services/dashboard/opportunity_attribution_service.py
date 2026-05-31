"""Opportunity drilldown and summary services."""

from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import fetch_scenario_rows, str_any, value_any
from app.services.dashboard.schemas import OpportunityResponse, OpportunitySummaryRow, WaterfallAttributionRow


def opportunity_attribution(
    db: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: str,
    end_period: str,
    waterfall_type: str | None = None,
    marketing_channel: str | None = None,
    region: str | None = None,
    segment: str | None = None,
    owner: str | None = None,
    closed_only: bool = False,
    remaining_only: bool = False,
) -> list[WaterfallAttributionRow]:
    del waterfall_type
    filters = {"marketing_channel": marketing_channel, "region": region, "segment": segment, "owner": owner}
    rows: list[WaterfallAttributionRow] = []
    for src_scenario, period, table_name, raw in fetch_scenario_rows(
        db,
        organization_id,
        scenario=scenario,
        suffix="opportunities",
        fallback="opportunities",
        start_period=start_period,
        end_period=end_period,
        filters=filters,
    ):
        stage = str_any(raw, "stage") or ""
        if closed_only and stage.lower() != "closed won":
            continue
        if remaining_only and stage.lower() in {"closed won", "closed lost"}:
            continue
        amount = value_any(raw, "amount_arr")
        probability = value_any(raw, "probability")
        rows.append(
            WaterfallAttributionRow(
                organization_id=str(organization_id),
                scenario=src_scenario,
                period=period,
                waterfall_type="opportunity",
                customer_id=str_any(raw, "customer_id"),
                customer_name=str_any(raw, "customer_name"),
                opportunity_id=str_any(raw, "opportunity_id"),
                opportunity_name=str_any(raw, "opportunity_name"),
                owner=str_any(raw, "owner", "owner_rep_id"),
                region=str_any(raw, "region"),
                segment=str_any(raw, "segment"),
                marketing_channel=str_any(raw, "marketing_channel"),
                stage=stage,
                probability=probability,
                close_date=str_any(raw, "close_date", "actual_close_date", "expected_close_date"),
                contract_start_date=str_any(raw, "contract_start_date"),
                billing_cadence=str_any(raw, "billing_cadence"),
                payment_terms=str_any(raw, "payment_terms", "billing_terms"),
                amount=amount,
                arr_impact=amount,
                mrr_impact=amount / Decimal("12") if amount else Decimal("0"),
                source_table=table_name,
                raw={k: str(v) for k, v in raw.items() if v is not None},
            )
        )
    return rows


def summarize_opportunities(organization_id: uuid.UUID, rows: list[WaterfallAttributionRow], group_key: str) -> list[OpportunitySummaryRow]:
    grouped: dict[tuple[str, str, str], list[WaterfallAttributionRow]] = defaultdict(list)
    for row in rows:
        key = str(getattr(row, group_key) or "Unassigned")
        grouped[(row.scenario, row.period, key)].append(row)
    out: list[OpportunitySummaryRow] = []
    for (scenario, period, key), items in grouped.items():
        out.append(
            OpportunitySummaryRow(
                organization_id=str(organization_id),
                scenario=scenario,
                period=period,
                stage=key if group_key == "stage" else None,
                marketing_channel=key if group_key == "marketing_channel" else None,
                owner=key if group_key == "owner" else None,
                region=key if group_key == "region" else None,
                segment=key if group_key == "segment" else None,
                opportunity_count=len(items),
                amount_arr=sum((item.arr_impact for item in items), Decimal("0")),
                weighted_arr=sum((item.arr_impact * item.probability for item in items), Decimal("0")),
                source_table=", ".join(sorted({item.source_table for item in items})),
            )
        )
    return sorted(out, key=lambda r: (r.period, r.stage or r.marketing_channel or r.owner or ""))


def stage_summary(db: Session, organization_id: uuid.UUID, **params) -> OpportunityResponse:
    rows = opportunity_attribution(db, organization_id, **params)
    return OpportunityResponse(organization_id=str(organization_id), scenario=params["scenario"], start_period=params["start_period"], end_period=params["end_period"], rows=summarize_opportunities(organization_id, rows, "stage"), attribution=rows)


def closed_by_month(db: Session, organization_id: uuid.UUID, **params) -> OpportunityResponse:
    rows = opportunity_attribution(db, organization_id, closed_only=True, **params)
    return OpportunityResponse(organization_id=str(organization_id), scenario=params["scenario"], start_period=params["start_period"], end_period=params["end_period"], rows=summarize_opportunities(organization_id, rows, "marketing_channel"), attribution=rows)


def remaining_pipeline(db: Session, organization_id: uuid.UUID, **params) -> OpportunityResponse:
    rows = opportunity_attribution(db, organization_id, remaining_only=True, **params)
    return OpportunityResponse(organization_id=str(organization_id), scenario=params["scenario"], start_period=params["start_period"], end_period=params["end_period"], rows=summarize_opportunities(organization_id, rows, "stage"), attribution=rows)
