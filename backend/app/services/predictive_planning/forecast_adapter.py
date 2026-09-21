"""Forecast → Plan Assurance packet adapter.

Forecast Engine (and later Board) should produce a plan packet and call the same
``/assess`` / ``/simulate`` engine Budget uses. Horizon and open-period semantics
differ; constraint math does not.
"""

from __future__ import annotations

from typing import Any


def build_forecast_plan_packet(
    *,
    period_label: str,
    budget_year: int | None,
    bop_arr: float | None,
    dec_arr: float | None,
    target_arr: float | None,
    yoy_growth_pct: float | None,
    fy_nn: float | None = None,
    fy_rev: float | None = None,
    fy_ebitda: float | None = None,
    end_cash: float | None = None,
    cash_floor: float | None = None,
    min_cash: float | None = None,
    min_cash_period: str | None = None,
    cash_by_month: list[float] | None = None,
    avg_grr: float | None = None,
    min_grr: float | None = None,
    sales_end: float | None = None,
    cs_end: float | None = None,
    ae_needed: float | None = None,
    cs_needed: float | None = None,
    cover_pct: float | None = None,
    hire_pct: float | None = None,
    bench_target: float | None = None,
    pipeline_coverage: float | None = None,
    pipeline_min: float | None = 2.5,
    jan_hc: float | None = None,
    jan_hc_expected: float | None = None,
    dec_hc: float | None = None,
    fy_mkt: float | None = None,
    fy_mql: float | None = None,
    fy_ch_mql: float | None = None,
    fy_spend_id: float | None = None,
    mix_dev_max: float | None = None,
    fy_is_sm: float | None = None,
    fy_gtm_sm: float | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a camelCase packet compatible with ``PlanPacket`` aliases."""

    packet: dict[str, Any] = {
        "period_label": period_label,
        "budget_year": budget_year,
        "yoyGrowthPct": yoy_growth_pct,
        "bopArr": bop_arr,
        "decArr": dec_arr,
        "targetArr": target_arr,
        "fyNn": fy_nn if fy_nn is not None else (
            (dec_arr - bop_arr) if dec_arr is not None and bop_arr is not None else None
        ),
        "fyRev": fy_rev,
        "fyEbitda": fy_ebitda,
        "endCash": end_cash,
        "cashFloor": cash_floor if cash_floor is not None else 10_000_000.0,
        "minCash": min_cash if min_cash is not None else end_cash,
        "minCashPeriod": min_cash_period,
        "cashByMonth": cash_by_month,
        "avgGrr": avg_grr,
        "minGrr": min_grr,
        "salesEnd": sales_end,
        "csEnd": cs_end,
        "aeNeeded": ae_needed,
        "csNeeded": cs_needed,
        "coverPct": cover_pct,
        "hirePct": hire_pct,
        "benchTarget": bench_target,
        "pipelineCoverage": pipeline_coverage,
        "pipelineMin": pipeline_min,
        "janHc": jan_hc,
        "janHcExpected": jan_hc_expected if jan_hc_expected is not None else jan_hc,
        "decHc": dec_hc,
        "fyMkt": fy_mkt,
        "fyMql": fy_mql,
        "fyChMql": fy_ch_mql if fy_ch_mql is not None else fy_mql,
        "fySpendId": fy_spend_id if fy_spend_id is not None else fy_mkt,
        "mixDevMax": mix_dev_max if mix_dev_max is not None else 0.0,
        "fyIsSm": fy_is_sm,
        "fyGtmSm": fy_gtm_sm if fy_gtm_sm is not None else fy_mkt,
        "surface": "forecast",
    }
    if extra:
        packet.update(extra)
    return {k: v for k, v in packet.items() if v is not None}


#: Forecast-specific notes for assess method_notes when scenario == "forecast".
FORECAST_METHOD_NOTES = [
    "Packet produced by the Forecast adapter — same constraint registry as Budget.",
    "Open-period / horizon semantics differ from annual Budget; dollars still come from the deterministic Forecast model.",
]
