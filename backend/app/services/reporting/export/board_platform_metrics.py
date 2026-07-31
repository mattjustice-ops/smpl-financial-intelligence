"""Single source of truth for board platform + deck export metrics.

All CM / QTD / YTD / FY Actual, Budget, and Forecast values use the same
rollup helpers as the board UI (`board_period_ytd`, `board_visuals`).
"""

from __future__ import annotations

import calendar
import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, Mapping

from app.services.reporting.export.board_chart_service import _wf
from app.services.reporting.export.board_metrics_snapshot import build_metrics_snapshot
from app.services.reporting.export.board_period_ytd import (
    PeriodRollup,
    rollup_cash,
    rollup_ebitda,
    rollup_ending_arr,
    rollup_pipeline_created,
    rollup_revenue,
)
from app.services.reporting.export.board_slide_commentary_payload import (
    fmt_deck_money,
    fmt_deck_pct,
    fmt_deck_var,
    fmt_deck_var_pct,
)
from app.services.reporting.export.effective_periods import export_fiscal_periods
from app.services.reporting.export.is_line_resolver import ending_cash_at, fs_sum_periods
from app.services.reporting.export.period_views import qtd_periods, ytd_periods
from app.services.reporting.export.reporting_period_engine import build_period_context
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.period_utils import prior_period, to_period
from app.services.reporting.three_statement_payload import CFS_FIELD_SPECS

ZERO = Decimal("0")

Horizon = Literal["cm", "qtd", "ytd", "fy_outlook"]
Scenario = Literal["actual", "budget", "forecast"]

# CFS lines to sum for YTD (flows). Stock lines handled separately.
_CFS_YTD_SUM_KEYS = (
    "net_income",
    "da",
    "sbc",
    "chg_ar",
    "chg_dr",
    "chg_ap",
    "chg_prepaids",
    "cfo",
    "capex",
    "cfi",
    "cff",
    "net_change",
)


@dataclass(frozen=True)
class MetricSource:
    """Documents warehouse provenance for audit / tie-out."""

    metric_id: str
    table: str
    field_or_line: str
    scenario: str
    horizon: str
    rollup_fn: str


def gross_margin_pct(bundle: ReportingBundle, period: str, scenario: str) -> Decimal | None:
    """Gross margin % = Gross Profit / Revenue (matches management P&L / board dashboard)."""
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if not fs:
        return None
    gp = rev = ZERO
    for row in fs.income_statement.rows:
        if str(row.period)[:7] != period or row.scenario != scenario:
            continue
        li = row.line_item.lower()
        if "gross profit" in li:
            gp = row.amount
        elif ("gross margin" in li or li == "gm") and gp == ZERO:
            # Some feeds store GM as a ratio (0.70) or percent (70)
            if row.amount <= Decimal("1.5"):
                return row.amount * 100
            return row.amount
        if "revenue" in li and "deferred" not in li and "cost" not in li:
            rev = row.amount
    if rev and gp:
        return (gp / rev) * 100
    return None


def gross_margin_pct_horizon(
    bundle: ReportingBundle,
    periods: list[str],
    scenario: str,
) -> Decimal | None:
    """Gross margin % for a horizon = sum(GP) / sum(Revenue) when multiple months."""
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if not fs or not periods:
        return None
    gp = rev = ZERO
    wanted = {to_period(p) for p in periods}
    for row in fs.income_statement.rows:
        p = to_period(str(row.period)[:7])
        if p not in wanted or row.scenario != scenario:
            continue
        li = row.line_item.lower()
        if "gross profit" in li:
            gp += row.amount
        elif "revenue" in li and "deferred" not in li and "cost" not in li:
            rev += row.amount
    if rev:
        return (gp / rev) * 100
    return None


def headcount_totals(bundle: ReportingBundle, period: str, scenario: str) -> tuple[int, int]:
    hc = 0
    open_roles = 0
    target = to_period(period)
    for row in bundle.headcount:
        if to_period(str(row.period)) != target or row.scenario != scenario:
            continue
        hc += int(Decimal(str(row.headcount or 0)))
        open_roles += int(Decimal(str(row.open_roles or 0)))
    return hc, open_roles


def ending_arr_at_period(bundle: ReportingBundle, period: str, scenario: str) -> Decimal:
    for wtype in ("ending", "ending_arr"):
        val = _wf(bundle, "arr", wtype, period, scenario)
        if val:
            return val
    return ZERO


def _cash_wf_amount(
    bundle: ReportingBundle,
    period: str,
    scenario: str,
    *wtypes: str,
    abs_out: bool = False,
) -> Decimal:
    """Resolve cash bridge line from comparison waterfalls (alias-aware)."""
    for wtype in wtypes:
        val = _wf(bundle, "cash_flow", wtype, period, scenario)
        if val:
            return abs(val) if abs_out else val
    return ZERO


def _cash_bridge_table_amount(
    cash_bridge_data: dict[str, Any] | None,
    scenario: str,
    period: str,
    field: str,
    *,
    abs_out: bool = False,
) -> Decimal | None:
    if not cash_bridge_data:
        return None
    row = (cash_bridge_data.get(scenario) or {}).get(period) or {}
    raw = row.get(field)
    if raw is None:
        return None
    val = Decimal(str(raw))
    return abs(val) if abs_out else val


def _bs_cash_at(bundle: ReportingBundle, period: str, scenario: str) -> Decimal | None:
    val = ending_cash_at(bundle, period, scenario)
    return val if val else None


def _fy_outlook_gross_margin_pct(bundle: ReportingBundle) -> Decimal | None:
    """FY gross margin = sum(GP) / sum(Revenue) using Actual closed + Forecast open months."""
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if not fs:
        return None
    as_of = bundle.as_of_period
    periods = export_fiscal_periods(bundle.start_period, bundle.end_period)
    gp = rev = ZERO
    wanted = {to_period(p) for p in periods}
    for row in fs.income_statement.rows:
        p = to_period(str(row.period)[:7])
        if p not in wanted:
            continue
        scen = "Actual" if p <= as_of else "Forecast"
        if row.scenario != scen:
            continue
        li = row.line_item.lower()
        if "gross profit" in li:
            gp += row.amount
        elif "revenue" in li and "deferred" not in li and "cost" not in li:
            rev += row.amount
    if rev:
        return (gp / rev) * 100
    return None


def _fy_budget_gross_margin_pct(bundle: ReportingBundle) -> Decimal | None:
    periods = export_fiscal_periods(bundle.start_period, bundle.end_period)
    return gross_margin_pct_horizon(bundle, periods, "Budget")


def _budget_qtd_flow(bundle: ReportingBundle, line_needle: str) -> Decimal:
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if not fs:
        return ZERO
    as_of = bundle.as_of_period
    periods = qtd_periods(as_of)
    return fs_sum_periods(bundle, periods, "Budget", line_needle)


def _budget_qtd_waterfall(
    bundle: ReportingBundle,
    key: str,
    wtype: str,
) -> Decimal:
    as_of = bundle.as_of_period
    total = ZERO
    for p in qtd_periods(as_of):
        total += _wf(bundle, key, wtype, p, "Budget")
    return total


def _rollup_value(
    rollup: PeriodRollup,
    horizon: Horizon,
    kind: Scenario,
    *,
    flow: bool = False,
    bundle: ReportingBundle | None = None,
    wf_key: str | None = None,
    wf_type: str | None = None,
    fs_needle: str | None = None,
) -> Decimal:
    if kind == "budget":
        if horizon == "qtd":
            if flow and bundle and fs_needle:
                return _budget_qtd_flow(bundle, fs_needle)
            if flow and bundle and wf_key and wf_type:
                return _budget_qtd_waterfall(bundle, wf_key, wf_type)
            return rollup.budget_cm
        budget_map = {
            "cm": rollup.budget_cm,
            "qtd": rollup.budget_cm,
            "ytd": rollup.budget_ytd,
            "fy_outlook": rollup.budget_fy,
        }
        return budget_map[horizon]
    actual_map = {
        "cm": rollup.current_month,
        "qtd": rollup.qtd,
        "ytd": rollup.ytd,
        "fy_outlook": rollup.fy_outlook,
    }
    return actual_map[horizon]


def _period_label(period: str) -> str:
    return f"{calendar.month_name[int(period[5:7])]} {period[:4]}"


def _quarter_label(period: str) -> str:
    month = int(period.split("-")[1])
    return f"Q{(month - 1) // 3 + 1}"


def _ytd_label(period: str) -> str:
    month_abbr = calendar.month_abbr[int(period[5:7])]
    return f"Jan–{month_abbr} {period[:4]}"


def build_period_matrix(bundle: ReportingBundle) -> dict[str, Any]:
    """Same horizons as board `executive_period_table` plus Gross Margin % row."""
    as_of = bundle.as_of_period
    cur = bundle.currency
    qtd_p = qtd_periods(as_of)
    ytd_p = ytd_periods(as_of)

    arr = rollup_ending_arr(bundle)
    rev = rollup_revenue(bundle)
    ebitda = rollup_ebitda(bundle)
    cash = rollup_cash(bundle)
    pipe = rollup_pipeline_created(bundle)

    def row(
        metric: str,
        rollup: PeriodRollup,
        *,
        is_pct: bool = False,
        flow: bool = False,
        wf_key: str | None = None,
        wf_type: str | None = None,
        fs_needle: str | None = None,
    ) -> dict[str, Any]:
        horizons = ("cm", "qtd", "ytd", "fy_outlook")
        out: dict[str, Any] = {"metric": metric, "currency": cur}
        kw = dict(flow=flow, bundle=bundle, wf_key=wf_key, wf_type=wf_type, fs_needle=fs_needle)
        for h in horizons:
            act = _rollup_value(rollup, h, "actual", **kw)  # type: ignore[arg-type]
            bud = _rollup_value(rollup, h, "budget", **kw)  # type: ignore[arg-type]
            if is_pct:
                out[h] = {
                    "actual": fmt_deck_pct(act, as_percent=False) if act else "n/a",
                    "budget": fmt_deck_pct(bud, as_percent=False) if bud else "n/a",
                }
            else:
                out[h] = {
                    "actual": fmt_deck_money(act),
                    "budget": fmt_deck_money(bud),
                    "variance": fmt_deck_var(act, bud),
                    "var_pct": fmt_deck_var_pct(act, bud),
                }
        out["ytd_vs_budget"] = fmt_deck_var_pct(rollup.ytd, rollup.budget_ytd) if not is_pct else "n/a"
        return out

    gm_row: dict[str, Any] = {"metric": "Gross Margin %", "currency": cur}
    gm_cm_a = gross_margin_pct(bundle, as_of, "Actual")
    gm_cm_b = gross_margin_pct(bundle, as_of, "Budget")
    gm_qtd_a = gross_margin_pct_horizon(bundle, qtd_p, "Actual")
    gm_qtd_b = gross_margin_pct_horizon(bundle, qtd_p, "Budget")
    gm_ytd_a = gross_margin_pct_horizon(bundle, ytd_p, "Actual")
    gm_ytd_b = gross_margin_pct_horizon(bundle, ytd_p, "Budget")
    for h, a, b in (
        ("cm", gm_cm_a, gm_cm_b),
        ("qtd", gm_qtd_a, gm_qtd_b),
        ("ytd", gm_ytd_a, gm_ytd_b),
        ("fy_outlook", gm_ytd_a, gm_ytd_b),
    ):
        gm_row[h] = {
            "actual": fmt_deck_pct(a, as_percent=False) if a is not None else "n/a",
            "budget": fmt_deck_pct(b, as_percent=False) if b is not None else "n/a",
        }

    return {
        "headers": ["Metric", "CM", "QTD", "YTD", "FY Outlook", "YTD vs Budget"],
        "horizon_labels": {
            "cm": _period_label(as_of),
            "qtd": _quarter_label(as_of),
            "ytd": _ytd_label(as_of),
            "fy_outlook": f"FY {as_of[:4]} Outlook",
        },
        "rows": [
            row("Ending ARR", arr),
            row("Revenue", rev, flow=True, fs_needle="revenue"),
            row("EBITDA", ebitda, flow=True, fs_needle="ebitda"),
            gm_row,
            row("Ending Cash", cash),
            row("Pipeline Created (flow)", pipe, flow=True, wf_key="pipeline", wf_type="pipeline_created"),
        ],
        "sources": [
            MetricSource("ending_arr", "comparison_waterfalls", "arr.ending_arr", "Actual/Budget", "CM/QTD/YTD/FY", "rollup_ending_arr").__dict__,
            MetricSource("revenue", "income_statement", "Revenue", "Actual/Budget", "CM/QTD/YTD/FY", "rollup_revenue").__dict__,
            MetricSource("gross_margin_pct", "income_statement", "Gross Margin / Revenue", "Actual/Budget", "CM/QTD/YTD", "gross_margin_pct").__dict__,
            MetricSource("ending_cash", "comparison_waterfalls", "cash_flow.ending_cash", "Actual/Budget", "CM/QTD/YTD/FY", "rollup_cash").__dict__,
        ],
    }


def _sum_cfs_from_fs(
    bundle: ReportingBundle,
    periods: list[str],
    scenario: str,
) -> dict[str, Decimal]:
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    totals: dict[str, Decimal] = {k: ZERO for k in _CFS_YTD_SUM_KEYS}
    if not fs:
        return totals

    line_to_key: dict[str, str] = {}
    for key, _aliases in CFS_FIELD_SPECS:
        for alias in _aliases:
            line_to_key[alias.lower().replace("_", " ")] = key
    # Map normalized statement line names
    for mapping in (
        ("net income", "net_income"),
        ("depreciation and amortization", "da"),
        ("stock-based compensation", "sbc"),
        ("change in accounts receivable", "chg_ar"),
        ("change in deferred revenue", "chg_dr"),
        ("change in accounts payable", "chg_ap"),
        ("change in prepaids", "chg_prepaids"),
        ("net cash provided by operating activities", "cfo"),
        ("capital expenditures", "capex"),
        ("net cash used in investing activities", "cfi"),
        ("net cash provided by financing activities", "cff"),
        ("net change in cash", "net_change"),
    ):
        line_to_key[mapping[0]] = mapping[1]

    wanted = {to_period(p) for p in periods}
    for row in fs.cash_flow.rows:
        p = to_period(str(row.period)[:7])
        if p not in wanted or row.scenario != scenario:
            continue
        li = row.line_item.lower()
        key = line_to_key.get(li)
        if not key and "operating activit" in li:
            key = "cfo"
        if key and key in totals:
            totals[key] += row.amount
    return totals


def _ytd_beginning_cash(
    bundle: ReportingBundle,
    ts_data: dict[str, Any] | None,
    ytd_p: list[str],
    scenario: str,
) -> Decimal | None:
    if not ytd_p:
        return None
    first = ytd_p[0]
    if ts_data and scenario in ts_data:
        cfs = (ts_data[scenario].get("cfs") or {})
        beg = cfs.get(first, {}).get("beginning_cash")
        if beg is not None:
            return Decimal(str(beg))
        bs = (ts_data[scenario].get("bs") or {})
        prior = prior_period(first)
        for key in (prior, first):
            if key in bs and bs[key].get("cash") is not None:
                return Decimal(str(bs[key]["cash"]))
    beg = _cfs_point_from_fs(bundle, first, scenario, "beginning cash")
    if beg:
        return beg
    prior = prior_period(first)
    bs_cash = _bs_cash_at(bundle, prior, scenario) or _bs_cash_at(bundle, first, scenario)
    if bs_cash is not None:
        return bs_cash
    return _cash_wf_amount(bundle, first, scenario, "beginning_cash", "beginning")


def _fmt_cfs_line(val: Decimal | None, *, allow_zero: bool = False) -> str:
    if val is None:
        return "n/a"
    if not allow_zero and val == ZERO:
        return "n/a"
    return fmt_deck_money(val)


def _cfs_point_from_fs(bundle: ReportingBundle, period: str, scenario: str, needle: str) -> Decimal:
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if not fs:
        return ZERO
    n = needle.lower()
    for row in fs.cash_flow.rows:
        if str(row.period)[:7] != period or row.scenario != scenario:
            continue
        if n in row.line_item.lower():
            return row.amount
    return ZERO


def _sum_cfs_from_ts(
    ts_data: dict[str, Any],
    periods: list[str],
    scenario: str,
) -> dict[str, float | None]:
    block = ts_data.get(scenario) or {}
    cfs_by_period = block.get("cfs") or {}
    totals: dict[str, float] = {k: 0.0 for k in _CFS_YTD_SUM_KEYS}
    for period in periods:
        row = cfs_by_period.get(period) or {}
        for key in _CFS_YTD_SUM_KEYS:
            val = row.get(key)
            if val not in (None, ""):
                totals[key] += float(val)
    return totals


def build_ytd_cash_flow_statement(
    bundle: ReportingBundle,
    ts_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """YTD indirect CFS — Actual + Budget (matches board 3-statement tab)."""
    as_of = bundle.as_of_period
    ytd_p = ytd_periods(as_of)
    cur = bundle.currency

    def pack_scenario(scenario: str) -> dict[str, str]:
        if ts_data and scenario in ts_data:
            totals = _sum_cfs_from_ts(ts_data, ytd_p, scenario)
            end = (ts_data[scenario].get("cfs") or {}).get(as_of, {}).get("ending_cash")
        else:
            dec = _sum_cfs_from_fs(bundle, ytd_p, scenario)
            totals = {k: float(v) for k, v in dec.items()}
            end = _cfs_point_from_fs(bundle, as_of, scenario, "ending cash")

        beg_val = _ytd_beginning_cash(bundle, ts_data, ytd_p, scenario)
        end_val = Decimal(str(end)) if end is not None else None
        if end_val is None and end:
            end_val = Decimal(str(end))

        def fmt(key: str) -> str:
            val = totals.get(key)
            if val is None or val == 0:
                return "n/a"
            return fmt_deck_money(Decimal(str(val)))

        return {
            "beginning_cash": _fmt_cfs_line(beg_val, allow_zero=True),
            "net_income": fmt("net_income"),
            "depreciation_amortization": fmt("da"),
            "stock_based_compensation": fmt("sbc"),
            "change_in_ar": fmt("chg_ar"),
            "change_in_deferred_revenue": fmt("chg_dr"),
            "change_in_ap": fmt("chg_ap"),
            "change_in_prepaids": fmt("chg_prepaids"),
            "cfo": fmt("cfo"),
            "capex": fmt("capex"),
            "cfi": fmt("cfi"),
            "cff": fmt("cff"),
            "net_change_in_cash": fmt("net_change"),
            "ending_cash": _fmt_cfs_line(end_val, allow_zero=True),
            "ytd_periods": ytd_p,
            "currency": cur,
        }

    return {
        "label": f"YTD Cash Flow Statement ({_ytd_label(as_of)})",
        "actual": pack_scenario("Actual"),
        "budget": pack_scenario("Budget"),
        "source": "build_ts_data.cfs" if ts_data else "financial_statements.cash_flow",
    }


def build_cash_liquidity_block(
    bundle: ReportingBundle,
    cash_bridge_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cash bridge + ending cash Actual/Budget for CM and YTD."""
    as_of = bundle.as_of_period
    cash_r = rollup_cash(bundle)
    cur = bundle.currency
    floor = Decimal("10000000")

    _BRIDGE_LINES: tuple[tuple[str, str, tuple[str, ...], str | None, bool], ...] = (
        ("Beginning cash", "beginning_cash", ("beginning_cash", "beginning"), None, False),
        ("Collections", "collections", ("cash_collections", "collections"), None, False),
        ("Payroll", "payroll", ("payroll_cash_out", "payroll"), "payroll", True),
        ("Vendor payments", "vendor_payments", ("vendor_cash_out", "vendor_cash_out_n30", "vendor_payments", "vendor"), "vendor", True),
        ("Commissions", "commissions", ("commission_cash_out", "commissions", "commission"), "commission", True),
        ("Capex", "capex", ("capex",), "capex", True),
        ("Ending cash", "ending_cash", ("ending_cash", "ending"), "ending_cash", False),
    )

    prior = prior_period(as_of)

    def line_amount(
        bridge_field: str | None,
        wf_types: tuple[str, ...],
        scenario: str,
        *,
        abs_out: bool,
        period: str | None = None,
    ) -> Decimal:
        p = period or as_of
        if bridge_field == "beginning_cash":
            val = ending_cash_at(bundle, prior if p == as_of else prior_period(p), scenario)
            return val
        if bridge_field == "ending_cash":
            return ending_cash_at(bundle, p, scenario)
        if bridge_field:
            table_val = _cash_bridge_table_amount(cash_bridge_data, scenario, p, bridge_field, abs_out=abs_out)
            if table_val is not None and table_val != ZERO:
                return table_val
        return _cash_wf_amount(bundle, p, scenario, *wf_types, abs_out=abs_out)

    bridge_rows: list[dict[str, str]] = []
    for label, _key, wf_types, bridge_field, abs_out in _BRIDGE_LINES:
        actual = line_amount(bridge_field, wf_types, "Actual", abs_out=abs_out)
        budget = line_amount(bridge_field, wf_types, "Budget", abs_out=abs_out)
        bridge_rows.append(
            {
                "label": label,
                "actual": fmt_deck_money(actual) if actual else "—",
                "budget": fmt_deck_money(budget) if budget else "—",
            }
        )

    cfo_a = _cash_wf_amount(bundle, as_of, "Actual", "cfo")
    cfo_b = _cash_wf_amount(bundle, as_of, "Budget", "cfo")
    cash_bud_cm = line_amount("ending_cash", ("ending_cash", "ending"), "Budget", abs_out=False)

    ytd_p = ytd_periods(as_of)
    coll_ytd = ZERO
    for p in ytd_p:
        coll_ytd += _cash_wf_amount(bundle, p, "Actual", "cash_collections", "collections")

    return {
        "current_month": {
            "cash_bop": bridge_rows[0]["actual"] if bridge_rows else "—",
            "collections": bridge_rows[1]["actual"] if len(bridge_rows) > 1 else "—",
            "payroll": bridge_rows[2]["actual"] if len(bridge_rows) > 2 else "—",
            "vendor_payments": bridge_rows[3]["actual"] if len(bridge_rows) > 3 else "—",
            "commissions": bridge_rows[4]["actual"] if len(bridge_rows) > 4 else "—",
            "capex": bridge_rows[5]["actual"] if len(bridge_rows) > 5 else "—",
            "cash_eop_actual": bridge_rows[-1]["actual"] if bridge_rows else fmt_deck_money(cash_r.current_month),
            "cash_eop_budget": cash_bud_cm and fmt_deck_money(cash_bud_cm) or bridge_rows[-1]["budget"],
            "cfo_actual": fmt_deck_money(cfo_a) if cfo_a else "—",
            "cfo_budget": fmt_deck_money(cfo_b) if cfo_b else "—",
            "cash_headroom_vs_floor": fmt_deck_money(cash_r.current_month - floor),
            "cash_floor": fmt_deck_money(floor),
        },
        "bridge_table": {
            "columns": ["Line Item", "Actual", "Budget"],
            "rows": bridge_rows,
        },
        "ytd": {
            "collections": fmt_deck_money(coll_ytd),
            "cash_eop_actual": fmt_deck_money(cash_r.ytd),
            "cash_eop_budget": fmt_deck_money(cash_r.budget_fy),
        },
        "currency": cur,
    }


def build_fy_outlook_block(bundle: ReportingBundle) -> dict[str, Any]:
    """FY outlook — EoY ARR is Dec point-in-time, not sum of monthly endings."""
    as_of = bundle.as_of_period
    year = as_of[:4]
    fiscal_end = to_period(bundle.end_period) if bundle.end_period else f"{year}-12"

    arr = rollup_ending_arr(bundle)
    rev = rollup_revenue(bundle)
    ebitda = rollup_ebitda(bundle)
    cash = rollup_cash(bundle)

    hc_actual, open_actual = headcount_totals(bundle, as_of, "Actual")
    hc_budget, open_budget = headcount_totals(bundle, fiscal_end, "Budget")
    hc_fy_forecast, _ = headcount_totals(bundle, fiscal_end, "Forecast")

    arr_eoy_actual = ending_arr_at_period(bundle, fiscal_end, "Actual") or arr.fy_outlook
    arr_eoy_budget = ending_arr_at_period(bundle, fiscal_end, "Budget")
    arr_eoy_forecast = ending_arr_at_period(bundle, fiscal_end, "Forecast") or arr.fy_outlook
    cash_eoy_outlook = (
        _cash_wf_amount(bundle, fiscal_end, "Actual", "ending_cash", "ending")
        or _cash_wf_amount(bundle, fiscal_end, "Forecast", "ending_cash", "ending")
        or cash.fy_outlook
    )
    cash_eoy_budget = _cash_wf_amount(bundle, fiscal_end, "Budget", "ending_cash", "ending") or cash.budget_fy
    gm_outlook = _fy_outlook_gross_margin_pct(bundle)
    gm_budget = _fy_budget_gross_margin_pct(bundle)

    summary_table = [
        {
            "metric": "Ending ARR (Dec EoY)",
            "outlook": fmt_deck_money(arr_eoy_actual),
            "budget": fmt_deck_money(arr_eoy_budget),
            "note": "Point-in-time Dec — never sum monthly ARR",
        },
        {
            "metric": "FY Revenue",
            "outlook": fmt_deck_money(rev.fy_outlook),
            "budget": fmt_deck_money(rev.budget_fy),
            "note": "Outlook = Actual closed months + Forecast open months",
        },
        {
            "metric": "FY Gross Margin %",
            "outlook": fmt_deck_pct(gm_outlook / 100) if gm_outlook is not None else "n/a",
            "budget": fmt_deck_pct(gm_budget / 100) if gm_budget is not None else "n/a",
            "note": "Outlook and budget GM% are computed independently — do not copy the same value",
        },
        {
            "metric": "FY EBITDA",
            "outlook": fmt_deck_money(ebitda.fy_outlook),
            "budget": fmt_deck_money(ebitda.budget_fy),
            "note": "",
        },
        {
            "metric": "Ending Cash (Dec EoY)",
            "outlook": fmt_deck_money(cash_eoy_outlook),
            "budget": fmt_deck_money(cash_eoy_budget),
            "note": "Point-in-time Dec ending cash",
        },
    ]

    return {
        "fy_year": year,
        "fiscal_end_period": fiscal_end,
        "arr_eoy": {
            "actual_or_outlook": fmt_deck_money(arr_eoy_actual),
            "budget": fmt_deck_money(arr_eoy_budget),
            "forecast": fmt_deck_money(arr_eoy_forecast),
            "source": f"comparison_waterfalls.arr.ending_arr @ {fiscal_end}",
        },
        "revenue_fy": {
            "outlook": fmt_deck_money(rev.fy_outlook),
            "budget": fmt_deck_money(rev.budget_fy),
        },
        "gross_margin_fy": {
            "outlook": fmt_deck_pct(gm_outlook / 100) if gm_outlook is not None else "n/a",
            "budget": fmt_deck_pct(gm_budget / 100) if gm_budget is not None else "n/a",
        },
        "ebitda_fy": {
            "outlook": fmt_deck_money(ebitda.fy_outlook),
            "budget": fmt_deck_money(ebitda.budget_fy),
        },
        "cash_eoy": {
            "outlook": fmt_deck_money(cash_eoy_outlook),
            "budget": fmt_deck_money(cash_eoy_budget),
        },
        "summary_table": summary_table,
        "headcount": {
            "current_month_actual": hc_actual,
            "eoy_budget": hc_budget,
            "eoy_forecast": hc_fy_forecast,
            "open_reqs_current": open_actual,
            "format": "integer_headcount_not_dollars",
        },
    }



def _waterfall_display_m(value_m: float, *, is_total: bool) -> str:
    if is_total:
        return f"${abs(value_m):.2f}M"
    sign = "+" if value_m >= 0 else "-"
    return f"{sign}${abs(value_m):.2f}M"


def _compute_waterfall_shape_bars(
    *,
    kinds: list[str],
    offsets_m: list[float],
    heights_m: list[float],
    bar_colors: list[str],
    steps: list[dict[str, Any]],
    y_min: float,
    y_max: float,
    chart_x: float = 0.35,
    chart_y: float = 1.05,
    chart_w: float = 6.6,
    chart_h: float = 4.0,
) -> list[dict[str, Any]]:
    """Pre-computed bar rectangles for PptxGenJS addShape — avoids corrupt stacked charts."""
    n = len(kinds)
    bar_w = chart_w / n * 0.58
    step_w = chart_w / n

    def y_in(val_m: float) -> float:
        span = y_max - y_min
        ratio = (val_m - y_min) / span if span else 0
        return chart_y + chart_h - ratio * chart_h

    bars: list[dict[str, Any]] = []
    for i, kind in enumerate(kinds):
        bx = chart_x + i * step_w + (step_w - bar_w) / 2
        if kind == "total":
            y_bot_m, y_top_m = y_min, heights_m[i]
            label_pos = "above"
        elif kind == "increase":
            y_bot_m = offsets_m[i]
            y_top_m = offsets_m[i] + heights_m[i]
            label_pos = "above"
        else:
            y_bot_m = offsets_m[i]
            y_top_m = offsets_m[i] - heights_m[i]
            label_pos = "below"

        y_top = y_in(y_top_m)
        y_bot = y_in(y_bot_m)
        bars.append(
            {
                "x": round(bx, 3),
                "y": round(min(y_top, y_bot), 3),
                "w": round(bar_w, 3),
                "h": round(max(abs(y_bot - y_top), 0.05), 3),
                "color": bar_colors[i],
                "label": steps[i]["display"],
                "label_position": label_pos,
                "category": steps[i]["label"],
            }
        )
    return bars


def build_arr_waterfall_chart(bundle: ReportingBundle) -> dict[str, Any]:
    """Actual-only ARR waterfall — same structure as board platform ARR tab (boardWaterfallMonthM)."""
    as_of = bundle.as_of_period
    prior = prior_period(as_of)
    arr_prior = ending_arr_at_period(bundle, prior, "Actual")
    arr_act = ending_arr_at_period(bundle, as_of, "Actual")

    def comp(wtype: str) -> Decimal:
        for key in (wtype, f"{wtype}_arr"):
            val = _wf(bundle, "arr", key, as_of, "Actual")
            if val:
                return val
        return ZERO

    def to_m(val: Decimal) -> float:
        return round(float(val) / 1_000_000, 4)

    bop_m = to_m(arr_prior)
    nb_m = to_m(abs(comp("new_business")))
    exp_m = to_m(abs(comp("expansion")))
    react_m = to_m(abs(comp("reactivation")))
    con_m = -to_m(abs(comp("contraction")))
    churn_m = -to_m(abs(comp("churn")))

    after_nb = bop_m + nb_m
    after_exp = after_nb + exp_m
    after_react = after_exp + react_m
    after_con = after_react + con_m
    after_churn = after_con + churn_m

    labels = [
        "Begin ARR",
        "New Business",
        "Expansion",
        "Reactivation",
        "Contraction",
        "Churn",
        "End ARR",
    ]
    kinds = ["total", "increase", "increase", "increase", "decrease", "decrease", "total"]
    signed_m = [bop_m, nb_m, exp_m, react_m, con_m, churn_m, after_churn]
    offsets_m = [0, bop_m, after_nb, after_exp, after_con, after_churn, 0]
    heights_m = [bop_m, nb_m, exp_m, react_m, abs(con_m), abs(churn_m), after_churn]

    color_map = {
        "total": "00d4aa",
        "increase": "166534",
        "decrease": "991b1b",
    }
    bar_colors = [color_map[kind] for kind in kinds]

    steps = [
        {
            "label": label,
            "kind": kind,
            "value_m": signed_m[i],
            "display": _waterfall_display_m(signed_m[i], is_total=kind == "total"),
            "offset_m": offsets_m[i],
            "height_m": heights_m[i],
            "bar_color": bar_colors[i],
        }
        for i, (label, kind) in enumerate(zip(labels, kinds))
    ]

    month_label = f"{calendar.month_name[int(as_of[5:7])]} {as_of[:4]}"
    y_min = math.floor(min(bop_m, after_churn) * 0.97)
    y_max = math.ceil(max(bop_m, after_churn) * 1.02)
    chart_area = {"x": 0.35, "y": 1.05, "w": 6.6, "h": 4.0}
    shape_bars = _compute_waterfall_shape_bars(
        kinds=kinds,
        offsets_m=[round(v, 2) for v in offsets_m],
        heights_m=[round(v, 2) for v in heights_m],
        bar_colors=bar_colors,
        steps=steps,
        y_min=y_min,
        y_max=y_max,
        chart_x=chart_area["x"],
        chart_y=chart_area["y"],
        chart_w=chart_area["w"],
        chart_h=chart_area["h"],
    )

    return {
        "title": f"ARR waterfall — {month_label}",
        "subtitle": "Begin ARR → components → Ending ARR ($M)",
        "scenario": "Actual",
        "labels": labels,
        "steps": steps,
        "offsets_m": [round(v, 2) for v in offsets_m],
        "heights_m": [round(v, 2) for v in heights_m],
        "signed_m": [round(v, 2) for v in signed_m],
        "bar_colors": bar_colors,
        "shape_bars": shape_bars,
        "chart_area": chart_area,
        "colors": {
            "total": color_map["total"],
            "increase": color_map["increase"],
            "decrease": color_map["decrease"],
        },
        "y_axis": {
            "min_m": y_min,
            "max_m": y_max,
            "tick_format": "$0M",
        },
        "label_decimals": 2,
        "render": "shape_rectangles",
        "note": (
            "MANDATORY: draw slide 3 waterfall with slide.addShape rectangles from shape_bars "
            "(one rect + one text label per bar). DO NOT use addChart on slide 3 — stacked charts "
            "corrupt the PPTX. Actuals only — never Budget in a waterfall."
        ),
    }


def build_arr_bridge_block(bundle: ReportingBundle) -> dict[str, Any]:
    as_of = bundle.as_of_period
    prior = prior_period(as_of)
    arr_prior = ending_arr_at_period(bundle, prior, "Actual")
    arr_act = ending_arr_at_period(bundle, as_of, "Actual")
    arr_bud = ending_arr_at_period(bundle, as_of, "Budget")

    def comp(wtype: str, scenario: str = "Actual") -> Decimal:
        for key in (wtype, f"{wtype}_arr"):
            val = _wf(bundle, "arr", key, as_of, scenario)
            if val:
                return val
        return ZERO

    nb = comp("new_business")
    exp = comp("expansion")
    churn = abs(comp("churn"))
    react = comp("reactivation")
    cont = abs(comp("contraction"))
    nn = comp("new_arr") or comp("new_business")

    m = build_metrics_snapshot(bundle)
    grr = float((arr_act - churn) / arr_act * 100) if arr_act else None

    arr_prior_bud = ending_arr_at_period(bundle, prior, "Budget")

    return {
        "arr_bop": fmt_deck_money(arr_prior),
        "new_business": fmt_deck_money(nb),
        "new_business_budget": fmt_deck_money(comp("new_business", "Budget")),
        "expansion": fmt_deck_money(exp),
        "expansion_budget": fmt_deck_money(comp("expansion", "Budget")),
        "reactivation": fmt_deck_money(react),
        "reactivation_budget": fmt_deck_money(comp("reactivation", "Budget")),
        "contraction": fmt_deck_money(cont),
        "contraction_budget": fmt_deck_money(abs(comp("contraction", "Budget"))),
        "churn": fmt_deck_money(churn),
        "churn_budget": fmt_deck_money(abs(comp("churn", "Budget"))),
        "net_new": fmt_deck_money(nn),
        "net_new_budget": fmt_deck_money(comp("new_arr", "Budget") or comp("new_business", "Budget")),
        "arr_eop": fmt_deck_money(arr_act),
        "arr_eop_budget": fmt_deck_money(arr_bud),
        "gsr_pct": fmt_deck_pct(Decimal(str(grr / 100)), as_percent=False) if grr is not None else "n/a",
        "nsr_pct": fmt_deck_pct(m.nrr) if m.nrr is not None else "n/a",
        "pipeline_coverage_x": f"{float(m.pipeline_created / m.closed_won):.1f}x" if m.closed_won else "n/a",
        "waterfall_chart": build_arr_waterfall_chart(bundle),
        "bridge_table": {
            "columns": ["Component", "Actual", "Budget", "Variance"],
            "rows": [
                {"label": "Beginning ARR", "actual": fmt_deck_money(arr_prior), "budget": fmt_deck_money(arr_prior_bud), "variance": fmt_deck_var(arr_prior, arr_prior_bud)},
                {"label": "New Business", "actual": fmt_deck_money(nb), "budget": fmt_deck_money(comp("new_business", "Budget")), "variance": fmt_deck_var(nb, comp("new_business", "Budget"))},
                {"label": "Expansion", "actual": fmt_deck_money(exp), "budget": fmt_deck_money(comp("expansion", "Budget")), "variance": fmt_deck_var(exp, comp("expansion", "Budget"))},
                {"label": "Reactivation", "actual": fmt_deck_money(react), "budget": fmt_deck_money(comp("reactivation", "Budget")), "variance": fmt_deck_var(react, comp("reactivation", "Budget"))},
                {"label": "Contraction", "actual": fmt_deck_money(cont), "budget": fmt_deck_money(abs(comp("contraction", "Budget"))), "variance": fmt_deck_var(cont, abs(comp("contraction", "Budget")))},
                {"label": "Churn", "actual": fmt_deck_money(churn), "budget": fmt_deck_money(abs(comp("churn", "Budget"))), "variance": fmt_deck_var(churn, abs(comp("churn", "Budget")))},
                {"label": "Ending ARR", "actual": fmt_deck_money(arr_act), "budget": fmt_deck_money(arr_bud), "variance": fmt_deck_var(arr_act, arr_bud)},
            ],
        },
    }


# Variance Commentary tab — row-level provenance (board platform, deck, MDA package).
VARIANCE_ROW_SOURCES: dict[str, dict[str, str]] = {
    "vc_arr_ending": {
        "metric": "Ending ARR",
        "table": "comparison_waterfalls",
        "field": "arr.ending_arr",
        "rollup_fn": "rollup_ending_arr",
        "deck_block": "period_matrix",
    },
    "vc_net_new_arr": {
        "metric": "Net New ARR",
        "table": "comparison_waterfalls",
        "field": "arr.new_arr | arr.new_business",
        "rollup_fn": "rollup_waterfall_metric(flow=True)",
        "deck_block": "arr_analysis.bridge_table",
    },
    "vc_revenue": {
        "metric": "Revenue",
        "table": "income_statement",
        "field": "Revenue",
        "rollup_fn": "rollup_revenue",
        "deck_block": "period_matrix",
    },
    "vc_gross_margin": {
        "metric": "Gross Margin %",
        "table": "income_statement",
        "field": "Gross Profit / Revenue",
        "rollup_fn": "gross_margin_pct_horizon",
        "deck_block": "period_matrix",
    },
    "vc_ebitda": {
        "metric": "EBITDA",
        "table": "income_statement",
        "field": "EBITDA",
        "rollup_fn": "rollup_ebitda",
        "deck_block": "period_matrix",
    },
    "vc_sm_pipeline": {
        "metric": "S&M / Pipeline",
        "table": "income_statement",
        "field": "Sales & Marketing (P&L)",
        "rollup_fn": "build_pl_detail_block.sm",
        "deck_block": "pl_detail + gtm_performance.channels",
    },
    "vc_cash": {
        "metric": "Ending Cash",
        "table": "comparison_waterfalls",
        "field": "cash_flow.ending_cash",
        "rollup_fn": "rollup_cash",
        "deck_block": "period_matrix | cash_liquidity",
    },
    "vc_headcount": {
        "metric": "Total HC",
        "table": "workforce_period_summary | headcount_plan",
        "field": "sum(headcount) @ close month",
        "rollup_fn": "headcount_totals",
        "deck_block": "fy_outlook.headcount",
        "format": "integer — never dollars",
    },
}

VARIANCE_PERIOD_MATRIX_METRICS: dict[str, str] = {
    "vc_arr_ending": "Ending ARR",
    "vc_revenue": "Revenue",
    "vc_gross_margin": "Gross Margin %",
    "vc_ebitda": "EBITDA",
    "vc_cash": "Ending Cash",
}


def build_deliverable_data_map(period_matrix: dict[str, Any]) -> dict[str, Any]:
    """Documents shared warehouse provenance across board UI, deck, and MDA package."""
    return {
        "canonical_engine": "board_platform_metrics",
        "shared_payload_builder": "build_deck_payload",
        "shared_deliverables": [
            "board_platform_ui — executive period table / board tabs",
            "mda_deck_pptx — Prompt 5 (period_matrix, arr_analysis, pl_detail, cash_liquidity)",
            "mda_package_xlsx — Prompt 2 Variance Commentary metrics + Claude commentary",
        ],
        "period_matrix_sources": period_matrix.get("sources") or [],
        "variance_commentary_rows": VARIANCE_ROW_SOURCES,
        "future": "Customer-facing Validation sheet will assert these tie-outs automatically.",
    }


def verify_variance_commentary_tieout(
    display: dict[str, Any],
    period_matrix: dict[str, Any],
    *,
    fail_closed: bool = False,
) -> list[str]:
    """Assert MDA Variance Commentary numbers match period_matrix (deck slide 2 source).

    By default returns issue strings (legacy warn list). With ``fail_closed=True``
    (P15), any mismatch or missing tie-out row raises ``CommentaryIntegrityError``
    so customer-visible MD&A emit cannot proceed with unbound figures.
    """
    from app.services.commentary.claim_verify import CommentaryIntegrityError

    warnings: list[str] = []
    rows_by_id = {str(r.get("row_id")): r for r in display.get("rows") or []}
    matrix_by_metric = {str(r.get("metric")): r for r in period_matrix.get("rows") or []}
    for row_id, metric in VARIANCE_PERIOD_MATRIX_METRICS.items():
        vc_row = rows_by_id.get(row_id)
        mx_row = matrix_by_metric.get(metric)
        if not vc_row or not mx_row:
            warnings.append(f"Missing tie-out row for {row_id} ({metric}).")
            continue
        for horizon, matrix_key in (("cm", "cm"), ("qtd", "qtd"), ("ytd", "ytd")):
            vc_blk = vc_row.get(horizon) or {}
            mx_blk = mx_row.get(matrix_key) or {}
            for field in ("actual", "budget", "var"):
                vc_val = str(vc_blk.get(field) or "").strip()
                mx_val = str(mx_blk.get(field) or mx_blk.get("variance") or "").strip()
                if vc_val and mx_val and vc_val != mx_val:
                    warnings.append(
                        f"{row_id} {horizon}.{field}: MDA '{vc_val}' != period_matrix '{mx_val}'"
                    )
    if fail_closed:
        mismatches = [w for w in warnings if " != " in w]
        if mismatches:
            raise CommentaryIntegrityError(
                "P15 fail-closed: variance commentary vs period_matrix mismatch: "
                + "; ".join(mismatches)
            )
    return warnings


def evidence_values_from_mda_payload(payload: dict[str, Any]) -> dict[str, "Decimal"]:
    """Flatten display / period-matrix numbers into an evidence map for claim verify."""
    from decimal import Decimal

    from app.services.commentary.claim_verify import flatten_evidence_values

    values: dict[str, Decimal] = {}
    display = payload.get("variance_commentary_display") or {}
    deck = payload.get("deck_payload") or {}
    matrix = deck.get("period_matrix") or {}
    flatten_evidence_values(display, prefix="variance_commentary_display", out=values)
    flatten_evidence_values(matrix, prefix="period_matrix", out=values)
    # Also accept preformatted money strings by parsing via claim_verify helpers.
    from app.services.commentary.claim_verify import _to_decimal

    parsed: dict[str, Decimal] = {}
    for key, val in values.items():
        if isinstance(val, Decimal):
            parsed[key] = val
            continue
        num = _to_decimal(val)
        if num is not None:
            parsed[key] = num
    return parsed


def evidence_values_from_deck_payload(payload: dict[str, Any]) -> dict[str, "Decimal"]:
    """Flatten Prompt 5 / board deck payload numbers into an evidence map."""
    from decimal import Decimal

    from app.services.commentary.claim_verify import _to_decimal, flatten_evidence_values

    values: dict[str, Decimal] = {}
    flatten_evidence_values(payload, prefix="deck", out=values)
    parsed: dict[str, Decimal] = {}
    for key, val in values.items():
        if isinstance(val, Decimal):
            parsed[key] = val
            continue
        num = _to_decimal(val)
        if num is not None:
            parsed[key] = num
    return parsed


_MONTH_ABBR_NUM = {calendar.month_abbr[i]: f"{i:02d}" for i in range(1, 13)}
_M_SCALE_CEILING = Decimal("10000")  # values tagged *_m below this are treated as $M units


def _deck_close_period(payload: Mapping[str, Any] | dict[str, Any]) -> str | None:
    pc = payload.get("period_context") if isinstance(payload, dict) else None
    if isinstance(pc, dict):
        close = str(pc.get("close_period") or "").strip()
        if close:
            return to_period(close)
    close = str(payload.get("close_period") or "").strip()
    return to_period(close) if close else None


def _infer_series_kind(key: str, close_period: str | None) -> str:
    low = key.lower()
    if any(h in low for h in ("pipeline", "opportunity", "opportunities", "deal_highlight")):
        return "pipeline"
    if "budget" in low:
        return "budget"
    if any(
        h in low
        for h in (
            "forecast",
            "outlook",
            "fy_outlook",
            "ending_arr_outlook",
            "revenue_outlook",
        )
    ):
        return "forecast"
    if any(h in low for h in ("bridge", "waterfall", "variance", "cash_liquidity", "arr_analysis")):
        return "bridge"
    # Period-keyed actual vs forecast when close is known.
    if close_period:
        for part in low.replace("[", ".").replace("]", ".").split("."):
            if len(part) == 7 and part[4] == "-" and part[:4].isdigit() and part[5:].isdigit():
                return "actual" if part <= close_period else "forecast"
    return "actual"


def _promote_million_scale_keys(
    values: dict[str, "Decimal"],
    kinds: dict[str, str],
    close_period: str | None,
) -> None:
    """If a key ends with _m and looks like millions, also store absolute dollars."""
    from decimal import Decimal

    extras: dict[str, Decimal] = {}
    for key, val in list(values.items()):
        leaf = key.rsplit(".", 1)[-1]
        if not leaf.endswith("_m") and "outlook_m" not in leaf and not leaf.endswith("_m]"):
            # Also handle monthly_trends.revenue_outlook_m[3] style.
            if "_m[" not in key and not key.endswith("_m"):
                continue
        if abs(val) >= _M_SCALE_CEILING:
            continue
        abs_key = f"{key}.__dollars"
        extras[abs_key] = val * Decimal("1000000")
        kinds[abs_key] = kinds.get(key) or _infer_series_kind(key, close_period)
    values.update(extras)


def _add_monthly_trend_absolute_evidence(
    payload: dict[str, Any],
    values: dict[str, "Decimal"],
    kinds: dict[str, str],
    close_period: str | None,
) -> None:
    """Materialize Jan–Dec trend series as absolute dollars with actual/forecast labels."""
    from decimal import Decimal

    from app.services.commentary.claim_verify import _to_decimal

    trends = payload.get("monthly_trends") or {}
    if not isinstance(trends, dict):
        return
    months = trends.get("months") or []
    pc = payload.get("period_context") or {}
    year = str((pc.get("year") if isinstance(pc, dict) else None) or (close_period or "")[:4] or "")
    if not year or len(year) != 4:
        return

    series_specs = (
        ("ending_arr_m", "ending_arr", "actual"),
        ("ending_arr_outlook_m", "ending_arr_outlook", "forecast"),
        ("ending_arr_budget_m", "ending_arr_budget", "budget"),
        ("revenue_outlook_m", "revenue_outlook", "forecast"),
        ("revenue_budget_m", "revenue_budget", "budget"),
        ("pipeline_created_m", "pipeline_created", "pipeline"),
    )
    for series_key, metric, default_kind in series_specs:
        arr = trends.get(series_key)
        if not isinstance(arr, list):
            continue
        for idx, raw in enumerate(arr):
            num = _to_decimal(raw)
            if num is None or num == 0:
                continue
            month_token = str(months[idx]) if idx < len(months) else ""
            mm = _MONTH_ABBR_NUM.get(month_token) or (
                month_token if len(month_token) == 2 and month_token.isdigit() else None
            )
            period = f"{year}-{mm}" if mm else None
            # Chart series may be absolute dollars OR millions — promote both.
            dollars = num if abs(num) >= _M_SCALE_CEILING else num * Decimal("1000000")
            if default_kind in {"budget", "pipeline"}:
                kind = default_kind
            elif period and close_period:
                kind = "actual" if period <= close_period else "forecast"
            else:
                kind = default_kind
            key = (
                f"story.{kind}.{metric}.{period}"
                if period
                else f"story.{kind}.{metric}[{idx}]"
            )
            values[key] = dollars
            kinds[key] = kind
            # Keep compact millions form for charts that quote 86.1 not 86100000.
            if abs(dollars) >= _M_SCALE_CEILING:
                m_key = f"{key}.millions"
                values[m_key] = (dollars / Decimal("1000000")).quantize(Decimal("0.001"))
                kinds[m_key] = kind


def _add_deal_and_bridge_story_keys(
    payload: dict[str, Any],
    values: dict[str, "Decimal"],
    kinds: dict[str, str],
) -> None:
    """Promote deals, bridges, and outlook blocks into stable story.* evidence keys."""
    from app.services.commentary.claim_verify import _to_decimal

    deals = payload.get("deal_highlights") or {}
    if isinstance(deals, dict):
        for bucket in ("top_new_customers", "top_expansion", "top_churn", "top_slipped"):
            rows = deals.get(bucket) or []
            if not isinstance(rows, list):
                continue
            kind = "pipeline" if bucket in {"top_slipped", "top_expansion"} else "actual"
            for idx, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                amt = _to_decimal(row.get("arr"))
                if amt is None:
                    continue
                name = str(row.get("name") or f"deal_{idx}")[:48]
                slug = "".join(ch if ch.isalnum() else "_" for ch in name.lower()).strip("_")
                key = f"story.pipeline.deal.{bucket}.{slug or idx}"
                values[key] = amt
                kinds[key] = "pipeline" if "slipped" in bucket or kind == "pipeline" else kind

    for block_name, kind in (
        ("cash_liquidity", "bridge"),
        ("arr_analysis", "bridge"),
        ("fy_outlook", "forecast"),
        ("gtm_performance", "pipeline"),
        ("gtm_funnel", "pipeline"),
        ("pl_detail", "actual"),
        ("executive_summary", "actual"),
        ("mom_context", "actual"),
    ):
        block = payload.get(block_name)
        if block is None:
            continue
        from app.services.commentary.claim_verify import flatten_evidence_values

        nested: dict[str, Decimal] = {}
        flatten_evidence_values(block, prefix=f"story.{kind}.{block_name}", out=nested)
        for key, val in nested.items():
            values[key] = val
            kinds[key] = kind


def build_evidence_package_from_deck_payload(
    payload: dict[str, Any] | None,
    *,
    org_id: str | None = None,
    loaded_at: str | None = None,
    is_final: bool | None = None,
    prompt_value_cap: int = 500,
) -> dict[str, Any]:
    """Rich Prompt 5 evidence package — actuals, forecast, pipeline, bridges.

    Widens the verify/prompt surface so board narrative can use post-close
    forecast, pipeline/opportunities, cash/ARR bridges, and variance drivers
    without false P15 shutdowns. Invented figures outside the package still fail
    verify (soft-strip on Prompt 5 export).
    """
    from decimal import Decimal

    from app.services.commentary.claim_verify import (
        TOL_ACTUALS,
        TOL_RATIO,
        attach_sources_to_values,
    )

    if not payload:
        return {
            "values": {},
            "values_decimal": {},
            "_sources": {},
            "close_period": None,
            "period_label": None,
            "tolerance_actuals": str(TOL_ACTUALS),
            "tolerance_ratio": str(TOL_RATIO),
            "series_kinds": {},
            "policy": (
                "State only numeric values present in values (within $1.00 for money). "
                "Label actuals (≤ close_period) vs forecast/pipeline after close. "
                "Rich narrative from this package is encouraged — do not invent outside it."
            ),
        }

    close_period = _deck_close_period(payload)
    values: dict[str, Decimal] = dict(evidence_values_from_deck_payload(payload))
    kinds: dict[str, str] = {k: _infer_series_kind(k, close_period) for k in values}

    _promote_million_scale_keys(values, kinds, close_period)
    _add_monthly_trend_absolute_evidence(payload, values, kinds, close_period)
    _add_deal_and_bridge_story_keys(payload, values, kinds)

    # Drop bare calendar years that look numeric (same bar as claim_verify).
    import re

    year_re = re.compile(r"^(19|20)\d{2}$")
    values = {
        k: v
        for k, v in values.items()
        if not (v == v.to_integral_value() and year_re.match(str(int(v))))
    }

    sources = attach_sources_to_values(
        values,
        period_label=close_period,
        org_id=org_id,
        loaded_at=loaded_at,
        is_final=is_final,
        series_kinds=kinds,
    )

    # Prefer story.* / bridge / forecast / pipeline keys in the LLM-facing preview.
    def _rank(key: str) -> tuple[int, str]:
        low = key.lower()
        if low.startswith("story."):
            return (0, key)
        if any(h in low for h in ("forecast", "outlook", "pipeline", "bridge", "waterfall")):
            return (1, key)
        if low.startswith("deck."):
            return (2, key)
        return (3, key)

    ordered = sorted(values.keys(), key=_rank)
    prompt_keys = ordered[: max(50, prompt_value_cap)]
    prompt_values = {k: str(values[k]) for k in prompt_keys}
    prompt_sources = {k: sources[k] for k in prompt_keys if k in sources}

    return {
        "values": prompt_values,
        "values_decimal": values,
        "_sources": sources,
        "prompt_sources": prompt_sources,
        "close_period": close_period,
        "period_label": close_period,
        "tolerance_actuals": str(TOL_ACTUALS),
        "tolerance_ratio": str(TOL_RATIO),
        "series_kinds": {
            "actual": "Closed periods ≤ close_period — state as actuals",
            "forecast": "Open periods after close_period — label as forecast/outlook",
            "pipeline": "Pipeline / opportunities / coverage — label as pipeline",
            "budget": "Budget comparables",
            "bridge": "Cash bridge / ARR·MRR waterfall / variance bridge components",
        },
        "policy": (
            "Prefer every customer-visible $ / % / Nx from values (TOL_ACTUALS=$1.00). "
            f"close_period={close_period or 'n/a'}: periods ≤ close are Actuals; "
            "periods after close are Forecast. Pipeline/opportunity dollars only from "
            "pipeline-tagged keys. Use package context for rich board narrative — "
            "do not invent figures, causes, or watch-outs outside values / attribution allowlist. "
            "Cite _sources keys where feasible."
        ),
    }


def validate_deck_payload(payload: dict[str, Any]) -> list[str]:
    """Pre-flight warnings before calling Claude."""
    warnings: list[str] = []
    cfs = payload.get("ytd_cash_flow_statement") or {}
    for scenario in ("actual", "budget"):
        block = cfs.get(scenario) or {}
        if block.get("cfo") == "n/a" and block.get("ending_cash") == "n/a":
            warnings.append(f"YTD CFS {scenario} is empty — check budget/actual cash flow tables.")
    hc = (payload.get("fy_outlook") or {}).get("headcount") or {}
    if hc.get("eoy_budget") == 0 and hc.get("current_month_actual") == 0:
        warnings.append("Headcount is zero — verify headcount_plan / workforce tables loaded.")
    matrix = payload.get("period_matrix") or {}
    rows = matrix.get("rows") or []
    if not rows:
        warnings.append("Period matrix is empty.")
    return warnings


def build_deck_payload(
    bundle: ReportingBundle,
    ts_data: dict[str, Any] | None = None,
    cash_bridge_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Full Prompt 5 payload — pre-formatted, board-platform-aligned."""
    as_of = bundle.as_of_period
    ctx = build_period_context(bundle)
    matrix = build_period_matrix(bundle)

    rev_row = next((r for r in matrix["rows"] if r["metric"] == "Revenue"), {})
    arr_row = next((r for r in matrix["rows"] if r["metric"] == "Ending ARR"), {})
    gm_row = next((r for r in matrix["rows"] if r["metric"] == "Gross Margin %"), {})
    cash_row = next((r for r in matrix["rows"] if r["metric"] == "Ending Cash"), {})
    ebitda_row = next((r for r in matrix["rows"] if r["metric"] == "EBITDA"), {})

    return {
        "organization": bundle.organization_name or bundle.organization_id,
        "currency": bundle.currency,
        "period_context": {
            "close_period": as_of,
            "close_period_label": _period_label(as_of),
            "quarter": _quarter_label(as_of),
            "year": as_of[:4],
            "ytd_label": _ytd_label(as_of),
            "output_filename": f"SMPL_Board_Review_{as_of}.pptx",
            "ytd_periods": list(ctx.ytd_periods),
            "qtd_periods": list(ctx.qtd_periods),
        },
        "period_matrix": matrix,
        "executive_summary": {
            "note": "Use period_matrix rows only — do not recalculate.",
            "revenue": rev_row,
            "ending_arr": arr_row,
            "gross_margin_pct": gm_row,
            "ebitda": ebitda_row,
            "ending_cash": cash_row,
        },
        "arr_analysis": build_arr_bridge_block(bundle),
        "pl_review": {
            "note": "Use period_matrix Revenue and Gross Margin % rows for CM/QTD/YTD.",
            "revenue_cm": rev_row.get("cm"),
            "revenue_qtd": rev_row.get("qtd"),
            "revenue_ytd": rev_row.get("ytd"),
            "gross_margin_cm": gm_row.get("cm"),
            "ebitda_cm": ebitda_row.get("cm"),
        },
        "cash_liquidity": build_cash_liquidity_block(bundle, cash_bridge_data=cash_bridge_data),
        "appendix": {
            "ytd_cash_flow_statement": build_ytd_cash_flow_statement(bundle, ts_data),
            "label": "Appendix A — YTD Cash Flow Statement",
        },
        "ytd_cash_flow_statement": build_ytd_cash_flow_statement(bundle, ts_data),
        "fy_outlook": build_fy_outlook_block(bundle),
        "validation_status": bundle.validation.status,
        "data_gaps": [
            {"section": g.section, "status": g.status, "message": g.message}
            for g in (bundle.data_gaps or [])[:10]
        ],
        "formatting_rules": {
            "money": "Use display strings exactly as provided (e.g. $7.41M).",
            "percent": "Use display strings exactly (e.g. 79.2%).",
            "headcount": "Integers only — never format as dollars or divide by 1000.",
            "no_recalculation": "Every table cell must copy a value from this payload verbatim.",
        },
        "data_map": build_deliverable_data_map(matrix),
    }
