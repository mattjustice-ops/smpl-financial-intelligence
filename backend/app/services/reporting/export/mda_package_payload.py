"""Prompt 2 MD&A package payload — board-platform metrics for variance commentary."""

from __future__ import annotations

import calendar
from decimal import Decimal
from typing import Any

from app.services.commentary.claim_verify import _to_decimal
from app.services.reporting.export.board_metrics_snapshot import build_metrics_snapshot
from app.services.reporting.export.board_period_ytd import rollup_waterfall_metric
from app.services.reporting.export.board_platform_metrics import (
    build_deck_payload,
    build_deliverable_data_map,
    evidence_values_from_mda_payload,
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
from app.services.reporting.export.prompt5_deck import _marketing_by_channel
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


def _var_pct_from_display(actual: str, budget: str) -> str:
    """Variance % derived from the same rounded figures shown in the sheet.

    Commentary quotes a variance percent for every row, but only period_matrix
    metrics carried one. Deriving it from the display strings keeps the published
    percent tied to the actual/budget the reader sees, so it round-trips through
    claim verification instead of reading as an invented number.
    """
    act = _to_decimal(actual)
    bud = _to_decimal(budget)
    if act is None or bud is None or bud == 0:
        return ""
    return fmt_deck_var_pct(act, bud)


def _display_horizon(row: dict[str, Any], horizon: str) -> dict[str, str]:
    """One actual/budget/var/var_pct cell group for variance_commentary_display."""
    blk = row.get(horizon) or {}
    actual = str(blk.get("actual", "") or "")
    budget = str(blk.get("budget", "") or "")
    out = {
        "actual": actual,
        "budget": budget,
        "var": str(blk.get("var", blk.get("variance", "")) or ""),
    }
    var_pct = str(blk.get("var_pct", "") or "") or _var_pct_from_display(actual, budget)
    if var_pct:
        out["var_pct"] = var_pct
    return out


def _horizon_block(row: dict[str, Any], horizon: str) -> dict[str, str]:
    blk = row.get(horizon) or {}
    actual = str(blk.get("actual") or "")
    budget = str(blk.get("budget") or "")
    return {
        "actual": actual,
        "budget": budget,
        "var": str(blk.get("variance") or blk.get("var") or ""),
        "var_pct": str(blk.get("var_pct") or "") or _var_pct_from_display(actual, budget),
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
        actual = str(row.get("actual") or "")
        budget = str(row.get("budget") or "")
        return {
            "actual": actual,
            "budget": budget,
            "var": str(row.get("variance") or row.get("var") or ""),
            "var_pct": _var_pct_from_display(actual, budget),
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

    # The QTD/YTD blocks carry variance already; the current-month block did not,
    # so component commentary computed its own and drifted off the engine value.
    def _arr_period_block(key: str) -> dict[str, str]:
        actual = str(arr.get(key, "") or "")
        budget = str(arr.get(f"{key}_budget", "") or "")
        out = {"actual": actual, "budget": budget}
        act_dec = _to_decimal(actual)
        bud_dec = _to_decimal(budget)
        if act_dec is not None and bud_dec is not None:
            out["variance"] = fmt_deck_money(act_dec - bud_dec)
        var_pct = _var_pct_from_display(actual, budget)
        if var_pct:
            out["var_pct"] = var_pct
        return out

    arr_rows = [
        {
            "row_id": f"arr_{key}",
            "metric": label,
            "period": _arr_period_block(key),
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
            # "5.5x pipeline/spend" carries the ratio in prose, so it never became a
            # numeric evidence value and every cited efficiency figure was stripped.
            "efficiency_x": ch["efficiency_x"],
            "rank": str(i + 1),
        }
        for i, ch in enumerate(channels[:10])
    ]

    # Every cash row used to receive the same aggregate current_month block, so a
    # row asking for payroll commentary was handed the whole-month cash summary and
    # the model supplied its own payroll figures. Each line now carries its own
    # bridge actual/budget, which is what the commentary is asked to explain.
    _cash_bridge_by_label = {
        str(r.get("label") or "").strip().lower(): r
        for r in ((cash.get("bridge_table") or {}).get("rows") or [])
        if isinstance(r, dict)
    }

    def _cash_line_block(label: str) -> dict[str, str]:
        row = _cash_bridge_by_label.get(label.strip().lower()) or {}
        actual = str(row.get("actual") or "")
        budget = str(row.get("budget") or "")
        if not actual and not budget:
            return {"line": label}
        out = {"line": label, "actual": actual, "budget": budget}
        act_dec = _to_decimal(actual)
        bud_dec = _to_decimal(budget)
        if act_dec is not None and bud_dec is not None:
            out["var"] = fmt_deck_money(act_dec - bud_dec)
        var_pct = _var_pct_from_display(actual, budget)
        if var_pct:
            out["var_pct"] = var_pct
        return out

    def _cfo_block() -> dict[str, str]:
        """Cash flow from operations, the line this sheet actually reports."""
        cm = cash.get("current_month") or {}
        actual = str(cm.get("cfo_actual") or "")
        budget = str(cm.get("cfo_budget") or "")
        out = {"line": "Cash flow from operations", "actual": actual, "budget": budget}
        act_dec = _to_decimal(actual)
        bud_dec = _to_decimal(budget)
        if act_dec is not None and bud_dec is not None:
            out["var"] = fmt_deck_money(act_dec - bud_dec)
        var_pct = _var_pct_from_display(actual, budget)
        if var_pct:
            out["var_pct"] = var_pct
        return out

    # Risks & Opportunities is derived from the close, not from a static card list.
    # The seeded cards carried magnitudes that no longer matched the engine, so any
    # figure the model copied off them failed claim verification and the cell was
    # lost. Ranking real budget variances keeps every number citable and makes the
    # matrix reflect the period actually being reported.
    ro_candidates: list[tuple[str, str, str, dict[str, str], bool]] = [
        ("revenue", "Revenue", "Revenue", _pl_horizon("ytd", "revenue"), True),
        ("ebitda", "EBITDA", "P&L", _pl_horizon("ytd", "ebitda"), True),
        ("arr_ending", "Ending ARR", "ARR", _horizon_block(arr_row, "ytd"), True),
        ("net_new_arr", "Net New ARR", "ARR", nn_h["ytd"], True),
        ("gross_margin", "Gross Margin %", "Margin", _horizon_block(gm, "ytd"), True),
        ("cash", "Ending Cash", "Cash", _horizon_block(cash_row, "ytd"), True),
        ("sm_spend", "S&M Spend", "GTM", sm_ytd, False),
        ("churn", "ARR Churn", "Retention", _arr_component_horizons(bundle, "churn")["ytd"], False),
        ("expansion", "ARR Expansion", "ARR", _arr_component_horizons(bundle, "expansion")["ytd"], True),
        (
            "contraction",
            "ARR Contraction",
            "Retention",
            _arr_component_horizons(bundle, "contraction")["ytd"],
            False,
        ),
    ]

    revenue_ytd = _to_decimal(str((_pl_horizon("ytd", "revenue")).get("actual") or "")) or ZERO

    def _impact(var_abs: Decimal) -> str:
        """Severity scaled to YTD revenue so it travels across company sizes."""
        if not revenue_ytd:
            return "MEDIUM"
        share = var_abs / revenue_ytd
        if share >= Decimal("0.02"):
            return "HIGH"
        return "MEDIUM" if share >= Decimal("0.005") else "LOW"

    scored: list[tuple[Decimal, str, dict[str, Any]]] = []
    for key, label, cat, blk, higher_is_better in ro_candidates:
        var_dec = _to_decimal(str(blk.get("var") or ""))
        if var_dec is None or var_dec == 0:
            continue
        favorable = (var_dec > 0) if higher_is_better else (var_dec < 0)
        var_abs = abs(var_dec)
        scored.append(
            (
                var_abs,
                "OPP" if favorable else "RISK",
                {
                    "row_id": f"ro_{'opp' if favorable else 'risk'}_{key}",
                    "type": "OPP" if favorable else "RISK",
                    "category": cat,
                    "impact": _impact(var_abs),
                    "data": {
                        "metric": label,
                        "actual": blk.get("actual", ""),
                        "budget": blk.get("budget", ""),
                        "var": blk.get("var", ""),
                        "var_pct": blk.get("var_pct", ""),
                        "horizon": "YTD",
                        "direction": "favorable" if favorable else "unfavorable",
                    },
                },
            )
        )

    scored.sort(key=lambda t: t[0], reverse=True)
    ro_rows = [row for _, typ, row in scored if typ == "RISK"][:4]
    ro_rows += [row for _, typ, row in scored if typ == "OPP"][:4]

    # Income-statement commentary always reasons in variance percent and percent of
    # revenue. Publishing only actual/budget/variance left the model to divide, and
    # every rounded result it produced missed the engine value and was stripped.
    def _is_block(blk: dict[str, Any], revenue_blk: dict[str, Any]) -> dict[str, str]:
        actual = str(blk.get("actual", "") or "")
        budget = str(blk.get("budget", "") or "")
        out = {
            "actual": actual,
            "budget": budget,
            "variance": str(blk.get("variance", "") or ""),
        }
        var_pct = _var_pct_from_display(actual, budget)
        if var_pct:
            out["var_pct"] = var_pct
        act_dec = _to_decimal(actual)
        rev_dec = _to_decimal(str(revenue_blk.get("actual", "") or ""))
        if act_dec is not None and rev_dec:
            # Already scaled to percent, so suppress the ratio auto-scaling that
            # would otherwise read a genuine 1.2%-of-revenue line as 120%.
            out["pct_of_revenue"] = fmt_deck_pct(
                act_dec / rev_dec * 100, as_percent=False
            )
        return out

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
                "period": _is_block(cm, (pl_detail.get("cm") or {}).get("revenue") or {}),
                "qtd": _is_block(qtd, (pl_detail.get("qtd") or {}).get("revenue") or {}),
                "ytd": _is_block(ytd, (pl_detail.get("ytd") or {}).get("revenue") or {}),
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
                "cm": _display_horizon(r, "period"),
                "qtd": _display_horizon(r, "qtd"),
                "ytd": _display_horizon(r, "ytd"),
            }
            for r in variance_rows
        ],
    }
    # Soft list for payload inspection; Prompt 2 emit path re-runs with fail_closed=True.
    tie_out_warnings = verify_variance_commentary_tieout(variance_commentary_display, matrix)
    payload_warnings = validate_deck_payload(deck) + tie_out_warnings
    sheets = {
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
                {"row_id": f"cf_{line}", "period": _cash_line_block(label)}
                for line, label in (
                    ("collections", "Collections"),
                    ("payroll", "Payroll"),
                    ("vendor_payments", "Vendor payments"),
                    ("commissions", "Commissions"),
                    ("capex", "Capex"),
                    ("cash_eop_actual", "Ending cash"),
                )
            ],
        ),
        "cash_flow_statement": _sheet_spec(
            "YTD CFS lines from appendix. 200 chars per column.",
            200,
            [{"row_id": "cfs_cfo", "period": _cfo_block()}],
        ),
        "gtm_review": _sheet_spec("Marketing channel efficiency. 175 chars per column.", 175, gtm_rows),
        "headcount": _sheet_spec("Headcount by department. 200 chars per column.", 200, []),
        "risks_and_opportunities": {
            "description": "Risks & Opportunities matrix. Description 350 chars, action 200 chars.",
            "max_chars_description": 350,
            "max_chars_action": 200,
            "rows": ro_rows,
        },
    }

    # Every sheet the model must write commentary for has to be citable. Scoping
    # this to the variance_commentary rows left GTM, headcount and GL figures with
    # no _sources key, so correct sentences quoting them were stripped as uncited.
    evidence_values_map = {
        k: str(v)
        for k, v in evidence_values_from_mda_payload(
            {
                "variance_commentary_display": variance_commentary_display,
                "deck_payload": deck,
                "sheets": sheets,
            }
        ).items()
    }
    from app.services.commentary.claim_verify import attach_sources_to_values

    evidence_sources = attach_sources_to_values(
        evidence_values_map,
        period_label=_period_label(as_of),
        org_id=None,
        loaded_at=None,
        is_final=None,
    )
    evidence_package = {
        "period_label": _period_label(as_of),
        "freeze_id": None,
        "tolerance_actuals": "1.00",
        "org_id": None,
        "loaded_at": None,
        "is_final": None,
        "variance_commentary_display": variance_commentary_display,
        "period_matrix": matrix,
        "values": evidence_values_map,
        "_sources": evidence_sources,
    }

    from app.services.commentary.attribution_verify import (
        build_attribution_package_from_mda_payload,
    )

    attribution_package = build_attribution_package_from_mda_payload(
        {
            "close_period": as_of,
            "close_period_label": _period_label(as_of),
            "deck_payload": deck,
            "variance_commentary_display": variance_commentary_display,
            "arr_analysis": arr,
            "cash_liquidity": cash,
            "sheets": sheets,
        }
    )

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
        "sheets": sheets,
        "variance_commentary_display": variance_commentary_display,
        "deck_payload": deck,
        "evidence_package": evidence_package,
        "attribution_package": attribution_package,
        "instructions": (
            "Generate commentary for all sheets. Return a single JSON object with sheet name keys. "
            "For all sheets except risks_and_opportunities, each row_id maps to an object with "
            "period_vs_budget, qtd_vs_budget, ytd_vs_budget strings. For risks_and_opportunities, "
            "each row_id maps to description and recommended_action. Enforce character limits. "
            "risks_and_opportunities rows are engine-ranked budget variances: write the "
            "description from that row's own metric, actual, budget, var and var_pct, and "
            "state the recommended action for that variance. Do not introduce a risk theme "
            "the row's figures do not support. "
            "Each column must stand alone. No bullets. No line breaks. "
            "State only dollar/percent figures present in evidence_package.values / display rows. "
            "Cite each material number with a _sources key, table.column, formula_id, or path "
            "(e.g. '$110,000 (mrr_waterfall.ending_mrr)'). "
            "Causal drivers must appear in attribution_package.allowed_drivers; "
            "multi-driver 'and'/comma lists require every named driver allowlisted; "
            "if that list is empty, restate metrics without inventing causes."
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
