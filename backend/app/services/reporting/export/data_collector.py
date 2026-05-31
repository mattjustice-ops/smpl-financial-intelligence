"""Collect reporting bundle from existing dashboard and statement services."""

from __future__ import annotations

import calendar
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.commentary.openai_client import build_openai_commentary_client
from app.services.commentary.service import generate_commentary
from app.services.dashboard.executive_service import executive_flow
from app.services.dashboard.pipeline_opportunity_drilldown_service import pipeline_drilldown
from app.services.dashboard.query_utils import decimal_value, fetch_table_rows, table_exists, value_any
from app.services.financial_statements.financial_statement_service import SummaryResponse, summary
from app.services.organizations import get_organization_or_404
from app.services.dashboard.opportunity_attribution_service import opportunity_attribution
from app.services.reporting.export.commentary_engine import generate_mda_commentary
from app.services.reporting.export.commentary_metrics import build_commentary_fields_for_export
from app.services.reporting.export.multi_scenario import (
    assess_data_gaps,
    collect_comparison_financial_statements,
    collect_comparison_waterfalls,
    collect_marketing_comparison,
)
from app.services.reporting.export.schemas import (
    CommentaryField,
    GlDetailRow,
    HeadcountRow,
    ReportingBundle,
)
from app.services.reporting.export.validation_precheck import run_export_validation_bundle
from app.services.reporting.period_utils import to_period


def _statement_date_range(start_period: str, end_period: str) -> tuple[date, date]:
    start = date(int(start_period[:4]), int(start_period[5:7]), 1)
    y, m = int(end_period[:4]), int(end_period[5:7])
    last = calendar.monthrange(y, m)[1]
    end = date(y, m, last)
    return start, end


def _period_label(as_of_period: str) -> str:
    p = to_period(as_of_period)
    dt = date(int(p[:4]), int(p[5:7]), 1)
    return dt.strftime("%B %Y")


def _load_gl_detail(db: Session, organization_id: uuid.UUID, start: str, end: str) -> list[GlDetailRow]:
    if not table_exists(db, "gl_actuals"):
        return []
    rows: list[GlDetailRow] = []
    for raw in fetch_table_rows(db, "gl_actuals", organization_id):
        period_raw = raw.get("period") or raw.get("posting_period")
        if not period_raw:
            continue
        period = to_period(str(period_raw))
        if period < start or period > end:
            continue
        rows.append(
            GlDetailRow(
                scenario=str(raw.get("version") or raw.get("scenario") or "Actual"),
                period=period,
                department=str(raw.get("department") or raw.get("dept") or "") or None,
                account=str(raw.get("account") or raw.get("account_name") or "") or None,
                account_group=str(raw.get("account_group") or raw.get("account_type") or "") or None,
                expense_type=str(raw.get("expense_type") or raw.get("category") or "") or None,
                amount=value_any(
                    raw,
                    "amount",
                    "balance",
                    "debit",
                    "credit",
                    "net_amount",
                ),
                source_table="gl_actuals",
            )
        )
    return rows


def _load_headcount(db: Session, organization_id: uuid.UUID, start: str, end: str) -> list[HeadcountRow]:
    from app.services.workforce.integration import load_headcount_from_workforce_summary

    wf_rows = load_headcount_from_workforce_summary(db, organization_id, start, end)
    if wf_rows:
        return [
            HeadcountRow(
                scenario=str(row["scenario"]),
                period=str(row["period"]),
                department=str(row.get("department") or "") or None,
                headcount=row.get("headcount"),
                open_roles=row.get("open_roles"),
                hiring_plan=row.get("hiring_plan"),
                source_table=str(row.get("source_table") or "workforce_period_summary"),
            )
            for row in wf_rows
        ]

    out: list[HeadcountRow] = []
    for table, default_scenario in (
        ("headcount_plan", "Actual"),
        ("forecast_headcount_plan", "Forecast"),
    ):
        if not table_exists(db, table):
            continue
        for raw in fetch_table_rows(db, table, organization_id):
            period_raw = raw.get("period")
            if not period_raw:
                continue
            period = to_period(str(period_raw))
            if period < start or period > end:
                continue
            out.append(
                HeadcountRow(
                    scenario=str(raw.get("version") or raw.get("scenario") or default_scenario),
                    period=period,
                    department=str(raw.get("department") or "") or None,
                    headcount=decimal_value(raw.get("headcount")) if raw.get("headcount") not in (None, "") else None,
                    open_roles=decimal_value(raw.get("open_roles")) if raw.get("open_roles") not in (None, "") else None,
                    hiring_plan=decimal_value(raw.get("hiring_plan")) if raw.get("hiring_plan") not in (None, "") else None,
                    source_table=table,
                )
            )
    return out


def collect_reporting_bundle(
    db: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: str,
    end_period: str,
    as_of_period: str | None = None,
    include_ai_commentary: bool = False,
    **dashboard_filters,
) -> ReportingBundle:
    org = get_organization_or_404(db, organization_id)
    start = to_period(start_period)
    end = to_period(end_period)
    as_of = to_period(as_of_period or end_period)

    params = {
        "scenario": scenario,
        "start_period": start,
        "end_period": end,
        **dashboard_filters,
    }
    executive = executive_flow(db, organization_id, **params)

    comparison_waterfalls = collect_comparison_waterfalls(
        db,
        organization_id,
        start_period=start,
        end_period=end,
        **dashboard_filters,
    )
    comparison_financial = collect_comparison_financial_statements(
        db,
        organization_id,
        start_period=start,
        end_period=end,
    )
    marketing_comparison = collect_marketing_comparison(
        db,
        organization_id,
        start_period=start,
        end_period=end,
        marketing_channel=dashboard_filters.get("marketing_channel"),
    )

    fs_start, fs_end = _statement_date_range(start, end)
    financial: SummaryResponse | None = comparison_financial
    if financial is None:
        try:
            financial = summary(
                db,
                organization_id,
                scenario=scenario,
                start_period=fs_start,
                end_period=fs_end,
            )
        except Exception:
            financial = None

    drill_filters = {
        k: v
        for k, v in dashboard_filters.items()
        if k in {"region", "segment", "owner", "marketing_channel"} and v
    }
    drilldown_payload: dict = {}
    for wf_type in ("pipeline_created", "closed_won", "closed_lost", "slipped_pipeline"):
        try:
            drill = pipeline_drilldown(
                db,
                organization_id,
                scenario=scenario,
                period=as_of,
                waterfall_type=wf_type,
                **drill_filters,
            )
            drilldown_payload[wf_type] = drill.model_dump(mode="json")
        except Exception:
            drilldown_payload[wf_type] = {"opportunities": [], "waterfall_type": wf_type}

    gl_detail = _load_gl_detail(db, organization_id, start, end)
    headcount = _load_headcount(db, organization_id, start, end)

    # Attribution for commentary/drilldown: close month only (keeps exports fast).
    attr_filters = {
        k: dashboard_filters[k]
        for k in ("region", "segment", "owner", "marketing_channel")
        if k in dashboard_filters
    }
    opportunity_rows: list = []
    try:
        opportunity_rows = opportunity_attribution(
            db,
            organization_id,
            scenario=scenario,
            start_period=as_of,
            end_period=as_of,
            closed_only=False,
            **attr_filters,
        )
    except Exception:
        opportunity_rows = []

    data_gaps = assess_data_gaps(
        comparison_waterfalls=comparison_waterfalls,
        financial=financial,
        marketing=marketing_comparison,
        gl_count=len(gl_detail),
        headcount_count=len(headcount),
        as_of_period=as_of,
    )

    commentary = None
    commentary_fields = build_commentary_fields_for_export(
        as_of,
        comparison_waterfalls,
        financial,
        marketing_comparison,
        gl_detail,
    )

    partial_bundle = ReportingBundle(
        organization_id=str(organization_id),
        organization_name=getattr(org, "name", None),
        scenario=scenario,
        start_period=start,
        end_period=end,
        as_of_period=as_of,
        period_label=_period_label(as_of),
        executive_flow=executive,
        financial_statements=financial,
        comparison_waterfalls=comparison_waterfalls,
        comparison_financial_statements=comparison_financial,
        marketing_comparison=marketing_comparison,
        gl_detail=gl_detail,
        headcount=headcount,
        pipeline_drilldown=drilldown_payload,
        opportunity_attribution=opportunity_rows,
        data_gaps=data_gaps,
        commentary_fields=commentary_fields,
    )
    mda_commentary = generate_mda_commentary(partial_bundle, use_ai=include_ai_commentary)

    if include_ai_commentary and get_settings().openai_api_key:
        try:
            from app.services.reporting.export.board_inputs_mapper import build_commentary_inputs

            inputs = build_commentary_inputs(
                organization_name=org.name,
                as_of_period=as_of,
                bundle_data=executive,
                financial=financial,
            )
            client = build_openai_commentary_client()
            commentary = generate_commentary(inputs, client)
            commentary_fields[0] = CommentaryField(
                section="Executive Summary",
                period=as_of,
                what_changed=commentary.executive_summary.narrative[:500],
                leadership_attention="; ".join(
                    r.description for r in commentary.risks_and_opportunities[:3]
                ),
                source="ai",
            )
        except Exception:
            commentary = None

    bundle = ReportingBundle(
        organization_id=str(organization_id),
        organization_name=getattr(org, "name", None),
        scenario=scenario,
        start_period=start,
        end_period=end,
        as_of_period=as_of,
        period_label=_period_label(as_of),
        executive_flow=executive,
        financial_statements=financial,
        comparison_waterfalls=comparison_waterfalls,
        comparison_financial_statements=comparison_financial,
        marketing_comparison=marketing_comparison,
        gl_detail=gl_detail,
        headcount=headcount,
        pipeline_drilldown=drilldown_payload,
        opportunity_attribution=opportunity_rows,
        mda_commentary=mda_commentary,
        data_gaps=data_gaps,
        commentary=commentary,
        commentary_fields=commentary_fields,
    )
    bundle.validation = run_export_validation_bundle(bundle)
    return bundle
