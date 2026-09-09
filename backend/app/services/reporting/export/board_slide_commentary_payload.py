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
        "cash_flow_statement",
        "gtm_performance",
        "gtm_funnel",
        "risks_opportunities",
        "financial_outlook",
        "board_actions",
    }
)

# Limits must fit complete board sentences (actual / budget / variance / implication).
# PPTX template export still fits text to shape boxes separately; do not pre-mangle
# AI commentary with ultra-short deck stubs (legacy 15-word / 85-char caps).
_DEFAULT_MAX_WORDS_PER_BULLET = 60
_DEFAULT_MAX_CHARS_PER_BULLET = 480

_SLIDE_SPECS: dict[str, dict[str, Any]] = {
    "executive_summary": {
        "slide_number": 2,
        "slide_title": "Executive Summary",
        "max_bullets": 5,
        "max_words_per_bullet": _DEFAULT_MAX_WORDS_PER_BULLET,
        "max_chars_per_bullet": _DEFAULT_MAX_CHARS_PER_BULLET,
    },
    "arr_waterfall": {
        "slide_number": 3,
        "slide_title": "ARR Analysis",
        "max_bullets": 2,
        "max_words_per_bullet": _DEFAULT_MAX_WORDS_PER_BULLET,
        "max_chars_per_bullet": _DEFAULT_MAX_CHARS_PER_BULLET,
    },
    "gaap_revenue": {
        "slide_number": 4,
        "slide_title": "P&L Review",
        "max_bullets": 5,
        "max_words_per_bullet": _DEFAULT_MAX_WORDS_PER_BULLET,
        "max_chars_per_bullet": _DEFAULT_MAX_CHARS_PER_BULLET,
    },
    "cash_forecast": {
        "slide_number": 5,
        "slide_title": "Cash & Liquidity",
        "max_bullets": 4,
        "max_words_per_bullet": _DEFAULT_MAX_WORDS_PER_BULLET,
        "max_chars_per_bullet": _DEFAULT_MAX_CHARS_PER_BULLET,
    },
    "cash_flow_statement": {
        "slide_number": 6,
        "slide_title": "Cash Flow Statement",
        "max_bullets": 4,
        "max_words_per_bullet": _DEFAULT_MAX_WORDS_PER_BULLET,
        "max_chars_per_bullet": _DEFAULT_MAX_CHARS_PER_BULLET,
    },
    "gtm_performance": {
        "slide_number": 7,
        "slide_title": "GTM & Marketing",
        "max_bullets": 11,
        "max_words_per_bullet": _DEFAULT_MAX_WORDS_PER_BULLET,
        "max_chars_per_bullet": _DEFAULT_MAX_CHARS_PER_BULLET,
    },
    "gtm_funnel": {
        "slide_number": 8,
        "slide_title": "Funnel Analysis",
        "max_bullets": 4,
        "max_words_per_bullet": _DEFAULT_MAX_WORDS_PER_BULLET,
        "max_chars_per_bullet": _DEFAULT_MAX_CHARS_PER_BULLET,
    },
    "risks_opportunities": {
        "slide_number": 9,
        "slide_title": "Risks & Opportunities",
        "max_bullets": 4,
        "max_words_per_bullet": _DEFAULT_MAX_WORDS_PER_BULLET,
        "max_chars_per_bullet": _DEFAULT_MAX_CHARS_PER_BULLET,
    },
    "financial_outlook": {
        "slide_number": 10,
        "slide_title": "Financial Outlook",
        "max_bullets": 4,
        "max_words_per_bullet": _DEFAULT_MAX_WORDS_PER_BULLET,
        "max_chars_per_bullet": _DEFAULT_MAX_CHARS_PER_BULLET,
    },
    "board_actions": {
        "slide_number": 11,
        "slide_title": "Board Actions",
        "max_bullets": 4,
        "max_words_per_bullet": _DEFAULT_MAX_WORDS_PER_BULLET,
        "max_chars_per_bullet": _DEFAULT_MAX_CHARS_PER_BULLET,
    },
}

# Interactive board regenerate floor — never below full-sentence board narrative length.
_INTERACTIVE_MIN_WORDS_PER_BULLET = _DEFAULT_MAX_WORDS_PER_BULLET
_INTERACTIVE_MIN_CHARS_PER_BULLET = _DEFAULT_MAX_CHARS_PER_BULLET


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


def money_trio(stem: str, actual: Decimal | None, budget: Decimal | None) -> dict[str, str]:
    """actual / budget / variance $ / variance % for one money metric.

    Board bullets must state a variance, but most slide metrics shipped only
    actual and budget, so the model subtracted the two rounded figures itself.
    That arithmetic misses the engine value (a true -$84.2K reads as -$90.0K)
    and the bullet is then deleted as unverifiable. Computing from raw values
    here means the bullet copies an engine number instead of deriving one.
    """
    out = {
        f"{stem}_actual": fmt_deck_money(actual),
        f"{stem}_budget": fmt_deck_money(budget),
    }
    if actual is not None and budget is not None:
        out[f"{stem}_var"] = fmt_deck_var(actual, budget)
        out[f"{stem}_var_pct"] = fmt_deck_var_pct(actual, budget)
    return out


def ratio_fields(stem: str, value: Decimal | None) -> dict[str, str]:
    """A multiple as both display text and a bare number.

    "5.5x" carries the ratio inside a unit suffix, so it never parsed into the
    evidence map and every cited coverage/efficiency multiple was unverifiable.
    The bare "<stem>_x" value is what claim verification can actually match.
    """
    if value is None:
        return {stem: "n/a"}
    return {stem: f"{float(value):.1f}x", f"{stem}_x": f"{float(value):.1f}"}


def pct_trio(stem: str, actual: Decimal | None, budget: Decimal | None) -> dict[str, str]:
    """actual / budget / bps delta for one percentage metric.

    Percent metrics get a basis-point delta rather than a percent-of-a-percent,
    which is the board convention and the only unambiguous reading.
    """
    out = {
        f"{stem}_actual": fmt_deck_pct(actual, as_percent=False) if actual is not None else "n/a",
        f"{stem}_budget": fmt_deck_pct(budget, as_percent=False) if budget is not None else "n/a",
    }
    if actual is not None and budget is not None:
        out[f"{stem}_var_bps"] = f"{(Decimal(actual) - Decimal(budget)) * 100:+.0f}bps"
    return out


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
    """Gross margin % = Gross Profit / Revenue."""
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if not fs:
        return None
    gp = rev = Decimal("0")
    for row in fs.income_statement.rows:
        if str(row.period)[:7] != period or row.scenario != scenario:
            continue
        li = row.line_item.lower()
        if "gross profit" in li:
            gp = row.amount
        elif ("gross margin" in li or li == "gm") and gp == 0:
            if row.amount <= Decimal("1.5"):
                return row.amount * 100
            return row.amount
        if "revenue" in li and "deferred" not in li and "cost" not in li:
            rev = row.amount
    if rev and gp:
        return (gp / rev) * 100
    return None


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
        **money_trio("revenue", m.revenue_actual, m.revenue_budget),
        **money_trio("arr_ending", arr.current_month, arr.budget_cm),
        # Long-standing key the deck template reads; same value as arr_ending_var.
        "arr_var_dollar": fmt_deck_var(arr.current_month, arr.budget_cm),
        **money_trio("net_new_arr", m.net_new_arr, m.new_arr_budget),
        # The summary slides quote N$R, so they need the retention components that
        # explain it; without them "driven by churn" reads as an unsupported cause.
        **money_trio(
            "new_business",
            _arr_component(bundle, as_of, "new_business", "Actual"),
            _arr_component(bundle, as_of, "new_business", "Budget"),
        ),
        **money_trio(
            "expansion",
            _arr_component(bundle, as_of, "expansion", "Actual"),
            _arr_component(bundle, as_of, "expansion", "Budget"),
        ),
        **money_trio(
            "churn",
            abs(_arr_component(bundle, as_of, "churn", "Actual")),
            abs(_arr_component(bundle, as_of, "churn", "Budget")),
        ),
        **pct_trio("gross_margin", gm_act, gm_bud),
        **money_trio("ebitda", m.ebitda_actual, m.ebitda_budget),
        **money_trio("cash", cash.current_month, cash_bud or cash.budget_cm),
        **_cash_floor_fields(cash.current_month),
        "n_dollar_r_actual": fmt_deck_pct(ndr) if ndr is not None else "n/a",
        "n_dollar_r_budget": "n/a",
        **money_trio("ytd_revenue", rev.ytd, rev.budget_ytd),
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
    pipeline_cov = None
    if m.pipeline_created and m.closed_won:
        pipeline_cov = m.pipeline_created / max(m.closed_won, Decimal("1"))
    return {
        **money_trio("arr_ending", arr.current_month, arr.budget_cm),
        **money_trio("net_new_arr", m.net_new_arr, m.new_arr_budget),
        **money_trio("new_business", nb_a, nb_b),
        **money_trio("expansion", exp_a, exp_b),
        **money_trio("churn", churn_a, churn_b),
        "n_dollar_r_actual": fmt_deck_pct(m.nrr) if m.nrr is not None else "n/a",
        "g_dollar_r_actual": fmt_deck_pct(gdr) if gdr is not None else "n/a",
        **ratio_fields("pipeline_coverage", pipeline_cov),
        "pipeline_ending": fmt_deck_money(pipeline_end),
        **money_trio("fy_arr", arr.fy_outlook, arr.budget_fy),
        "fy_arr_forecast": fmt_deck_money(arr.fy_outlook),
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
        **money_trio("revenue", m.revenue_actual, m.revenue_budget),
        **pct_trio("gross_margin", gm_act, gm_bud),
        **money_trio("ebitda", m.ebitda_actual, m.ebitda_budget),
        **money_trio("sm", sm_a, sm_b),
        **money_trio("rd", rd_a, rd_b),
        **money_trio("ytd_revenue", rev.ytd, rev.budget_ytd),
        "known_one_time_items": "n/a",
    }


CASH_FLOOR = Decimal("10000000")


def _cash_floor_fields(cash_actual: Decimal | None) -> dict[str, str]:
    """Publish the floor and headroom on every slide whose bullets discuss cash.

    Both are deterministic, but they used to live only on the cash slides, so the
    same accurate liquidity sentence verified there and was deleted on the summary
    slides for quoting figures that slide never published.
    """
    if cash_actual is None:
        return {}
    return {
        "cash_floor": fmt_deck_money(CASH_FLOOR),
        "cash_headroom": fmt_deck_money(cash_actual - CASH_FLOOR),
        # Liquidity bullets reach for a coverage multiple, and cash over floor is a
        # real quotient of two published figures. Leaving it unpublished meant the
        # model divided them itself and the bullet was deleted for a number the
        # engine could have stated exactly.
        **ratio_fields("cash_floor_coverage", cash_actual / CASH_FLOOR),
        **ratio_fields(
            "cash_headroom_coverage", (cash_actual - CASH_FLOOR) / CASH_FLOOR
        ),
    }


def _metrics_cash(bundle: ReportingBundle, m, as_of: str) -> dict[str, str]:
    cash = rollup_cash(bundle)
    cash_bud = _wf(bundle, "cash_flow", "ending_cash", as_of, "Budget")
    collections = _wf(bundle, "cash_flow", "collections", as_of, "Actual") or _wf(
        bundle, "cash_flow", "cash_collections", as_of, "Actual"
    )
    cfo_a = _wf(bundle, "cash_flow", "cfo", as_of, "Actual")
    cfo_b = _wf(bundle, "cash_flow", "cfo", as_of, "Budget")
    return {
        **money_trio("cash", cash.current_month, cash_bud or cash.budget_cm),
        "collections_actual": fmt_deck_money(collections),
        **money_trio("cfo", cfo_a, cfo_b),
        **_cash_floor_fields(cash.current_month),
        "h2_cash_forecast": fmt_deck_money(cash.fy_outlook),
    }


def _metrics_gtm(bundle: ReportingBundle, m, as_of: str) -> dict[str, str]:
    spend = m.marketing_spend
    pipeline = m.pipeline_from_marketing or m.pipeline_created
    blended = (pipeline / spend) if spend else None
    pipe_end = _wf(bundle, "pipeline", "ending_pipeline", as_of, "Actual")
    # Funnel conversion was the one GTM figure with no published form, so every
    # bullet quoting it divided SQL by MQL and failed verification.
    mql_to_sql = (Decimal(m.sql) / Decimal(m.mql) * 100) if m.mql else None
    return {
        "marketing_spend_actual": fmt_deck_money(spend),
        "marketing_spend_budget": "n/a",
        "pipeline_created_actual": fmt_deck_money(m.pipeline_created),
        "pipeline_ending": fmt_deck_money(pipe_end),
        **ratio_fields("pipeline_coverage", blended),
        **ratio_fields("blended_efficiency", blended),
        "closed_won_arr_actual": fmt_deck_money(m.closed_won_arr_mkt or m.closed_won),
        "mql_to_sql_conversion": (
            f"{float(mql_to_sql):.1f}%" if mql_to_sql is not None else "n/a"
        ),
        **money_trio(
            "sm",
            _is_line_amount(bundle, as_of, "sales and marketing", "Actual"),
            _is_line_amount(bundle, as_of, "sales and marketing", "Budget"),
        ),
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
        # Budget comparators for the retention components: with actuals alone the
        # only contrast available was churn against expansion, which the model kept
        # expressing as an invented percentage.
        **money_trio(
            "churn",
            abs(_arr_component(bundle, as_of, "churn", "Actual")) or m.churn,
            abs(_arr_component(bundle, as_of, "churn", "Budget")),
        ),
        **money_trio(
            "expansion",
            _arr_component(bundle, as_of, "expansion", "Actual") or m.expansion,
            _arr_component(bundle, as_of, "expansion", "Budget"),
        ),
        "deferred_pipeline": fmt_deck_money(m.slipped),
        "pipeline_created": fmt_deck_money(m.pipeline_created),
        "cash_actual": fmt_deck_money(m.cash_actual),
        **_cash_floor_fields(m.cash_actual),
        "data_gaps": gaps or "none",
    }


_METRIC_BUILDERS = {
    "executive_summary": _metrics_executive,
    "arr_waterfall": _metrics_arr,
    "gaap_revenue": _metrics_pl,
    "cash_forecast": _metrics_cash,
    "cash_flow_statement": _metrics_cash,
    "gtm_performance": _metrics_gtm,
    "gtm_funnel": _metrics_gtm,
    "risks_opportunities": _metrics_risks,
    "financial_outlook": _metrics_executive,
    "board_actions": _metrics_risks,
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


def slide_prompt_limits(slide_key: str) -> tuple[int, int, int]:
    spec = _SLIDE_SPECS[slide_key]
    return (
        int(spec["max_bullets"]),
        int(spec["max_words_per_bullet"]),
        int(spec.get("max_chars_per_bullet", _DEFAULT_MAX_CHARS_PER_BULLET)),
    )


def interactive_slide_prompt_limits(slide_key: str) -> tuple[int, int, int]:
    """Limits for board UI / AI regenerate — full sentences, not PPTX stub length.

    Applies to every key in ``_SLIDE_SPECS`` / ``BOARD_DECK_SLIDE_KEYS``.
    """
    max_bullets, max_words, max_chars = slide_prompt_limits(slide_key)
    return (
        max_bullets,
        max(max_words, _INTERACTIVE_MIN_WORDS_PER_BULLET),
        max(max_chars, _INTERACTIVE_MIN_CHARS_PER_BULLET),
    )
