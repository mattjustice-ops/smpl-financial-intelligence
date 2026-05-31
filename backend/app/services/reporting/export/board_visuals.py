"""Board-ready visuals: YTD framing, single primary chart per slide, executive tables."""

from __future__ import annotations

from decimal import Decimal

from app.services.board_package.package import fmt_money, fmt_pct
from app.services.board_package.schemas import ChartSpec, KpiCard, TableSpec
from app.services.reporting.export.board_chart_service import (
    _chart,
    _kpi,
    _wf,
    executive_scorecard_kpis,
    arr_waterfall_chart,
    arr_retention_kpis,
    cash_forecast_line_chart,
    deferred_revenue_chart,
    executive_callouts,
    opportunity_spotlights,
    pipeline_aging_chart,
    revenue_story_chart,
)
from app.services.reporting.export.board_chart_density import (
    prepare_chart_for_executive,
    prepare_trend_chart,
)
from app.services.reporting.export.board_slide_viability import chart_has_decision_value
from app.services.reporting.export.board_format_utils import variance_subtext
from app.services.reporting.export.board_metrics_snapshot import build_metrics_snapshot
from app.services.reporting.export.reporting_period_engine import build_period_context
from app.services.reporting.export.saas_semantic_reporting import (
    PipelineAgeBucket,
    build_channel_dimensions,
    build_movement_attribution,
    build_pipeline_aging,
    build_revenue_lineage,
    collapse_channels,
    movement_chart_categories,
)
from app.services.reporting.export.board_period_ytd import (
    PeriodRollup,
    monthly_ending_arr_series,
    monthly_flow_series,
    rollup_cash,
    rollup_ebitda,
    rollup_ending_arr,
    rollup_pipeline_created,
    rollup_revenue,
)
from app.services.reporting.export.schemas import ReportingBundle


def _pct_var(actual: Decimal, budget: Decimal) -> str:
    if budget == 0:
        return "—"
    return f"{float((actual - budget) / budget):.0%}"


def _rollup_row(label: str, r: PeriodRollup, cur: str) -> list[str]:
    return [
        label,
        fmt_money(r.current_month, cur),
        fmt_money(r.qtd, cur),
        fmt_money(r.ytd, cur),
        fmt_money(r.fy_outlook, cur),
        _pct_var(r.ytd, r.budget_ytd),
    ]


def executive_period_table(bundle: ReportingBundle) -> TableSpec:
    cur = bundle.currency
    rows = [
        _rollup_row("Ending ARR", rollup_ending_arr(bundle), cur),
        _rollup_row("Revenue", rollup_revenue(bundle), cur),
        _rollup_row("EBITDA", rollup_ebitda(bundle), cur),
        _rollup_row("Ending Cash", rollup_cash(bundle), cur),
        _rollup_row("Pipeline Created (YTD flow)", rollup_pipeline_created(bundle), cur),
    ]
    return TableSpec(
        headers=["Metric", "CM", "QTD", "YTD", "FY Outlook", "YTD vs Budget"],
        rows=rows,
    )


def executive_summary_kpis(bundle: ReportingBundle) -> list[KpiCard]:
    """CM-focused KPIs — max 4 on slide."""
    return executive_scorecard_kpis(bundle)[:4]


def executive_cm_kpis(bundle: ReportingBundle) -> list[KpiCard]:
    cur = bundle.currency
    arr = rollup_ending_arr(bundle)
    rev = rollup_revenue(bundle)
    ebitda = rollup_ebitda(bundle)
    cash = rollup_cash(bundle)
    return [
        _kpi(
            "ARR (CM)",
            fmt_money(arr.current_month, cur),
            subtext=variance_subtext(arr.current_month, arr.budget_cm, currency=cur),
            group="growth",
            tone="favorable" if arr.current_month >= arr.budget_cm else "unfavorable",
        ),
        _kpi(
            "Revenue (CM)",
            fmt_money(rev.current_month, cur),
            subtext=f"YTD {fmt_money(rev.ytd, cur)}",
            group="profitability",
        ),
        _kpi(
            "EBITDA (CM)",
            fmt_money(ebitda.current_month, cur),
            subtext=f"YTD {fmt_money(ebitda.ytd, cur)}",
            group="profitability",
        ),
        _kpi("Cash", fmt_money(cash.current_month, cur), subtext=f"FY outlook {fmt_money(cash.fy_outlook, cur)}", group="liquidity"),
    ]


def executive_trajectory_chart(bundle: ReportingBundle) -> ChartSpec | None:
    ctx = build_period_context(bundle)
    labels, act, outlook, budget = monthly_ending_arr_series(bundle)
    if not labels or (not any(act) and not any(outlook)):
        return None
    periods = list(ctx.fiscal_periods)
    spec = prepare_trend_chart(
        "Ending ARR — YTD Actual + FY Outlook",
        periods[: len(labels)],
        {"Actual": act, "Outlook": outlook},
        chart_type="line",
    )
    return spec if chart_has_decision_value(spec) else None


def gtm_top_kpis(bundle: ReportingBundle) -> list[KpiCard]:
    m = build_metrics_snapshot(bundle)
    cur = bundle.currency
    ratio = (m.pipeline_from_marketing / m.marketing_spend) if m.marketing_spend else None
    kpis = [
        _kpi("Marketing Spend (CM)", fmt_money(m.marketing_spend, cur), group="gtm"),
        _kpi("Pipeline Created (CM)", fmt_money(m.pipeline_from_marketing, cur), group="gtm"),
        _kpi("Closed Won ARR (CM)", fmt_money(m.closed_won_arr_mkt or m.closed_won, cur), group="gtm", tone="favorable"),
    ]
    if ratio:
        kpis.append(_kpi("Pipe / Spend", f"{float(ratio):.1f}x", group="efficiency"))
    return kpis[:4]


def gtm_pipeline_trend_chart(bundle: ReportingBundle) -> ChartSpec | None:
    labels, act, outlook = monthly_flow_series(bundle, "pipeline", "pipeline_created")
    if not any(act) and not any(outlook):
        return None
    return _chart(
        "Pipeline Created by Month",
        labels,
        {"Actual": act, "Outlook": outlook},
        chart_type="column",
        y_axis_label="ARR ($)",
    )


def funnel_chart(bundle: ReportingBundle) -> ChartSpec | None:
    as_of = bundle.as_of_period
    mkt = bundle.marketing_comparison
    if not mkt:
        return None
    mql = sql = sal = opp = Decimal("0")
    for row in mkt.actual:
        if row.period != as_of:
            continue
        mql += row.mqls
        sql += row.sqls
        sal += row.sals
        opp += row.opportunities_created
    if mql == 0 and sql == 0:
        return None
    cats = ["MQL", "SQL", "SAL", "Opps"]
    counts = [float(mql), float(sql), float(sal), float(opp)]
    conv: list[float] = []
    prev = counts[0] or 1.0
    for i, c in enumerate(counts):
        if i == 0:
            conv.append(100.0)
        else:
            conv.append(round(100 * c / prev, 0) if prev else 0)
            prev = c or prev
    return _chart(
        "Funnel Volume (CM) — counts only",
        cats,
        {"Count": counts},
        chart_type="column",
        y_axis_label="Count",
    )


def funnel_conversion_table(bundle: ReportingBundle) -> TableSpec | None:
    as_of = bundle.as_of_period
    mkt = bundle.marketing_comparison
    if not mkt:
        return None
    mql = sql = sal = opp = Decimal("0")
    for row in mkt.actual:
        if row.period != as_of:
            continue
        mql += row.mqls
        sql += row.sqls
        sal += row.sals
        opp += row.opportunities_created
    won = abs(_wf(bundle, "pipeline", "closed_won", as_of))
    rows: list[list[str]] = []
    if mql:
        rows.append(["MQL → SQL", f"{float(sql / mql):.0%}" if mql else "—", f"{int(sql)} SQLs", ""])
    if sql:
        rows.append(["SQL → SAL", f"{float(sal / sql):.0%}" if sql else "—", f"{int(sal)} SALs", ""])
    if sal:
        rows.append(["SAL → Opps", f"{float(opp / sal):.0%}" if sal else "—", f"{int(opp)} opps", ""])
    rows.append(["Closed Won ARR", "—", fmt_money(won, bundle.currency), "Separate from counts"])
    return TableSpec(headers=["Stage", "Conv %", "Volume", ""], rows=rows)


def pipeline_health_chart(bundle: ReportingBundle) -> ChartSpec | None:
    m = build_metrics_snapshot(bundle)
    cats = ["Created", "Closed Won", "Closed Lost", "Deferred"]
    vals = [
        float(m.pipeline_created),
        float(m.closed_won),
        float(m.closed_lost),
        float(m.slipped),
    ]
    if not any(vals):
        return None
    spec = _chart(
        "Pipeline Activity (CM) — creation & conversion",
        cats,
        {"ARR ($)": vals},
        chart_type="column",
        y_axis_label="ARR",
        archetype="pipeline_movement_bridge",
    )
    return (
        prepare_chart_for_executive(spec, movement_type="pipeline_movement")
        if spec
        else None
    )


def pipeline_movement_split_chart(bundle: ReportingBundle) -> ChartSpec | None:
    """Operational movement lineage — not same-month creation only."""
    summary = build_movement_attribution(bundle)
    cats, arr_vals, counts = movement_chart_categories(summary)
    if not cats:
        return None
    note = f"{sum(counts)} movements · {bundle.as_of_period}"
    spec = _chart(
        f"CRM Movement Lineage ({note})",
        cats,
        {"ARR": arr_vals},
        chart_type="column",
        y_axis_label="ARR",
        archetype="pipeline_movement_bridge",
    )
    return (
        prepare_chart_for_executive(spec, movement_type="pipeline_movement")
        if spec
        else None
    )


def pipeline_health_kpis(bundle: ReportingBundle) -> list[KpiCard]:
    m = build_metrics_snapshot(bundle)
    cur = bundle.currency
    created = m.pipeline_created
    won = m.closed_won
    coverage = (created / won) if won else None
    return [
        _kpi("Pipeline Created", fmt_money(created, cur), group="gtm"),
        _kpi("Active Pipe (proxy)", fmt_money(m.active_pipeline_proxy, cur), group="gtm"),
        _kpi("Coverage (CM)", fmt_pct(coverage) if coverage else "n/a", subtext="Created / closed won", group="gtm"),
    ]


def channel_efficiency_ranked(bundle: ReportingBundle, *, max_rows: int = 9) -> TableSpec | None:
    cur = bundle.currency
    dims = collapse_channels(build_channel_dimensions(bundle), top_n=5, bottom_n=3)
    if not dims:
        return None
    rows = [
        [
            r.channel[:16],
            fmt_money(r.spend, cur),
            fmt_money(r.pipeline_created, cur),
            fmt_money(r.closed_won_arr, cur),
            f"{r.pipeline_per_spend:.1f}x" if r.pipeline_per_spend else "—",
            "Strong" if (r.pipeline_per_spend or 0) >= 2.5 else "Watch",
        ]
        for r in dims[:max_rows]
    ]
    return TableSpec(
        headers=["Channel", "Spend", "Pipeline", "Closed Won", "Pipe/Spend", "Signal"],
        rows=rows,
    )


def mda_narrative_cards(comm) -> list[str]:
    return [
        f"What changed: {comm.what_happened}" if comm.what_happened else "",
        f"Why: {comm.why_it_happened}" if comm.why_it_happened else "",
        f"Impact: {comm.impact}" if comm.impact else "",
        f"Risks: {comm.unfavorable}" if comm.unfavorable else "",
        f"Actions: {comm.recommended_actions}" if comm.recommended_actions else "",
    ]


def executive_wins_risks(bundle: ReportingBundle) -> tuple[list[str], list[str], list[str]]:
    callouts = executive_callouts(bundle)
    wins = [c.text for c in callouts if c.kind == "win"][:3]
    risks = [c.text for c in callouts if c.kind == "risk"][:3]
    actions = [c.text for c in callouts if c.kind == "action"][:3]
    return wins, risks, actions


# Re-export chart builders used unchanged
def arr_slide_chart(bundle):  # noqa: ANN001
    return arr_waterfall_chart(bundle)


def arr_slide_kpis(bundle):  # noqa: ANN001
    return arr_retention_kpis(bundle)


def cash_slide_chart(bundle):  # noqa: ANN001
    return cash_forecast_line_chart(bundle) or None


def revenue_slide_chart(bundle: ReportingBundle) -> ChartSpec | None:
    lineage = build_revenue_lineage(bundle)
    if not any([lineage.ending_arr, lineage.billings, lineage.gaap_revenue]):
        return revenue_story_chart(bundle)
    cats = ["ARR", "Billings", "Deferred", "Revenue", "Collections", "Cash"]
    vals = [
        float(lineage.ending_arr),
        float(lineage.billings),
        float(lineage.deferred_revenue),
        float(lineage.gaap_revenue),
        float(lineage.collections),
        float(lineage.ending_cash),
    ]
    spec = _chart("SaaS Revenue Lineage", cats, {"Amount": vals}, chart_type="column", y_axis_label="USD")
    return prepare_chart_for_executive(spec) if spec else None


def deferred_slide_chart(bundle):  # noqa: ANN001
    return deferred_revenue_chart(bundle)


def retention_trend_chart(bundle: ReportingBundle) -> ChartSpec | None:
    labels, act_e, out_e = monthly_flow_series(bundle, "arr", "expansion_arr")
    if not any(act_e):
        labels, act_e, out_e = monthly_flow_series(bundle, "arr", "expansion")
    _, act_c, out_c = monthly_flow_series(bundle, "arr", "churn_arr")
    if not any(act_c):
        _, act_c, out_c = monthly_flow_series(bundle, "arr", "churn")
    churn_line = [-abs(v) for v in out_c]
    if not labels or (not any(act_e) and not any(churn_line)):
        return None
    return _chart(
        "Expansion vs Churn (monthly ARR)",
        labels,
        {"Expansion": out_e, "Churn": churn_line},
        chart_type="column",
        y_axis_label="ARR ($)",
    )


def opportunity_cards(bundle):  # noqa: ANN001
    return opportunity_spotlights(bundle)


def pipeline_aging_slide_chart(bundle: ReportingBundle) -> ChartSpec | None:
    aging = build_pipeline_aging(bundle)
    if not any(aging.values()):
        return pipeline_aging_chart(bundle)
    cats = [b.value for b in PipelineAgeBucket]
    vals = [float(aging[b]) for b in PipelineAgeBucket]
    spec = _chart("Active Pipeline by Age", cats, {"ARR": vals}, chart_type="column", y_axis_label="ARR")
    return prepare_chart_for_executive(spec) if spec else None
