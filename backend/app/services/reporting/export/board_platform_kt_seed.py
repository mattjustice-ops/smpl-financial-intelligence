"""Deterministic Key Takeaways seed for Prompt 5 — fallback when Claude/soft-strip blanks slots."""

from __future__ import annotations

from typing import Any

KT_SEED_MARKER = "KEY TAKEAWAYS SEED (MUST-USE FALLBACK)"


def _s(block: dict[str, Any] | None, *keys: str, default: str = "—") -> str:
    cur: Any = block or {}
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    if cur in (None, "", "n/a", "N/A", "—"):
        return default
    return str(cur)


def _period_label(payload: dict[str, Any]) -> str:
    pc = payload.get("period_context") or {}
    return str(pc.get("close_period_label") or pc.get("close_period") or payload.get("period_label") or "close")


def build_seed_key_takeaways(payload: dict[str, Any]) -> dict[str, list[str]]:
    """Build 4–5 board-ready takeaway bullets per narrative slide from payload metrics.

    Numbers are copied from the deck payload (already evidence-backed). Used as:
    1) prompt must-fill slots, and 2) post-soft-strip refill when a bullet is ``—``.
    """
    label = _period_label(payload)
    pm = payload.get("period_matrix") or {}
    arr = pm.get("arr") or pm.get("ending_arr") or {}
    rev = pm.get("revenue") or {}
    ebitda = pm.get("ebitda") or {}
    cash = pm.get("cash") or pm.get("ending_cash") or {}
    gtm = payload.get("gtm_performance") or {}
    arr_a = payload.get("arr_analysis") or {}
    pl = payload.get("pl_detail") or {}
    pl_cm = pl.get("cm") or {}
    pl_ytd = pl.get("ytd") or {}
    cash_l = payload.get("cash_liquidity") or {}
    cash_cm = cash_l.get("current_month") or {}
    cash_ytd = cash_l.get("ytd") or {}
    fy = payload.get("fy_outlook") or {}
    pipe_wf = (gtm.get("pipeline_waterfall_chart") or {}) if isinstance(gtm, dict) else {}

    arr_act = _s(arr, "actual", default=_s(arr_a, "ending_arr", "actual"))
    arr_var = _s(arr, "variance", default=_s(arr_a, "ending_arr", "variance"))
    rev_cm = _s(pl_cm, "revenue", "actual", default=_s(rev, "actual"))
    rev_cm_var = _s(pl_cm, "revenue", "variance", default=_s(rev, "variance"))
    rev_ytd = _s(pl_ytd, "revenue", "actual")
    rev_ytd_var = _s(pl_ytd, "revenue", "variance")
    ebitda_cm = _s(pl_cm, "ebitda", "actual", default=_s(ebitda, "actual"))
    ebitda_var = _s(pl_cm, "ebitda", "variance", default=_s(ebitda, "variance"))
    ni_cm = _s(pl_cm, "net_income", "actual")
    ni_var = _s(pl_cm, "net_income", "variance")
    gm_cm = _s(pl_cm, "gross_margin_pct", "actual")
    gm_ytd = _s(pl_ytd, "gross_margin_pct", "actual")
    cash_act = _s(cash, "actual", default=_s(cash_cm, "cash_eop_actual"))
    cash_var = _s(cash, "variance")
    ytd_coll = _s(cash_ytd, "collections")
    ytd_cash = _s(cash_ytd, "cash_eop_actual")
    coverage = _s(gtm, "pipeline_coverage_x")
    slipped = _s(gtm, "slipped_pipeline")
    slipped_bud = _s(gtm, "slipped_pipeline_budget")
    closed_lost = _s(gtm, "closed_lost")
    closed_lost_bud = _s(gtm, "closed_lost_budget")
    pipe_created = _s(gtm, "pipeline_created")
    ending_pipe = _s(gtm, "ending_pipeline")
    begin_pipe = _s(gtm, "beginning_pipeline", default=_s(pipe_wf, "beginning_display"))
    closed_won = _s(gtm, "closed_won")
    fy_arr = _s(fy, "arr_eoy", "outlook", default=_s(fy, "ending_arr", "outlook"))
    fy_arr_bud = _s(fy, "arr_eoy", "budget", default=_s(fy, "ending_arr", "budget"))
    fy_cash = _s(fy, "cash_eoy", "outlook")
    fy_cash_bud = _s(fy, "cash_eoy", "budget")
    fy_rev = _s(fy, "revenue_fy", "outlook", default=_s(fy, "revenue", "outlook"))
    fy_rev_bud = _s(fy, "revenue_fy", "budget", default=_s(fy, "revenue", "budget"))

    return {
        "slide_2_executive": [
            f"1. ARR {arr_act} vs budget variance {arr_var} in {label}; track net-new timing vs plan.",
            f"2. Revenue {rev_cm} CM ({rev_cm_var}); YTD {rev_ytd} ({rev_ytd_var}) — manage expansion/new mix.",
            f"3. EBITDA {ebitda_cm} ({ebitda_var}); opex discipline holding despite revenue headwind.",
            f"4. Cash {cash_act} ({cash_var}); YTD collections {ytd_coll} support liquidity into H2.",
            f"5. Pipeline coverage {coverage}; slipped {slipped} needs next-quarter re-staging.",
        ],
        "slide_3_arr": [
            f"1. Ending ARR {arr_act} ({arr_var}) in {label}; MoM bridge shows component mix vs budget.",
            f"2. Retention: churn/contraction vs plan — keep G$R discipline while expanding.",
            f"3. Net-new vs budget; expansion/new timing drives the bridge residual.",
            f"4. FY ARR outlook {fy_arr} vs {fy_arr_bud}; pipeline coverage {coverage} supports H2 ramp.",
        ],
        "slide_4_pl": [
            f"1. Revenue {rev_cm} CM ({rev_cm_var}); YTD {rev_ytd} ({rev_ytd_var}) — close the gap via conversion.",
            f"2. Gross margin {gm_cm} CM / {gm_ytd} YTD on plan; COGS discipline intact.",
            f"3. EBITDA {ebitda_cm} ({ebitda_var}); sustain opex control through H2.",
            f"4. Net income {ni_cm} ({ni_var}); profitability trajectory remains intact.",
            f"5. Board action: certify P&L tie-out and approve H2 revenue acceleration plan.",
        ],
        "slide_5_cash": [
            f"1. Ending cash {cash_act} in {label}; vs budget {cash_var}.",
            f"2. YTD collections {ytd_coll}; YTD ending cash {ytd_cash} — primary liquidity read.",
            f"3. Monthly bridge: collections vs payroll/vendor/commission outflows drive MoM change.",
            f"4. FY cash outlook {fy_cash} vs {fy_cash_bud}; update H2 collections model.",
            f"5. Maintain cash floor discipline; deploy excess only against board-approved bets.",
        ],
        "slide_6_gtm": [
            f"1. Closed-lost {closed_lost} vs budget {closed_lost_bud}; run loss review before H2 push.",
            f"2. Slipped pipeline {slipped} vs {slipped_bud}; re-stage with owners and next steps.",
            f"3. Coverage {coverage} vs ending ARR; YTD closed won {closed_won}.",
            f"4. Pipeline created {pipe_created}; reallocate spend toward efficient channels.",
            f"5. Board action: approve channel reallocation and slipped-deal validation checklist.",
        ],
        "slide_7_pipeline": [
            f"1. Beginning pipeline {begin_pipe} → ending {ending_pipe} (additive waterfall for {label}).",
            f"2. Created {pipe_created}; closed won {closed_won}; closed lost {closed_lost}.",
            f"3. Slipped {slipped} vs {slipped_bud}; clear the slip backlog before forecasting H2.",
            f"4. Coverage {coverage} supports ramp; prioritize enterprise conversion velocity.",
        ],
        "slide_9_outlook": [
            f"1. FY ARR outlook {fy_arr} vs {fy_arr_bud}; coverage {coverage} supports H2 acceleration.",
            f"2. FY revenue {fy_rev} vs {fy_rev_bud}; conversion of ending pipeline {ending_pipe} is the lever.",
            f"3. Cash outlook {fy_cash} vs {fy_cash_bud}; collections moderation expected in H2.",
            f"4. Board action: approve updated FY outlook and H2 pipeline acceleration plan.",
        ],
    }


def format_kt_seed_block(payload: dict[str, Any]) -> str:
    """Prompt block — Claude must fill every KT slot; use these if inventing would fail verify."""
    seeds = payload.get("key_takeaways_by_slide") or build_seed_key_takeaways(payload)
    lines = [
        f"{KT_SEED_MARKER}",
        "Every Key Takeaways panel MUST have 3–5 filled bullets (never blank or lone '—').",
        "Prefer rewritten insight bullets from packages; if a slot would be empty/soft-stripped,",
        "copy the matching seed bullet VERBATIM (numbers already match EVIDENCE PACKAGE).",
        "",
    ]
    for slide_key, bullets in seeds.items():
        lines.append(f"{slide_key}:")
        for b in bullets:
            lines.append(f"  - {b}")
        lines.append("")
    return "\n".join(lines)
