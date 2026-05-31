"""DB-facing helpers for the MRR engine.

Responsibilities:
  - Compute per-customer MRR for an arbitrary month, from the demo
    `subscriptions` table (using `current_mrr` as the steady-state value over
    each subscription's lifetime — a reasonable demo simplification).
  - Determine which customers had positive MRR in any month *before* a given
    cutoff (used to distinguish NEW from REACTIVATION).
  - Persist computed customer-level rows back into `mrr_waterfall`.
"""

from __future__ import annotations

import calendar
import uuid
from datetime import date
from decimal import Decimal
from typing import Iterable

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.demo_finance import MrrWaterfall, Subscription
from app.services.mrr.engine import CustomerMrrMovement, quantize_money

ZERO = Decimal("0")


def month_start(d: date) -> date:
    return d.replace(day=1)


def month_end(d: date) -> date:
    last = calendar.monthrange(d.year, d.month)[1]
    return d.replace(day=last)


def previous_month_start(d: date) -> date:
    if d.month == 1:
        return date(d.year - 1, 12, 1)
    return date(d.year, d.month - 1, 1)


def customer_mrr_for_month(
    session: Session, organization_id: uuid.UUID, period_start: date
) -> dict[str, Decimal]:
    """Sum `current_mrr` of all subscriptions active during `period_start`'s month.

    A subscription is active in a month if start_date <= month_end AND
    (end_date IS NULL OR end_date >= month_start).
    """
    m_start = month_start(period_start)
    m_end = month_end(period_start)

    stmt = (
        select(
            Subscription.customer_id,
            func.coalesce(func.sum(Subscription.current_mrr), 0).label("mrr"),
        )
        .where(
            Subscription.organization_id == organization_id,
            Subscription.start_date <= m_end,
            or_(Subscription.end_date.is_(None), Subscription.end_date >= m_start),
        )
        .group_by(Subscription.customer_id)
    )
    return {
        row.customer_id: quantize_money(Decimal(row.mrr or 0))
        for row in session.execute(stmt).all()
    }


def historical_active_customers(
    session: Session, organization_id: uuid.UUID, before_period_start: date
) -> set[str]:
    """Customers that had a subscription start *before* `before_period_start`
    with positive `current_mrr` — i.e., they had MRR at some point in history.
    """
    stmt = (
        select(Subscription.customer_id)
        .where(
            Subscription.organization_id == organization_id,
            Subscription.start_date < before_period_start,
            Subscription.current_mrr.isnot(None),
            Subscription.current_mrr > 0,
        )
        .distinct()
    )
    return {row[0] for row in session.execute(stmt).all()}


def upsert_mrr_waterfall_rows(
    session: Session,
    organization_id: uuid.UUID,
    rows: Iterable[CustomerMrrMovement],
    *,
    chunk_size: int = 500,
) -> int:
    """Upsert customer-level waterfall rows. Returns count upserted."""
    payloads = [
        {
            "organization_id": organization_id,
            "period": r.period,
            "customer_id": r.customer_id,
            "movement_type": r.movement_type.value,
            "beginning_mrr": r.beginning_mrr,
            "new_mrr": r.new_mrr,
            "expansion_mrr": r.expansion_mrr,
            "contraction_mrr": r.contraction_mrr,
            "churn_mrr": r.churn_mrr,
            "reactivation_mrr": r.reactivation_mrr,
            "ending_mrr": r.ending_mrr,
        }
        for r in rows
    ]
    if not payloads:
        return 0

    table = MrrWaterfall.__table__
    pk_cols = [c.name for c in table.primary_key.columns]
    total = 0
    for i in range(0, len(payloads), chunk_size):
        chunk = payloads[i : i + chunk_size]
        stmt = pg_insert(MrrWaterfall).values(chunk)
        excluded = stmt.excluded
        upd = {
            c.name: getattr(excluded, c.name)
            for c in table.columns
            if c.name not in pk_cols and c.name not in {"created_at"}
        }
        upd["updated_at"] = func.now()
        session.execute(stmt.on_conflict_do_update(index_elements=pk_cols, set_=upd))
        total += len(chunk)
    return total


def fetch_persisted_summary(
    session: Session, organization_id: uuid.UUID, period_start: date
) -> dict[str, Decimal]:
    """Sum stored waterfall components for a period (sanity check / dashboards)."""
    stmt = select(
        func.coalesce(func.sum(MrrWaterfall.beginning_mrr), 0).label("beginning_mrr"),
        func.coalesce(func.sum(MrrWaterfall.new_mrr), 0).label("new_mrr"),
        func.coalesce(func.sum(MrrWaterfall.expansion_mrr), 0).label("expansion_mrr"),
        func.coalesce(func.sum(MrrWaterfall.contraction_mrr), 0).label("contraction_mrr"),
        func.coalesce(func.sum(MrrWaterfall.churn_mrr), 0).label("churn_mrr"),
        func.coalesce(func.sum(MrrWaterfall.reactivation_mrr), 0).label("reactivation_mrr"),
        func.coalesce(func.sum(MrrWaterfall.ending_mrr), 0).label("ending_mrr"),
    ).where(
        and_(
            MrrWaterfall.organization_id == organization_id,
            MrrWaterfall.period == period_start,
        )
    )
    row = session.execute(stmt).one()
    return {
        "beginning_mrr": Decimal(row.beginning_mrr or 0),
        "new_mrr": Decimal(row.new_mrr or 0),
        "expansion_mrr": Decimal(row.expansion_mrr or 0),
        "contraction_mrr": Decimal(row.contraction_mrr or 0),
        "churn_mrr": Decimal(row.churn_mrr or 0),
        "reactivation_mrr": Decimal(row.reactivation_mrr or 0),
        "ending_mrr": Decimal(row.ending_mrr or 0),
    }
