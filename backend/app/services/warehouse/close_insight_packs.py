"""Close insight packs — facts commentary may cite after Table Update.

Six packs: customer behavior, ARR vs revenue/deferred, billings/cash,
forecast miss, GTM capacity, retention. Empty keys are reserved for richer
grain later.
"""

from __future__ import annotations

import json
import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import table_exists
from app.services.reporting.period_utils import prior_period
from app.services.commentary.customer_events import pipeline_review

logger = logging.getLogger(__name__)

FACTS_TABLE = "actual_close_insight_facts"
COMPILED_PREFIX = "compiled:"
CENT = Decimal("0.01")
MATERIALITY = 10_000


def money(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP))


def _dec(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _table_columns(db: Session, table: str) -> set[str]:
    rows = db.execute(
        text(
            """
            select column_name
            from information_schema.columns
            where table_schema = 'public' and table_name = :table
            """
        ),
        {"table": table},
    ).all()
    return {str(name) for (name,) in rows}


def build_and_store_insight_packs(
    db: Session,
    organization_id: uuid.UUID,
    period: str,
    *,
    deferred: dict[str, float] | None = None,
    bookings: float | None = None,
) -> dict[str, Any]:
    """Build packs for ``period`` and persist when the facts table exists."""
    org = str(organization_id)
    packs = {
        "customer_behavior": _customer_behavior(db, org, period),
        "arr_vs_revenue_deferred": _arr_vs_revenue_deferred(db, org, period, deferred),
        "billings_cash": _billings_cash(db, org, period),
        "forecast_miss": _forecast_miss(db, organization_id, period),
        "gtm_capacity": _gtm_capacity(db, org, period),
        "retention": _retention(db, org, period),
    }
    packs["meta"] = {
        "period": period,
        "bookings": bookings,
        "schema_version": 1,
    }
    _store_packs(db, org, period, packs)
    return packs


def load_insight_packs(db: Session, organization_id: uuid.UUID, period: str) -> dict[str, Any] | None:
    if not table_exists(db, FACTS_TABLE):
        return None
    found = db.execute(
        text(
            f"""
            select packs
            from "{FACTS_TABLE}"
            where organization_id = :org and left(cast(period as text), 7) = :period
            order by source_row_number desc
            limit 1
            """
        ),
        {"org": str(organization_id), "period": period},
    ).first()
    if not found or found[0] in (None, ""):
        return None
    raw = found[0]
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None


def load_insight_packs_by_period(
    db: Session, organization_id: uuid.UUID, periods: list[str]
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for period in periods:
        packs = load_insight_packs(db, organization_id, period)
        if packs:
            out[period] = packs
    return out


def _store_packs(db: Session, org: str, period: str, packs: dict[str, Any]) -> bool:
    if not table_exists(db, FACTS_TABLE):
        return False
    columns = _table_columns(db, FACTS_TABLE)
    if "packs" not in columns or "period" not in columns:
        return False
    db.execute(
        text(
            f"""
            delete from "{FACTS_TABLE}"
            where organization_id = :org and left(cast(period as text), 7) = :period
            """
        ),
        {"org": org, "period": period},
    )
    nxt = db.execute(
        text(f'select coalesce(max(source_row_number), 0) + 1 from "{FACTS_TABLE}" where organization_id = :org'),
        {"org": org},
    ).scalar()
    payload = {
        "organization_id": org,
        "source_row_number": int(nxt or 1),
        "source_filename": f"{COMPILED_PREFIX}insight_packs:{period}",
        "period": f"{period}-01",
        "version": "Actual",
        "packs": json.dumps(packs),
    }
    used = [key for key in payload if key in columns or key in {"organization_id", "source_row_number", "source_filename"}]
    names = ", ".join(f'"{key}"' for key in used)
    # psycopg3 cannot adapt a raw dict for JSON/JSONB via text(); bind JSON text and cast.
    marks = ", ".join(
        "cast(:packs as jsonb)" if key == "packs" else f":{key}"
        for key in used
    )
    db.execute(text(f'insert into "{FACTS_TABLE}" ({names}) values ({marks})'), {key: payload[key] for key in used})
    return True


def _customer_behavior(db: Session, org: str, period: str) -> dict[str, Any]:
    history = _history_rows(db, org, period)
    mix: dict[str, dict[str, float | int]] = {}
    for row in history:
        bucket = str(row.get("waterfall_line") or row.get("movement_type") or "other")
        amount = abs(_dec(row.get("movement_arr")))
        slot = mix.setdefault(bucket, {"arr": 0.0, "count": 0})
        slot["arr"] = float(Decimal(str(slot["arr"])) + amount)
        slot["count"] = int(slot["count"]) + 1

    movers = sorted(
        (
            {
                "customer_id": str(row.get("customer_id") or ""),
                "customer_name": str(row.get("customer_name") or ""),
                "waterfall_line": str(row.get("waterfall_line") or ""),
                "customer_bucket": str(row.get("customer_bucket") or ""),
                "movement_arr": money(_dec(row.get("movement_arr"))),
            }
            for row in history
            if abs(_dec(row.get("movement_arr"))) >= MATERIALITY
        ),
        key=lambda item: -abs(float(item["movement_arr"] or 0)),
    )[:10]

    nb_period = sum(
        1 for row in history if str(row.get("customer_bucket") or "") == "New Business"
    )
    cs_period = sum(
        1 for row in history if str(row.get("customer_bucket") or "") == "Customer Success"
    )

    trailing = _trailing_bucket_totals(db, org, period, months=6)
    current_churn = float(mix.get("churn", mix.get("no_start", {})).get("arr", 0) or 0)
    if "no_start" in mix:
        current_churn += float(mix["no_start"].get("arr", 0) or 0)
    avg_churn = trailing.get("churn_avg")

    return {
        "mix": mix,
        "top_movers": movers,
        "vintage_split": {"new_business_movers": nb_period, "customer_success_movers": cs_period},
        "vs_run_rate": {
            "churn_arr": current_churn,
            "trailing_churn_avg": avg_churn,
            "churn_above_run_rate": (
                None
                if avg_churn is None
                else money(Decimal(str(current_churn)) - Decimal(str(avg_churn)))
            ),
        },
        # Prepared for later product/UOM grain
        "upgrade_subtype_mix": {},
        "uom_intensity": {},
    }


def _arr_vs_revenue_deferred(
    db: Session, org: str, period: str, deferred: dict[str, float] | None
) -> dict[str, Any]:
    waterfall = _waterfall_row(db, org, period)
    recognized = _recognized_total(db, org, period)
    net_new = None
    if waterfall:
        net_new = money(
            _dec(waterfall.get("new_business_arr"))
            + _dec(waterfall.get("expansion_arr"))
            + _dec(waterfall.get("reactivation_arr"))
            - _dec(waterfall.get("contraction_arr"))
            - _dec(waterfall.get("churn_arr"))
        )
    dr = deferred or _read_deferred(db, org, period) or {}
    return {
        "net_new_arr": net_new,
        "recognized_revenue": money(recognized) if recognized is not None else None,
        "deferred_beginning": money(dr.get("beginning")),
        "deferred_billings": money(dr.get("billings")),
        "deferred_recognized": money(dr.get("recognized")),
        "deferred_ending": money(dr.get("ending")),
        "arr_vs_recognized_gap": (
            None
            if net_new is None or recognized is None
            else money(Decimal(str(net_new)) / 12 - recognized)
        ),
        "asc606_elements": {},
    }


def _billings_cash(db: Session, org: str, period: str) -> dict[str, Any]:
    by_driver: dict[str, float] = {}
    if table_exists(db, "actual_invoice_billing_schedule"):
        rows = db.execute(
            text(
                """
                select coalesce(driver, '') as driver, sum(cast(billings as numeric)) as tot
                from actual_invoice_billing_schedule
                where organization_id = :org and left(cast(period as text), 7) = :period
                group by 1
                """
            ),
            {"org": org, "period": period},
        ).all()
        for driver, tot in rows:
            label = "implementation" if "implement" in str(driver).casefold() else (
                "quarterly" if "quarter" in str(driver).casefold() else (
                    "annual" if "annual" in str(driver).casefold() or "12" in str(driver) else (
                        "monthly" if "month" in str(driver).casefold() else str(driver or "other")
                    )
                )
            )
            by_driver[label] = float(by_driver.get(label, 0) + float(tot or 0))

    collections = None
    if table_exists(db, "actual_cash_collections"):
        found = db.execute(
            text(
                """
                select cash_collections
                from actual_cash_collections
                where organization_id = :org and left(cast(period as text), 7) = :period
                limit 1
                """
            ),
            {"org": org, "period": period},
        ).first()
        if found:
            collections = money(_dec(found[0]))

    bridge_check = None
    bridge_note = None
    if table_exists(db, "actual_cash_flow_bridge"):
        found = db.execute(
            text(
                """
                select bridge_check, notes
                from actual_cash_flow_bridge
                where organization_id = :org and left(cast(period as text), 7) = :period
                limit 1
                """
            ),
            {"org": org, "period": period},
        ).first()
        if found:
            bridge_check = money(_dec(found[0]))
            bridge_note = str(found[1] or "")[:240] or None

    return {
        "billings_by_cadence": by_driver,
        "collections": collections,
        "bridge_check": bridge_check,
        "bridge_note": bridge_note,
        "next_bill_dates": [],
    }


def _forecast_miss(db: Session, organization_id: uuid.UUID, period: str) -> dict[str, Any]:
    try:
        from app.services.reporting.source_trace import forecast_month_deals

        expected, closed = forecast_month_deals(db, organization_id, period)
        events = pipeline_review(expected, closed, MATERIALITY)
    except Exception:
        logger.exception("forecast miss pack failed for %s", period)
        events = []
    return {
        "events": events,
        "expected_count": None,
        "closed_count": None,
        "succeeds_contract_links": [],
    }


def _gtm_capacity(db: Session, org: str, period: str) -> dict[str, Any]:
    nb = None
    waterfall = _waterfall_row(db, org, period)
    if waterfall:
        nb = money(_dec(waterfall.get("new_business_arr")))
    sm = _gl_line_total(db, org, period, accounts=None, line_hint="sales")
    heads = None
    return {
        "new_business_arr": nb,
        "sm_expense": sm,
        "nb_per_sm": (
            None
            if nb is None or not sm
            else money(Decimal(str(nb)) / Decimal(str(sm)))
        ),
        "ae_heads": heads,
        "quota_coverage": None,
    }


def _retention(db: Session, org: str, period: str) -> dict[str, Any]:
    waterfall = _waterfall_row(db, org, period)
    movers = []
    if table_exists(db, "actual_customer_arr_history"):
        rows = db.execute(
            text(
                """
                select customer_name, waterfall_line, movement_arr, customer_bucket
                from actual_customer_arr_history
                where organization_id = :org and left(cast(period as text), 7) = :period
                  and customer_bucket = 'Customer Success'
                order by abs(cast(movement_arr as numeric)) desc
                limit 8
                """
            ),
            {"org": org, "period": period},
        ).mappings()
        movers = [
            {
                "customer_name": str(row.get("customer_name") or ""),
                "waterfall_line": str(row.get("waterfall_line") or ""),
                "movement_arr": money(_dec(row.get("movement_arr"))),
            }
            for row in rows
        ]
    return {
        "gross_retention_rate": (
            float(waterfall["gross_retention_rate"])
            if waterfall and waterfall.get("gross_retention_rate") not in (None, "")
            else None
        ),
        "net_dollar_retention_rate": (
            float(waterfall["net_dollar_retention_rate"])
            if waterfall and waterfall.get("net_dollar_retention_rate") not in (None, "")
            else None
        ),
        "customer_success_movers": movers,
        "cohort_curves": {},
    }


def _history_rows(db: Session, org: str, period: str) -> list[dict[str, Any]]:
    if not table_exists(db, "actual_customer_arr_history"):
        return []
    rows = db.execute(
        text(
            """
            select customer_id, customer_name, movement_type, waterfall_line, customer_bucket,
                   movement_arr, beginning_arr, ending_arr
            from actual_customer_arr_history
            where organization_id = :org and left(cast(period as text), 7) = :period
            """
        ),
        {"org": org, "period": period},
    ).mappings()
    return [dict(row) for row in rows]


def _trailing_bucket_totals(db: Session, org: str, period: str, months: int) -> dict[str, float | None]:
    if not table_exists(db, "actual_mrr_waterfall"):
        return {}
    cursor = period
    churn_vals: list[Decimal] = []
    for _ in range(months):
        cursor = prior_period(cursor)
        if not cursor:
            break
        row = _waterfall_row(db, org, cursor)
        if row:
            churn_vals.append(_dec(row.get("churn_arr")))
    if not churn_vals:
        return {"churn_avg": None}
    avg = sum(churn_vals, Decimal("0")) / Decimal(len(churn_vals))
    return {"churn_avg": money(avg)}


def _waterfall_row(db: Session, org: str, period: str) -> dict[str, Any] | None:
    if not table_exists(db, "actual_mrr_waterfall"):
        return None
    columns = _table_columns(db, "actual_mrr_waterfall")
    wanted = [
        name
        for name in (
            "beginning_arr",
            "ending_arr",
            "new_business_arr",
            "expansion_arr",
            "contraction_arr",
            "churn_arr",
            "reactivation_arr",
            "net_new_arr",
            "gross_retention_rate",
            "net_dollar_retention_rate",
        )
        if name in columns
    ]
    if not wanted:
        return None
    found = db.execute(
        text(
            f"""
            select {", ".join(wanted)}
            from actual_mrr_waterfall
            where organization_id = :org and left(cast(period as text), 7) = :period
            limit 1
            """
        ),
        {"org": org, "period": period},
    ).mappings().first()
    return dict(found) if found else None


def _recognized_total(db: Session, org: str, period: str) -> Decimal | None:
    if not table_exists(db, "actual_revenue_recognition"):
        return None
    found = db.execute(
        text(
            """
            select coalesce(sum(cast(recognized_revenue as numeric)), 0), count(*)
            from actual_revenue_recognition
            where organization_id = :org and left(cast(period as text), 7) = :period
            """
        ),
        {"org": org, "period": period},
    ).first()
    if not found or int(found[1] or 0) == 0:
        return None
    return _dec(found[0])


def _read_deferred(db: Session, org: str, period: str) -> dict[str, float] | None:
    if not table_exists(db, "actual_deferred_revenue_waterfall"):
        return None
    found = db.execute(
        text(
            """
            select beginning_deferred_revenue, new_billings, revenue_recognized, ending_deferred_revenue
            from actual_deferred_revenue_waterfall
            where organization_id = :org and left(cast(period as text), 7) = :period
            limit 1
            """
        ),
        {"org": org, "period": period},
    ).first()
    if not found:
        return None
    return {
        "beginning": float(_dec(found[0])),
        "billings": float(_dec(found[1])),
        "recognized": float(_dec(found[2])),
        "ending": float(_dec(found[3])),
    }


def _gl_line_total(db: Session, org: str, period: str, accounts: list[str] | None, line_hint: str) -> float | None:
    if not table_exists(db, "gl_actuals"):
        return None
    # S&M: expense_type / account_group / account_name contains sales or marketing
    found = db.execute(
        text(
            """
            select coalesce(sum(amount), 0), count(*)
            from gl_actuals
            where organization_id = :org
              and left(cast(period as text), 7) = :period
              and (
                lower(coalesce(account_group, '')) like '%sales%'
                or lower(coalesce(account_group, '')) like '%marketing%'
                or lower(coalesce(expense_type, '')) like '%sales%'
                or lower(coalesce(expense_type, '')) like '%marketing%'
                or lower(coalesce(account_name, '')) like '%sales & marketing%'
              )
            """
        ),
        {"org": org, "period": period},
    ).first()
    if not found or int(found[1] or 0) == 0:
        return None
    # Debit-positive expenses are positive amounts
    return money(_dec(found[0]))
