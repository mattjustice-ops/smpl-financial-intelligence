"""Build narrative-ordered board deck slides (GTM → Cash story chain)."""

from __future__ import annotations

from datetime import date

from app.services.board_package.package import fmt_money
from app.services.board_package.schemas import BoardPackage, CalloutBlock, SlideContent
from app.services.reporting.export.board_chart_service import (
    arr_retention_kpis,
    cash_operating_chart,
    department_variance_table,
    executive_callouts,
    headcount_bridge_chart,
    headcount_kpis,
)
from app.services.reporting.export.board_commentary_service import SlideCommentary
from app.services.reporting.export.board_reference_tables import arr_rollforward_table
from app.services.reporting.export.board_chart_service import _kpi
from app.services.board_package.package import fmt_pct
from app.services.reporting.export.board_metrics_snapshot import build_metrics_snapshot
from app.services.reporting.export.board_semantic_mappings import (
    NARRATIVE_SLIDE_ORDER,
    SECTION_DIVIDERS,
    filter_slides_for_package,
)
from app.presentation.templates.archetypes import apply_template_to_slide
from app.services.reporting.export.board_slide_templates import assemble_slide
from app.services.reporting.export.board_slide_viability import filter_board_slides
from app.services.reporting.export.board_story_chain import SECTION_TRANSITIONS, key_takeaway_from_commentary
from app.services.reporting.export.board_visuals import (
    arr_slide_chart,
    arr_slide_kpis,
    cash_slide_chart,
    channel_efficiency_ranked,
    deferred_slide_chart,
    executive_period_table,
    executive_summary_kpis,
    executive_trajectory_chart,
    executive_wins_risks,
    funnel_chart,
    funnel_conversion_table,
    gtm_pipeline_trend_chart,
    gtm_top_kpis,
    mda_narrative_cards,
    opportunity_cards,
    pipeline_aging_slide_chart,
    pipeline_health_chart,
    pipeline_health_kpis,
    pipeline_movement_split_chart,
    retention_trend_chart,
    revenue_slide_chart,
)
from app.services.reporting.export.mda_pptx import _optional_table, _wf_amount
from app.services.reporting.export.schemas import ReportingBundle


def _section_transition(
    slide_id: str,
    anchor_id: str,
    bundle: ReportingBundle,
    commentary: dict[str, SlideCommentary],
) -> SlideContent | None:
    """Rich section divider: title, chain, narrative, one KPI."""
    meta = SECTION_TRANSITIONS.get(anchor_id)
    if not meta:
        label, title = SECTION_DIVIDERS.get(anchor_id, ("", "Section"))
        return apply_template_to_slide(
            SlideContent(
                slide_id=slide_id,
                title=title,
                section_label=label,
                layout="section_transition",
                subtitle="",
            )
        )

    comm = commentary.get(meta.get("narrative_key", anchor_id), SlideCommentary())
    narrative = key_takeaway_from_commentary(comm) or comm.what_happened or comm.impact
    if not narrative:
        narrative = meta.get("chain", "")
    if len(narrative.strip()) < 8:
        return None

    m = build_metrics_snapshot(bundle)
    cur = bundle.currency
    kpi = None
    if anchor_id == "gtm_performance":
        won = m.closed_won
        created = m.pipeline_created
        cov = (created / won) if won else None
        kpi = _kpi(
            "Coverage (CM)",
            fmt_pct(cov) if cov else "n/a",
            subtext=f"Pipeline {fmt_money(created, cur)} / closed {fmt_money(won, cur)}",
            group="gtm",
        )
    elif anchor_id in ("pipeline_health", "arr_waterfall"):
        kpi = _kpi(
            "Ending ARR",
            fmt_money(m.ending_arr, cur),
            subtext=f"Net new {fmt_money(m.net_new_arr, cur)}",
            group="growth",
        )
    elif anchor_id == "gaap_revenue":
        kpi = _kpi(
            "Revenue (CM)",
            fmt_money(m.revenue_actual, cur),
            subtext="ARR → billings → recognition",
            group="growth",
        )
    elif anchor_id == "cash_forecast":
        kpi = _kpi(
            "Ending Cash",
            fmt_money(m.cash_actual or m.cash_forecast, cur),
            subtext="Liquidity trajectory",
            group="liquidity",
        )

    return apply_template_to_slide(
        SlideContent(
            slide_id=slide_id,
            title=meta["title"],
            section_label="OPERATING REVIEW",
            subtitle=meta.get("chain", ""),
            layout="section_transition",
            narrative=narrative[:220],
            kpi_cards=[kpi] if kpi else [],
            key_takeaway=narrative[:140],
        )
    )


def _executive_takeaway_bullets(comm: SlideCommentary, bundle: ReportingBundle) -> list[str]:
    """IMG 8039-style key takeaways — what / why / impact / action."""
    lines: list[str] = []
    if comm.what_happened:
        lines.append(f"What changed: {comm.what_happened}")
    if comm.why_it_happened:
        lines.append(f"Why: {comm.why_it_happened}")
    if comm.impact:
        lines.append(f"So what: {comm.impact}")
    for b in comm.bullets_favorable_unfavorable_watch():
        if b and len(lines) < 5:
            lines.append(b)
    if comm.recommended_actions and len(lines) < 5:
        lines.append(f"Action: {comm.recommended_actions}")
    if not lines:
        lines.extend(_wins_risks_bullets(bundle)[:4])
    return lines[:5]


def _wins_risks_bullets(bundle: ReportingBundle) -> list[str]:
    wins, risks, actions = executive_wins_risks(bundle)
    lines: list[str] = []
    for w in wins:
        lines.append(f"Win: {w}")
    for r in risks:
        lines.append(f"Risk: {r}")
    for a in actions:
        lines.append(f"Action: {a}")
    return lines[:6]


def _exec_callouts(bundle: ReportingBundle) -> list[CalloutBlock]:
    wins, risks, actions = executive_wins_risks(bundle)
    out: list[CalloutBlock] = []
    for w in wins:
        out.append(CalloutBlock(kind="win", text=w, owner="CEO"))
    for r in risks:
        out.append(CalloutBlock(kind="risk", text=r, owner="CFO"))
    for a in actions:
        out.append(CalloutBlock(kind="action", text=a, owner="CEO"))
    return out[:6]


def _risk_matrix_callouts(bundle: ReportingBundle, comm: SlideCommentary) -> list[CalloutBlock]:
    from app.services.reporting.export.board_metrics_snapshot import build_metrics_snapshot

    m = build_metrics_snapshot(bundle)
    items: list[CalloutBlock] = []
    if m.slipped:
        items.append(
            CalloutBlock(
                kind="risk",
                text=f"GTM — deferred pipeline {fmt_money(m.slipped, bundle.currency)} may compress coverage.",
                owner="CRO",
            )
        )
    if m.churn:
        items.append(
            CalloutBlock(
                kind="risk",
                text=f"Forecast — churn {fmt_money(m.churn, bundle.currency)} pressures retention confidence.",
                owner="CFO",
            )
        )
    if bundle.validation.failed_count:
        items.append(
            CalloutBlock(
                kind="risk",
                text=f"Data — {bundle.validation.failed_count} validation check(s) failed before distribution.",
                owner="CFO",
            )
        )
    if m.expansion > m.churn:
        items.append(
            CalloutBlock(
                kind="action",
                text="Opportunity — scale expansion plays where expansion exceeds churn.",
                owner="CRO",
            )
        )
    if comm.recommended_actions:
        items.append(CalloutBlock(kind="action", text=comm.recommended_actions, owner="CEO"))
    return items[:6]


def _build_slide_by_id(
    slide_id: str,
    bundle: ReportingBundle,
    commentary: dict[str, SlideCommentary],
) -> SlideContent | None:
    as_of = bundle.as_of_period
    comm = commentary.get(slide_id) or SlideCommentary()

    if slide_id == "executive_summary":
        return assemble_slide(
            slide_id,
            "Executive Summary",
            bundle,
            comm,
            section_label="EXECUTIVE SUMMARY",
            subtitle=f"Close {as_of} · Actual + Forecast · CM / QTD / YTD / FY Outlook",
            table=executive_period_table(bundle),
            chart=executive_trajectory_chart(bundle),
            kpi_cards=executive_summary_kpis(bundle),
            callouts=[],
            bullets=_executive_takeaway_bullets(comm, bundle),
            commentary_heading="Key takeaways",
            key_takeaway=comm.impact or comm.recommended_actions,
            footnote="Source: MRR waterfall (ARR), pipeline waterfall, cash bridge",
            max_table_rows=6,
            max_kpis=4,
        )

    if slide_id == "mda_summary":
        cards = [c for c in mda_narrative_cards(comm) if c]
        return assemble_slide(
            slide_id,
            "SaaS MD&A Summary",
            bundle,
            comm,
            section_label="MD&A",
            bullets=cards[:5] or None,
            commentary_heading="Management interpretation",
            key_takeaway=comm.impact or comm.recommended_actions,
        )

    if slide_id == "gtm_performance":
        return assemble_slide(
            slide_id,
            "GTM Performance",
            bundle,
            comm,
            section_label="GTM",
            chart=gtm_pipeline_trend_chart(bundle),
            kpi_cards=gtm_top_kpis(bundle),
            commentary_heading="GTM narrative",
            bullets=None,
        )

    if slide_id == "marketing_channels":
        tbl = channel_efficiency_ranked(bundle, max_rows=6)
        return assemble_slide(
            slide_id,
            "Marketing Channel Efficiency",
            bundle,
            commentary.get("marketing_channels", comm),
            section_label="GTM · CHANNELS",
            table=tbl,
            commentary_heading="Channel signals",
            max_table_rows=5,
        )

    if slide_id == "funnel_conversion":
        chart = funnel_chart(bundle)
        table = funnel_conversion_table(bundle) if not chart else None
        return assemble_slide(
            slide_id,
            "Funnel Conversion",
            bundle,
            commentary.get("funnel_conversion", comm),
            section_label="FUNNEL",
            chart=chart,
            table=table,
            commentary_heading="Conversion quality",
        )

    if slide_id == "pipeline_health":
        return assemble_slide(
            slide_id,
            "Pipeline Health",
            bundle,
            comm,
            section_label="PIPELINE",
            chart=pipeline_health_chart(bundle) or pipeline_aging_slide_chart(bundle),
            kpi_cards=pipeline_health_kpis(bundle),
        )

    if slide_id == "pipeline_movement":
        return assemble_slide(
            slide_id,
            "Pipeline Movement",
            bundle,
            comm,
            section_label="PIPELINE · MOVEMENT",
            chart=pipeline_movement_split_chart(bundle),
            commentary_heading="CRM activity",
        )

    if slide_id == "opportunity_drilldown":
        return assemble_slide(
            slide_id,
            "Opportunity Drilldown",
            bundle,
            comm,
            section_label="PIPELINE · DEALS",
            spotlight_cards=opportunity_cards(bundle),
        )

    if slide_id == "arr_waterfall":
        chart = arr_slide_chart(bundle)
        table = arr_rollforward_table(bundle) if not chart else None
        return assemble_slide(
            slide_id,
            "ARR / MRR Waterfall",
            bundle,
            comm,
            section_label="ARR",
            chart=chart,
            table=table,
            kpi_cards=arr_slide_kpis(bundle),
            max_table_rows=5,
        )

    if slide_id == "retention_churn":
        churn = abs(_wf_amount(bundle, "arr", "churn_arr", as_of) or _wf_amount(bundle, "arr", "churn", as_of))
        expansion = _wf_amount(bundle, "arr", "expansion_arr", as_of) or _wf_amount(bundle, "arr", "expansion", as_of)
        return assemble_slide(
            slide_id,
            "Retention & Churn",
            bundle,
            commentary.get("retention_churn", comm),
            section_label="ARR · RETENTION",
            chart=retention_trend_chart(bundle),
            kpi_cards=arr_slide_kpis(bundle),
            table=_optional_table(
                ["Component", "ARR (CM)"],
                [
                    ["Expansion", fmt_money(expansion, bundle.currency)],
                    ["Churn", fmt_money(churn, bundle.currency)],
                ],
            ),
        )

    if slide_id == "gaap_revenue":
        return assemble_slide(
            slide_id,
            "GAAP Revenue Bridge",
            bundle,
            commentary.get("gaap_revenue", comm),
            section_label="REVENUE",
            chart=revenue_slide_chart(bundle),
        )

    if slide_id == "deferred_revenue":
        return assemble_slide(
            slide_id,
            "Deferred Revenue / Billings",
            bundle,
            commentary.get("deferred_revenue", comm),
            section_label="REVENUE · DEFERRED",
            chart=deferred_slide_chart(bundle),
        )

    if slide_id == "cash_forecast":
        from app.services.reporting.export.board_metrics_snapshot import build_metrics_snapshot

        m = build_metrics_snapshot(bundle)
        return assemble_slide(
            slide_id,
            "Cash Forecast",
            bundle,
            comm,
            section_label="CASH",
            chart=cash_slide_chart(bundle) or cash_operating_chart(bundle),
            table=_optional_table(
                ["Driver", "Amount"],
                [
                    ["Ending Cash", fmt_money(m.cash_actual, bundle.currency)],
                    ["FY Outlook", fmt_money(m.cash_forecast, bundle.currency)],
                ],
            ),
        )

    if slide_id == "headcount":
        return assemble_slide(
            slide_id,
            "Headcount & Hiring",
            bundle,
            commentary.get("headcount", comm),
            section_label="CAPACITY",
            chart=headcount_bridge_chart(bundle),
            kpi_cards=headcount_kpis(bundle),
            commentary_heading="Workforce",
        )

    if slide_id == "department_spend":
        return assemble_slide(
            slide_id,
            "Department Spend / P&L",
            bundle,
            commentary.get("department_spend", comm),
            section_label="FINANCIALS",
            table=department_variance_table(bundle),
            commentary_heading="Spend drivers",
        )

    if slide_id == "risks_opportunities":
        return assemble_slide(
            slide_id,
            "Risks & Opportunities",
            bundle,
            comm,
            section_label="DECISIONS",
            callouts=_risk_matrix_callouts(bundle, comm),
        )

    if slide_id == "validation":
        val_rows = [
            [c.validation_name[:36], c.status, str(c.variance or "")[:12]]
            for c in bundle.validation.checks[:10]
        ]
        return assemble_slide(
            slide_id,
            "Validation / Data Quality",
            bundle,
            commentary.get("validation", comm),
            section_label="APPENDIX",
            subtitle=f"Overall: {bundle.validation.status.upper()}",
            table=_optional_table(["Check", "Status", "Variance"], val_rows),
            max_table_rows=10,
        )

    return None


def build_board_slides(
    bundle: ReportingBundle,
    commentary: dict[str, SlideCommentary],
    *,
    include_validation_appendix: bool = True,
    package_mode: str = "full_board",
    include_section_dividers: bool = True,
) -> list[SlideContent]:
    order = list(NARRATIVE_SLIDE_ORDER)
    if not include_validation_appendix:
        order = [s for s in order if s != "validation"]
    order = filter_slides_for_package(order, package_mode)  # type: ignore[arg-type]

    slides: list[SlideContent] = []
    for slide_id in order:
        if include_section_dividers and package_mode == "full_board" and slide_id in SECTION_TRANSITIONS:
            section = _section_transition(f"section_{slide_id}", slide_id, bundle, commentary)
            if section:
                slides.append(section)
        built = _build_slide_by_id(slide_id, bundle, commentary)
        if built:
            slides.append(built)
    return filter_board_slides(slides)


def build_board_package(
    bundle: ReportingBundle,
    commentary: dict[str, SlideCommentary],
    *,
    include_validation_appendix: bool = True,
    package_mode: str = "full_board",
) -> BoardPackage:
    as_of = bundle.as_of_period
    prepared = date(int(as_of[:4]), int(as_of[5:7]), 1)
    titles = {
        "executive_summary": "Executive Summary",
        "gtm_deep_dive": "GTM Operating Review",
        "finance_deep_dive": "Finance Operating Review",
        "variance_commentary": "Variance Commentary",
    }
    label = titles.get(package_mode, "SMPL Board Operating Review")
    from app.services.reporting.export.company_context import COMPANY_NAME

    org = bundle.organization_name or COMPANY_NAME
    slides = build_board_slides(
        bundle,
        commentary,
        include_validation_appendix=include_validation_appendix,
        package_mode=package_mode,
    )
    return BoardPackage(
        organization_name=org,
        period_label=f"{bundle.period_label} — {label}",
        prepared_for="Board of Directors",
        prepared_date=prepared,
        currency=bundle.currency,
        slides=slides,
    )
