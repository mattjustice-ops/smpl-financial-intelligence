"""DB-facing helpers for the bookings forecast engine.

Loads opportunities from the demo `opportunities` table and (optionally)
computes default historical win rates from rows whose `stage` matches the
configured "won" / "lost" labels — useful in demos where no separate
closed-opportunity feed exists yet.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.demo_finance import Opportunity as OpportunityRow
from app.services.bookings.engine import Opportunity, WinRates

DEFAULT_WON_STAGES: frozenset[str] = frozenset({"Closed Won", "closed_won", "won"})
DEFAULT_LOST_STAGES: frozenset[str] = frozenset({"Closed Lost", "closed_lost", "lost"})

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


def _to_decimal(v: object) -> Decimal:
    if v is None:
        return ZERO
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def normalize_probability(p: object) -> Decimal:
    """Return probability in 0..1 form, accepting either 0..1 or 0..100.

    A value > 1 is treated as a percentage (e.g. 70 -> 0.70). Values are
    clamped to [0, 1] so a stray 250 won't blow up the forecast.
    """
    v = _to_decimal(p)
    if v > ONE:
        v = v / HUNDRED
    if v < ZERO:
        return ZERO
    if v > ONE:
        return ONE
    return v


def load_open_opportunities(
    session: Session,
    organization_id: uuid.UUID,
    *,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    won_stages: Iterable[str] = DEFAULT_WON_STAGES,
    lost_stages: Iterable[str] = DEFAULT_LOST_STAGES,
) -> list[Opportunity]:
    """Return open (not yet won/lost) opportunities, optionally filtered to a window."""
    closed = set(won_stages) | set(lost_stages)
    stmt = select(OpportunityRow).where(OpportunityRow.organization_id == organization_id)
    if period_start is not None:
        stmt = stmt.where(OpportunityRow.expected_close_date >= period_start)
    if period_end is not None:
        stmt = stmt.where(OpportunityRow.expected_close_date <= period_end)

    out: list[Opportunity] = []
    for row in session.scalars(stmt).all():
        if row.stage and row.stage in closed:
            continue
        if row.expected_close_date is None:
            # Without an expected_close_date we cannot bucket this opportunity,
            # so it cannot contribute to a period forecast.
            continue
        out.append(
            Opportunity(
                opportunity_id=row.opportunity_id,
                customer_id=row.customer_id,
                stage=row.stage or "Unknown",
                amount=_to_decimal(row.amount_arr),
                probability=normalize_probability(row.probability),
                expected_close_date=row.expected_close_date,
                rep_id=row.rep_id,
                segment=row.segment,
                pipeline_created_date=None,
            )
        )
    return out


def compute_historical_win_rates(
    session: Session,
    organization_id: uuid.UUID,
    *,
    won_stages: Iterable[str] = DEFAULT_WON_STAGES,
    lost_stages: Iterable[str] = DEFAULT_LOST_STAGES,
) -> WinRates:
    """Compute by-stage and by-segment win rates from closed opportunities.

    NOTE: For richer history you'd typically have a closed-opportunity feed
    with explicit `is_won` flags. Here we use opportunity rows whose `stage`
    matches the won/lost labels.
    """
    won_set = set(won_stages)
    lost_set = set(lost_stages)
    stmt = select(OpportunityRow).where(OpportunityRow.organization_id == organization_id)

    by_stage_w: dict[str, int] = defaultdict(int)
    by_stage_t: dict[str, int] = defaultdict(int)
    by_segment_w: dict[str, int] = defaultdict(int)
    by_segment_t: dict[str, int] = defaultdict(int)

    total_w = 0
    total_t = 0

    for row in session.scalars(stmt).all():
        stage = row.stage or "Unknown"
        if stage not in won_set and stage not in lost_set:
            continue
        is_won = stage in won_set
        segment = row.segment or ""
        by_stage_t[stage] += 1
        by_segment_t[segment] += 1
        total_t += 1
        if is_won:
            by_stage_w[stage] += 1
            by_segment_w[segment] += 1
            total_w += 1

    overall = Decimal(total_w) / Decimal(total_t) if total_t > 0 else Decimal("0.25")

    return WinRates(
        by_stage={k: Decimal(by_stage_w[k]) / Decimal(by_stage_t[k]) for k in by_stage_t if by_stage_t[k] > 0},
        by_segment={
            k: Decimal(by_segment_w[k]) / Decimal(by_segment_t[k])
            for k in by_segment_t
            if by_segment_t[k] > 0
        },
        overall=overall,
    )
