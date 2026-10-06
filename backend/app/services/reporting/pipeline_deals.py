"""CRM deals for the Forecast Engine GTM tab, read from the deal tables.

Closed months come from ``actual_opportunities`` (the deals behind the booked waterfall);
later months come from ``forecast_opportunities`` (the open pipeline). Each month and deal
type carries the same shape the engine's built-in pipeline uses, plus ``expected``: deals
expected to close (closed deals count 1, open deals count their probability). Closed-lost
deals are listed with ``outcome: lost`` and summed in ``lost_total`` / ``lost_count`` only.

The pipeline book (open pipe, created, won, lost, slipped) comes from the pipeline waterfall
tables for the deal types sales works: New Business, Expansion and Reactivation.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import fetch_table_rows
from app.services.reporting.period_utils import to_period

DEAL_TYPES = ("New Business", "Expansion", "Reactivation", "Contraction", "Churn")
NEW_BUSINESS = "New Business"
BOOKING_TYPES = ("New Business", "Expansion", "Reactivation")
BOOK_FIELDS = {
    "begin": ("beginning_pipeline_arr",),
    "created": ("pipeline_arr_created", "new_pipeline_created"),
    "won": ("closed_won_arr",),
    "lost": ("closed_lost_arr",),
    "slipped": ("slipped_pipeline_arr", "slipped_arr"),
    "end": ("ending_pipeline_arr",),
}
FORECAST_BOOK_FIELDS = ("created", "lost", "slipped")


def _num(value: Any) -> float:
    try:
        return float(str(value).replace(",", "").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def _deal_period(raw: dict[str, Any]) -> str | None:
    value = raw.get("period") or raw.get("forecast_period")
    if value in (None, ""):
        return None
    try:
        return to_period(value)
    except (TypeError, ValueError):
        return None


def _is_lost(raw: dict[str, Any]) -> bool:
    return any("lost" in str(raw.get(k) or "").lower() for k in ("close_status", "stage"))


def _deal(raw: dict[str, Any], *, closed: bool) -> dict[str, Any]:
    arr = _num(raw.get("amount_arr"))
    if _is_lost(raw):
        outcome, prob = "lost", 0.0
    else:
        outcome, prob = ("won", 1.0) if closed else ("open", _num(raw.get("probability")))
    return {
        "id": raw.get("opportunity_id"),
        "customer": raw.get("customer_name") or raw.get("customer_id") or "",
        "stage": raw.get("stage") or "",
        "segment": raw.get("segment") or "",
        "region": raw.get("region") or "",
        "owner": raw.get("owner") or "",
        "channel": raw.get("marketing_channel") or "",
        "billing": raw.get("billing_cadence") or "",
        "arr": round(arr, 2),
        "weighted": round(arr * prob, 2),
        "prob": round(prob * 100),
        "probability": prob,
        "outcome": outcome,
    }


def _add(buckets: dict[str, dict[str, dict[str, Any]]], period: str, deal_type: str, deal: dict[str, Any]) -> None:
    bucket = buckets[period].setdefault(
        deal_type,
        {"total": 0.0, "weighted": 0.0, "count": 0, "expected": 0.0, "lost_total": 0.0, "lost_count": 0, "deals": []},
    )
    if deal["outcome"] == "lost":
        deal.pop("probability")
        bucket["lost_total"] += deal["arr"]
        bucket["lost_count"] += 1
        bucket["deals"].append(deal)
        return
    bucket["total"] += deal["arr"]
    bucket["weighted"] += deal["weighted"]
    bucket["count"] += 1
    bucket["expected"] += deal.pop("probability")
    bucket["deals"].append(deal)


def pipeline_from_rows(
    actual_rows: Iterable[dict[str, Any]],
    forecast_rows: Iterable[dict[str, Any]],
    *,
    as_of: str,
) -> dict[str, Any]:
    """``{period: {deal_type: {total, weighted, count, expected, deals}}}`` from deal rows."""
    buckets: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for raw in actual_rows:
        period, deal_type = _deal_period(raw), raw.get("opportunity_type")
        if period and period <= as_of and deal_type in DEAL_TYPES:
            _add(buckets, period, deal_type, _deal(raw, closed=True))
    for raw in forecast_rows:
        period, deal_type = _deal_period(raw), raw.get("opportunity_type")
        if period and period > as_of and deal_type in DEAL_TYPES:
            _add(buckets, period, deal_type, _deal(raw, closed=False))
    out: dict[str, Any] = {}
    for period in sorted(buckets):
        out[period] = {}
        for deal_type in DEAL_TYPES:
            bucket = buckets[period].get(deal_type)
            if not bucket:
                continue
            bucket["deals"].sort(key=lambda d: -d["weighted"])
            bucket["total"] = round(bucket["total"], 2)
            bucket["weighted"] = round(bucket["weighted"], 2)
            bucket["expected"] = round(bucket["expected"], 4)
            bucket["lost_total"] = round(bucket["lost_total"], 2)
            out[period][deal_type] = bucket
    return out


def _book_value(raw: dict[str, Any], names: tuple[str, ...]) -> float:
    for name in names:
        if raw.get(name) not in (None, ""):
            return _num(raw.get(name))
    return 0.0


def pipeline_book_from_rows(
    actual_rows: Iterable[dict[str, Any]],
    forecast_rows: Iterable[dict[str, Any]],
    *,
    as_of: str,
) -> dict[str, dict[str, float]]:
    """Monthly pipeline book for New Business + Expansion + Reactivation.

    Closed months carry all six waterfall fields from the actual table. Later months carry
    only created / lost / slipped from the forecast table: the engine rolls the open pipe
    forward from the last closed month and takes won from the weighted deals.
    """
    out: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for rows, closed in ((actual_rows, True), (forecast_rows, False)):
        fields = BOOK_FIELDS if closed else {k: BOOK_FIELDS[k] for k in FORECAST_BOOK_FIELDS}
        for raw in rows:
            period = _deal_period(raw)
            if not period or raw.get("opportunity_type") not in BOOKING_TYPES or (period <= as_of) != closed:
                continue
            for key, names in fields.items():
                out[period][key] += _book_value(raw, names)
    return {p: {k: round(v, 2) for k, v in out[p].items()} for p in sorted(out)}


def build_pipeline_book(db: Session, organization_id: uuid.UUID, *, as_of: str) -> dict[str, dict[str, float]]:
    """Pipeline book from the pipeline waterfall tables; empty when they are not loaded."""
    return pipeline_book_from_rows(
        fetch_table_rows(db, "actual_pipeline_waterfall", organization_id),
        fetch_table_rows(db, "forecast_pipeline_waterfall", organization_id),
        as_of=as_of,
    )


def build_opp_pipeline(db: Session, organization_id: uuid.UUID, *, as_of: str) -> dict[str, Any]:
    """CRM pipeline from the deal tables; empty when they are not loaded."""
    return pipeline_from_rows(
        fetch_table_rows(db, "actual_opportunities", organization_id),
        fetch_table_rows(db, "forecast_opportunities", organization_id),
        as_of=as_of,
    )


def closed_new_business_acv(pipeline: dict[str, Any], *, as_of: str) -> float | None:
    """Average ARR of closed New Business deals through ``as_of``; None without closed deals."""
    total, count = 0.0, 0
    for period, by_type in pipeline.items():
        nb = by_type.get(NEW_BUSINESS) if period <= as_of else None
        if nb:
            total += nb["total"]
            count += nb["count"]
    return round(total / count, 2) if count else None
