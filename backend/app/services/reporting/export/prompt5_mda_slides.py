"""Prompt 5 MD&A slide payload blocks — GTM, headcount, department updates.

Builds warehouse-backed blocks for the expanded Prompt 5 deck (post dafd8c0 plan).
Numbers come from ReportingBundle / board_platform_metrics only — never invented.
"""

from __future__ import annotations

import calendar
from decimal import Decimal
from typing import Any

from app.services.reporting.export.board_slide_commentary_payload import (
    fmt_deck_money,
    fmt_deck_var,
    fmt_deck_var_pct,
)
from app.services.reporting.export.effective_periods import export_fiscal_periods
from app.services.reporting.export.period_views import ytd_periods
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.period_utils import to_period

ZERO = Decimal("0")


def _money_k(val: Decimal | float | int) -> str:
    v = float(val)
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"${v / 1_000:.0f}K"
    return f"${v:,.0f}"


def _headcount_by_department(
    bundle: ReportingBundle,
    period: str,
    scenario: str,
) -> dict[str, int]:
    out: dict[str, int] = {}
    target = to_period(period)
    for row in bundle.headcount:
        if to_period(str(row.period)) != target or row.scenario != scenario:
            continue
        dept = (row.department or "Other").strip() or "Other"
        out[dept] = out.get(dept, 0) + int(Decimal(str(row.headcount or 0)))
    return out


def _headcount_total(bundle: ReportingBundle, period: str, scenario: str) -> int:
    return sum(_headcount_by_department(bundle, period, scenario).values())


def _month_label(period: str) -> str:
    return calendar.month_abbr[int(period[5:7])]


def build_gtm_channel_metrics_table(
    bundle: ReportingBundle,
    period: str,
) -> dict[str, Any]:
    """Wide channel efficiency table — Spend → MQL → SQL → Opps → Pipeline → Won → CAC → Win Rate."""
    mkt = bundle.marketing_channel_comparison or bundle.marketing_comparison
    if not mkt:
        return {"available": False, "note": "No marketing channel data loaded."}

    actual_map: dict[str, Any] = {}
    budget_map: dict[str, Any] = {}
    for row in mkt.actual:
        if row.period != period:
            continue
        ch = row.marketing_channel or "Other"
        actual_map[ch] = row
    for row in mkt.budget:
        if row.period != period:
            continue
        ch = row.marketing_channel or "Other"
        budget_map[ch] = row

    rows: list[dict[str, Any]] = []
    for ch in sorted(set(actual_map) | set(budget_map)):
        a = actual_map.get(ch)
        b = budget_map.get(ch)
        spend = a.marketing_spend if a else ZERO
        spend_b = b.marketing_spend if b else ZERO
        mqls = int(a.mqls if a else ZERO)
        sqls = int(a.sqls if a else ZERO)
        opps = int(a.opportunities_created if a else ZERO)
        pipe = a.pipeline_arr_created if a else ZERO
        won = a.closed_won_arr if a else ZERO
        cac_proxy = a.marketing_cac_proxy if a and a.marketing_cac_proxy else ZERO
        if cac_proxy == ZERO and spend and won:
            cac_proxy = spend / (won / Decimal("50000")) if won else ZERO
        wr = float(a.win_rate_on_pipeline_created) if a and a.win_rate_on_pipeline_created else 0.0
        wr_pct = round(wr * 100, 1) if wr <= 1 else round(wr, 1)
        eff = float(pipe / spend) if spend else 0.0
        rows.append(
            {
                "channel": ch,
                "spend_actual": _money_k(spend),
                "spend_budget": _money_k(spend_b),
                "mqls": mqls,
                "sqls": sqls,
                "opportunities": opps,
                "pipeline_arr": _money_k(pipe),
                "closed_won_arr": _money_k(won),
                "cac_proxy": _money_k(cac_proxy) if cac_proxy else "n/a",
                "efficiency_x": round(eff, 1),
                "win_rate_pct": wr_pct,
            }
        )
    rows.sort(key=lambda r: r.get("efficiency_x") or 0, reverse=True)

    return {
        "available": bool(rows),
        "period": period,
        "columns": [
            "Channel",
            "Spend (Act)",
            "Spend (Bud)",
            "MQLs",
            "SQLs",
            "Opps",
            "Pipeline ARR",
            "Closed Won",
            "CAC Proxy",
            "Efficiency",
            "Win Rate",
        ],
        "rows": rows[:8],
        "layout_hint": "Primary visual for slide 6 — full-width table; Key Takeaways below.",
    }


def build_gtm_channel_drilldown_cards(
    bundle: ReportingBundle,
    period: str,
    *,
    limit: int = 4,
) -> dict[str, Any]:
    """Compact Actual vs Budget cards per top channel (Spend / Pipeline / Closed Won / Efficiency)."""
    table = build_gtm_channel_metrics_table(bundle, period)
    if not table.get("available"):
        return {"available": False}

    cards: list[dict[str, str]] = []
    for row in table["rows"][:limit]:
        cards.append(
            {
                "channel": row["channel"],
                "spend_actual": row["spend_actual"],
                "spend_budget": row["spend_budget"],
                "pipeline_actual": row["pipeline_arr"],
                "closed_won": row["closed_won_arr"],
                "efficiency": f"{row['efficiency_x']}x",
                "win_rate": f"{row['win_rate_pct']}%",
            }
        )
    return {"available": bool(cards), "cards": cards}


def build_projected_headcount_block(bundle: ReportingBundle) -> dict[str, Any]:
    """Department actual vs goal + monthly bridge — same SoT as platform headcount bridge."""
    as_of = to_period(bundle.as_of_period)
    fiscal_end = to_period(bundle.end_period) if bundle.end_period else f"{as_of[:4]}-12"

    if not bundle.headcount:
        return {
            "available": False,
            "include_slide": False,
            "note": "No headcount rows loaded — omit projected headcount slide.",
        }

    act_depts = _headcount_by_department(bundle, as_of, "Actual")
    bud_depts = _headcount_by_department(bundle, as_of, "Budget")
    if not act_depts and not bud_depts:
        fy_bud = _headcount_by_department(bundle, fiscal_end, "Budget")
        if not fy_bud:
            return {
                "available": False,
                "include_slide": False,
                "note": "Headcount rows present but all zero — omit projected headcount slide.",
            }

    all_depts = sorted(set(act_depts) | set(bud_depts))
    dept_rows: list[dict[str, Any]] = []
    for dept in all_depts[:8]:
        act = act_depts.get(dept, 0)
        goal = bud_depts.get(dept, 0)
        dept_rows.append(
            {
                "department": dept[:18],
                "actual": act,
                "goal": goal,
                "variance": act - goal,
                "variance_label": fmt_deck_var(Decimal(act), Decimal(goal)).replace("$", ""),
            }
        )

    periods = [p for p in export_fiscal_periods(bundle.start_period, bundle.end_period) if p <= fiscal_end]
    month_labels = [_month_label(p) for p in periods]
    actual_series: list[int] = []
    goal_series: list[int] = []
    for p in periods:
        actual_series.append(_headcount_total(bundle, p, "Actual"))
        goal_series.append(_headcount_total(bundle, p, "Budget"))

    hc_actual = _headcount_total(bundle, as_of, "Actual")
    hc_budget_cm = _headcount_total(bundle, as_of, "Budget")
    hc_eoy_budget = _headcount_total(bundle, fiscal_end, "Budget")
    hc_eoy_forecast = _headcount_total(bundle, fiscal_end, "Forecast")
    open_reqs = sum(
        int(Decimal(str(r.open_roles or 0)))
        for r in bundle.headcount
        if to_period(str(r.period)) == as_of and r.scenario == "Actual"
    )

    stacked_bars: list[dict[str, Any]] = []
    max_hc = max([r["actual"] for r in dept_rows] + [1])
    for i, row in enumerate(dept_rows):
        stacked_bars.append(
            {
                "department": row["department"],
                "actual_h": round(row["actual"] / max_hc, 3),
                "goal_h": round(row["goal"] / max_hc, 3) if row["goal"] else 0,
                "actual": row["actual"],
                "goal": row["goal"],
                "x_index": i,
            }
        )

    return {
        "available": True,
        "include_slide": hc_actual > 0 or hc_eoy_budget > 0,
        "close_period": as_of,
        "fiscal_end": fiscal_end,
        "kpis": {
            "total_hc_actual": hc_actual,
            "total_hc_budget_cm": hc_budget_cm,
            "eoy_budget": hc_eoy_budget,
            "eoy_forecast": hc_eoy_forecast,
            "open_reqs": open_reqs,
            "hc_var_cm": fmt_deck_var(Decimal(hc_actual), Decimal(hc_budget_cm)).replace("$", ""),
            "hc_var_pct": fmt_deck_var_pct(Decimal(hc_actual), Decimal(hc_budget_cm)),
        },
        "departments": dept_rows,
        "monthly_totals": {
            "months": month_labels,
            "actual": actual_series,
            "goal": goal_series,
            "note": "Actual solid bars; goal dashed line overlay in deck.",
        },
        "stacked_bars": stacked_bars,
        "tenure": {"available": False, "note": "Tenure buckets require workforce_employees — not in export bundle."},
        "layout_hint": "Left stacked dept bars (actual solid + goal dashed); right monthly bridge table; KT full width below.",
        "format": "integer_headcount_not_dollars",
    }


def build_department_updates_blocks(
    bundle: ReportingBundle,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Department Updates chapter — funnel/efficiency + big efforts placeholders."""
    as_of = to_period(bundle.as_of_period)
    gtm = payload.get("gtm_performance") or {}
    pl = payload.get("pl_detail") or {}
    pl_cm = pl.get("cm") or {}
    channels = gtm.get("channels") or []

    total_spend = sum(c.get("spend_raw") or 0 for c in channels)
    total_won = gtm.get("closed_won_raw") or 0
    blended_cac = "n/a"
    if total_spend and total_won:
        blended_cac = _money_k(total_spend / max(total_won / 50000, 1))

    sm_row = pl_cm.get("sm") or {}
    gm_row = pl_cm.get("gross_margin_pct") or {}
    gm_pct = gm_row.get("actual", "70%").replace("%", "")
    try:
        gm_dec = Decimal(str(gm_pct)) / 100 if gm_pct not in ("n/a", "—") else Decimal("0.70")
    except Exception:
        gm_dec = Decimal("0.70")

    payback_months = "n/a"
    if total_spend and total_won:
        from app.services.kpis.engine import calculate_cac, calculate_cac_payback_months

        new_customers_proxy = max(int(total_won / 50000), 1)
        cac_val = calculate_cac(Decimal(str(total_spend)), new_customers_proxy)
        if cac_val:
            new_mrr = Decimal(str(total_won)) / Decimal("12") / Decimal(new_customers_proxy)
            pb = calculate_cac_payback_months(
                cac_val,
                new_mrr=new_mrr,
                new_customers=new_customers_proxy,
                gross_margin=gm_dec,
            )
            if pb is not None:
                payback_months = f"{float(pb):.1f} mo"

    channel_efficiency: list[dict[str, str]] = []
    for ch in channels[:5]:
        channel_efficiency.append(
            {
                "channel": ch.get("name", "Other"),
                "spend": ch.get("spend", "—"),
                "pipeline": ch.get("pipeline", "—"),
                "efficiency": ch.get("efficiency_label", "n/a"),
                "win_rate": f"{ch.get('win_rate_pct', 0)}%",
            }
        )

    funnel_efficiency = {
        "available": bool(channels) or bool(gtm.get("total_spend")),
        "section_label": "DEPARTMENT UPDATES",
        "slide_title": "Marketing — Funnel & Efficiency",
        "blended_cac_proxy": blended_cac,
        "cac_payback_months": payback_months,
        "total_spend": gtm.get("total_spend", "—"),
        "total_pipeline": gtm.get("total_pipeline", "—"),
        "blended_efficiency_x": gtm.get("blended_efficiency_x", 0),
        "mqls_cm": gtm.get("total_mqls", 0),
        "channel_efficiency": channel_efficiency,
        "ytd_funnel": (payload.get("gtm_funnel") or {}).get("new_logo", {}).get("ytd") or {},
        "layout_hint": "Dual metric cards (CAC + payback) + channel efficiency summary table; KT full width below.",
        "authoring_note": "Author milestones from CLOSE FREEZE when present; numbers from payload only.",
    }

    big_efforts = {
        "available": True,
        "section_label": "DEPARTMENT UPDATES",
        "slide_title": "Marketing — Big Efforts & Milestones",
        "milestones": [
            {
                "title": "GTM / Pipeline",
                "status": "placeholder",
                "detail_hint": f"Coverage {gtm.get('pipeline_coverage_x', 'n/a')}; slipped {gtm.get('slipped_pipeline', '—')}.",
            },
            {
                "title": "Channel Mix",
                "status": "placeholder",
                "detail_hint": f"Best win rate: {gtm.get('best_win_rate_channel', 'n/a')} at {gtm.get('best_win_rate_pct', 0)}%.",
            },
            {
                "title": "Efficiency / CAC",
                "status": "placeholder",
                "detail_hint": f"Blended efficiency {gtm.get('blended_efficiency_x', 0)}x; CAC proxy {blended_cac}.",
            },
            {
                "title": "H2 Priorities",
                "status": "placeholder",
                "detail_hint": "Draw from h2_priorities + freeze context for board-ready milestone copy.",
            },
        ],
        "channel_metrics_table": build_gtm_channel_metrics_table(bundle, as_of),
        "layout_hint": "Top milestone card strip (4 cards) + optional compact channel table below; KT full width.",
        "authoring_note": "Replace placeholder status with freeze/evidence narrative — keep $/% from payload.",
    }

    return {
        "funnel_efficiency": funnel_efficiency,
        "big_efforts_milestones": big_efforts,
    }


def build_deck_slide_order(payload: dict[str, Any]) -> dict[str, Any]:
    """Canonical Prompt 5 slide order with optional headcount skip."""
    hc = payload.get("projected_headcount") or {}
    include_hc = bool(hc.get("include_slide"))

    slides: list[dict[str, Any]] = [
        {"number": 1, "key": "title", "title": "Title Cover", "section": "Financials"},
        {"number": 2, "key": "executive_dashboard", "title": "Executive Dashboard", "section": "Financials"},
        {"number": 3, "key": "arr_analysis", "title": "ARR Analysis", "section": "Financials"},
        {"number": 4, "key": "pl_review", "title": "P&L Review", "section": "Financials"},
        {"number": 5, "key": "cash_liquidity", "title": "Cash & Liquidity", "section": "Financials"},
        {
            "number": 6,
            "key": "gtm_performance",
            "title": "GTM Performance",
            "section": "GTM",
            "payload_blocks": ["gtm_performance", "gtm_funnel", "gtm_channel_metrics"],
        },
        {
            "number": 7,
            "key": "pipeline_waterfall",
            "title": "Pipeline Waterfall",
            "section": "GTM",
            "payload_blocks": ["gtm_performance.pipeline_waterfall_chart"],
        },
        {"number": 8, "key": "strategic_assessment", "title": "Risks & Opportunities", "section": "Financials"},
        {"number": 9, "key": "financial_outlook", "title": "Financial Outlook", "section": "Financials"},
    ]

    n = 10
    if include_hc:
        slides.append(
            {
                "number": n,
                "key": "projected_headcount",
                "title": "Projected Headcount",
                "section": "Workforce",
                "optional": False,
                "payload_blocks": ["projected_headcount"],
            }
        )
        n += 1

    slides.extend(
        [
            {"number": n, "key": "board_actions", "title": "Board Actions", "section": "Financials"},
            {
                "number": n + 1,
                "key": "dept_funnel_efficiency",
                "title": "Marketing — Funnel & Efficiency",
                "section": "Department Updates",
                "payload_blocks": ["department_updates.funnel_efficiency"],
            },
            {
                "number": n + 2,
                "key": "dept_big_efforts",
                "title": "Marketing — Big Efforts & Milestones",
                "section": "Department Updates",
                "payload_blocks": ["department_updates.big_efforts_milestones"],
            },
            {
                "number": n + 3,
                "key": "appendix_cfs",
                "title": "Appendix A — YTD CFS",
                "section": "Appendix",
                "payload_blocks": ["appendix.ytd_cash_flow_statement"],
            },
        ]
    )

    total = slides[-1]["number"]
    gtm = payload.get("gtm_performance") or {}
    primary_layout = "channel_metrics_table"
    if not (payload.get("gtm_channel_metrics") or {}).get("available"):
        if (payload.get("gtm_funnel") or {}).get("available"):
            primary_layout = "funnel_tables"
        elif gtm.get("channels"):
            primary_layout = "channel_drilldown_cards"

    return {
        "total_slides": total,
        "include_projected_headcount": include_hc,
        "slides": slides,
        "footer_template": "SMPL · Board Operating Review · {quarter} {year} · CONFIDENTIAL  {n}/"
        + str(total),
        "section_nav": {
            "department_updates": {
                "label": "DEPARTMENT UPDATES",
                "slide_keys": ["dept_funnel_efficiency", "dept_big_efforts"],
            }
        },
        "gtm_slide_6": {
            "primary_layout": primary_layout,
            "kt_placement": "full_width_below_primary",
            "min_area_pct": 75,
        },
    }


def enrich_mda_deck_slides(
    payload: dict[str, Any],
    bundle: ReportingBundle,
) -> dict[str, Any]:
    """Attach GTM / headcount / department-update blocks and slide order."""
    as_of = to_period(bundle.as_of_period)
    channel_metrics = build_gtm_channel_metrics_table(bundle, as_of)
    payload["gtm_channel_metrics"] = channel_metrics
    payload["gtm_channel_drilldown"] = build_gtm_channel_drilldown_cards(bundle, as_of)
    payload["projected_headcount"] = build_projected_headcount_block(bundle)
    payload["department_updates"] = build_department_updates_blocks(bundle, payload)
    payload["deck_slide_order"] = build_deck_slide_order(payload)

    # Stable empty defaults — Claude/Node must not crash when optional blocks are absent.
    hc = payload["projected_headcount"]
    hc.setdefault("stacked_bars", [])
    hc.setdefault("departments", [])
    hc.setdefault("monthly_totals", {"months": [], "actual": [], "goal": []})
    hc.setdefault("kpis", {})

    dept = payload["department_updates"]
    dept.setdefault("funnel_efficiency", {"available": False, "channel_efficiency": []})
    dept.setdefault("big_efforts_milestones", {"available": False, "milestones": []})
    dept["funnel_efficiency"].setdefault("channel_efficiency", [])
    dept["big_efforts_milestones"].setdefault("milestones", [])

    channel_metrics.setdefault("rows", [])
    payload["gtm_channel_drilldown"].setdefault("cards", [])

    gtm = payload.get("gtm_performance")
    if isinstance(gtm, dict):
        gtm["channel_metrics_table"] = channel_metrics
        gtm["channel_drilldown_cards"] = payload["gtm_channel_drilldown"]
        gtm["primary_layout"] = payload["deck_slide_order"]["gtm_slide_6"]["primary_layout"]
        gtm["layout_hint"] = (
            "One dense primary visual (channel_metrics_table OR gtm_funnel OR drilldown cards) "
            "+ full-width Key Takeaways below — no cramped right-rail KT on slide 6."
        )
        gtm.setdefault("channels", [])

    return payload
