"""SaaS semantic reporting: movements, dimensions, lineage, and executive rollups."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from app.services.dashboard.schemas import WaterfallAttributionRow
from app.services.reporting.export.reporting_period_engine import (
    ReportingPeriodContext,
    build_period_context,
)
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.period_utils import to_period

ZERO = Decimal("0")


class OpportunityMovementType(str, Enum):
    NEW_CREATED = "new_opportunity_created"
    EXISTING_ADVANCED = "existing_opportunity_advanced"
    PRIOR_PERIOD_CLOSED_WON = "prior_period_closed_won"
    PRIOR_PERIOD_CLOSED_LOST = "prior_period_closed_lost"
    DEFERRED = "deferred_slipped"
    FORECAST_PUSH = "forecast_push"
    EXPANSION = "expansion_opportunity"
    RENEWAL = "renewal_opportunity"
    OTHER = "other_movement"


class PipelineAgeBucket(str, Enum):
    DAYS_0_30 = "0-30 Days"
    DAYS_31_60 = "31-60 Days"
    DAYS_61_90 = "61-90 Days"
    DAYS_90_PLUS = "90+ Days"


@dataclass
class ClassifiedOpportunity:
    movement_type: OpportunityMovementType
    period: str
    opportunity_id: str | None
    opportunity_name: str | None
    arr_impact: Decimal
    owner: str | None = None
    segment: str | None = None
    region: str | None = None
    marketing_channel: str | None = None
    stage: str | None = None
    created_period: str | None = None
    forecast_impact: Decimal = ZERO


@dataclass
class MovementAttributionSummary:
    as_of: str
    currency: str
    buckets: dict[OpportunityMovementType, list[ClassifiedOpportunity]] = field(default_factory=dict)
    arr_by_bucket: dict[OpportunityMovementType, Decimal] = field(default_factory=dict)
    count_by_bucket: dict[OpportunityMovementType, int] = field(default_factory=dict)

    def arr(self, movement: OpportunityMovementType) -> Decimal:
        return self.arr_by_bucket.get(movement, ZERO)

    def count(self, movement: OpportunityMovementType) -> int:
        return self.count_by_bucket.get(movement, 0)


@dataclass
class ChannelEfficiencyRow:
    channel: str
    spend: Decimal = ZERO
    mqls: Decimal = ZERO
    sqls: Decimal = ZERO
    sals: Decimal = ZERO
    opportunities: Decimal = ZERO
    pipeline_created: Decimal = ZERO
    closed_won_arr: Decimal = ZERO
    pipeline_per_spend: float | None = None
    win_rate: float | None = None
    cac_proxy: Decimal | None = None


@dataclass
class RevenueLineageNode:
    stage: str
    amount: Decimal
    period: str
    scenario: str = "Actual"


@dataclass
class RevenueLineage:
    as_of: str
    currency: str
    ending_arr: Decimal = ZERO
    billings: Decimal = ZERO
    deferred_revenue: Decimal = ZERO
    gaap_revenue: Decimal = ZERO
    collections: Decimal = ZERO
    ending_cash: Decimal = ZERO
    nodes: list[RevenueLineageNode] = field(default_factory=list)


def _opp_rows(bundle: ReportingBundle) -> list[WaterfallAttributionRow]:
    rows: list[WaterfallAttributionRow] = list(bundle.opportunity_attribution or [])
    if rows:
        return rows
    for payload in bundle.pipeline_drilldown.values():
        for raw in payload.get("opportunities") or []:
            if isinstance(raw, WaterfallAttributionRow):
                rows.append(raw)
            elif isinstance(raw, dict):
                rows.append(
                    WaterfallAttributionRow(
                        organization_id=bundle.organization_id,
                        scenario=str(raw.get("scenario", bundle.scenario)),
                        period=str(raw.get("period", bundle.as_of_period))[:7],
                        waterfall_type=str(raw.get("waterfall_type", "pipeline_created")),
                        opportunity_id=str(raw.get("opportunity_id")) if raw.get("opportunity_id") else None,
                        opportunity_name=str(raw.get("opportunity_name") or raw.get("customer_name") or ""),
                        owner=str(raw.get("owner")) if raw.get("owner") else None,
                        region=str(raw.get("region")) if raw.get("region") else None,
                        segment=str(raw.get("segment")) if raw.get("segment") else None,
                        marketing_channel=str(raw.get("marketing_channel")) if raw.get("marketing_channel") else None,
                        stage=str(raw.get("stage")) if raw.get("stage") else None,
                        arr_impact=Decimal(str(raw.get("amount_arr") or raw.get("arr_impact") or 0)),
                        amount=Decimal(str(raw.get("amount") or 0)),
                        source_table=str(raw.get("source_table", "")),
                        raw={k: str(v) for k, v in raw.items() if v is not None},
                    )
                )
    return rows


def _created_period_for_opp(rows: list[WaterfallAttributionRow], opp_id: str | None) -> str | None:
    if not opp_id:
        return None
    created: list[str] = []
    for r in rows:
        if r.opportunity_id != opp_id:
            continue
        raw_cp = (r.raw or {}).get("created_period") or (r.raw or {}).get("opportunity_created_period")
        if raw_cp:
            created.append(to_period(str(raw_cp)[:7]))
        elif r.waterfall_type == "pipeline_created":
            created.append(to_period(r.period))
    return min(created) if created else None


def classify_opportunity_movement(
    row: WaterfallAttributionRow,
    *,
    as_of: str,
    first_created_period: str | None,
) -> OpportunityMovementType:
    wt = row.waterfall_type
    period = to_period(row.period)
    as_of_p = to_period(as_of)
    stage = (row.stage or "").lower()
    raw = row.raw or {}
    label = str(raw.get("pipeline_movement_type", "")).lower()

    if "expansion" in label or "expansion" in stage:
        return OpportunityMovementType.EXPANSION
    if "renewal" in label or "renew" in stage:
        return OpportunityMovementType.RENEWAL
    if "forecast" in label and "push" in label:
        return OpportunityMovementType.FORECAST_PUSH
    if wt == "slipped_pipeline" or "slip" in label or "defer" in label:
        return OpportunityMovementType.DEFERRED
    if wt == "pipeline_created":
        if first_created_period and first_created_period < period:
            return OpportunityMovementType.EXISTING_ADVANCED
        return OpportunityMovementType.NEW_CREATED
    if wt == "closed_won":
        if first_created_period and first_created_period < as_of_p:
            return OpportunityMovementType.PRIOR_PERIOD_CLOSED_WON
        return OpportunityMovementType.NEW_CREATED if first_created_period == period else OpportunityMovementType.PRIOR_PERIOD_CLOSED_WON
    if wt == "closed_lost":
        if first_created_period and first_created_period < as_of_p:
            return OpportunityMovementType.PRIOR_PERIOD_CLOSED_LOST
        return OpportunityMovementType.PRIOR_PERIOD_CLOSED_LOST
    if "advance" in label or "stage" in label:
        return OpportunityMovementType.EXISTING_ADVANCED
    return OpportunityMovementType.OTHER


def build_movement_attribution(bundle: ReportingBundle) -> MovementAttributionSummary:
    as_of = bundle.as_of_period
    rows = _opp_rows(bundle)
    first_created: dict[str, str | None] = {}
    for r in rows:
        oid = r.opportunity_id or r.opportunity_name
        if oid and oid not in first_created:
            first_created[oid] = _created_period_for_opp(rows, r.opportunity_id)

    summary = MovementAttributionSummary(as_of=as_of, currency=bundle.currency)
    for r in rows:
        if to_period(r.period) != to_period(as_of):
            continue
        oid = r.opportunity_id or r.opportunity_name
        mt = classify_opportunity_movement(
            r,
            as_of=as_of,
            first_created_period=first_created.get(oid) if oid else None,
        )
        co = ClassifiedOpportunity(
            movement_type=mt,
            period=r.period,
            opportunity_id=r.opportunity_id,
            opportunity_name=r.opportunity_name,
            arr_impact=abs(r.arr_impact or r.amount or ZERO),
            owner=r.owner,
            segment=r.segment,
            region=r.region,
            marketing_channel=r.marketing_channel,
            stage=r.stage,
            created_period=first_created.get(oid) if oid else None,
        )
        summary.buckets.setdefault(mt, []).append(co)
        summary.arr_by_bucket[mt] = summary.arr_by_bucket.get(mt, ZERO) + co.arr_impact
        summary.count_by_bucket[mt] = summary.count_by_bucket.get(mt, 0) + 1
    return summary


def pipeline_age_bucket(days_open: int) -> PipelineAgeBucket:
    if days_open <= 30:
        return PipelineAgeBucket.DAYS_0_30
    if days_open <= 60:
        return PipelineAgeBucket.DAYS_31_60
    if days_open <= 90:
        return PipelineAgeBucket.DAYS_61_90
    return PipelineAgeBucket.DAYS_90_PLUS


def pipeline_quality_score(*, stage: str | None, probability: Decimal, days_open: int) -> float:
    """0–100 heuristic for forecastability."""
    prob = float(probability or 0)
    if prob > 1:
        prob = prob / 100
    stage_bonus = 20 if stage and any(s in stage.lower() for s in ("negotiat", "proposal", "contract")) else 0
    age_penalty = min(40, days_open // 3)
    return max(0.0, min(100.0, prob * 60 + stage_bonus + max(0, 30 - age_penalty)))


def build_pipeline_aging(bundle: ReportingBundle) -> dict[PipelineAgeBucket, Decimal]:
    as_of = bundle.as_of_period
    rows = [r for r in _opp_rows(bundle) if to_period(r.period) == to_period(as_of)]
    buckets: dict[PipelineAgeBucket, Decimal] = {b: ZERO for b in PipelineAgeBucket}
    for r in rows:
        if r.waterfall_type not in ("pipeline_created", "slipped_pipeline"):
            continue
        raw = r.raw or {}
        days = int(raw.get("days_in_stage") or raw.get("pipeline_age_days") or 45)
        bucket = pipeline_age_bucket(days)
        buckets[bucket] += abs(r.arr_impact or ZERO)
    return buckets


def build_channel_dimensions(bundle: ReportingBundle, *, period: str | None = None) -> list[ChannelEfficiencyRow]:
    as_of = to_period(period or bundle.as_of_period)
    mkt = bundle.marketing_comparison
    if not mkt:
        return []
    by_ch: dict[str, ChannelEfficiencyRow] = {}
    for row in mkt.actual:
        if to_period(row.period) != as_of:
            continue
        ch = (row.marketing_channel or "Unknown").strip()
        rec = by_ch.setdefault(ch, ChannelEfficiencyRow(channel=ch))
        rec.spend += row.marketing_spend
        rec.mqls += row.mqls
        rec.sqls += row.sqls
        rec.sals += row.sals
        rec.opportunities += row.opportunities_created
        rec.pipeline_created += row.pipeline_arr_created
        rec.closed_won_arr += row.closed_won_arr
    for rec in by_ch.values():
        if rec.spend:
            rec.pipeline_per_spend = float(rec.pipeline_created / rec.spend)
            rec.cac_proxy = rec.spend / rec.closed_won_arr if rec.closed_won_arr else None
        if rec.opportunities:
            rec.win_rate = float(rec.closed_won_arr / rec.pipeline_created) if rec.pipeline_created else None
    return sorted(by_ch.values(), key=lambda x: -(x.pipeline_per_spend or 0))


def collapse_channels(
    rows: list[ChannelEfficiencyRow],
    *,
    top_n: int = 5,
    bottom_n: int = 3,
) -> list[ChannelEfficiencyRow]:
    if len(rows) <= top_n + bottom_n:
        return rows
    top = rows[:top_n]
    bottom = rows[-bottom_n:]
    middle = rows[top_n:-bottom_n] if bottom_n else rows[top_n:]
    other = ChannelEfficiencyRow(channel="Other")
    for r in middle:
        other.spend += r.spend
        other.pipeline_created += r.pipeline_created
        other.closed_won_arr += r.closed_won_arr
        other.mqls += r.mqls
        other.sqls += r.sqls
    if other.spend:
        other.pipeline_per_spend = float(other.pipeline_created / other.spend)
    return top + ([other] if middle else []) + bottom


def _wf_line(bundle: ReportingBundle, key: str, wtype: str, period: str, scenario: str = "Actual") -> Decimal:
    for row in bundle.comparison_waterfalls.get(key) or []:
        if row.period == period and row.waterfall_type == wtype and row.scenario == scenario:
            return row.amount
    return ZERO


def _fs_line(bundle: ReportingBundle, needle: str, period: str, scenario: str = "Actual") -> Decimal:
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if not fs:
        return ZERO
    n = needle.lower()
    for row in fs.income_statement.rows:
        if to_period(str(row.period)[:7]) != to_period(period):
            continue
        if row.scenario != scenario:
            continue
        if n in row.line_item.lower():
            return row.amount
    return ZERO


def build_revenue_lineage(bundle: ReportingBundle) -> RevenueLineage:
    as_of = bundle.as_of_period
    ctx = build_period_context(bundle)
    arr = _wf_line(bundle, "arr", "ending_arr", as_of) or _wf_line(bundle, "arr", "ending", as_of)
    billings = _wf_line(bundle, "deferred_revenue", "billings", as_of) or _wf_line(
        bundle, "deferred_revenue", "billings_collected", as_of
    )
    deferred = _wf_line(bundle, "deferred_revenue", "ending_deferred", as_of) or _wf_line(
        bundle, "deferred_revenue", "ending", as_of
    )
    revenue = _fs_line(bundle, "revenue", as_of)
    collections = _wf_line(bundle, "cash_flow", "collections", as_of)
    cash = _wf_line(bundle, "cash_flow", "ending_cash", as_of)
    nodes = [
        RevenueLineageNode("Ending ARR", arr, as_of),
        RevenueLineageNode("Billings", billings, as_of),
        RevenueLineageNode("Deferred Revenue", deferred, as_of),
        RevenueLineageNode("GAAP Revenue", revenue, as_of),
        RevenueLineageNode("Collections", collections, as_of),
        RevenueLineageNode("Ending Cash", cash, as_of),
    ]
    return RevenueLineage(
        as_of=as_of,
        currency=bundle.currency,
        ending_arr=arr,
        billings=billings,
        deferred_revenue=deferred,
        gaap_revenue=revenue,
        collections=collections,
        ending_cash=cash,
        nodes=nodes,
    )


def movement_chart_categories(summary: MovementAttributionSummary) -> tuple[list[str], list[float], list[int]]:
    """Executive movement bridge — lineage buckets, not raw waterfall keys."""
    order = [
        OpportunityMovementType.NEW_CREATED,
        OpportunityMovementType.EXISTING_ADVANCED,
        OpportunityMovementType.PRIOR_PERIOD_CLOSED_WON,
        OpportunityMovementType.PRIOR_PERIOD_CLOSED_LOST,
        OpportunityMovementType.DEFERRED,
        OpportunityMovementType.FORECAST_PUSH,
    ]
    labels: list[str] = []
    arr_vals: list[float] = []
    counts: list[int] = []
    short = {
        OpportunityMovementType.NEW_CREATED: "New Created",
        OpportunityMovementType.EXISTING_ADVANCED: "Advanced",
        OpportunityMovementType.PRIOR_PERIOD_CLOSED_WON: "Prior Won",
        OpportunityMovementType.PRIOR_PERIOD_CLOSED_LOST: "Prior Lost",
        OpportunityMovementType.DEFERRED: "Deferred",
        OpportunityMovementType.FORECAST_PUSH: "Forecast Push",
    }
    for mt in order:
        c = summary.count(mt)
        a = float(summary.arr(mt))
        if c == 0 and a == 0:
            continue
        labels.append(short[mt])
        arr_vals.append(a)
        counts.append(c)
    return labels, arr_vals, counts
