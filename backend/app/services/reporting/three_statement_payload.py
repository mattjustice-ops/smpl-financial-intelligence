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

IS_KEY_MAP: dict[str, str] = {
    "revenue": "revenue",
    "cost_of_revenue": "cogs",
    "gross_profit": "gross_profit",
    "sales_and_marketing": "sm",
    "research_and_development": "rd",
    "general_and_administrative": "ga",
    "total_operating_expenses": "total_opex",
    "ebitda": "ebitda",
    "depreciation_and_amortization": "da",
    "interest_expense": "interest",
    "net_income": "net_income",
}

BS_KEY_MAP: dict[str, str] = {
    "cash": "cash",
    "accounts_receivable": "ar",
    "accounts_payable": "ap",
    "deferred_revenue": "dr",
    "equity": "equity",
}

CFS_KEY_MAP: dict[str, str] = {
    "beginning_cash": "beginning_cash",
    "net_income": "net_income",
    "depreciation_and_amortization": "da",
    "stock_based_compensation": "sbc",
    "change_in_accounts_receivable": "chg_ar",
    "change_in_deferred_revenue": "chg_dr",
    "change_in_accounts_payable": "chg_ap",
    "change_in_prepaids": "chg_prepaids",
    "net_cash_from_operating_activities": "cfo",
    "capital_expenditures": "capex",
    "net_cash_from_investing_activities": "cfi",
    "net_cash_from_financing_activities": "cff",
    "net_change_in_cash": "net_change",
    "ending_cash": "ending_cash",
}


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


def _period_dict_from_rows(
    rows: list[dict[str, Any]],
    key_map: dict[str, str],
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
        for src, dst in key_map.items():
            val = _dec(value_any(raw, src, src.replace("_", " ")))
            if val is not None:
                bucket[dst] = val
        if extra:
            for k, fn in extra.items():
                bucket[k] = fn(bucket)
    return out


def _enrich_is(row: dict[str, float | None]) -> None:
    rev = row.get("revenue")
    gp = row.get("gross_profit")
    if rev and rev != 0:
        row["sub_rev"] = rev * 0.967
        row["svc_rev"] = rev * 0.033
        row["gm_pct"] = (gp / rev) if gp is not None else None
    opex = (row.get("sm") or 0) + (row.get("rd") or 0) + (row.get("ga") or 0)
    if row.get("total_opex") is None and opex:
        row["total_opex"] = opex
    row.setdefault("op_income", row.get("ebitda"))
    row.setdefault("pretax", row.get("net_income"))
    row.setdefault("tax", 0.0)


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
    for scenario, prefix in (("Actual", "actual"), ("Forecast", "forecast"), ("Budget", "budget")):
        is_rows = _read_statement_table(db, organization_id, f"{prefix}_income_statement")
        bs_rows = _read_statement_table(db, organization_id, f"{prefix}_balance_sheet")
        cfs_rows = _read_statement_table(db, organization_id, f"{prefix}_cash_flow_statement")

        is_data = _period_dict_from_rows(is_rows, IS_KEY_MAP)
        for period, row in is_data.items():
            _enrich_is(row)

        bs_data = _period_dict_from_rows(bs_rows, BS_KEY_MAP)
        cfs_data = _period_dict_from_rows(cfs_rows, CFS_KEY_MAP)

        periods = sorted(
            {
                p
                for p in period_range(start_period, end_period)
                if p in is_data or p in bs_data or p in cfs_data
            }
        )
        if not periods:
            continue
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
    cfs_rows = _read_statement_table(db, organization_id, "actual_cash_flow_statement")
    mrr_rows = _read_statement_table(db, organization_id, "actual_mrr_waterfall")

    is_by_period = _period_dict_from_rows(is_rows, IS_KEY_MAP)
    bs_by_period = _period_dict_from_rows(bs_rows, BS_KEY_MAP)
    cfs_by_period = _period_dict_from_rows(cfs_rows, CFS_KEY_MAP)

    for period in sorted(set(is_by_period) | set(bs_by_period) | set(cfs_by_period)):
        if period > as_of:
            continue
        row: dict[str, float | None] = {}
        row.update(is_by_period.get(period, {}))
        row.update(bs_by_period.get(period, {}))
        row.update(cfs_by_period.get(period, {}))
        for mrr in mrr_rows:
            if to_period(str(mrr.get("period", ""))) != period:
                continue
            row["arr_bop"] = _dec(value_any(mrr, "beginning_arr", "beginning_mrr"))
            row["arr_eop"] = _dec(value_any(mrr, "ending_arr", "ending_mrr"))
            row["arr_nb"] = _dec(value_any(mrr, "new_business_arr", "new_mrr"))
            row["arr_exp"] = _dec(value_any(mrr, "expansion_arr", "expansion_mrr"))
            row["arr_churn"] = _dec(value_any(mrr, "churn_arr", "churn_mrr"))
            row["arr_cont"] = _dec(value_any(mrr, "contraction_arr", "contraction_mrr"))
            row["arr_react"] = _dec(value_any(mrr, "reactivation_arr", "reactivation_mrr"))
            row["arr_nn"] = _dec(value_any(mrr, "net_new_arr", "net_new_mrr"))
            row["nrr"] = _dec(value_any(mrr, "net_dollar_retention_rate", "nrr"))
            row["grr"] = _dec(value_any(mrr, "gross_retention_rate", "grr"))
        if row:
            actuals[period] = row
    return {"actuals": actuals}


def build_shared_reporting_payload(
    db: Session,
    organization_id: uuid.UUID,
    *,
    block_on_validation: bool = True,
) -> dict[str, Any]:
    from app.models.organization import Organization

    org = db.get(Organization, organization_id)
    if org is None:
        raise ValueError("Organization not found")
    ensure_org_reporting_defaults(db, org)
    as_of, start_period, end_period = resolve_org_reporting_window(db, org)

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

    ts_data = build_ts_data(db, organization_id, as_of=as_of, start_period=start_period, end_period=end_period)
    src = build_forecast_engine_src(db, organization_id, as_of=as_of)

    return {
        "meta": {
            "organization_id": str(organization_id),
            "organization_name": org.name,
            "close_month": as_of,
            "start_period": start_period,
            "end_period": end_period,
            "fiscal_year_end_month": int(org.fiscal_year_end_month or 12),
        },
        "TS_DATA": ts_data,
        "SRC": src,
        "validation": bundle.validation.model_dump(mode="json"),
    }
