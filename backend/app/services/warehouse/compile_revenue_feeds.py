"""Derive recognition / implementation / recurring schedules from billing.

Used on Table Update when the customer did not upload those subledgers for the
close month. Totals must still tie to GL before commentary measures attach.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import table_exists

logger = logging.getLogger(__name__)

COMPILED_PREFIX = "compiled:"
CENT = Decimal("0.01")
DEFAULT_RECURRING_RATE = Decimal("0.10")

IMPL_TABLE = "actual_implementation_schedule"
RECOG_TABLE = "actual_revenue_recognition"
RSVC_TABLE = "actual_recurring_services_schedule"
BILLING_TABLE = "actual_invoice_billing_schedule"


def money(value: Decimal) -> str:
    return f"{value.quantize(CENT, rounding=ROUND_HALF_UP):.2f}"


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


def _customer_loaded(db: Session, table: str, org: str, period: str) -> bool:
    if not table_exists(db, table):
        return False
    found = db.execute(
        text(
            f"""
            select 1
            from "{table}"
            where organization_id = :org
              and left(cast(period as text), 7) = :period
              and coalesce(source_filename, '') not like 'compiled:%'
              and coalesce(source_filename, '') not like 'Compiled · %'
            limit 1
            """
        ),
        {"org": org, "period": period},
    ).first()
    return found is not None


def compile_revenue_feeds(
    db: Session,
    organization_id: uuid.UUID,
    period: str,
    *,
    subscriptions: list[dict[str, Any]] | None = None,
) -> bool:
    """Write impl / recognition / recurring from billing when those tables are empty for the month."""
    org = str(organization_id)
    if not table_exists(db, BILLING_TABLE):
        return False
    billing = _billing_rows(db, org, period)
    if not billing:
        return False
    wrote = False
    wrote = _compile_implementation(db, org, period, billing) or wrote
    wrote = _compile_recognition_and_recurring(db, org, period, billing, subscriptions or []) or wrote
    return wrote


def _billing_rows(db: Session, org: str, period: str) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            f"""
            select *
            from "{BILLING_TABLE}"
            where organization_id = :org and left(cast(period as text), 7) = :period
            """
        ),
        {"org": org, "period": period},
    ).mappings()
    return [dict(row) for row in rows]


def _is_implementation(driver: str) -> bool:
    text_value = (driver or "").casefold()
    return "implementation" in text_value or text_value.startswith("imp")


def _is_subscription_bundle(driver: str) -> bool:
    text_value = (driver or "").casefold()
    return "subscription" in text_value or "recurring" in text_value


def _compile_implementation(
    db: Session, org: str, period: str, billing: list[dict[str, Any]]
) -> bool:
    if not table_exists(db, IMPL_TABLE) or _customer_loaded(db, IMPL_TABLE, org, period):
        return False
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(billing):
        if not _is_implementation(str(raw.get("driver") or "")):
            continue
        fee = _dec(raw.get("billings"))
        if fee == 0:
            continue
        rows.append(
            {
                "version": "Actual",
                "customer_id": str(raw.get("customer_id") or ""),
                "customer_name": str(raw.get("customer_name") or ""),
                "segment": "",
                "source": "billing",
                "source_record_id": str(raw.get("invoice_id") or ""),
                "win_probability": "1",
                "implementation_fee": money(fee),
                "invoice_id": str(raw.get("invoice_id") or ""),
                "invoice_date": str(raw.get("invoice_date") or ""),
                "due_date": str(raw.get("due_date") or ""),
                "collection_period": str(raw.get("collection_period") or ""),
            }
        )
    if not rows:
        return False
    return _replace_compiled_rows(db, IMPL_TABLE, org, period, rows, f"{COMPILED_PREFIX}billing_impl:{period}")


def _recurring_rate(db: Session, org: str, period: str) -> Decimal:
    """Prefer the last loaded recognition month's recurring ÷ subscription; else default."""
    if not table_exists(db, RECOG_TABLE):
        return DEFAULT_RECURRING_RATE
    found = db.execute(
        text(
            f"""
            select left(cast(period as text), 7) as per,
                   sum(case when lower(coalesce(revenue_type,'')) like '%subscription%'
                             and lower(coalesce(revenue_type,'')) not like '%recurring%'
                             and lower(coalesce(revenue_type,'')) not like '%implement%'
                            then cast(recognized_revenue as numeric) else 0 end) as sub,
                   sum(case when lower(coalesce(revenue_type,'')) like '%recurring%'
                            then cast(recognized_revenue as numeric) else 0 end) as rsvc
            from "{RECOG_TABLE}"
            where organization_id = :org
              and left(cast(period as text), 7) < :period
              and coalesce(source_filename, '') not like 'compiled:%'
            group by 1
            having sum(case when lower(coalesce(revenue_type,'')) like '%subscription%'
                             and lower(coalesce(revenue_type,'')) not like '%recurring%'
                            then cast(recognized_revenue as numeric) else 0 end) > 0
            order by 1 desc
            limit 1
            """
        ),
        {"org": org, "period": period},
    ).first()
    if not found or not found[1]:
        return DEFAULT_RECURRING_RATE
    sub, rsvc = _dec(found[1]), _dec(found[2])
    if sub <= 0:
        return DEFAULT_RECURRING_RATE
    rate = (rsvc / sub).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    if rate <= 0 or rate >= 1:
        return DEFAULT_RECURRING_RATE
    return rate


def _compile_recognition_and_recurring(
    db: Session,
    org: str,
    period: str,
    billing: list[dict[str, Any]],
    subscriptions: list[dict[str, Any]],
) -> bool:
    need_recog = table_exists(db, RECOG_TABLE) and not _customer_loaded(db, RECOG_TABLE, org, period)
    need_rsvc = table_exists(db, RSVC_TABLE) and not _customer_loaded(db, RSVC_TABLE, org, period)
    if not need_recog and not need_rsvc:
        return False

    bundle_total = sum(
        (_dec(raw.get("billings")) for raw in billing if _is_subscription_bundle(str(raw.get("driver") or ""))),
        Decimal("0"),
    )
    impl_total = sum(
        (_dec(raw.get("billings")) for raw in billing if _is_implementation(str(raw.get("driver") or ""))),
        Decimal("0"),
    )
    if bundle_total <= 0 and impl_total <= 0:
        return False

    rate = _recurring_rate(db, org, period)
    # subscription + recurring = bundle; split by rate: rsvc = rate/(1+rate)*bundle when
    # recurring is rate * subscription and bundle = sub + rsvc = sub*(1+rate)
    sub_total = (bundle_total / (Decimal("1") + rate)).quantize(CENT, rounding=ROUND_HALF_UP)
    rsvc_total = (bundle_total - sub_total).quantize(CENT, rounding=ROUND_HALF_UP)

    weights = _customer_arr_weights(subscriptions)
    if not weights:
        # Fall back to billing customer shares for the bundle drivers
        weights = {}
        for raw in billing:
            if not _is_subscription_bundle(str(raw.get("driver") or "")):
                continue
            cid = str(raw.get("customer_id") or "")
            if cid:
                weights[cid] = weights.get(cid, Decimal("0")) + _dec(raw.get("billings"))
    if not weights:
        return False
    weight_sum = sum(weights.values(), Decimal("0"))
    if weight_sum <= 0:
        return False

    names = {
        str(raw.get("customer_id") or ""): str(raw.get("customer_name") or "")
        for raw in billing
        if raw.get("customer_id")
    }

    recog_rows: list[dict[str, Any]] = []
    rsvc_rows: list[dict[str, Any]] = []
    allocated_sub = Decimal("0")
    allocated_rsvc = Decimal("0")
    ordered = sorted(weights.items(), key=lambda item: (-item[1], item[0]))
    for index, (customer_id, weight) in enumerate(ordered):
        share = weight / weight_sum
        if index == len(ordered) - 1:
            sub_amt = (sub_total - allocated_sub).quantize(CENT, rounding=ROUND_HALF_UP)
            rsvc_amt = (rsvc_total - allocated_rsvc).quantize(CENT, rounding=ROUND_HALF_UP)
        else:
            sub_amt = (sub_total * share).quantize(CENT, rounding=ROUND_HALF_UP)
            rsvc_amt = (rsvc_total * share).quantize(CENT, rounding=ROUND_HALF_UP)
            allocated_sub += sub_amt
            allocated_rsvc += rsvc_amt
        arr = weight
        name = names.get(customer_id) or customer_id
        if need_recog and sub_amt != 0:
            recog_rows.append(
                {
                    "version": "Actual",
                    "customer_id": customer_id,
                    "customer_name": name,
                    "recognized_revenue": money(sub_amt),
                    "recognized_arr": money(arr),
                    "revenue_type": "Subscription",
                }
            )
        if need_recog and rsvc_amt != 0:
            recog_rows.append(
                {
                    "version": "Actual",
                    "customer_id": customer_id,
                    "customer_name": name,
                    "recognized_revenue": money(rsvc_amt),
                    "recognized_arr": money(arr),
                    "revenue_type": "Recurring Services",
                }
            )
        if need_rsvc and rsvc_amt != 0:
            rsvc_rows.append(
                {
                    "version": "Actual",
                    "customer_id": customer_id,
                    "customer_name": name,
                    "segment": "",
                    "weight_source": "compiled subscription ARR",
                    "customer_arr": money(arr),
                    "month_subscription_revenue": money(sub_amt),
                    "rate": str(rate),
                    "recurring_services_revenue": money(rsvc_amt),
                    "invoice_id": "",
                    "invoice_date": "",
                    "due_date": "",
                    "collection_period": "",
                }
            )

    # Implementation recognition rows
    if need_recog:
        for raw in billing:
            if not _is_implementation(str(raw.get("driver") or "")):
                continue
            fee = _dec(raw.get("billings"))
            if fee == 0:
                continue
            recog_rows.append(
                {
                    "version": "Actual",
                    "customer_id": str(raw.get("customer_id") or ""),
                    "customer_name": str(raw.get("customer_name") or ""),
                    "recognized_revenue": money(fee),
                    "recognized_arr": "0.00",
                    "revenue_type": "Implementation & Onboarding",
                }
            )

    wrote = False
    if need_recog and recog_rows:
        wrote = (
            _replace_compiled_rows(
                db, RECOG_TABLE, org, period, recog_rows, f"{COMPILED_PREFIX}billing_recognition:{period}"
            )
            or wrote
        )
    if need_rsvc and rsvc_rows:
        wrote = (
            _replace_compiled_rows(
                db, RSVC_TABLE, org, period, rsvc_rows, f"{COMPILED_PREFIX}billing_rsvc:{period}"
            )
            or wrote
        )
    return wrote


def _customer_arr_weights(subscriptions: list[dict[str, Any]]) -> dict[str, Decimal]:
    weights: dict[str, Decimal] = {}
    for row in subscriptions:
        customer = str(row.get("customer_id") or "")
        if not customer:
            continue
        amount = _dec(row.get("current_arr"))
        if amount <= 0 and row.get("current_mrr") not in (None, ""):
            amount = _dec(row.get("current_mrr")) * 12
        if amount <= 0:
            continue
        status = str(row.get("status") or "").casefold()
        if status and status not in {"active", "live", ""}:
            continue
        weights[customer] = weights.get(customer, Decimal("0")) + amount
    return weights


def _replace_compiled_rows(
    db: Session,
    table: str,
    org: str,
    period: str,
    rows: list[dict[str, Any]],
    filename: str,
) -> bool:
    columns = _table_columns(db, table)
    if "period" not in columns:
        return False
    db.execute(
        text(
            f"""
            delete from "{table}"
            where organization_id = :org
              and left(cast(period as text), 7) = :period
              and (
                coalesce(source_filename, '') like 'compiled:%'
                or coalesce(source_filename, '') like 'Compiled · %'
              )
            """
        ),
        {"org": org, "period": period},
    )
    nxt = db.execute(
        text(f'select coalesce(max(source_row_number), 0) + 1 from "{table}" where organization_id = :org'),
        {"org": org},
    ).scalar()
    start = int(nxt or 1)
    for index, values in enumerate(rows):
        payload: dict[str, Any] = {
            "organization_id": org,
            "source_row_number": start + index,
            "source_filename": filename,
            "period": period if "period" in columns else f"{period}-01",
        }
        # Prefer YYYY-MM-01 when column looks date-like via existing rows; store month key as text period.
        if columns and "period" in columns:
            payload["period"] = f"{period}-01" if period.count("-") == 1 else period
        payload.update(values)
        used = [
            key
            for key in payload
            if key in columns or key in {"organization_id", "source_row_number", "source_filename"}
        ]
        names = ", ".join(f'"{key}"' for key in used)
        marks = ", ".join(f":{key}" for key in used)
        db.execute(
            text(f'insert into "{table}" ({names}) values ({marks})'),
            {key: payload[key] for key in used},
        )
    return True
