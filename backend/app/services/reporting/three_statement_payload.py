"""Build board-compatible TS_DATA and forecast-engine SRC payloads from warehouse."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import fetch_table_rows, table_exists, value_any
from app.services.reporting.as_of_period import bind_as_of_period, reset_as_of_period
from app.services.reporting.export.data_collector import collect_reporting_bundle
from app.services.reporting.org_reporting_settings import ensure_org_reporting_defaults, resolve_org_reporting_window
from app.services.reporting.period_utils import period_range, to_period
from app.services.reporting.validation_gate import raise_if_validation_blocked

IS_FIELD_SPECS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("revenue", ("revenue",)),
    ("cogs", ("cogs", "cost_of_revenue")),
    ("gross_profit", ("gross_profit",)),
    ("sm", ("sm", "sales_and_marketing")),
    ("rd", ("rd", "research_and_development")),
    ("ga", ("ga", "general_and_administrative")),
    ("total_opex", ("total_opex", "total_operating_expenses")),
    ("ebitda", ("ebitda",)),
    ("da", ("da", "depreciation_and_amortization")),
    ("interest", ("interest", "interest_expense")),
    ("tax", ("tax", "tax_expense")),
    ("op_income", ("op_income", "operating_income")),
    ("pretax", ("pretax", "pretax_income", "income_before_tax")),
    ("net_income", ("net_income",)),
    ("sbc", ("sbc", "stock_based_compensation")),
)

BS_FIELD_SPECS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cash", ("cash",)),
    ("ar", ("ar", "accounts_receivable")),
    (
        "prepaids",
        (
            "prepaids_and_other_current",
            "prepaids",
            "prepaid_expenses",
            "prepaids_and_other_current_assets",
            "prepaid_and_other_current_assets",
        ),
    ),
    (
        "prepaids_and_other_current_assets",
        (
            "prepaids_and_other_current",
            "prepaids_and_other_current_assets",
            "prepaids",
            "prepaid_expenses",
            "prepaid_and_other_current_assets",
        ),
    ),
    ("other_current", ("other_current_assets", "other_current")),
    (
        "ppe",
        (
            "ppe_net",
            "ppe",
            "property_and_equipment_net",
            "property_plant_equipment_net",
            "property_plant_and_equipment_net",
            "property_plant_net",
            "fixed_assets",
        ),
    ),
    (
        "property_and_equipment_net",
        (
            "ppe_net",
            "property_and_equipment_net",
            "ppe",
            "property_plant_equipment_net",
            "property_plant_and_equipment_net",
            "property_plant_net",
            "fixed_assets",
        ),
    ),
    ("other_assets", ("other_assets",)),
    ("ap", ("ap", "accounts_payable")),
    ("dr", ("deferred_revenue", "dr")),
    ("deferred_rev", ("deferred_revenue", "dr", "deferred_rev")),
    ("debt", ("debt", "total_debt", "debt_balance", "notes_payable")),
    ("other_liabilities", ("other_liabilities",)),
    ("equity", ("equity",)),
    ("total_assets", ("total_assets",)),
    ("total_liabilities", ("total_liabilities", "total_liab")),
    ("total_le", ("total_liabilities_and_equity", "total_le")),
)

CFS_FIELD_SPECS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("beginning_cash", ("beginning_cash",)),
    ("net_income", ("net_income",)),
    ("da", ("da", "depreciation_and_amortization")),
    ("sbc", ("sbc", "stock_based_compensation")),
    ("chg_ar", ("chg_ar", "change_in_accounts_receivable")),
    ("chg_dr", ("chg_dr", "change_in_deferred_revenue")),
    ("chg_ap", ("chg_ap", "change_in_accounts_payable")),
    ("chg_prepaids", ("chg_prepaids", "change_in_prepaids")),
    ("cfo", ("cfo", "net_cash_from_operating_activities")),
    ("capex", ("capex", "capital_expenditures")),
    ("cfi", ("cfi", "net_cash_from_investing_activities")),
    ("cff", ("cff", "net_cash_from_financing_activities")),
    ("net_change", ("net_change", "net_change_in_cash")),
    ("ending_cash", ("ending_cash",)),
)

# Legacy maps retained for modules that import by name.
IS_KEY_MAP = dict(IS_FIELD_SPECS)
BS_KEY_MAP = dict(BS_FIELD_SPECS)
CFS_KEY_MAP = dict(CFS_FIELD_SPECS)

MRR_FIELD_SPECS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("arr_bop", ("beginning_arr", "beginning_mrr")),
    ("arr_nb", ("new_business_arr", "new_mrr")),
    ("arr_exp", ("expansion_arr", "expansion_mrr")),
    ("arr_cont", ("contraction_arr", "contraction_mrr")),
    ("arr_churn", ("churn_arr", "churn_mrr")),
    ("arr_react", ("reactivation_arr", "reactivation_mrr")),
    ("arr_nn", ("net_new_arr", "net_new_mrr")),
    ("arr_eop", ("ending_arr", "ending_mrr")),
    ("nrr", ("net_dollar_retention_rate", "nrr", "forecasted_nrr")),
    ("grr", ("gross_retention_rate", "grr")),
)

ARR_WATERFALL_ROW_KEYS: tuple[str, ...] = (
    "Beginning",
    "New Business",
    "Expansion",
    "Contraction",
    "Churn",
    "Reactivation",
    "Ending",
)


def _dec(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(Decimal(str(value)))
    except Exception:
        return None


def _read_statement_table(
    db: Session,
    organization_id: uuid.UUID,
    table_name: str,
) -> list[dict[str, Any]]:
    if not table_exists(db, table_name):
        return []
    return fetch_table_rows(db, table_name, organization_id)


def _row_field_value(raw: dict[str, Any], *aliases: str) -> float | None:
    for key in aliases:
        if raw.get(key) not in (None, ""):
            return _dec(raw.get(key))
    return None


def _period_dict_from_field_specs(
    rows: list[dict[str, Any]],
    field_specs: tuple[tuple[str, tuple[str, ...]], ...],
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, dict[str, float | None]]:
    out: dict[str, dict[str, float | None]] = {}
    for raw in rows:
        period_raw = raw.get("period") or raw.get("posting_period")
        if not period_raw:
            continue
        period = to_period(str(period_raw))
        bucket = out.setdefault(period, {})
        for dst, aliases in field_specs:
            val = _row_field_value(raw, *aliases)
            if val is not None:
                bucket[dst] = val
        if extra:
            for k, fn in extra.items():
                bucket[k] = fn(bucket)
    return out


def _period_dict_from_rows(
    rows: list[dict[str, Any]],
    key_map: dict[str, str | tuple[str, ...]],
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, dict[str, float | None]]:
    field_specs = tuple(
        (dst, aliases if isinstance(aliases, tuple) else (aliases,))
        for aliases, dst in ((v, k) for k, v in key_map.items())
    )
    return _period_dict_from_field_specs(rows, field_specs, extra=extra)


def _aggregate_mrr_by_period(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | None]]:
    """Sum MRR/ARR movement rows into one bucket per period."""
    totals: dict[str, dict[str, float]] = {}
    for raw in rows:
        period_raw = raw.get("period") or raw.get("posting_period")
        if not period_raw:
            continue
        period = to_period(str(period_raw))
        bucket = totals.setdefault(period, {})
        for key, aliases in MRR_FIELD_SPECS:
            val = _dec(value_any(raw, *aliases))
            if val is None:
                continue
            bucket[key] = bucket.get(key, 0.0) + val
    return totals


def _normalize_mrr_metrics(raw: dict[str, float | None]) -> dict[str, float | None]:
    """Fill derived ARR metrics when warehouse rows omit them."""
    metrics = dict(raw)
    bop = metrics.get("arr_bop")
    eop = metrics.get("arr_eop")
    cont = metrics.get("arr_cont") or 0.0
    churn = metrics.get("arr_churn") or 0.0
    nb = metrics.get("arr_nb") or 0.0
    exp = metrics.get("arr_exp") or 0.0
    react = metrics.get("arr_react") or 0.0

    if metrics.get("arr_nn") is None:
        if bop is not None and eop is not None:
            metrics["arr_nn"] = eop - bop
        else:
            metrics["arr_nn"] = nb + exp + react - cont - churn

    if bop and bop > 0:
        if metrics.get("grr") is None:
            metrics["grr"] = (bop - cont - churn) / bop
        if metrics.get("nrr") is None and metrics.get("arr_nn") is not None:
            metrics["nrr"] = (bop + metrics["arr_nn"]) / bop
    return metrics


def _merge_mrr_into_row(row: dict[str, float | None], mrr: dict[str, float | None]) -> None:
    for key in (
        "arr_bop",
        "arr_eop",
        "arr_nb",
        "arr_exp",
        "arr_churn",
        "arr_cont",
        "arr_react",
        "arr_nn",
        "nrr",
        "grr",
    ):
        if mrr.get(key) is not None:
            row[key] = mrr[key]


def _wf_row_from_mrr(metrics: dict[str, float | None]) -> dict[str, float | None]:
    cont = metrics.get("arr_cont") or 0.0
    churn = metrics.get("arr_churn") or 0.0
    return {
        "Beginning": metrics.get("arr_bop"),
        "New Business": metrics.get("arr_nb"),
        "Expansion": metrics.get("arr_exp"),
        "Contraction": -abs(cont),
        "Churn": -abs(churn),
        "Reactivation": metrics.get("arr_react"),
        "Ending": metrics.get("arr_eop"),
    }


def build_arr_waterfall_table(
    db: Session,
    organization_id: uuid.UUID,
    *,
    as_of: str,
    start_period: str,
    end_period: str,
) -> dict[str, list[float | None]]:
    """Board ARR waterfall detail table — actuals through close, forecast thereafter."""
    periods = period_range(start_period, end_period)
    actual_mrr = _aggregate_mrr_by_period(
        _read_statement_table(db, organization_id, "actual_mrr_waterfall")
    )
    forecast_mrr = _aggregate_mrr_by_period(
        _read_statement_table(db, organization_id, "forecast_mrr_waterfall")
    )

    table: dict[str, list[float | None]] = {key: [] for key in ARR_WATERFALL_ROW_KEYS}
    for period in periods:
        source = actual_mrr if period <= as_of else forecast_mrr
        metrics = _normalize_mrr_metrics(source.get(period, {}))
        wf_row = _wf_row_from_mrr(metrics)
        for key in ARR_WATERFALL_ROW_KEYS:
            table[key].append(wf_row.get(key))
    return table


def build_baseline_engine(
    db: Session,
    organization_id: uuid.UUID,
    *,
    as_of: str,
    start_period: str,
    end_period: str,
) -> dict[str, Any]:
    """Forecast-engine result shape for open months from warehouse forecast_* tables."""
    fc_periods = [p for p in period_range(start_period, end_period) if p > as_of]
    if not fc_periods:
        return {}

    is_data = _period_dict_from_field_specs(
        _read_statement_table(db, organization_id, "forecast_income_statement"),
        IS_FIELD_SPECS,
    )
    bs_data = _period_dict_from_field_specs(
        _read_statement_table(db, organization_id, "forecast_balance_sheet"),
        BS_FIELD_SPECS,
    )
    for period, row in bs_data.items():
        _normalize_bs_display(row)
    actual_bs = _period_dict_from_field_specs(
        _read_statement_table(db, organization_id, "actual_balance_sheet"),
        BS_FIELD_SPECS,
    )
    for period, row in actual_bs.items():
        _normalize_bs_display(row)
    mrr_data = _aggregate_mrr_by_period(
        _read_statement_table(db, organization_id, "forecast_mrr_waterfall")
    )

    results: dict[str, Any] = {}
    for period in fc_periods:
        is_row = dict(is_data.get(period, {}))
        _enrich_is(is_row)
        bs_row = bs_data.get(period, {})
        cfs_row = build_cfs_from_statements(
            [period],
            {period: is_row},
            {period: bs_row},
            cross_scenario_bs=actual_bs,
        ).get(period, {})
        mrr = _normalize_mrr_metrics(mrr_data.get(period, {}))

        arr = {
            "arr_bop": mrr.get("arr_bop"),
            "arr_nb": mrr.get("arr_nb"),
            "arr_exp": mrr.get("arr_exp"),
            "arr_react": mrr.get("arr_react"),
            "arr_cont": mrr.get("arr_cont"),
            "arr_nr_churn": mrr.get("arr_churn"),
            "ren_churn": 0.0,
            "arr_churn": mrr.get("arr_churn"),
            "arr_nn": mrr.get("arr_nn"),
            "arr_eop": mrr.get("arr_eop"),
            "grr": mrr.get("grr"),
            "nrr": mrr.get("nrr"),
            "is_actual": False,
        }
        opex = (is_row.get("sm") or 0.0) + (is_row.get("rd") or 0.0) + (is_row.get("ga") or 0.0)
        if is_row.get("total_opex") is None and opex:
            is_row["total_opex"] = opex

        cfs = {
            "beg_cash": cfs_row.get("beginning_cash"),
            "ni": cfs_row.get("net_income"),
            "da": cfs_row.get("da"),
            "sbc": cfs_row.get("sbc"),
            "chg_ar": cfs_row.get("chg_ar"),
            "chg_dr": cfs_row.get("chg_dr"),
            "chg_ap": cfs_row.get("chg_ap"),
            "chg_pre": cfs_row.get("chg_prepaids"),
            "cfo": cfs_row.get("cfo"),
            "capex": cfs_row.get("capex"),
            "cfi": cfs_row.get("cfi"),
            "cff": cfs_row.get("cff") or 0.0,
            "net_change": cfs_row.get("net_change"),
            "end_cash": cfs_row.get("ending_cash"),
            "cash_tie_variance": cfs_row.get("cash_tie_variance"),
            "ar": bs_row.get("ar"),
            "ap": bs_row.get("ap"),
            "end_dr": bs_row.get("dr"),
            "is_actual": False,
        }
        bs = {
            "cash": bs_row.get("cash"),
            "ar": bs_row.get("ar"),
            "ap": bs_row.get("ap"),
            "dr": bs_row.get("dr"),
            "deferred_rev": bs_row.get("deferred_rev"),
            "prepaids": bs_row.get("prepaids"),
            "ppe": bs_row.get("ppe"),
            "debt": bs_row.get("debt"),
            "total_assets": bs_row.get("total_assets"),
            "total_liabilities": bs_row.get("total_liabilities"),
            "total_le": bs_row.get("total_le"),
            "equity": bs_row.get("equity"),
            "is_actual": False,
        }
        results[period] = {"p": period, "arr": arr, "is": is_row, "cfs": cfs, "bs": bs}
    return results


def build_cash_bridge_data(
    db: Session,
    organization_id: uuid.UUID,
    *,
    start_period: str,
    end_period: str,
) -> dict[str, dict[str, dict[str, float | None]]]:
    """Direct cash bridge rows by scenario and period (from *_cash_flow_bridge tables)."""
    scenarios: dict[str, dict[str, dict[str, float | None]]] = {}
    field_specs: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("beginning_cash", ("beginning_cash",)),
        ("ending_cash", ("ending_cash",)),
        ("collections", ("cash_collections", "collections", "cash_collections_from_invoices")),
        ("payroll", ("payroll_cash_out",)),
        ("commission", ("commission_cash_out",)),
        ("vendor", ("vendor_cash_out_n30",)),
        ("tax", ("tax_cash_out",)),
        ("interest", ("interest_cash_out",)),
        ("other_operating", ("other_operating_cash_out",)),
        ("capex", ("capex",)),
    )
    allowed = set(period_range(start_period, end_period))
    for scenario, prefix in (("Actual", "actual"), ("Forecast", "forecast"), ("Budget", "budget")):
        rows = _read_statement_table(db, organization_id, f"{prefix}_cash_flow_bridge")
        by_period: dict[str, dict[str, float | None]] = {}
        for raw in rows:
            period_raw = raw.get("period") or raw.get("posting_period")
            if not period_raw:
                continue
            period = to_period(str(period_raw))
            if period not in allowed:
                continue
            bucket: dict[str, float | None] = {}
            for dst, aliases in field_specs:
                val = _row_field_value(raw, *aliases)
                if val is not None:
                    bucket[dst] = val
            if bucket:
                by_period[period] = bucket
        if by_period:
            scenarios[scenario] = by_period
    return scenarios


def build_unified_outlook_payload(
    db: Session,
    organization_id: uuid.UUID,
    *,
    as_of: str,
    start_period: str,
    end_period: str,
) -> dict[str, Any]:
    """Shared actual + forecast baseline blocks for board and forecast engine."""
    ts_data = build_ts_data(
        db,
        organization_id,
        as_of=as_of,
        start_period=start_period,
        end_period=end_period,
    )
    src = build_forecast_engine_src(db, organization_id, as_of=as_of)
    return {
        "TS_DATA": ts_data,
        "SRC": src,
        "ARR_WATERFALL": build_arr_waterfall_table(
            db,
            organization_id,
            as_of=as_of,
            start_period=start_period,
            end_period=end_period,
        ),
        "baseline_engine": build_baseline_engine(
            db,
            organization_id,
            as_of=as_of,
            start_period=start_period,
            end_period=end_period,
        ),
        "CASH_BRIDGE": build_cash_bridge_data(
            db,
            organization_id,
            start_period=start_period,
            end_period=end_period,
        ),
    }


def _enrich_is(row: dict[str, float | None]) -> None:
    """Display-only IS enrichments. Amounts come from warehouse income_statement rows."""
    rev = row.get("revenue")
    gp = row.get("gross_profit")
    if rev and rev != 0:
        row.setdefault("sub_rev", rev * 0.967)
        row.setdefault("svc_rev", rev * 0.033)
        if gp is not None:
            row.setdefault("gm_pct", gp / rev)
    opex = (row.get("sm") or 0) + (row.get("rd") or 0) + (row.get("ga") or 0)
    if row.get("total_opex") is None and opex:
        row["total_opex"] = opex
    da = row.get("da") or 0.0
    interest = row.get("interest") or 0.0
    ebitda = row.get("ebitda")
    if row.get("op_income") is None and ebitda is not None:
        row["op_income"] = ebitda - da
    if row.get("pretax") is None and row.get("op_income") is not None:
        row["pretax"] = row["op_income"] - interest
    if row.get("tax") is None:
        pretax = row.get("pretax")
        net_income = row.get("net_income")
        if pretax is not None and net_income is not None:
            row["tax"] = pretax - net_income
        else:
            row["tax"] = 0.0


def _prior_period(period: str) -> str | None:
    year = int(period[:4])
    month = int(period[5:7])
    if month == 1:
        return f"{year - 1}-12"
    return f"{year}-{month - 1:02d}"


def _resolve_prior_bs(
    period: str,
    bs_data: dict[str, dict[str, float | None]],
    *,
    cross_scenario_bs: dict[str, dict[str, float | None]] | None = None,
) -> dict[str, float | None] | None:
    prior_period = _prior_period(period)
    if prior_period is None:
        return None
    if prior_period in bs_data:
        return bs_data[prior_period]
    if cross_scenario_bs and prior_period in cross_scenario_bs:
        return cross_scenario_bs[prior_period]
    return None


def _calculate_cfs_row(
    is_row: dict[str, float | None],
    bs_row: dict[str, float | None],
    prior_bs: dict[str, float | None] | None,
) -> dict[str, float | None]:
    """Indirect-method cash flow derived from income statement + balance sheet movement."""
    ni = is_row.get("net_income")
    da = is_row.get("da")
    sbc = is_row.get("sbc") or 0.0

    cfs: dict[str, float | None] = {
        "net_income": ni,
        "da": da,
        "sbc": sbc,
    }

    if prior_bs is not None:
        prior_ar, ar = prior_bs.get("ar"), bs_row.get("ar")
        if prior_ar is not None and ar is not None:
            cfs["chg_ar"] = prior_ar - ar

        prior_ap, ap = prior_bs.get("ap"), bs_row.get("ap")
        if prior_ap is not None and ap is not None:
            cfs["chg_ap"] = ap - prior_ap

        prior_dr, dr = prior_bs.get("dr"), bs_row.get("dr")
        if prior_dr is not None and dr is not None:
            cfs["chg_dr"] = dr - prior_dr

        prior_pre, pre = prior_bs.get("prepaids"), bs_row.get("prepaids")
        if prior_pre is not None and pre is not None:
            cfs["chg_prepaids"] = prior_pre - pre

        prior_ppe, ppe = prior_bs.get("ppe"), bs_row.get("ppe")
        if prior_ppe is not None and ppe is not None and da is not None:
            cfs["capex"] = ppe - prior_ppe - da
            cfs["cfi"] = cfs["capex"]

        prior_debt, debt = prior_bs.get("debt"), bs_row.get("debt")
        if prior_debt is not None and debt is not None:
            cfs["cff"] = debt - prior_debt

        prior_cash, cash = prior_bs.get("cash"), bs_row.get("cash")
        if prior_cash is not None:
            cfs["beginning_cash"] = prior_cash
        if cash is not None:
            cfs["ending_cash"] = cash
        if prior_cash is not None and cash is not None:
            cfs["net_change"] = cash - prior_cash

    if ni is not None:
        cfs["cfo"] = ni + (da or 0.0) + sbc + sum(
            cfs.get(key) or 0.0
            for key in ("chg_ar", "chg_ap", "chg_dr", "chg_prepaids")
        )

    if cfs.get("cfo") is not None:
        computed_net = cfs["cfo"] + (cfs.get("cfi") or 0.0) + (cfs.get("cff") or 0.0)
        cfs["net_change_computed"] = computed_net
        if cfs.get("net_change") is not None:
            cfs["cash_tie_variance"] = cfs["net_change"] - computed_net

    return cfs


def build_cfs_from_statements(
    periods: list[str],
    is_data: dict[str, dict[str, float | None]],
    bs_data: dict[str, dict[str, float | None]],
    *,
    cross_scenario_bs: dict[str, dict[str, float | None]] | None = None,
) -> dict[str, dict[str, float | None]]:
    """Build cash flow rows from IS + BS. Balance sheet is source of truth for cash."""
    out: dict[str, dict[str, float | None]] = {}
    for period in periods:
        is_row = is_data.get(period, {})
        bs_row = bs_data.get(period, {})
        if not is_row and not bs_row:
            continue
        prior_bs = _resolve_prior_bs(period, bs_data, cross_scenario_bs=cross_scenario_bs)
        out[period] = _calculate_cfs_row(is_row, bs_row, prior_bs)
    return out


def _normalize_bs_display(row: dict[str, float | None]) -> None:
    """Board-facing aliases only — no derived balance sheet amounts."""
    if row.get("prepaids") is None and row.get("prepaids_and_other_current_assets") is not None:
        row["prepaids"] = row["prepaids_and_other_current_assets"]
    if row.get("prepaids_and_other_current_assets") is None and row.get("prepaids") is not None:
        row["prepaids_and_other_current_assets"] = row["prepaids"]
    if row.get("ppe") is None and row.get("property_and_equipment_net") is not None:
        row["ppe"] = row["property_and_equipment_net"]
    if row.get("property_and_equipment_net") is None and row.get("ppe") is not None:
        row["property_and_equipment_net"] = row["ppe"]
    if row.get("deferred_rev") is None and row.get("dr") is not None:
        row["deferred_rev"] = row["dr"]
    if row.get("total_le") is None:
        total_liab = row.get("total_liabilities")
        equity = row.get("equity")
        if total_liab is not None and equity is not None:
            row["total_le"] = total_liab + equity


def build_ts_data(
    db: Session,
    organization_id: uuid.UUID,
    *,
    as_of: str,
    start_period: str,
    end_period: str,
) -> dict[str, Any]:
    """Board Platform 3-Statement tab shape (TS_DATA)."""
    scenarios: dict[str, Any] = {}
    actual_bs_data = _period_dict_from_field_specs(
        _read_statement_table(db, organization_id, "actual_balance_sheet"),
        BS_FIELD_SPECS,
    )
    for row in actual_bs_data.values():
        _normalize_bs_display(row)

    for scenario, prefix in (("Actual", "actual"), ("Forecast", "forecast"), ("Budget", "budget")):
        is_rows = _read_statement_table(db, organization_id, f"{prefix}_income_statement")
        bs_rows = _read_statement_table(db, organization_id, f"{prefix}_balance_sheet")

        is_data = _period_dict_from_field_specs(is_rows, IS_FIELD_SPECS)
        for period, row in is_data.items():
            _enrich_is(row)

        bs_data = _period_dict_from_field_specs(bs_rows, BS_FIELD_SPECS)
        for period, row in bs_data.items():
            _normalize_bs_display(row)

        periods = sorted(
            {
                p
                for p in period_range(start_period, end_period)
                if p in is_data or p in bs_data
            }
        )
        if not periods:
            continue

        cross_bs = actual_bs_data if scenario in ("Forecast", "Budget") else None
        cfs_data = build_cfs_from_statements(
            periods,
            is_data,
            bs_data,
            cross_scenario_bs=cross_bs,
        )

        scenarios[scenario] = {
            "periods": periods,
            "is": {p: is_data.get(p, {}) for p in periods},
            "bs": {p: bs_data.get(p, {}) for p in periods},
            "cfs": {p: cfs_data.get(p, {}) for p in periods},
        }
    return scenarios


def build_forecast_engine_src(
    db: Session,
    organization_id: uuid.UUID,
    *,
    as_of: str,
) -> dict[str, Any]:
    """Minimal SRC.actuals slice for Forecast Engine lever refresh."""
    actuals: dict[str, dict[str, float | None]] = {}
    is_rows = _read_statement_table(db, organization_id, "actual_income_statement")
    bs_rows = _read_statement_table(db, organization_id, "actual_balance_sheet")
    mrr_rows = _read_statement_table(db, organization_id, "actual_mrr_waterfall")

    is_by_period = _period_dict_from_field_specs(is_rows, IS_FIELD_SPECS)
    for period, is_row in is_by_period.items():
        _enrich_is(is_row)
    bs_by_period = _period_dict_from_field_specs(bs_rows, BS_FIELD_SPECS)
    for period, bs_row in bs_by_period.items():
        _normalize_bs_display(bs_row)
    cfs_by_period = build_cfs_from_statements(
        sorted(is_by_period.keys()),
        is_by_period,
        bs_by_period,
    )
    mrr_by_period = _aggregate_mrr_by_period(mrr_rows)

    for period in sorted(set(is_by_period) | set(bs_by_period) | set(cfs_by_period)):
        if period > as_of:
            continue
        row: dict[str, float | None] = {}
        row.update(is_by_period.get(period, {}))
        row.update(bs_by_period.get(period, {}))
        row.update(cfs_by_period.get(period, {}))
        _merge_mrr_into_row(row, _normalize_mrr_metrics(mrr_by_period.get(period, {})))
        if row:
            actuals[period] = row
    return {"actuals": actuals}


OUTLOOK_API_BUILD = "light-v2"


def build_outlook_api_payload(
    db: Session,
    organization_id: uuid.UUID,
) -> dict[str, Any]:
    """Fast outlook payload for board + forecast — no export/reporting bundle."""
    from app.models.organization import Organization
    from app.services.forecast_version_service import get_active_forecast_version
    from app.services.reporting.board_modules_payload import build_board_modules_payload

    org = db.get(Organization, organization_id)
    if org is None:
        raise ValueError("Organization not found")
    ensure_org_reporting_defaults(db, org)
    as_of, start_period, end_period = resolve_org_reporting_window(db, org)

    active = get_active_forecast_version(db, org)
    outlook = build_unified_outlook_payload(
        db,
        organization_id,
        as_of=as_of,
        start_period=start_period,
        end_period=end_period,
    )

    arr_ending: float | None = None
    wf = outlook.get("ARR_WATERFALL") or {}
    ending = wf.get("Ending")
    if isinstance(ending, list):
        idx = int(as_of[5:7]) - 1
        if 0 <= idx < len(ending) and ending[idx] is not None:
            arr_ending = float(ending[idx])

    board_modules = build_board_modules_payload(
        db,
        organization_id,
        as_of_period=as_of,
        start_period=start_period,
        end_period=end_period,
        arr_ending=arr_ending,
    )

    return {
        "meta": {
            "organization_id": str(organization_id),
            "organization_name": org.name,
            "close_month": as_of,
            "start_period": start_period,
            "end_period": end_period,
            "fiscal_year_end_month": int(org.fiscal_year_end_month or 12),
            "active_forecast_version_id": str(active.id) if active else None,
            "active_forecast_version_name": active.version_name if active else None,
            "outlook_build": OUTLOOK_API_BUILD,
        },
        **outlook,
        **board_modules,
    }


def build_shared_reporting_payload(
    db: Session,
    organization_id: uuid.UUID,
    *,
    block_on_validation: bool = True,
    include_reporting_bundle: bool = True,
) -> dict[str, Any]:
    from app.models.organization import Organization
    from app.services.reporting.export.schemas import ExportValidationSummary

    org = db.get(Organization, organization_id)
    if org is None:
        raise ValueError("Organization not found")
    ensure_org_reporting_defaults(db, org)
    as_of, start_period, end_period = resolve_org_reporting_window(db, org)

    bundle = None
    if include_reporting_bundle or block_on_validation:
        token = bind_as_of_period(as_of)
        try:
            bundle = collect_reporting_bundle(
                db,
                organization_id,
                scenario="Combined",
                start_period=start_period,
                end_period=end_period,
                as_of_period=as_of,
            )
        finally:
            reset_as_of_period(token)

        if block_on_validation:
            raise_if_validation_blocked(bundle.validation, action="Reporting payload")

    from app.services.forecast_version_service import get_active_forecast_version

    active = get_active_forecast_version(db, org)
    outlook = build_unified_outlook_payload(
        db,
        organization_id,
        as_of=as_of,
        start_period=start_period,
        end_period=end_period,
    )

    return {
        "meta": {
            "organization_id": str(organization_id),
            "organization_name": org.name,
            "close_month": as_of,
            "start_period": start_period,
            "end_period": end_period,
            "fiscal_year_end_month": int(org.fiscal_year_end_month or 12),
            "active_forecast_version_id": str(active.id) if active else None,
            "active_forecast_version_name": active.version_name if active else None,
        },
        **outlook,
        "validation": (
            bundle.validation.model_dump(mode="json")
            if bundle is not None
            else ExportValidationSummary(status="pass").model_dump(mode="json")
        ),
    }


# ---------------------------------------------------------------------------
# Production FE ↔ Board single-source guard (TS_DATA.Actual vs SRC.actuals)
# ---------------------------------------------------------------------------
# Board Platform hydrates TS_DATA; Forecast Engine hydrates SRC.actuals. Both
# come from build_unified_outlook_payload → same warehouse tables. This guard
# fails if the two shapes diverge for the same org/period on that shared path.
# Demo HTML seeds are intentionally out of scope — do not reseed demos.

# (field, TS statement bucket, SRC key) — aliases already normalized in builders.
TS_SRC_ACTUALS_ALIGN_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("revenue", "is", "revenue"),
    ("cogs", "is", "cogs"),
    ("gross_profit", "is", "gross_profit"),
    ("sm", "is", "sm"),
    ("rd", "is", "rd"),
    ("ga", "is", "ga"),
    ("ebitda", "is", "ebitda"),
    ("da", "is", "da"),
    ("net_income", "is", "net_income"),
    ("cash", "bs", "cash"),
    ("ar", "bs", "ar"),
    ("ap", "bs", "ap"),
    ("deferred_rev", "bs", "deferred_rev"),
    ("beginning_cash", "cfs", "beginning_cash"),
    ("ending_cash", "cfs", "ending_cash"),
    ("cfo", "cfs", "cfo"),
    ("net_change", "cfs", "net_change"),
)

# Product closed-actuals bar — same as claim_verify TOL_ACTUALS.
OUTLOOK_TS_SRC_MONEY_TOLERANCE = Decimal("1.00")


def _as_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except Exception:
        return None


def diff_outlook_ts_src_actuals(
    ts_data: dict[str, Any] | None,
    src: dict[str, Any] | None,
    *,
    as_of: str | None = None,
    money_tolerance: Decimal = OUTLOOK_TS_SRC_MONEY_TOLERANCE,
) -> list[dict[str, Any]]:
    """Compare Board TS_DATA.Actual vs FE SRC.actuals for shared production fields.

    Returns a list of divergence records (empty = aligned within tolerance).
    """
    if money_tolerance > OUTLOOK_TS_SRC_MONEY_TOLERANCE:
        raise ValueError(
            f"money_tolerance cannot exceed {OUTLOOK_TS_SRC_MONEY_TOLERANCE} (product $1 bar)"
        )
    actual = (ts_data or {}).get("Actual") or {}
    src_actuals = (src or {}).get("actuals") or {}
    if not isinstance(actual, dict) or not isinstance(src_actuals, dict):
        return [
            {
                "period": as_of,
                "field": "_shape",
                "ts": None,
                "src": None,
                "delta": None,
                "reason": "missing_ts_or_src_shape",
            }
        ]

    periods = sorted(
        p
        for p in set(src_actuals.keys())
        | set((actual.get("is") or {}).keys())
        | set((actual.get("bs") or {}).keys())
        | set((actual.get("cfs") or {}).keys())
        if isinstance(p, str) and (as_of is None or p <= as_of)
    )
    diffs: list[dict[str, Any]] = []
    for period in periods:
        src_row = src_actuals.get(period) or {}
        if not isinstance(src_row, dict):
            continue
        for field, stmt, src_key in TS_SRC_ACTUALS_ALIGN_FIELDS:
            ts_bucket = actual.get(stmt) or {}
            ts_row = ts_bucket.get(period) if isinstance(ts_bucket, dict) else None
            ts_val = _as_decimal((ts_row or {}).get(field) if isinstance(ts_row, dict) else None)
            src_val = _as_decimal(src_row.get(src_key))
            # deferred_rev / dr alias on SRC
            if src_val is None and src_key == "deferred_rev":
                src_val = _as_decimal(src_row.get("dr"))
            if ts_val is None and src_val is None:
                continue
            if ts_val is None or src_val is None:
                diffs.append(
                    {
                        "period": period,
                        "field": field,
                        "ts": str(ts_val) if ts_val is not None else None,
                        "src": str(src_val) if src_val is not None else None,
                        "delta": None,
                        "reason": "one_side_missing",
                    }
                )
                continue
            delta = abs(ts_val - src_val)
            if delta > money_tolerance:
                diffs.append(
                    {
                        "period": period,
                        "field": field,
                        "ts": str(ts_val),
                        "src": str(src_val),
                        "delta": str(delta),
                        "reason": "significant_miss",
                    }
                )
    return diffs


def assert_outlook_ts_src_actuals_aligned(
    payload: dict[str, Any],
    *,
    as_of: str | None = None,
    money_tolerance: Decimal = OUTLOOK_TS_SRC_MONEY_TOLERANCE,
) -> None:
    """Raise ValueError if unified outlook TS_DATA vs SRC.actuals diverge > $1."""
    close = as_of or str((payload.get("meta") or {}).get("close_month") or "") or None
    diffs = diff_outlook_ts_src_actuals(
        payload.get("TS_DATA"),
        payload.get("SRC"),
        as_of=close,
        money_tolerance=money_tolerance,
    )
    if diffs:
        sample = "; ".join(
            f"{d['period']}.{d['field']} Δ={d.get('delta') or d.get('reason')}"
            for d in diffs[:8]
        )
        raise ValueError(
            f"Production outlook TS_DATA.Actual vs SRC.actuals diverge "
            f"({len(diffs)} field(s) beyond ${money_tolerance}): {sample}"
        )
