"""Data-driven CFO commentary (semantic drivers + optional OpenAI)."""

from __future__ import annotations

import logging
from decimal import Decimal

from app.core.config import get_settings
from app.services.commentary.llm_factory import build_commentary_llm_client
from app.services.dashboard.schemas import WaterfallAttributionRow
from app.services.financial_statements.financial_statement_service import SummaryResponse
from app.services.marketing.schemas import ActualBudgetForecastResponse
from app.services.reporting.export.board_inputs_mapper import (
    REVENUE_LINE_ITEMS,
    build_commentary_inputs,
)
from app.services.reporting.export.period_views import build_summary_metrics, variance_pack
from app.services.reporting.export.schemas import CommentaryField, ReportingBundle, WaterfallSummaryRow
from app.services.reporting.export.semantic_model import classify_opportunity
from app.services.reporting.period_utils import to_period

logger = logging.getLogger(__name__)


def _fmt_money(value: Decimal | None) -> str:
    if value is None:
        return ""
    if value == 0:
        return "$0"
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= Decimal("1000000"):
        return f"{sign}${v / Decimal('1000000'):,.2f}M"
    if v >= Decimal("1000"):
        return f"{sign}${v / Decimal('1000'):,.1f}K"
    return f"{sign}${v:,.0f}"


def _top_opportunity_drivers(
    opportunities: list[WaterfallAttributionRow],
    *,
    movement_filter: str | None = None,
    limit: int = 3,
) -> str:
    rows = opportunities
    if movement_filter:
        rows = [r for r in rows if movement_filter.lower() in (r.stage or "").lower() or movement_filter in (r.waterfall_type or "")]
    rows = sorted(rows, key=lambda r: abs(r.arr_impact), reverse=True)[:limit]
    if not rows:
        return ""
    parts: list[str] = []
    for row in rows:
        tags = classify_opportunity(
            stage=row.stage,
            region=row.region,
            segment=row.segment,
            owner=row.owner,
            marketing_channel=row.marketing_channel,
            arr_impact=row.arr_impact,
        )
        parts.append(
            f"{row.opportunity_name or row.customer_name or 'Deal'} ({tags.region}, {tags.arr_band}, "
            f"{_fmt_money(row.arr_impact)} ARR)"
        )
    return "; ".join(parts)


def _revenue_commentary(bundle: ReportingBundle, as_of: str) -> CommentaryField:
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    field = CommentaryField(section="Income Statement / Revenue", period=as_of)
    if not fs:
        field.leadership_attention = "Upload Actual/Budget/Forecast income statement CSVs."
        return field

    # (scenario, period) -> line_item -> amount. Keeping line items separate stops a
    # subtotal and its component from being added together, and confining the scan to
    # the close month's own fiscal year keeps "YTD" from sweeping in prior years.
    year = as_of[:4]
    by_period: dict[tuple[str, str], dict[str, Decimal]] = {}
    for row in fs.income_statement.rows:
        line_item = (row.line_item or "").strip().lower()
        if line_item not in REVENUE_LINE_ITEMS:
            continue
        p = to_period(str(row.period))
        if p[:4] != year or p > as_of:
            continue
        scenario = (row.scenario or "").strip().lower()
        bucket = by_period.setdefault((scenario, p), {})
        bucket[line_item] = bucket.get(line_item, Decimal("0")) + row.amount

    def pick(bucket: dict[str, Decimal]) -> Decimal:
        for line_item in REVENUE_LINE_ITEMS:
            if line_item in bucket:
                return bucket[line_item]
        return Decimal("0")

    def ytd(scenario: str) -> Decimal:
        return sum(
            (pick(v) for (s, _), v in by_period.items() if s == scenario), Decimal("0")
        )

    cm_a = pick(by_period.get(("actual", as_of), {}))
    cm_b = pick(by_period.get(("budget", as_of), {}))
    ytd_a = ytd("actual")
    ytd_b = ytd("budget")

    var = variance_pack(cm_a, cm_b)
    var_d = var.get("var_d") or Decimal("0")
    direction = "above" if var_d > 0 else "below" if var_d < 0 else "in line with"
    field.what_changed = (
        f"Revenue for {as_of} was {_fmt_money(cm_a)} actual vs {_fmt_money(cm_b)} budget "
        f"({_fmt_money(var_d)} {direction} plan)."
    )
    field.variance_driver = (
        f"YTD actual revenue {_fmt_money(ytd_a)} vs budget {_fmt_money(ytd_b)} "
        f"for {year} through {as_of}."
    )
    if (var.get("var_d") or 0) > 0:
        field.favorable = "Revenue outperformed budget in the close month."
    elif (var.get("var_d") or 0) < 0:
        field.unfavorable = "Revenue trailed budget in the close month."
    field.leadership_attention = "Validate expansion timing and churn pockets before board distribution."
    field.metric_context = field.what_changed
    field.source = "metrics"
    return field


def _arr_commentary(bundle: ReportingBundle, as_of: str) -> CommentaryField:
    arr = bundle.comparison_waterfalls.get("arr", [])
    field = CommentaryField(section="MRR / ARR Waterfall", period=as_of)
    ending_a = ending_b = new_a = churn_a = Decimal("0")
    for row in arr:
        if row.period != as_of:
            continue
        if row.waterfall_type in {"ending", "ending_arr"}:
            if row.scenario == "Actual":
                ending_a = row.amount
            elif row.scenario == "Budget":
                ending_b = row.amount
        if row.waterfall_type in {"new_arr", "new_business"} and row.scenario == "Actual":
            new_a = row.amount
        if row.waterfall_type in {"churn_arr", "churn"} and row.scenario == "Actual":
            churn_a = row.amount

    if not ending_a and not ending_b:
        field.leadership_attention = "Load MRR waterfall CSVs — source of truth for ARR movement."
        return field

    field.what_changed = (
        f"Ending ARR {_fmt_money(ending_a)} actual vs {_fmt_money(ending_b)} budget; "
        f"new business {_fmt_money(new_a)}; churn {_fmt_money(churn_a)}."
    )
    opps = bundle.opportunity_attribution
    drivers = _top_opportunity_drivers(opps, movement_filter="closed won")
    if drivers:
        field.variance_driver = f"Closed-won drivers: {drivers}."
    field.metric_context = field.what_changed
    field.source = "metrics"
    return field


def _pipeline_commentary(bundle: ReportingBundle, as_of: str) -> CommentaryField:
    pipeline = bundle.comparison_waterfalls.get("pipeline", [])
    field = CommentaryField(section="Pipeline Health", period=as_of)
    metrics: dict[str, Decimal] = {}
    for row in pipeline:
        if row.period != as_of or row.scenario != "Actual":
            continue
        metrics[row.waterfall_type] = row.amount
    if not metrics:
        field.leadership_attention = "Pipeline waterfall empty — use pipeline_waterfall tables, not marketing_pipeline."
        return field
    field.what_changed = (
        f"Pipeline created {_fmt_money(metrics.get('pipeline_created'))}; "
        f"closed won {_fmt_money(metrics.get('closed_won'))}; "
        f"slipped {_fmt_money(metrics.get('slipped_pipeline'))}."
    )
    slipped = _top_opportunity_drivers(bundle.opportunity_attribution, movement_filter="slipped")
    if slipped:
        field.unfavorable = f"Notable slipped deals: {slipped}."
    field.metric_context = field.what_changed
    field.source = "metrics"
    return field


def _cash_commentary(bundle: ReportingBundle, as_of: str) -> CommentaryField:
    cash = bundle.comparison_waterfalls.get("cash_flow", [])
    field = CommentaryField(section="Cash Forecast", period=as_of)

    def amount(types: set[str], scenario: str) -> Decimal | None:
        for row in cash:
            if row.period != as_of or row.scenario != scenario:
                continue
            if row.waterfall_type in types:
                return row.amount
        return None

    collection_types = {"cash_collections", "collections"}
    ending_a = amount({"ending_cash"}, "Actual")
    ending_b = amount({"ending_cash"}, "Budget")
    collections_a = amount(collection_types, "Actual")
    collections_b = amount(collection_types, "Budget")

    parts = [f"Ending cash {_fmt_money(ending_a)} actual"]
    if ending_b is not None:
        parts[0] += f" vs {_fmt_money(ending_b)} budget"
    if collections_a is not None:
        collections_text = f"collections {_fmt_money(collections_a)} actual"
        if collections_b is not None:
            collections_text += f" vs {_fmt_money(collections_b)} budget"
        parts.append(collections_text)
    field.what_changed = "; ".join(parts) + " (cash flow bridge source of truth)."

    if collections_a is not None and collections_b is not None and collections_a < collections_b:
        field.unfavorable = (
            f"Collections trailed budget by {_fmt_money(collections_b - collections_a)}."
        )
    field.leadership_attention = "Confirm ending cash ties to balance sheet cash in Validation tab."
    field.metric_context = field.what_changed
    field.source = "metrics"
    return field


def generate_mda_commentary(bundle: ReportingBundle, *, use_ai: bool = False) -> list[CommentaryField]:
    as_of = bundle.as_of_period
    sections = [
        _revenue_commentary(bundle, as_of),
        _arr_commentary(bundle, as_of),
        _pipeline_commentary(bundle, as_of),
        _cash_commentary(bundle, as_of),
        CommentaryField(
            section="SaaS MD&A Summary",
            period=as_of,
            what_changed="See section commentary for revenue, ARR, pipeline, and cash movements.",
            leadership_attention="Review Validation Checks before board distribution.",
            metric_context=f"Close month {as_of}; Actual Jan–{as_of[:7]} vs Budget; Forecast outlook for open months.",
            source="metrics",
        ),
        CommentaryField(
            section="Risks & Opportunities",
            period=as_of,
            leadership_attention="; ".join(g.message for g in bundle.data_gaps if g.status != "ok")[:500],
            recommended_actions="Resolve failed validations and reload missing CSV sources.",
            source="metrics",
        ),
    ]

    settings = get_settings()
    if use_ai and (settings.anthropic_api_key or settings.openai_api_key):
        try:
            from app.services.commentary.prompts import SYSTEM_PROMPT, build_user_prompt
            from app.services.reporting.export.company_context import strategic_context_for_prompt
            from app.services.reporting.export.export_sheet_registry import monthly_close_requirements_prompt

            inputs = build_commentary_inputs(
                organization_name=bundle.organization_name,
                as_of_period=as_of,
                bundle_data=bundle.executive_flow,
                financial=bundle.comparison_financial_statements or bundle.financial_statements,
                comparison_waterfalls=bundle.comparison_waterfalls,
            )
            client = build_commentary_llm_client()
            user_prompt = (
                build_user_prompt(inputs)
                + "\n\n"
                + strategic_context_for_prompt()
                + "\n\n"
                + monthly_close_requirements_prompt()
            )
            ai_raw = client.generate(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)
            from app.services.commentary.schemas import CommentaryOutput

            ai = CommentaryOutput.model_validate({**ai_raw, "period_label": inputs.period_label})
            sections[0] = CommentaryField(
                section="Executive Summary",
                period=as_of,
                what_changed=ai.executive_summary.narrative,
                variance_driver=ai.revenue_commentary.narrative[:400],
                leadership_attention="; ".join(r.description for r in ai.risks_and_opportunities[:4]),
                source="ai",
                metric_context=sections[0].metric_context,
            )
        except Exception:
            logger.exception(
                "AI MD&A commentary failed for %s (%s); falling back to metric templates",
                bundle.organization_name,
                as_of,
            )

    return sections
