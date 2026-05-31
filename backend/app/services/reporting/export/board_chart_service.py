"""Chart and KPI builders for executive board decks."""

from __future__ import annotations

from decimal import Decimal

from app.services.board_package.package import fmt_money, fmt_pct
from app.services.board_package.schemas import ChartSpec, KpiCard, TableSpec
from app.services.reporting.export.board_format_utils import (
    direction_from_delta,
    direction_glyph,
    tone_from_variance,
    variance_subtext,
)
from app.services.reporting.export.board_semantic_mappings import metric_group_for
from app.services.reporting.export.schemas import ReportingBundle


def _wf(bundle: ReportingBundle, key: str, wtype: str, period: str, scenario: str = "Actual") -> Decimal:
    for row in bundle.comparison_waterfalls.get(key) or []:
        if row.period == period and row.waterfall_type == wtype and row.scenario == scenario:
            return row.amount
    wf = bundle.executive_flow.waterfalls.get(key)
    if wf:
        for row in wf.rows:
            if row.period == period and row.waterfall_type == wtype:
                return row.amount
    return Decimal("0")


def _kpi(
    label: str,
    value: str,
    *,
    subtext: str | None = None,
    tone: str = "neutral",
    group: str | None = None,
    direction: str | None = None,
) -> KpiCard:
    return KpiCard(
        label=label,
        value=value,
        subtext=subtext,
        tone=tone,  # type: ignore[arg-type]
        group=group,  # type: ignore[arg-type]
        direction=direction,  # type: ignore[arg-type]
    )


def _chart(
    title: str,
    categories: list[str],
    series: dict[str, list[float]],
    *,
    chart_type: str = "column",
    y_axis_label: str | None = None,
    archetype: str | None = None,
) -> ChartSpec:
    cats = categories[:8]
    trimmed = {k: v[: len(cats)] for k, v in series.items()}
    return ChartSpec(
        chart_type=chart_type,  # type: ignore[arg-type]
        archetype=archetype,
        title=title,
        categories=cats,
        series=trimmed,
        y_axis_label=y_axis_label,
        max_categories=8,
    )


# ---------------------------------------------------------------------------
# Executive scorecard (grouped KPIs with variance)
# ---------------------------------------------------------------------------


def executive_scorecard_kpis(bundle: ReportingBundle) -> list[KpiCard]:
    as_of = bundle.as_of_period
    cur = bundle.currency
    arr = _wf(bundle, "arr", "ending_arr", as_of) or _wf(bundle, "arr", "ending", as_of)
    arr_b = _wf(bundle, "arr", "ending_arr", as_of, "Budget") or _wf(bundle, "arr", "ending", as_of, "Budget")
    new_arr = _wf(bundle, "arr", "new_arr", as_of) or _wf(bundle, "arr", "new_business", as_of)
    churn = abs(_wf(bundle, "arr", "churn_arr", as_of) or _wf(bundle, "arr", "churn", as_of))
    grr = ((arr - churn) / arr) if arr else None

    revenue = ebitda = Decimal("0")
    rev_b = ebitda_b = Decimal("0")
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if fs:
        for row in fs.income_statement.rows:
            p = str(row.period)[:7]
            if p != as_of:
                continue
            if "revenue" in row.line_item.lower() and "deferred" not in row.line_item.lower():
                if row.scenario == "Actual":
                    revenue = row.amount
                elif row.scenario == "Budget":
                    rev_b = row.amount
            if "ebitda" in row.line_item.lower():
                if row.scenario == "Actual":
                    ebitda = row.amount
                elif row.scenario == "Budget":
                    ebitda_b = row.amount

    cash = _wf(bundle, "cash_flow", "ending_cash", as_of)
    created = _wf(bundle, "pipeline", "pipeline_created", as_of)
    won = abs(_wf(bundle, "pipeline", "closed_won", as_of))
    coverage = (created / won) if won else None
    spend = pipe_mkt = Decimal("0")
    if bundle.marketing_comparison:
        for row in bundle.marketing_comparison.actual:
            if row.period == as_of:
                spend += row.marketing_spend
                pipe_mkt += row.pipeline_arr_created
    pipe_eff = (pipe_mkt / spend) if spend else None
    hc = sum(int(r.headcount or 0) for r in bundle.headcount if r.period == as_of and r.scenario == "Actual")

    cards: list[KpiCard] = [
        _kpi(
            "Ending ARR",
            fmt_money(arr, cur),
            subtext=variance_subtext(arr, arr_b, currency=cur),
            tone=tone_from_variance(arr, arr_b),
            group="growth",
            direction=direction_from_delta(arr - arr_b),
        ),
        _kpi(
            "Net New ARR",
            fmt_money(new_arr, cur),
            group="growth",
            direction=direction_from_delta(new_arr),
        ),
        _kpi(
            "Revenue",
            fmt_money(revenue, cur),
            subtext=variance_subtext(revenue, rev_b, currency=cur),
            tone=tone_from_variance(revenue, rev_b),
            group="profitability",
            direction=direction_from_delta(revenue - rev_b),
        ),
        _kpi(
            "EBITDA",
            fmt_money(ebitda, cur),
            subtext=variance_subtext(ebitda, ebitda_b, currency=cur, label="vs Budget"),
            tone=tone_from_variance(ebitda, ebitda_b),
            group="profitability",
            direction=direction_from_delta(ebitda - ebitda_b),
        ),
        _kpi("Cash", fmt_money(cash, cur), group="liquidity", direction="flat"),
        _kpi(
            "Pipeline Coverage",
            fmt_pct(coverage) if coverage is not None else "n/a",
            subtext="Created / closed won (period)",
            group="gtm",
        ),
        _kpi("GRR", fmt_pct(grr) if grr is not None else "n/a", group="growth"),
        _kpi("Headcount", str(hc), group="efficiency"),
    ]
    if pipe_eff:
        cards.append(
            _kpi(
                "Pipeline / Spend",
                f"{float(pipe_eff):.1f}x",
                group="gtm",
                tone="favorable" if pipe_eff >= Decimal("2.5") else "neutral",
            )
        )
    return cards


def executive_callouts(bundle: ReportingBundle) -> list:
    from app.services.board_package.schemas import CalloutBlock
    from app.services.reporting.export.board_metrics_snapshot import build_metrics_snapshot

    m = build_metrics_snapshot(bundle)
    wins: list[CalloutBlock] = []
    risks: list[CalloutBlock] = []
    actions: list[CalloutBlock] = []

    if m.new_arr_actual > m.new_arr_budget and m.new_arr_budget:
        wins.append(
            CalloutBlock(
                kind="win",
                text=f"Net new ARR beat budget by {fmt_money(m.new_arr_actual - m.new_arr_budget, m.currency)}.",
            )
        )
    if m.expansion > m.churn:
        wins.append(
            CalloutBlock(
                kind="win",
                text="Expansion ARR exceeded churn, supporting net retention momentum.",
            )
        )
    if m.pipeline_from_marketing and m.marketing_spend:
        ratio = m.pipeline_from_marketing / m.marketing_spend
        if ratio >= Decimal("2.5"):
            wins.append(
                CalloutBlock(
                    kind="win",
                    text=f"GTM efficiency improved with pipeline/spend at {float(ratio):.1f}x.",
                )
            )

    if m.churn and m.ending_arr and (m.churn / m.ending_arr) > Decimal("0.05"):
        risks.append(
            CalloutBlock(kind="risk", text="Churn pressure warrants segment-level retention review.", owner="CRO")
        )
    if m.slipped:
        risks.append(
            CalloutBlock(
                kind="risk",
                text=f"Deferred/slipped pipeline of {fmt_money(m.slipped, m.currency)} may affect next-quarter coverage.",
                owner="CRO",
            )
        )
    if bundle.validation.failed_count:
        risks.append(
            CalloutBlock(
                kind="risk",
                text=f"{bundle.validation.failed_count} data validation check(s) failed — resolve before board send.",
                owner="CFO",
            )
        )

    actions.append(
        CalloutBlock(
            kind="action",
            text="Reconcile MRR waterfall to closed-won opportunities and refresh forecast confidence by segment.",
            owner="CFO",
        )
    )
    actions.append(
        CalloutBlock(
            kind="action",
            text="Double down on top-performing channels; pause or restructure bottom-quartile spend.",
            owner="CMO",
        )
    )
    return (wins[:3] + risks[:3] + actions[:3])[:9]


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------


def arr_waterfall_chart(bundle: ReportingBundle) -> ChartSpec | None:
    as_of = bundle.as_of_period
    order = [
        ("beginning_arr", "Beginning ARR"),
        ("new_arr", "New Business"),
        ("new_business", "New Business"),
        ("expansion_arr", "Expansion"),
        ("expansion", "Expansion"),
        ("contraction_arr", "Contraction"),
        ("contraction", "Contraction"),
        ("churn_arr", "Churn"),
        ("churn", "Churn"),
        ("reactivation_arr", "Reactivation"),
        ("ending_arr", "Ending ARR"),
        ("ending", "Ending ARR"),
    ]
    cats: list[str] = []
    vals: list[float] = []
    for wtype, label in order:
        if label in cats:
            continue
        amt = float(_wf(bundle, "arr", wtype, as_of))
        if amt == 0 and label not in {"Beginning ARR", "Ending ARR"}:
            continue
        cats.append(label)
        vals.append(amt)
    if len(cats) < 2:
        return None
    return _chart("ARR Bridge (MRR waterfall)", cats, {"ARR ($)": vals}, chart_type="waterfall", y_axis_label="ARR")


def arr_retention_kpis(bundle: ReportingBundle) -> list[KpiCard]:
    as_of = bundle.as_of_period
    cur = bundle.currency
    arr = _wf(bundle, "arr", "ending_arr", as_of) or _wf(bundle, "arr", "ending", as_of)
    churn = abs(_wf(bundle, "arr", "churn_arr", as_of) or _wf(bundle, "arr", "churn", as_of))
    expansion = _wf(bundle, "arr", "expansion_arr", as_of) or _wf(bundle, "arr", "expansion", as_of)
    new_arr = _wf(bundle, "arr", "new_arr", as_of) or _wf(bundle, "arr", "new_business", as_of)
    grr = ((arr - churn) / arr) if arr else None
    churn_pct = (churn / arr) if arr else None
    exp_pct = (expansion / arr) if arr else None
    return [
        _kpi("Net New ARR", fmt_money(new_arr, cur), group="growth"),
        _kpi("GRR", fmt_pct(grr) if grr else "n/a", group="growth"),
        _kpi("Churn %", fmt_pct(churn_pct) if churn_pct else "n/a", tone="unfavorable", group="growth"),
        _kpi("Expansion %", fmt_pct(exp_pct) if exp_pct else "n/a", tone="favorable", group="growth"),
    ]


def pipeline_activity_chart(bundle: ReportingBundle) -> ChartSpec | None:
    as_of = bundle.as_of_period
    cats = ["Created", "Closed Won", "Closed Lost", "Deferred"]
    keys = ["pipeline_created", "closed_won", "closed_lost", "slipped_pipeline"]
    vals = [abs(float(_wf(bundle, "pipeline", k, as_of))) for k in keys]
    if not any(vals):
        return None
    return _chart(
        "Pipeline Activity (period)",
        cats,
        {"ARR ($)": vals},
        y_axis_label="ARR",
    )


def pipeline_movement_chart(bundle: ReportingBundle) -> ChartSpec | None:
    """CRM movement view — counts where available, ARR otherwise."""
    as_of = bundle.as_of_period
    from app.services.reporting.export.board_metrics_snapshot import build_metrics_snapshot

    snap = build_metrics_snapshot(bundle)
    cats = ["New Pipeline", "Closed Won", "Closed Lost", "Deferred"]
    vals = [
        float(snap.pipeline_created),
        float(snap.closed_won),
        float(snap.closed_lost),
        float(snap.slipped),
    ]
    if not any(vals):
        return None
    counts = [
        snap.movement_counts.get("pipeline_created", 0),
        snap.movement_counts.get("closed_won", 0),
        snap.movement_counts.get("closed_lost", 0),
        snap.movement_counts.get("slipped_pipeline", 0),
    ]
    title = "CRM Movement Analysis"
    if any(counts):
        title += f" ({sum(counts)} opportunity movements)"
    return _chart(title, cats, {"ARR impact ($)": vals}, y_axis_label="ARR")


def pipeline_aging_chart(bundle: ReportingBundle) -> ChartSpec | None:
    """Bucket open pipeline opportunities by days to expected close."""
    buckets = {"0-30d": 0.0, "31-60d": 0.0, "61-90d": 0.0, "90+d": 0.0}
    as_of = bundle.as_of_period
    from datetime import date

    try:
        close_month = date(int(as_of[:4]), int(as_of[5:7]), 1)
    except ValueError:
        return None

    def _og(opp, *keys):
        if isinstance(opp, dict):
            for k in keys:
                if opp.get(k):
                    return opp[k]
        else:
            for k in keys:
                v = getattr(opp, k, None)
                if v:
                    return v
        return None

    for payload in bundle.pipeline_drilldown.values():
        for opp in payload.get("opportunities") or []:
            wt = _og(opp, "waterfall_type")
            if wt and wt not in (None, "pipeline_created"):
                continue
            cd = _og(opp, "close_date", "expected_close_date")
            if not cd or len(str(cd)) < 7:
                buckets["90+d"] += float(_og(opp, "arr_impact") or 0)
                continue
            try:
                parts = str(cd)[:10].split("-")
                close_d = date(int(parts[0]), int(parts[1]), int(parts[2]))
                days = (close_d - close_month).days
            except (ValueError, IndexError):
                buckets["90+d"] += float(_og(opp, "arr_impact") or 0)
                continue
            arr_v = float(_og(opp, "arr_impact") or 0)
            if days <= 30:
                buckets["0-30d"] += arr_v
            elif days <= 60:
                buckets["31-60d"] += arr_v
            elif days <= 90:
                buckets["61-90d"] += arr_v
            else:
                buckets["90+d"] += arr_v

    if not any(buckets.values()):
        return None
    return _chart("Pipeline Aging (active ARR proxy)", list(buckets.keys()), {"ARR ($)": list(buckets.values())})


def cash_forecast_line_chart(bundle: ReportingBundle) -> ChartSpec | None:
    """IMG 8055 — ending cash trend with minimum liquidity floor as second series."""
    as_of = bundle.as_of_period
    year = int(as_of[:4])
    periods: list[str] = []
    cash_vals: list[float] = []
    for m in range(1, 13):
        p = f"{year:04d}-{m:02d}"
        if p > as_of and bundle.scenario != "Forecast":
            break
        v = float(_wf(bundle, "cash_flow", "ending_cash", p, "Actual") or _wf(bundle, "cash_flow", "ending_cash", p, "Forecast"))
        if v == 0 and p != as_of:
            continue
        periods.append(p[5:7] + "/" + p[2:4])
        cash_vals.append(v)
    if len(periods) < 2:
        end = float(_wf(bundle, "cash_flow", "ending_cash", as_of))
        if end == 0:
            return cash_operating_chart(bundle)
        periods = ["Prior", as_of[5:7]]
        cash_vals = [end * 0.9, end]
    floor = min(cash_vals) * 0.4 if cash_vals else 0.0
    covenant = [floor] * len(periods)
    return ChartSpec(
        chart_type="line",
        title="Cash vs Liquidity Floor",
        categories=periods,
        series={"Ending Cash": cash_vals, "Min Floor (proxy)": covenant},
        y_axis_label="USD",
    )


def cash_operating_chart(bundle: ReportingBundle) -> ChartSpec | None:
    as_of = bundle.as_of_period
    items = [
        ("beginning_cash", "Beginning"),
        ("cash_collections", "Collections"),
        ("collections", "Collections"),
        ("payroll_cash_out", "Payroll"),
        ("vendor_cash_out", "Vendor"),
        ("commission_cash_out", "Commissions"),
        ("capex", "Capex"),
        ("ending_cash", "Ending"),
    ]
    cats: list[str] = []
    vals: list[float] = []
    for wtype, label in items:
        if label in cats:
            continue
        v = float(_wf(bundle, "cash_flow", wtype, as_of))
        cats.append(label)
        vals.append(v)
    if len(cats) < 2:
        return None
    return _chart("Operating Cash Bridge", cats, {"Cash ($)": vals}, chart_type="waterfall", y_axis_label="Cash")


def cash_bridge_chart(bundle: ReportingBundle) -> ChartSpec | None:
    return cash_operating_chart(bundle)


def deferred_revenue_chart(bundle: ReportingBundle) -> ChartSpec | None:
    as_of = bundle.as_of_period
    cur = bundle.currency
    beg = float(_wf(bundle, "deferred_revenue", "beginning_deferred_revenue", as_of))
    bill = float(
        _wf(bundle, "deferred_revenue", "new_billings", as_of)
        or _wf(bundle, "deferred_revenue", "billings", as_of)
    )
    rec = float(_wf(bundle, "deferred_revenue", "revenue_recognized", as_of))
    end = float(_wf(bundle, "deferred_revenue", "ending_deferred_revenue", as_of))
    return _chart(
        f"Billings → Deferred ({cur})",
        ["Beginning", "Billings", "Recognized", "Ending"],
        {"Amount": [beg, bill, -abs(rec), end]},
    )


def revenue_story_chart(bundle: ReportingBundle) -> ChartSpec | None:
    as_of = bundle.as_of_period
    net_new = float(_wf(bundle, "arr", "new_arr", as_of) or _wf(bundle, "arr", "new_business", as_of))
    bill = float(
        _wf(bundle, "deferred_revenue", "new_billings", as_of)
        or _wf(bundle, "deferred_revenue", "billings", as_of)
    )
    rec = float(_wf(bundle, "deferred_revenue", "revenue_recognized", as_of))
    rev = float(_wf(bundle, "deferred_revenue", "total_gaap_revenue", as_of))
    if not any((net_new, bill, rec, rev)):
        fs = bundle.comparison_financial_statements or bundle.financial_statements
        if fs:
            for row in fs.income_statement.rows:
                if str(row.period)[:7] == as_of and row.scenario == "Actual" and "revenue" in row.line_item.lower():
                    rev = float(row.amount)
                    break
    cats = ["Net New ARR", "Billings", "Deferred Recognized", "GAAP Revenue"]
    vals = [net_new, bill, abs(rec), rev]
    if not any(vals):
        return None
    return _chart("ARR → Billings → GAAP Revenue", cats, {"Flow ($)": vals}, y_axis_label="USD")


def funnel_volume_chart(bundle: ReportingBundle) -> ChartSpec | None:
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
    counts = [float(mql), float(sql), float(sal), float(opp)]
    return _chart("Funnel Volume (counts only)", ["MQL", "SQL", "SAL", "Opps"], {"Count": counts}, y_axis_label="Count")


def funnel_closed_won_kpi(bundle: ReportingBundle) -> KpiCard | None:
    as_of = bundle.as_of_period
    won = abs(_wf(bundle, "pipeline", "closed_won", as_of))
    if not won:
        return None
    return _kpi("Closed Won ARR", fmt_money(won, bundle.currency), group="gtm", tone="favorable")


def gtm_dollar_chart(bundle: ReportingBundle) -> ChartSpec | None:
    as_of = bundle.as_of_period
    mkt = bundle.marketing_comparison
    if not mkt:
        return None
    spend = pipe = won = Decimal("0")
    for row in mkt.actual:
        if row.period != as_of:
            continue
        spend += row.marketing_spend
        pipe += row.pipeline_arr_created
        won += row.closed_won_arr
    if spend == 0 and pipe == 0:
        return None
    return _chart("GTM Dollars", ["Spend", "Pipeline Created", "Closed Won ARR"], {"USD": [float(spend), float(pipe), float(won)]})


def gtm_efficiency_chart(bundle: ReportingBundle) -> ChartSpec | None:
    as_of = bundle.as_of_period
    mkt = bundle.marketing_comparison
    if not mkt:
        return None
    spend = pipe = Decimal("0")
    for row in mkt.actual:
        if row.period != as_of:
            continue
        spend += row.marketing_spend
        pipe += row.pipeline_arr_created
    if spend == 0:
        return None
    ratio = float(pipe / spend)
    return _chart("GTM Efficiency", ["Pipeline / Spend"], {"Ratio": [ratio]}, y_axis_label="x")


def gtm_volume_chart(bundle: ReportingBundle) -> ChartSpec | None:
    as_of = bundle.as_of_period
    mkt = bundle.marketing_comparison
    if not mkt:
        return None
    mql = sql = opp = Decimal("0")
    for row in mkt.actual:
        if row.period != as_of:
            continue
        mql += row.mqls
        sql += row.sqls
        opp += row.opportunities_created
    if not any((mql, sql, opp)):
        return None
    return _chart("Funnel Volume", ["MQL", "SQL", "Opps Created"], {"Count": [float(mql), float(sql), float(opp)]}, y_axis_label="Count")


def gtm_spend_pipeline_chart(bundle: ReportingBundle) -> ChartSpec | None:
    return gtm_dollar_chart(bundle)


def channel_efficiency_table(bundle: ReportingBundle, *, max_rows: int = 8) -> TableSpec | None:
    as_of = bundle.as_of_period
    cur = bundle.currency
    if not bundle.marketing_comparison:
        return None
    rows_data: list[tuple[str, Decimal, Decimal, Decimal, float]] = []
    for row in bundle.marketing_comparison.actual:
        if row.period != as_of:
            continue
        ch = row.marketing_channel or "Unknown"
        spend = row.marketing_spend
        pipe = row.pipeline_arr_created
        won = row.closed_won_arr
        ratio = float(pipe / spend) if spend else 0.0
        rows_data.append((ch, spend, pipe, won, ratio))
    if not rows_data:
        return None
    rows_data.sort(key=lambda x: -x[4])
    rows = [
        [
            ch[:22],
            fmt_money(spend, cur),
            fmt_money(pipe, cur),
            fmt_money(won, cur),
            f"{ratio:.1f}x",
        ]
        for ch, spend, pipe, won, ratio in rows_data[:max_rows]
    ]
    return TableSpec(
        headers=["Channel", "Spend", "Pipeline", "Closed Won", "Pipe/Spend"],
        rows=rows,
    )


def headcount_bridge_chart(bundle: ReportingBundle) -> ChartSpec | None:
    """Department ending headcount when bridge fields are unavailable."""
    as_of = bundle.as_of_period
    by_dept: dict[str, float] = {}
    for r in bundle.headcount:
        if r.period != as_of or r.scenario != "Actual":
            continue
        dept = (r.department or "Other")[:14]
        by_dept[dept] = by_dept.get(dept, 0) + float(r.headcount or 0)
    if not by_dept:
        return None
    items = sorted(by_dept.items(), key=lambda x: -x[1])[:6]
    return _chart(
        "Headcount by Department",
        [d for d, _ in items],
        {"FTE": [v for _, v in items]},
        y_axis_label="FTE",
    )


def headcount_kpis(bundle: ReportingBundle) -> list[KpiCard]:
    as_of = bundle.as_of_period
    cur = bundle.currency
    hc = sum(int(r.headcount or 0) for r in bundle.headcount if r.period == as_of and r.scenario == "Actual")
    arr = _wf(bundle, "arr", "ending_arr", as_of) or _wf(bundle, "arr", "ending", as_of)
    rev = Decimal("0")
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if fs:
        for row in fs.income_statement.rows:
            if str(row.period)[:7] == as_of and row.scenario == "Actual" and "revenue" in row.line_item.lower():
                rev = row.amount
                break
    rpe = (rev / hc) if hc else None
    arppe = (arr / hc) if hc else None
    out = [_kpi("Ending HC", str(hc), group="efficiency")]
    if rpe:
        out.append(_kpi("Revenue / FTE", fmt_money(rpe, cur), group="efficiency"))
    if arppe:
        out.append(_kpi("ARR / FTE", fmt_money(arppe, cur), group="efficiency"))
    return out


def department_variance_table(bundle: ReportingBundle, *, max_rows: int = 8) -> TableSpec | None:
    from collections import defaultdict

    as_of = bundle.as_of_period
    cur = bundle.currency
    actual: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    budget: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in bundle.gl_detail:
        if row.period != as_of:
            continue
        dept = row.department or "Unassigned"
        if row.scenario == "Actual":
            actual[dept] += row.amount
        elif row.scenario == "Budget":
            budget[dept] += row.amount
    if not actual:
        return None
    rows_out: list[list[str]] = []
    for dept in sorted(actual.keys(), key=lambda d: -abs(actual[d] - budget.get(d, 0))):
        a, b = actual[dept], budget.get(dept, Decimal("0"))
        delta = a - b
        pct = f"{float(delta / b):.0%}" if b else "n/a"
        flag = "▲ risk" if delta > b and abs(delta) > Decimal("10000") else ("▼ favorable" if delta < 0 else "●")
        rows_out.append([dept[:20], fmt_money(a, cur), fmt_money(b, cur), fmt_money(delta, cur), pct, flag])
    if not rows_out:
        return None
    return TableSpec(
        headers=["Department", "Actual", "Budget", "Var $", "Var %", "Signal"],
        rows=rows_out[:max_rows],
    )


def opportunity_spotlights(bundle: ReportingBundle) -> list[KpiCard]:
    cur = bundle.currency
    spotlights: list[KpiCard] = []
    priority = ("closed_won", "slipped_pipeline", "pipeline_created", "closed_lost")
    labels = {
        "closed_won": "Closed Won Spotlight",
        "slipped_pipeline": "Deferred Spotlight",
        "pipeline_created": "Top New Pipeline",
        "closed_lost": "Closed Lost Spotlight",
    }
    for movement in priority:
        payload = bundle.pipeline_drilldown.get(movement) or {}
        opps = payload.get("opportunities") or []
        if not opps:
            continue
        def _impact(o):
            if isinstance(o, dict):
                return abs(Decimal(str(o.get("arr_impact") or 0)))
            return abs(Decimal(str(getattr(o, "arr_impact", 0) or 0)))

        top = max(opps, key=_impact)
        if isinstance(top, dict):
            name = (top.get("opportunity_name") or top.get("customer_name") or "Opportunity")[:28]
            arr = Decimal(str(top.get("arr_impact") or 0))
            owner = (top.get("owner") or "")[:12]
        else:
            name = (getattr(top, "opportunity_name", None) or getattr(top, "customer_name", None) or "Opportunity")[:28]
            arr = Decimal(str(getattr(top, "arr_impact", 0) or 0))
            owner = (getattr(top, "owner", None) or "")[:12]
        spotlights.append(
            _kpi(
                labels.get(movement, movement),
                fmt_money(arr, cur),
                subtext=f"{name} | {owner}",
                tone="favorable" if movement == "closed_won" else "watch",
                group="gtm",
            )
        )
        if len(spotlights) >= 3:
            break
    return spotlights


def executive_kpi_cards(bundle: ReportingBundle) -> list[KpiCard]:
    return executive_scorecard_kpis(bundle)
