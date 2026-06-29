"""Prompt 2 MD&A package payload — board-platform metrics for variance commentary."""

from __future__ import annotations

import calendar
from decimal import Decimal
from typing import Any

from app.services.reporting.export.board_metrics_snapshot import build_metrics_snapshot
from app.services.reporting.export.board_period_ytd import rollup_waterfall_metric
from app.services.reporting.export.board_platform_metrics import (
    build_deck_payload,
    build_deliverable_data_map,
    validate_deck_payload,
    verify_variance_commentary_tieout,
)
from app.services.reporting.export.board_slide_commentary_payload import (
    fmt_deck_money,
    fmt_deck_pct,
    fmt_deck_var,
    fmt_deck_var_pct,
)
from app.services.reporting.export.period_views import qtd_periods
from app.services.reporting.export.deck_payload_enriched import build_pl_detail_block
from app.services.reporting.export.prompt5_deck import (
    _marketing_block,
    _marketing_by_channel,
    _risks_and_opportunities,
)
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.period_utils import prior_period, to_period

ZERO = Decimal("0")


def _period_label(period: str) -> str:
    year, month = period.split("-")
    return f"{calendar.month_name[int(month)]} {year}"


def _quarter_label(period: str) -> str:
    month = int(period.split("-")[1])
    return f"Q{(month - 1) // 3 + 1}"


def _ytd_label(period: str) -> str:
    year, month = period.split("-")
    return f"Jan–{calendar.month_name[int(month)]} {year}"


def _horizon_block(row: dict[str, Any], horizon: str) -> dict[str, str]:
    blk = row.get(horizon) or {}
    return {
        "actual": str(blk.get("actual") or ""),
        "budget": str(blk.get("budget") or ""),
        "var": str(blk.get("variance") or blk.get("var") or ""),
        "var_pct": str(blk.get("var_pct") or ""),
    }


def _rollup_horizons(rollup, *, is_pct: bool = False) -> dict[str, dict[str, str]]:
    def pack(act: Decimal, bud: Decimal) -> dict[str, str]:
        if is_pct:
            return {
                "actual": fmt_deck_pct(act, as_percent=False) if act is not None else "n/a",
                "budget": fmt_deck_pct(bud, as_percent=False) if bud is not None else "n/a",
            }
        return {
            "actual": fmt_deck_money(act),
            "budget": fmt_deck_money(bud),
            "var": fmt_deck_var(act, bud),
            "var_pct": fmt_deck_var_pct(act, bud),
        }

    qtd_bud = getattr(rollup, "budget_qtd", None)
    if qtd_bud is None:
        qtd_bud = ZERO
    return {
        "period": pack(rollup.current_month, rollup.budget_cm,),
        "qtd": pack(rollup.qtd, qtd_bud),
        "ytd": pack(rollup.ytd, rollup.budget_ytd),
    }


def _budget_qtd_waterfall(bundle: ReportingBundle, wtype: str) -> Decimal:
    budget = {}
    for row in bundle.comparison_waterfalls.get("arr") or []:
        if row.waterfall_type == wtype and row.scenario == "Budget":
            budget[to_period(row.period)] = row.amount
    return sum(budget.get(p, ZERO) for p in qtd_periods(bundle.as_of_period))


def _arr_component_horizons(bundle: ReportingBundle, wtype: str) -> dict[str, dict[str, str]]:
    rollup = rollup_waterfall_metric(bundle, "arr", wtype, flow=True)
    rollup.budget_qtd = _budget_qtd_waterfall(bundle, wtype)  # type: ignore[attr-defined]
    return _rollup_horizons(rollup)


def _matrix_row(matrix: dict[str, Any], metric: str) -> dict[str, Any]:
    for row in matrix.get("rows") or []:
        if row.get("metric") == metric:
            return row
    return {}


def _pl_horizon_blocks(pl_detail: dict[str, Any], line_key: str) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """CM / QTD / YTD blocks from enriched P&L detail (flow metrics like S&M)."""

    def _blk(horizon: str) -> dict[str, str]:
        row = (pl_detail.get(horizon) or {}).get(line_key) or {}
        return {
            "actual": str(row.get("actual") or ""),
            "budget": str(row.get("budget") or ""),
            "var": str(row.get("variance") or row.get("var") or ""),
        }

    return _blk("cm"), _blk("qtd"), _blk("ytd")


def _fmt_headcount_var(actual: int, budget: int) -> str:
    delta = actual - budget
    if delta == 0:
        return "—"
    return f"+{delta}" if delta > 0 else str(delta)


def _headcount_horizon_blocks(bundle: ReportingBundle, as_of: str, snap) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Point-in-time total HC at close month — integers, never dollar formatting."""
    from app.services.reporting.export.board_platform_metrics import headcount_totals

    actual, open_reqs = headcount_totals(bundle, as_of, "Actual")
    budget, _ = headcount_totals(bundle, as_of, "Budget")
    if actual <= 0 and snap.headcount:
        actual = int(snap.headcount)
    if budget <= 0:
        budget, _ = headcount_totals(bundle, as_of, "Forecast")
    if budget <= 0:
        budget = actual

    block = {
        "actual": str(actual),
        "budget": str(budget),
        "var": _fmt_headcount_var(actual, budget),
        "open_reqs": str(open_reqs),
    }
    return block, dict(block), dict(block)


def _sheet_spec(description: str, max_chars: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "description": description,
        "max_chars_per_column": max_chars,
        "rows": rows,
    }


def build_mda_package_payload(
    bundle: ReportingBundle,
    *,
    ts_data: dict[str, Any] | None = None,
    cash_bridge_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build Prompt 2 user message body from warehouse-aligned deck metrics."""
    deck = build_deck_payload(bundle, ts_data=ts_data, cash_bridge_data=cash_bridge_data)
    matrix = deck["period_matrix"]
    arr = deck["arr_analysis"]
    cash = deck["cash_liquidity"]
    fy = deck["fy_outlook"]
    m = build_metrics_snapshot(bundle)
    as_of = bundle.as_of_period
    month = _period_label(as_of).split()[0]

    rev = _matrix_row(matrix, "Revenue")
    arr_row = _matrix_row(matrix, "Ending ARR")
    gm = _matrix_row(matrix, "Gross Margin %")
    ebitda = _matrix_row(matrix, "EBITDA")
    cash_row = _matrix_row(matrix, "Ending Cash")

    nn_roll = rollup_waterfall_metric(bundle, "arr", "new_arr", flow=True)
    if nn_roll.current_month == ZERO:
        nn_roll = rollup_waterfall_metric(bundle, "arr", "new_business", flow=True)
    nn_roll.budget_qtd = _budget_qtd_waterfall(bundle, "new_arr") or _budget_qtd_waterfall(  # type: ignore[attr-defined]
        bundle, "new_business"
    )
    nn_h = _rollup_horizons(nn_roll)

    pl_detail = build_pl_detail_block(bundle, ts_data)
    sm_cm, sm_qtd, sm_ytd = _pl_horizon_blocks(pl_detail, "sm")
    hc_cm, hc_qtd, hc_ytd = _headcount_horizon_blocks(bundle, as_of, m)

    channels = _marketing_by_channel(bundle, as_of)
    gtm_block = _marketing_block(bundle, as_of, m)
    ro = _risks_and_opportunities(bundle, m)

    def vc_row(
        row_id: str,
        category: str,
        metric: str,
        *,
        period: dict[str, Any],
        qtd: dict[str, Any] | None = None,
        ytd: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            "row_id": row_id,
            "category": category,
            "metric": metric,
            "period": period,
            "qtd": qtd or period,
            "ytd": ytd or period,
        }
        if extra:
            row.update(extra)
        return row

    def _pl_horizon(horizon: str, key: str) -> dict[str, str]:
        row = (pl_detail.get(horizon) or {}).get(key) or {}
        return {
            "actual": str(row.get("actual") or ""),
            "budget": str(row.get("budget") or ""),
            "var": str(row.get("variance") or row.get("var") or ""),
        }

    variance_rows = [
        vc_row(
            "vc_arr_ending",
            "ARR",
            "Ending ARR",
            period=_horizon_block(arr_row, "cm"),
            qtd=_horizon_block(arr_row, "qtd"),
            ytd=_horizon_block(arr_row, "ytd"),
            extra={"driver": f"Net new ARR {arr.get('net_new', '')} vs budget {arr.get('net_new_budget', '')}"},
        ),
        vc_row(
            "vc_net_new_arr",
            "ARR",
            "Net New ARR",
            period=nn_h["period"],
            qtd=nn_h["qtd"],
            ytd=nn_h["ytd"],
        ),
        vc_row(
            "vc_revenue",
            "Revenue",
            "Revenue",
            period=_pl_horizon("cm", "revenue"),
            qtd=_pl_horizon("qtd", "revenue"),
            ytd=_pl_horizon("ytd", "revenue"),
        ),
        vc_row(
            "vc_gross_margin",
            "Revenue",
            "Gross Margin %",
            period=_horizon_block(gm, "cm"),
            qtd=_horizon_block(gm, "qtd"),
            ytd=_horizon_block(gm, "ytd"),
        ),
        vc_row(
            "vc_ebitda",
            "P&L",
            "EBITDA",
            period=_pl_horizon("cm", "ebitda"),
            qtd=_pl_horizon("qtd", "ebitda"),
            ytd=_pl_horizon("ytd", "ebitda"),
        ),
        vc_row(
            "vc_sm_pipeline",
            "GTM",
            "S&M / Pipeline",
            period={
                **sm_cm,
                "pipeline_ending": fmt_deck_money(m.pipeline_created),
                "coverage": arr.get("pipeline_coverage_x", "n/a"),
                "top_channels": ", ".join(c["name"] for c in channels[:3]),
            },
            qtd=sm_qtd,
            ytd=sm_ytd,
        ),
        vc_row(
            "vc_cash",
            "Cash",
            "Ending Cash",
            period=_horizon_block(cash_row, "cm"),
            qtd=_horizon_block(cash_row, "qtd"),
            ytd=_horizon_block(cash_row, "ytd"),
        ),
        vc_row(
            "vc_headcount",
            "Headcount",
            "Total HC",
            period=hc_cm,
            qtd=hc_qtd,
            ytd=hc_ytd,
        ),
    ]

    arr_rows = [
        {
            "row_id": f"arr_{key}",
            "metric": label,
            "period": {"actual": arr.get(key, ""), "budget": arr.get(f"{key}_budget", "")},
            "qtd": _arr_component_horizons(bundle, wf)["qtd"],
            "ytd": _arr_component_horizons(bundle, wf)["ytd"],
        }
        for key, label, wf in (
            ("new_business", "New Business", "new_business"),
            ("expansion", "Expansion", "expansion"),
            ("reactivation", "Reactivation", "reactivation"),
            ("contraction", "Contraction", "contraction"),
            ("churn", "Churn", "churn"),
            ("net_new", "Net New ARR", "new_arr"),
        )
    ]
    arr_rows.append(
        {
            "row_id": "arr_ending",
            "metric": "Ending ARR",
            "period": _horizon_block(arr_row, "cm"),
            "qtd": _horizon_block(arr_row, "qtd"),
            "ytd": {
                "actual": _horizon_block(arr_row, "ytd").get("actual", ""),
                "fy_forecast": fy["arr_eoy"].get("actual_or_outlook", ""),
                "fy_budget": fy["arr_eoy"].get("budget", ""),
            },
        }
    )

    gtm_rows = [
        {
            "row_id": f"gtm_{ch['name'].lower().replace(' ', '_').replace('.', '')}",
            "channel": ch["name"],
            "spend": ch["spend"],
            "pipeline": ch["pipeline"],
            "efficiency": ch["efficiency_label"],
            "rank": str(i + 1),
        }
        for i, ch in enumerate(channels[:10])
    ]

    ro_rows = []
    risk_map = [
        ("ro_gtm_paid_search", "RISK", "GTM", "HIGH"),
        ("ro_retention_smb", "RISK", "Retention", "HIGH"),
        ("ro_pipeline", "RISK", "Pipeline", "MEDIUM"),
        ("ro_cash_h2", "RISK", "Cash", "LOW"),
        ("ro_opp_gtm", "OPP", "GTM", "HIGH"),
        ("ro_opp_expansion", "OPP", "ARR", "HIGH"),
        ("ro_opp_margin", "OPP", "Margin", "MEDIUM"),
        ("ro_opp_cash", "OPP", "Cash", "MEDIUM"),
    ]
    risks = ro.get("risks") or []
    opps = ro.get("opportunities") or []
    for i, (row_id, typ, cat, impact) in enumerate(risk_map):
        src = risks[i] if typ == "RISK" and i < len(risks) else opps[max(0, i - 4)] if typ == "OPP" else {}
        ro_rows.append(
            {
                "row_id": row_id,
                "type": typ,
                "category": cat,
                "impact": impact,
                "data": {
                    "title": src.get("title", ""),
                    "detail": src.get("detail", ""),
                    "action": src.get("action", ""),
                    "pipeline_coverage": arr.get("pipeline_coverage_x", ""),
                    "blended_eff": gtm_block.get("blended_efficiency_x", ""),
                },
            }
        )

    is_rows = []
    for key, row_id in (
        ("revenue", "is_total_revenue"),
        ("gross_profit", "is_gross_profit"),
        ("sm", "is_sm"),
        ("rd", "is_rd"),
        ("ga", "is_ga"),
        ("ebitda", "is_ebitda"),
    ):
        cm = (pl_detail.get("cm") or {}).get(key) or {}
        qtd = (pl_detail.get("qtd") or {}).get(key) or {}
        ytd = (pl_detail.get("ytd") or {}).get(key) or {}
        is_rows.append(
            {
                "row_id": row_id,
                "period": {k: cm.get(k, "") for k in ("actual", "budget", "variance")},
                "qtd": {k: qtd.get(k, "") for k in ("actual", "budget", "variance")},
                "ytd": {k: ytd.get(k, "") for k in ("actual", "budget", "variance")},
            }
        )

    variance_commentary_display = {
        "sheet_title": f"SMPL · Variance Commentary · {_period_label(as_of)}",
        "metric_columns": [
            f"{month} Actual",
            f"{month} Budget",
            f"{month} Var",
            f"{_quarter_label(as_of)} Actual",
            f"{_quarter_label(as_of)} Budget",
            f"{_quarter_label(as_of)} Var",
            "YTD Actual",
            "YTD Budget",
            "YTD Var",
        ],
        "rows": [
            {
                "row_id": r["row_id"],
                "category": r["category"],
                "metric": r["metric"],
                "value_kind": (
                    "headcount"
                    if r["row_id"] == "vc_headcount"
                    else "percent"
                    if r["row_id"] == "vc_gross_margin"
                    else "money"
                ),
                "cm": {
                    "actual": r["period"].get("actual", ""),
                    "budget": r["period"].get("budget", ""),
                    "var": r["period"].get("var", r["period"].get("variance", "")),
                },
                "qtd": {
                    "actual": r["qtd"].get("actual", ""),
                    "budget": r["qtd"].get("budget", ""),
                    "var": r["qtd"].get("var", r["qtd"].get("variance", "")),
                },
                "ytd": {
                    "actual": r["ytd"].get("actual", ""),
                    "budget": r["ytd"].get("budget", ""),
                    "var": r["ytd"].get("var", r["ytd"].get("variance", "")),
                },
            }
            for r in variance_rows
        ],
    }
    tie_out_warnings = verify_variance_commentary_tieout(variance_commentary_display, matrix)
    payload_warnings = validate_deck_payload(deck) + tie_out_warnings

    return {
        "task": "mda_full_package",
        "close_period": as_of,
        "close_period_label": _period_label(as_of),
        "current_quarter": _quarter_label(as_of),
        "ytd_label": _ytd_label(as_of),
        "prior_period_label": _period_label(prior_period(as_of)),
        "commentary_columns": {
            "col_1": "period_vs_budget",
            "col_2": "qtd_vs_budget",
            "col_3": "ytd_vs_budget",
        },
        "sheets": {
            "variance_commentary": _sheet_spec(
                f"Board-facing Variance Commentary tab — {month} Actual/Budget/QTD/YTD. 400 chars per column.",
                400,
                variance_rows,
            ),
            "q2_vs_budget": _sheet_spec(
                "Q2 vs Budget summary blocks — Income Statement, ARR, Cash. 300 chars per column.",
                300,
                [{"row_id": "qvb_income_statement", "category": "INCOME STATEMENT"}],
            ),
            "arr_waterfall": _sheet_spec("ARR waterfall rows. 300 chars per column.", 300, arr_rows),
            "income_statement": _sheet_spec("Income statement GL lines. 200 chars per column.", 200, is_rows),
            "cash_forecast": _sheet_spec(
                "Cash bridge rows from cash_liquidity block. 200 chars per column.",
                200,
                [
                    {
                        "row_id": f"cf_{line}",
                        "period": cash.get("current_month", {}),
                    }
                    for line in ("collections", "payroll", "vendor_payments", "commissions", "capex", "cash_eop_actual")
                ],
            ),
            "cash_flow_statement": _sheet_spec(
                "YTD CFS lines from appendix. 200 chars per column.",
                200,
                [{"row_id": "cfs_cfo", "period": cash.get("current_month", {})}],
            ),
            "gtm_review": _sheet_spec("Marketing channel efficiency. 175 chars per column.", 175, gtm_rows),
            "headcount": _sheet_spec("Headcount by department. 200 chars per column.", 200, []),
            "risks_and_opportunities": {
                "description": "Risks & Opportunities matrix. Description 350 chars, action 200 chars.",
                "max_chars_description": 350,
                "max_chars_action": 200,
                "rows": ro_rows,
            },
        },
        "variance_commentary_display": variance_commentary_display,
        "deck_payload": deck,
        "instructions": (
            "Generate commentary for all sheets. Return a single JSON object with sheet name keys. "
            "For all sheets except risks_and_opportunities, each row_id maps to an object with "
            "period_vs_budget, qtd_vs_budget, ytd_vs_budget strings. For risks_and_opportunities, "
            "each row_id maps to description and recommended_action. Enforce character limits. "
            "Each column must stand alone. No bullets. No line breaks."
        ),
        "payload_meta": {
            "version": "prompt2_v1",
            "schema": "SMPL_API_Prompts_BoardDeck_MDA_v8_prompt2",
            "data_source": "board_platform_metrics.build_deck_payload",
            "data_map": build_deliverable_data_map(matrix),
            "deck_data_map": deck.get("data_map"),
        },
        "payload_warnings": payload_warnings,
        "tie_out_warnings": tie_out_warnings,
    }
