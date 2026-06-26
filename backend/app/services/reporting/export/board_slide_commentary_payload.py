"""Build per-slide metric JSON for board deck Claude commentary (Layer 2 payload)."""

from __future__ import annotations

import calendar
from decimal import Decimal
from typing import Any

from app.services.reporting.export.board_chart_service import _wf
from app.services.reporting.export.board_metrics_snapshot import build_metrics_snapshot
from app.services.reporting.export.board_period_ytd import (
    rollup_cash,
    rollup_ebitda,
    rollup_ending_arr,
    rollup_revenue,
)
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.period_utils import to_period

BOARD_DECK_SLIDE_KEYS = frozenset(
    {
        "executive_summary",
        "arr_waterfall",
        "gaap_revenue",
        "cash_forecast",
        "gtm_performance",
        "headcount",
        "risks_opportunities",
    }
)

_SLIDE_SPECS: dict[str, dict[str, Any]] = {
    "executive_summary": {
        "slide_number": 2,
        "slide_title": "Executive Summary",
        "max_bullets": 5,
        "max_words_per_bullet": 25,
    },
    "arr_waterfall": {
        "slide_number": 3,
        "slide_title": "ARR Analysis",
        "max_bullets": 4,
        "max_words_per_bullet": 25,
    },
    "gaap_revenue": {
        "slide_number": 4,
        "slide_title": "P&L Review",
        "max_bullets": 5,
        "max_words_per_bullet": 25,
    },
    "cash_forecast": {
        "slide_number": 5,
        "slide_title": "Cash & Liquidity",
        "max_bullets": 4,
        "max_words_per_bullet": 25,
    },
    "gtm_performance": {
        "slide_number": 6,
        "slide_title": "GTM & Marketing",
        "max_bullets": 4,
        "max_words_per_bullet": 25,
    },
    "headcount": {
        "slide_number": 7,
        "slide_title": "Workforce & Headcount",
        "max_bullets": 4,
        "max_words_per_bullet": 25,
    },
    "risks_opportunities": {
        "slide_number": 8,
        "slide_title": "Risks & Opportunities",
        "max_bullets": 4,
        "max_words_per_bullet": 25,
    },
}


def fmt_deck_money(value: Decimal | None) -> str:
    if value is None:
        return "n/a"
    v = Decimal(value)
    sign = "-" if v < 0 else ""
    abs_v = abs(v)
    if abs_v >= Decimal("1000000"):
        return f"{sign}${abs_v / Decimal('1000000'):,.2f}M"
    if abs_v >= Decimal("1000"):
        return f"{sign}${abs_v / Decimal('1000'):,.1f}K"
    return f"{sign}${abs_v:,.2f}"


def fmt_deck_pct(ratio: Decimal | None, *, as_percent: bool = True) -> str:
    if ratio is None:
        return "n/a"
    val = float(ratio) * 100 if as_percent and ratio <= Decimal("1.5") else float(ratio)
    return f"{val:.1f}%"


def fmt_deck_var(actual: Decimal, budget: Decimal) -> str:
    if budget == 0 and actual == 0:
        return "n/a"
    delta = actual - budget
    sign = "+" if delta >= 0 else ""
    return f"{sign}{fmt_deck_money(delta)}"


def fmt_deck_var_pct(actual: Decimal, budget: Decimal) -> str:
    if budget == 0:
        return "n/a"
    pct = (actual - budget) / budget * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"


def _close_month_label(period: str) -> str:
    return calendar.month_name[int(period[5:7])]


def _ytd_label(period: str) -> str:
    month_abbr = calendar.month_abbr[int(period[5:7])]
    return f"Jan–{month_abbr} {period[:4]}"


def _is_line_amount(
    bundle: ReportingBundle,
    period: str,
    needle: str,
    scenario: str,
) -> Decimal:
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if not fs:
        return Decimal("0")
    n = needle.lower()
    for row in fs.income_statement.rows:
        if str(row.period)[:7] != period:
            continue
        if row.scenario != scenario:
            continue
        if n in row.line_item.lower():
            return row.amount
    return Decimal("0")


def _gross_margin_pct(bundle: ReportingBundle, period: str, scenario: str) -> Decimal | None:
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if not fs:
        return None
    gm = rev = Decimal("0")
    for row in fs.income_statement.rows:
        if str(row.period)[:7] != period or row.scenario != scenario:
            continue
        li = row.line_item.lower()
        if "gross margin" in li or li == "gm":
            gm = row.amount
        if "revenue" in li and "deferred" not in li:
            rev = row.amount
    if rev:
        return (gm / rev) * 100 if gm and gm <= rev else gm
    return gm if gm else None


def _headcount_totals(bundle: ReportingBundle, period: str, scenario: str) -> tuple[int, int]:
    hc = 0
    open_roles = 0
    for row in bundle.headcount:
        if row.period != period or row.scenario != scenario:
            continue
        hc += int(row.headcount or 0)
        open_roles += int(row.open_roles or 0)
    return hc, open_roles


def _arr_component(bundle: ReportingBundle, period: str, wtype: str, scenario: str = "Actual") -> Decimal:
    for key in (wtype, f"{wtype}_arr"):
        val = _wf(bundle, "arr", key, period, scenario)
        if val:
            return val
    return Decimal("0")


def _metrics_executive(bundle: ReportingBundle, m, as_of: str) -> dict[str, str]:
    arr = rollup_ending_arr(bundle)
    rev = rollup_revenue(bundle)
    ebitda = rollup_ebitda(bundle)
    cash = rollup_cash(bundle)
    gm_act = _gross_margin_pct(bundle, as_of, "Actual")
    gm_bud = _gross_margin_pct(bundle, as_of, "Budget")
    cash_bud = _wf(bundle, "cash_flow", "ending_cash", as_of, "Budget")
    ndr = m.nrr if m.nrr is not None else None
    if ndr is None and m.grr is not None:
        ndr = m.grr
    return {
        "revenue_actual": fmt_deck_money(m.revenue_actual),
        "revenue_budget": fmt_deck_money(m.revenue_budget),
        "revenue_var_pct": fmt_deck_var_pct(m.revenue_actual, m.revenue_budget),
        "arr_ending_actual": fmt_deck_money(arr.current_month),
        "arr_ending_budget": fmt_deck_money(arr.budget_cm),
        "arr_var_dollar": fmt_deck_var(arr.current_month, arr.budget_cm),
        "net_new_arr_actual": fmt_deck_money(m.net_new_arr),
        "net_new_arr_budget": fmt_deck_money(m.new_arr_budget),
        "gross_margin_actual": fmt_deck_pct(gm_act, as_percent=False) if gm_act is not None else "n/a",
        "gross_margin_budget": fmt_deck_pct(gm_bud, as_percent=False) if gm_bud is not None else "n/a",
        "ebitda_actual": fmt_deck_money(m.ebitda_actual),
        "ebitda_budget": fmt_deck_money(m.ebitda_budget),
        "cash_actual": fmt_deck_money(cash.current_month),
        "cash_budget": fmt_deck_money(cash_bud or cash.budget_cm),
        "n_dollar_r_actual": fmt_deck_pct(ndr) if ndr is not None else "n/a",
        "n_dollar_r_budget": "n/a",
        "ytd_revenue_actual": fmt_deck_money(rev.ytd),
        "ytd_revenue_budget": fmt_deck_money(rev.budget_ytd),
    }


def _metrics_arr(bundle: ReportingBundle, m, as_of: str) -> dict[str, str]:
    arr = rollup_ending_arr(bundle)
    nb_a = _arr_component(bundle, as_of, "new_business", "Actual")
    nb_b = _arr_component(bundle, as_of, "new_business", "Budget")
    exp_a = _arr_component(bundle, as_of, "expansion", "Actual")
    exp_b = _arr_component(bundle, as_of, "expansion", "Budget")
    churn_a = abs(_arr_component(bundle, as_of, "churn", "Actual"))
    churn_b = abs(_arr_component(bundle, as_of, "churn", "Budget"))
    gdr = m.grr
    pipeline_end = _wf(bundle, "pipeline", "ending_pipeline", as_of, "Actual")
    pipeline_cov = "n/a"
    if m.pipeline_created and m.closed_won:
        pipeline_cov = f"{float(m.pipeline_created / max(m.closed_won, Decimal('1'))):.1f}x"
    return {
        "arr_ending_actual": fmt_deck_money(arr.current_month),
        "arr_ending_budget": fmt_deck_money(arr.budget_cm),
        "net_new_arr_actual": fmt_deck_money(m.net_new_arr),
        "net_new_arr_budget": fmt_deck_money(m.new_arr_budget),
        "new_business_actual": fmt_deck_money(nb_a),
        "new_business_budget": fmt_deck_money(nb_b),
        "expansion_actual": fmt_deck_money(exp_a),
        "expansion_budget": fmt_deck_money(exp_b),
        "churn_actual": fmt_deck_money(churn_a),
        "churn_budget": fmt_deck_money(churn_b),
        "n_dollar_r_actual": fmt_deck_pct(m.nrr) if m.nrr is not None else "n/a",
        "g_dollar_r_actual": fmt_deck_pct(gdr) if gdr is not None else "n/a",
        "pipeline_coverage": pipeline_cov,
        "pipeline_ending": fmt_deck_money(pipeline_end),
        "fy_arr_forecast": fmt_deck_money(arr.fy_outlook),
        "fy_arr_budget": fmt_deck_money(arr.budget_fy),
    }


def _metrics_pl(bundle: ReportingBundle, m, as_of: str) -> dict[str, str]:
    rev = rollup_revenue(bundle)
    gm_act = _gross_margin_pct(bundle, as_of, "Actual")
    gm_bud = _gross_margin_pct(bundle, as_of, "Budget")
    sm_a = _is_line_amount(bundle, as_of, "sales and marketing", "Actual") or _is_line_amount(
        bundle, as_of, "sm", "Actual"
    )
    sm_b = _is_line_amount(bundle, as_of, "sales and marketing", "Budget") or _is_line_amount(
        bundle, as_of, "sm", "Budget"
    )
    rd_a = _is_line_amount(bundle, as_of, "research", "Actual") or _is_line_amount(
        bundle, as_of, "rd", "Actual"
    )
    rd_b = _is_line_amount(bundle, as_of, "research", "Budget") or _is_line_amount(
        bundle, as_of, "rd", "Budget"
    )
    return {
        "revenue_actual": fmt_deck_money(m.revenue_actual),
        "revenue_budget": fmt_deck_money(m.revenue_budget),
        "gross_margin_actual": fmt_deck_pct(gm_act, as_percent=False) if gm_act is not None else "n/a",
        "gross_margin_budget": fmt_deck_pct(gm_bud, as_percent=False) if gm_bud is not None else "n/a",
        "ebitda_actual": fmt_deck_money(m.ebitda_actual),
        "ebitda_budget": fmt_deck_money(m.ebitda_budget),
        "sm_actual": fmt_deck_money(sm_a),
        "sm_budget": fmt_deck_money(sm_b),
        "rd_actual": fmt_deck_money(rd_a),
        "rd_budget": fmt_deck_money(rd_b),
        "ytd_revenue_actual": fmt_deck_money(rev.ytd),
        "ytd_revenue_budget": fmt_deck_money(rev.budget_ytd),
        "known_one_time_items": "n/a",
    }


def _metrics_cash(bundle: ReportingBundle, m, as_of: str) -> dict[str, str]:
    cash = rollup_cash(bundle)
    cash_bud = _wf(bundle, "cash_flow", "ending_cash", as_of, "Budget")
    collections = _wf(bundle, "cash_flow", "collections", as_of, "Actual") or _wf(
        bundle, "cash_flow", "cash_collections", as_of, "Actual"
    )
    cfo_a = _wf(bundle, "cash_flow", "cfo", as_of, "Actual")
    cfo_b = _wf(bundle, "cash_flow", "cfo", as_of, "Budget")
    floor = Decimal("10000000")
    headroom = cash.current_month - floor
    return {
        "cash_actual": fmt_deck_money(cash.current_month),
        "cash_budget": fmt_deck_money(cash_bud or cash.budget_cm),
        "collections_actual": fmt_deck_money(collections),
        "cfo_actual": fmt_deck_money(cfo_a),
        "cfo_budget": fmt_deck_money(cfo_b),
        "cash_floor": fmt_deck_money(floor),
        "cash_headroom": fmt_deck_money(headroom),
        "h2_cash_forecast": fmt_deck_money(cash.fy_outlook),
    }


def _metrics_gtm(bundle: ReportingBundle, m, as_of: str) -> dict[str, str]:
    spend = m.marketing_spend
    pipeline = m.pipeline_from_marketing or m.pipeline_created
    blended = f"{float(pipeline / spend):.1f}x" if spend else "n/a"
    pipe_end = _wf(bundle, "pipeline", "ending_pipeline", as_of, "Actual")
    return {
        "marketing_spend_actual": fmt_deck_money(spend),
        "marketing_spend_budget": "n/a",
        "pipeline_created_actual": fmt_deck_money(m.pipeline_created),
        "pipeline_ending": fmt_deck_money(pipe_end),
        "pipeline_coverage": blended,
        "blended_efficiency": blended,
        "closed_won_arr_actual": fmt_deck_money(m.closed_won_arr_mkt or m.closed_won),
        "sm_actual": fmt_deck_money(_is_line_amount(bundle, as_of, "sales and marketing", "Actual")),
        "sm_budget": fmt_deck_money(_is_line_amount(bundle, as_of, "sales and marketing", "Budget")),
        "mql_actual": str(int(m.mql)),
        "sql_actual": str(int(m.sql)),
    }


def _metrics_headcount(bundle: ReportingBundle, m, as_of: str) -> dict[str, str]:
    hc_a, open_a = _headcount_totals(bundle, as_of, "Actual")
    hc_b, _ = _headcount_totals(bundle, as_of, "Budget")
    arr = rollup_ending_arr(bundle)
    arr_per_emp = (arr.current_month / hc_a) if hc_a else None
    jan = f"{as_of[:4]}-01"
    hc_jan, _ = _headcount_totals(bundle, jan, "Actual")
    arr_jan = _wf(bundle, "arr", "ending_arr", jan, "Actual") or _wf(
        bundle, "arr", "ending", jan, "Actual"
    )
    hc_growth = "n/a"
    arr_growth = "n/a"
    if hc_jan and hc_a:
        hc_growth = fmt_deck_var_pct(Decimal(hc_a), Decimal(hc_jan))
    if arr_jan and arr.current_month:
        arr_growth = fmt_deck_var_pct(arr.current_month, arr_jan)
    return {
        "total_hc_actual": str(hc_a or m.headcount),
        "total_hc_budget": str(hc_b),
        "hc_var": fmt_deck_var(Decimal(hc_a), Decimal(hc_b)),
        "arr_per_employee": fmt_deck_money(arr_per_emp) if arr_per_emp else "n/a",
        "hc_vs_arr_growth": f"ARR {arr_growth}; HC {hc_growth}",
        "open_reqs": str(open_a),
        "quota_attainment": "n/a",
    }


def _metrics_risks(bundle: ReportingBundle, m, as_of: str) -> dict[str, str]:
    gaps = "; ".join(g.message for g in bundle.data_gaps if g.status != "ok")[:400]
    return {
        "validation_status": bundle.validation.status,
        "failed_checks": str(bundle.validation.failed_count),
        "churn_actual": fmt_deck_money(m.churn),
        "expansion_actual": fmt_deck_money(m.expansion),
        "deferred_pipeline": fmt_deck_money(m.slipped),
        "pipeline_created": fmt_deck_money(m.pipeline_created),
        "cash_actual": fmt_deck_money(m.cash_actual),
        "data_gaps": gaps or "none",
    }


_METRIC_BUILDERS = {
    "executive_summary": _metrics_executive,
    "arr_waterfall": _metrics_arr,
    "gaap_revenue": _metrics_pl,
    "cash_forecast": _metrics_cash,
    "gtm_performance": _metrics_gtm,
    "headcount": _metrics_headcount,
    "risks_opportunities": _metrics_risks,
}


def build_single_slide_payload(bundle: ReportingBundle, slide_key: str) -> dict[str, Any]:
    """Dynamic Layer 2 payload for one board slide."""
    if slide_key not in _SLIDE_SPECS:
        raise KeyError(f"Unknown board deck slide key: {slide_key}")

    as_of = to_period(bundle.as_of_period)
    m = build_metrics_snapshot(bundle)
    spec = dict(_SLIDE_SPECS[slide_key])
    builder = _METRIC_BUILDERS[slide_key]
    metrics = builder(bundle, m, as_of)

    return {
        "close_period": as_of,
        "close_period_label": _close_month_label(as_of),
        "ytd_label": _ytd_label(as_of),
        "organization": bundle.organization_name or "SMPL.ai",
        "currency": bundle.currency,
        "slide": {
            **spec,
            "metrics": metrics,
        },
    }


def slide_prompt_limits(slide_key: str) -> tuple[int, int]:
    spec = _SLIDE_SPECS[slide_key]
    return int(spec["max_bullets"]), int(spec["max_words_per_bullet"])
