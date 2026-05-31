"""Load gl_actuals rows for financial statement generation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.demo_finance import GlActual
from app.services.mrr.repository import month_start, previous_month_start


@dataclass(frozen=True)
class GlRow:
    period: date
    account_number: str
    account_name: Optional[str]
    statement: Optional[str]
    category: Optional[str]
    amount: Decimal
    currency: Optional[str]
    subsidiary: str


def _to_decimal(v: object) -> Decimal:
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def fetch_gl_rows(
    session: Session,
    organization_id: uuid.UUID,
    *,
    period_start: date,
    period_end: date,
    subsidiary: Optional[str] = None,
    version: str = "Actual",
) -> list[GlRow]:
    """Return GL rows whose period falls in [month_start(period_start), month_start(period_end)]."""
    # Include the month before period_start so balance-sheet deltas / cash flow can
    # compute beginning balances.
    p_start = previous_month_start(month_start(period_start))
    p_end = month_start(period_end)
    stmt = (
        select(GlActual)
        .where(
            GlActual.organization_id == organization_id,
            GlActual.period >= p_start,
            GlActual.period <= p_end,
            GlActual.version == version,
        )
        .order_by(GlActual.period, GlActual.account_number)
    )
    rows: list[GlRow] = []
    for r in session.scalars(stmt).all():
        if subsidiary is not None and (r.subsidiary or "") != subsidiary:
            continue
        rows.append(
            GlRow(
                period=r.period,
                account_number=r.account_number,
                account_name=r.account_name,
                statement=r.statement,
                category=r.category or r.statement_category,
                amount=_to_decimal(r.amount),
                currency=r.currency,
                subsidiary=r.subsidiary or "",
            )
        )
    return rows


def prior_period_for_bs(period_start: date) -> date:
    """Month immediately before period_start (for balance-sheet deltas)."""
    return previous_month_start(month_start(period_start))
