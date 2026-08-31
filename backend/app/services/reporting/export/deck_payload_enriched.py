"""Enriched Prompt 5 deck payload — full analyst-grade context for one-shot deck generation.

Merges board slide metrics, monthly trends, P&L GL detail, GTM funnel, and deal
highlights so Claude has parity with SMPL_API_Prompts BoardDeck MDA V3 template.
"""

from __future__ import annotations

import calendar
from decimal import Decimal
from typing import Any

from app.services.reporting.export.board_chart_service import _wf
from app.services.reporting.export.is_line_resolver import ending_cash_at, fs_by_period
from app.services.reporting.export.board_metrics_snapshot import build_metrics_snapshot
from app.services.reporting.export.board_period_ytd import _outlook_series
from app.services.reporting.export.board_period_ytd import (
    monthly_ending_arr_series,
    monthly_flow_series,
)
from app.services.reporting.export.board_slide_commentary_payload import (
    _METRIC_BUILDERS,
    _SLIDE_SPECS,
    fmt_deck_money,
    fmt_deck_pct,
    fmt_deck_var,
    fmt_deck_var_pct,
)
from app.services.reporting.export.effective_periods import export_fiscal_periods
from app.services.reporting.export.period_views import qtd_periods, ytd_periods
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.period_utils import prior_period, to_period

ZERO = Decimal("0")


def _to_m(val: float | Decimal) -> float:
    return round(float(val) / 1_000_000, 3)


def _opp_amount(opp: dict[str, Any]) -> Decimal:
    for key in ("arr_impact", "amount", "pipeline_arr", "arr"):
        raw = opp.get(key)
        if raw not in (None, "", 0):
            return Decimal(str(raw))
    return ZERO


def _opp_name(opp: dict[str, Any]) -> str:
    return str(
        opp.get("account_name")
        or opp.get("name")
        or opp.get("opportunity_name")
        or "Opportunity"
    )[:80]


def _fs_amount(bundle: ReportingBundle, periods: list[str], scenario: str, needle: str) -> Decimal:
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if not fs:
        return ZERO
    wanted = {to_period(p) for p in periods}
    n = needle.lower()
    total = ZERO
    for row in fs.income_statement.rows:
        p = to_period(str(row.period)[:7])
        if p not in wanted or row.scenario != scenario:
            continue
        li = row.line_item.lower()
        if n in li and "deferred" not in li:
            if n == "revenue" and "cost" in li:
                continue
            total += row.amount
    return total


def _ts_line(
    ts_data: dict[str, Any] | None,
    period: str,
    scenario: str,
    key: str,
) -> Decimal | None:
    if not ts_data:
        return None
    block = ((ts_data.get(scenario) or {}).get("is") or {}).get(period) or {}
    val = block.get(key)
    if val in (None, ""):
        return None
    return Decimal(str(val))


def build_mom_block(bundle: ReportingBundle) -> dict[str, str]:
    """Month-over-month context for executive commentary."""
    as_of = bundle.as_of_period
    prior = prior_period(as_of)
    m = build_metrics_snapshot(bundle)
    rev_prior = _fs_amount(bundle, [prior], "Actual", "revenue")
    rev_act = m.revenue_actual
    arr_prior = _wf(bundle, "arr", "ending", prior, "Actual") or _wf(
        bundle, "arr", "ending_arr", prior, "Actual"
    )
    arr_act = m.ending_arr
    cash_prior = ending_cash_at(bundle, prior, "Actual")
    cash_act = ending_cash_at(bundle, as_of, "Actual")

    def pct(cur: Decimal, prev: Decimal) -> str:
        if not prev:
            return "n/a"
        return f"{float((cur - prev) / prev * 100):+.1f}%"

    return {
        "prior_period": prior,
        "prior_period_label": f"{calendar.month_name[int(prior[5:7])]} {prior[:4]}",
        "revenue_mom_pct": pct(rev_act, rev_prior),
        "arr_mom_pct": pct(arr_act, arr_prior),
        "cash_mom_pct": pct(cash_act, cash_prior),
        "revenue_prior": fmt_deck_money(rev_prior),
        "arr_prior": fmt_deck_money(arr_prior),
        "cash_prior": fmt_deck_money(cash_prior),
    }


def _money_k(val: float | Decimal) -> str:
    v = float(val)
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"${v / 1_000:.0f}K"
    return f"${v:,.0f}"


def build_monthly_trends_block(
    bundle: ReportingBundle,
    ts_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Jan–Dec series for FY outlook chart on slide 9."""
    labels, act_arr, out_arr, bud_arr = monthly_ending_arr_series(bundle)
    periods = export_fiscal_periods(bundle.start_period, bundle.end_period)
    as_of = to_period(bundle.as_of_period)

    rev_actual = fs_by_period(bundle, "revenue", "Actual")
    rev_forecast = fs_by_period(bundle, "revenue", "Forecast")
    rev_budget = fs_by_period(bundle, "revenue", "Budget")
    rev_outlook = _outlook_series(bundle, rev_actual, rev_forecast)

    month_labels: list[str] = []
    rev_outlook_m: list[float] = []
    rev_budget_m: list[float] = []

    for period in periods:
        p = to_period(period)
        month_labels.append(calendar.month_abbr[int(p[5:7])])
        rev_outlook_m.append(_to_m(rev_outlook.get(p, ZERO)))
        rev_budget_m.append(_to_m(rev_budget.get(p, ZERO)))

    n = len(month_labels)

    return {
        "months": month_labels,
        "ending_arr_m": [round(v, 3) for v in act_arr[:n]],
        "ending_arr_outlook_m": [round(v, 3) for v in out_arr[:n]],
        "ending_arr_budget_m": [round(v, 3) for v in bud_arr[:n]],
        "revenue_outlook_m": rev_outlook_m,
        "revenue_budget_m": rev_budget_m,
        "pipeline_created_m": [
            _to_m(v)
            for v in (monthly_flow_series(bundle, "pipeline", "pipeline_created")[1][:n])
        ],
    }


def _pl_row(
    bundle: ReportingBundle,
    ts_data: dict[str, Any] | None,
    periods: list[str],
    line_key: str,
    fs_needle: str,
) -> dict[str, str]:
    act = ZERO
    bud = ZERO
    for p in periods:
        tp = to_period(p)
        ta = _ts_line(ts_data, tp, "Actual", line_key)
        tb = _ts_line(ts_data, tp, "Budget", line_key)
        act += ta if ta is not None else _fs_amount(bundle, [tp], "Actual", fs_needle)
        bud += tb if tb is not None else _fs_amount(bundle, [tp], "Budget", fs_needle)
    return {
        "actual": fmt_deck_money(act),
        "budget": fmt_deck_money(bud),
        "variance": fmt_deck_var(act, bud),
        "var_pct": fmt_deck_var_pct(act, bud),
    }


def build_pl_detail_block(
    bundle: ReportingBundle,
    ts_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Full P&L GL lines — CM and YTD (matches V3 template P&L section)."""
    from app.services.reporting.export.board_platform_metrics import (
        gross_margin_pct,
        gross_margin_pct_horizon,
    )

    as_of = bundle.as_of_period
    ytd_p = ytd_periods(as_of)
    qtd_p = qtd_periods(as_of)

    line_specs = (
        ("revenue", "revenue", "Revenue"),
        ("cogs", "cost of revenue", "COGS"),
        ("gross_profit", "gross profit", "Gross Profit"),
        ("sm", "sales and marketing", "S&M"),
        ("rd", "research", "R&D"),
        ("ga", "general and administrative", "G&A"),
        ("ebitda", "ebitda", "EBITDA"),
        ("da", "depreciation", "D&A"),
        ("net_income", "net income", "Net Income"),
    )

    def horizon_block(periods: list[str], label: str) -> dict[str, Any]:
        rows: dict[str, Any] = {}
        for key, needle, display in line_specs:
            rows[key] = {**_pl_row(bundle, ts_data, periods, key, needle), "label": display}
        gm_a = (
            gross_margin_pct(bundle, as_of, "Actual")
            if label == "cm"
            else gross_margin_pct_horizon(bundle, periods, "Actual")
        )
        gm_b = (
            gross_margin_pct(bundle, as_of, "Budget")
            if label == "cm"
            else gross_margin_pct_horizon(bundle, periods, "Budget")
        )
        gm_var = "—"
        if gm_a is not None and gm_b is not None:
            delta = float(gm_a) - float(gm_b)
            # gm_* are already percent points (e.g. 70.0) when as_percent=False path used below.
            gm_var = f"{delta:+.1f}pp"
        rows["gross_margin_pct"] = {
            "label": "Gross Margin %",
            "actual": fmt_deck_pct(gm_a, as_percent=False) if gm_a is not None else "n/a",
            "budget": fmt_deck_pct(gm_b, as_percent=False) if gm_b is not None else "n/a",
            "variance": gm_var,
        }
        return rows

    return {
        "cm": horizon_block([as_of], "cm"),
        "qtd": horizon_block(qtd_p, "qtd"),
        "ytd": horizon_block(ytd_p, "ytd"),
        "table_headers": [
            "Line Item",
            "CM Actual",
            "CM Budget",
            "CM Variance",
            "YTD Actual",
            "YTD Budget",
            "YTD Variance",
        ],
    }


def build_gtm_funnel_block(bundle: ReportingBundle) -> dict[str, Any]:
    """Q1/Q2/YTD funnel stages — new logo vs expansion where marketing data exists."""
    as_of = bundle.as_of_period
    year = as_of[:4]
    q1_p = [f"{year}-01", f"{year}-02", f"{year}-03"]
    q2_p = qtd_periods(as_of) if int(as_of[5:7]) >= 4 else []
    ytd_p = ytd_periods(as_of)
    mkt = bundle.marketing_channel_comparison or bundle.marketing_comparison
    if not mkt:
        return {"available": False, "note": "No marketing_comparison data loaded."}

    def sum_field(rows, period_list: list[str], field: str, scenario: str = "Actual") -> Decimal:
        total = ZERO
        wanted = {to_period(p) for p in period_list}
        for row in rows:
            if row.period not in wanted or row.scenario != scenario:
                continue
            total += getattr(row, field, ZERO) or ZERO
        return total

    def pack(period_list: list[str]) -> dict[str, str]:
        if not period_list:
            return {}
        return {
            "mqls": str(int(sum_field(mkt.actual, period_list, "mqls"))),
            "mqls_budget": str(int(sum_field(mkt.budget, period_list, "mqls"))),
            "sqls": str(int(sum_field(mkt.actual, period_list, "sqls"))),
            "sals": str(int(sum_field(mkt.actual, period_list, "sals"))),
            "opportunities": str(int(sum_field(mkt.actual, period_list, "opportunities_created"))),
            "pipeline_arr": fmt_deck_money(sum_field(mkt.actual, period_list, "pipeline_arr_created")),
            "pipeline_arr_budget": fmt_deck_money(sum_field(mkt.budget, period_list, "pipeline_arr_created")),
            "closed_won_arr": fmt_deck_money(sum_field(mkt.actual, period_list, "closed_won_arr")),
            "closed_won_budget": fmt_deck_money(sum_field(mkt.budget, period_list, "closed_won_arr")),
            "spend": fmt_deck_money(sum_field(mkt.actual, period_list, "marketing_spend")),
            "spend_budget": fmt_deck_money(sum_field(mkt.budget, period_list, "marketing_spend")),
        }

    return {
        "available": True,
        "new_logo": {
            "q1": pack(q1_p),
            "q2": pack(q2_p),
            "ytd": pack(ytd_p),
        },
        "note": "Budget from budget_marketing_pipeline (per-channel). Use new_logo tables for GTM Funnel slide (slide 7).",
    }


def build_deal_highlights_block(bundle: ReportingBundle) -> dict[str, Any]:
    """Top deals from pipeline drilldown for ARR / GTM commentary."""
    cur = bundle.currency
    as_of = bundle.as_of_period

    def top_opps(movement: str, limit: int = 5) -> list[dict[str, str]]:
        payload = bundle.pipeline_drilldown.get(movement) or {}
        opps = payload.get("opportunities") or []
        ranked = sorted(opps, key=lambda o: abs(_opp_amount(o)), reverse=True)
        out: list[dict[str, str]] = []
        for opp in ranked[:limit]:
            amt = _opp_amount(opp)
            if amt == ZERO:
                continue
            out.append(
                {
                    "name": _opp_name(opp),
                    "arr": fmt_deck_money(amt),
                    "segment": str(opp.get("segment") or opp.get("tier") or "n/a"),
                    "type": str(opp.get("type") or movement.replace("_", " ")),
                }
            )
        return out

    return {
        "top_new_customers": top_opps("closed_won", 5),
        "top_expansion": top_opps("expansion", 3) or top_opps("new_business", 3),
        "top_churn": top_opps("churn", 5),
        "top_slipped": top_opps("slipped_pipeline", 3),
        "close_period": as_of,
        "currency": cur,
    }


def build_all_slide_metrics(bundle: ReportingBundle) -> dict[str, Any]:
    """Prompt 1 per-slide metric blocks — same numbers board commentary uses."""
    as_of = to_period(bundle.as_of_period)
    m = build_metrics_snapshot(bundle)
    out: dict[str, Any] = {}
    for slide_key, builder in _METRIC_BUILDERS.items():
        if slide_key not in _SLIDE_SPECS:
            continue
        spec = _SLIDE_SPECS[slide_key]
        out[slide_key] = {
            "slide_title": spec["slide_title"],
            "max_bullets": spec["max_bullets"],
            "max_words_per_bullet": spec["max_words_per_bullet"],
            "max_chars_per_bullet": spec["max_chars_per_bullet"],
            "metrics": builder(bundle, m, as_of),
        }
    return out


def build_h2_priorities_stub(bundle: ReportingBundle) -> list[dict[str, str]]:
    """Placeholder H2 priority cards — Claude fills narrative from fy_outlook + metrics."""
    return [
        {
            "title": "ARR & GTM",
            "detail_hint": "Use fy_outlook.arr_eoy and pipeline_coverage from arr_analysis.",
        },
        {
            "title": "Profitability",
            "detail_hint": "Use pl_detail.ytd gross_margin_pct and ebitda rows.",
        },
        {
            "title": "Cash & runway",
            "detail_hint": "Use cash_liquidity and ytd_cash_flow_statement.",
        },
        {
            "title": "Workforce",
            "detail_hint": "Use fy_outlook.headcount integers.",
        },
    ]


def enrich_deck_payload(
    payload: dict[str, Any],
    bundle: ReportingBundle,
    ts_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach full analyst context blocks to base deck payload."""
    payload["mom_context"] = build_mom_block(bundle)
    payload["monthly_trends"] = build_monthly_trends_block(bundle, ts_data)
    payload["pl_detail"] = build_pl_detail_block(bundle, ts_data)
    payload["gtm_funnel"] = build_gtm_funnel_block(bundle)
    payload["deal_highlights"] = build_deal_highlights_block(bundle)
    payload["slide_metrics"] = build_all_slide_metrics(bundle)
    payload["h2_priorities"] = build_h2_priorities_stub(bundle)
    from app.services.reporting.export.prompt5_mda_slides import enrich_mda_deck_slides

    payload = enrich_mda_deck_slides(payload, bundle)
    payload["commentary_rules"] = {
        "min_trend_bullets_per_slide": 2,
        "require_deal_callouts_slides": [3, 6, 8],
        "require_dollar_impact_risks": True,
    }
    import json

    payload["payload_meta"] = {
        "version": "v3_full",
        "schema": "SMPL_API_Prompts_BoardDeck_MDA_v7",
        "layout_reference": "mda_deck_2026-06 v3.pptx",
        "approx_json_chars": len(json.dumps(payload, separators=(",", ":"))),
        "scale_note": "Future: tier summarization for 100x row counts; this build sends full SMPL context.",
    }
    return payload
