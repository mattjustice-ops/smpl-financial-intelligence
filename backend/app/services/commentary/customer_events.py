"""Large customers the revenue paragraph may name.

A customer is included when that customer's amount clears materiality.
The largest customer in a bucket is named. The others that also clear
the bar are a count and a total, so the paragraph stays one sentence.
Amounts are ARR. They sit beside recognized revenue.
"""

from __future__ import annotations

from typing import Any

BUCKETS = ("New Business", "Expansion", "Contraction", "Churn", "Reactivation")


def _amount(raw: dict[str, Any]) -> float | None:
    value = raw.get("amount")
    if value in (None, ""):
        value = raw.get("arr")
    try:
        return abs(float(value))
    except (TypeError, ValueError):
        return None


def _brief(rows: list[dict[str, float | str]], *, bucket: str, outcome: str) -> dict[str, Any] | None:
    ordered = sorted(rows, key=lambda item: (-float(item["amount"]), str(item["customer"])))
    if not ordered:
        return None
    named = ordered[0]
    rest = ordered[1:]
    return {
        "bucket": bucket,
        "customer": named["customer"],
        "amount": round(float(named["amount"]), 2),
        "others": len(rest),
        "others_amount": round(sum(float(item["amount"]) for item in rest), 2),
        "outcome": outcome,
    }


def _by_customer(pieces: list[dict[str, Any]], *, materiality: float) -> list[dict[str, float | str]]:
    totals: dict[str, float] = {}
    for piece in pieces:
        customer = str(piece.get("customer") or "").strip()
        amount = _amount(piece)
        if not customer or amount is None or amount < materiality:
            continue
        totals[customer] = totals.get(customer, 0.0) + amount
    return [{"customer": name, "amount": round(total, 2)} for name, total in totals.items() if total >= materiality]


def brief_lost(deals: list[dict[str, Any]], materiality: float) -> list[dict[str, Any]]:
    """Large closed-lost customers, one brief per opportunity type."""
    lost = [deal for deal in deals if str(deal.get("outcome") or "") == "lost"]
    kinds = [kind for kind in BUCKETS if any(str(deal.get("type") or "").strip() == kind for deal in lost)]
    for deal in lost:
        kind = str(deal.get("type") or "").strip()
        if kind and kind not in kinds:
            kinds.append(kind)
    events: list[dict[str, Any]] = []
    for kind in kinds:
        rows = _by_customer(
            [deal for deal in lost if str(deal.get("type") or "").strip() == kind],
            materiality=materiality,
        )
        event = _brief(rows, bucket=kind, outcome="lost")
        if event:
            events.append(event)
    return events


def brief_movements(pieces: list[dict[str, Any]], materiality: float) -> list[dict[str, Any]]:
    """What occurred in the month, one event per bucket that has a large customer."""
    events: list[dict[str, Any]] = []
    for bucket in BUCKETS:
        rows = _by_customer(
            [piece for piece in pieces if str(piece.get("type") or "") == bucket],
            materiality=materiality,
        )
        event = _brief(rows, bucket=bucket, outcome="occurred")
        if event:
            events.append(event)
    return events


def pipeline_review(
    expected: list[dict[str, Any]],
    closed: list[dict[str, Any]],
    materiality: float,
) -> list[dict[str, Any]]:
    """Forecast deals for the month, split into what came in and what did not."""
    closed_ids = {str(deal.get("id") or "") for deal in closed if deal.get("id")}
    closed_names = {
        str(deal.get("customer") or "").strip().casefold()
        for deal in closed
        if str(deal.get("customer") or "").strip()
    }
    came: list[dict[str, Any]] = []
    missed: list[dict[str, Any]] = []
    for deal in expected:
        customer = str(deal.get("customer") or "").strip()
        if not customer:
            continue
        deal_id = str(deal.get("id") or "")
        matched = (deal_id and deal_id in closed_ids) or customer.casefold() in closed_names
        lost = str(deal.get("outcome") or "") == "lost"
        (missed if lost or not matched else came).append(deal)
    events: list[dict[str, Any]] = []
    for outcome, deals in (("came in", came), ("did not come in", missed)):
        event = _brief(_by_customer(deals, materiality=materiality), bucket="expected", outcome=outcome)
        if event:
            events.append(event)
    return events
