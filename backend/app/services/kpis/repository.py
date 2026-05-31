"""DB-facing helpers that translate stored rows into KPI engine inputs."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.demo_finance import GlActual, MrrWaterfall, Opportunity
from app.services.mrr.repository import month_start

ZERO = Decimal("0")

# Heuristics to classify GL rows into S&M / OpEx / Revenue buckets.
SM_CATEGORIES = frozenset({"sales", "marketing", "sales & marketing", "s&m", "sm"})
OPEX_STATEMENTS = frozenset({"income", "income_statement", "operating", "opex"})
REVENUE_KEYWORDS = ("revenue", "subscription", "recurring")


def _to_decimal(v: object) -> Decimal:
    if v is None:
        return ZERO
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _categories_contain(value: Optional[str], terms: Iterable[str]) -> bool:
    if not value:
        return False
    v = value.lower()
    return any(t in v for t in terms)


def sum_gl_amount(
    session: Session,
    organization_id: uuid.UUID,
    period_start: date,
    period_end: date,
    *,
    categories: Optional[Iterable[str]] = None,
    statements: Optional[Iterable[str]] = None,
    keywords: Optional[Iterable[str]] = None,
) -> Decimal:
    """Sum gl_actuals.amount in a period, filtered by category/statement/keywords.

    Filters are OR'd against each row's `category` / `statement` / `account_name`.
    """
    stmt = select(GlActual).where(
        GlActual.organization_id == organization_id,
        GlActual.period >= period_start,
        GlActual.period <= period_end,
    )
    total = ZERO
    for row in session.scalars(stmt).all():
        amount = _to_decimal(row.amount)
        if categories and (row.category or "").lower() in {c.lower() for c in categories}:
            total += amount
            continue
        if statements and (row.statement or "").lower() in {s.lower() for s in statements}:
            total += amount
            continue
        if keywords and _categories_contain(row.account_name, keywords):
            total += amount
            continue
    return total


def revenue_for_period(
    session: Session, organization_id: uuid.UUID, period_start: date, period_end: date
) -> Decimal:
    """Sum revenue rows from gl_actuals (account_name contains 'revenue' or similar)."""
    return sum_gl_amount(
        session,
        organization_id,
        period_start,
        period_end,
        keywords=REVENUE_KEYWORDS,
    )


def sales_marketing_expense_for_period(
    session: Session, organization_id: uuid.UUID, period_start: date, period_end: date
) -> Decimal:
    return sum_gl_amount(
        session,
        organization_id,
        period_start,
        period_end,
        categories=SM_CATEGORIES,
    )


def operating_expense_for_period(
    session: Session, organization_id: uuid.UUID, period_start: date, period_end: date
) -> Decimal:
    return sum_gl_amount(
        session,
        organization_id,
        period_start,
        period_end,
        statements=OPEX_STATEMENTS,
    )


def load_mrr_summary_for_period(
    session: Session, organization_id: uuid.UUID, period: date
) -> dict[str, Decimal]:
    """Sum stored mrr_waterfall components for a period."""
    p = month_start(period)
    stmt = select(
        func.coalesce(func.sum(MrrWaterfall.beginning_mrr), 0).label("beginning_mrr"),
        func.coalesce(func.sum(MrrWaterfall.new_mrr), 0).label("new_mrr"),
        func.coalesce(func.sum(MrrWaterfall.expansion_mrr), 0).label("expansion_mrr"),
        func.coalesce(func.sum(MrrWaterfall.contraction_mrr), 0).label("contraction_mrr"),
        func.coalesce(func.sum(MrrWaterfall.churn_mrr), 0).label("churn_mrr"),
        func.coalesce(func.sum(MrrWaterfall.reactivation_mrr), 0).label("reactivation_mrr"),
        func.coalesce(func.sum(MrrWaterfall.ending_mrr), 0).label("ending_mrr"),
    ).where(and_(MrrWaterfall.organization_id == organization_id, MrrWaterfall.period == p))
    row = session.execute(stmt).one()
    return {
        "beginning_mrr": _to_decimal(row.beginning_mrr),
        "new_mrr": _to_decimal(row.new_mrr),
        "expansion_mrr": _to_decimal(row.expansion_mrr),
        "contraction_mrr": _to_decimal(row.contraction_mrr),
        "churn_mrr": _to_decimal(row.churn_mrr),
        "reactivation_mrr": _to_decimal(row.reactivation_mrr),
        "ending_mrr": _to_decimal(row.ending_mrr),
    }


def load_customer_counts(
    session: Session, organization_id: uuid.UUID, period: date
) -> dict[str, int]:
    """Customer counts derived from stored mrr_waterfall rows for `period`."""
    p = month_start(period)
    stmt = select(MrrWaterfall).where(
        MrrWaterfall.organization_id == organization_id,
        MrrWaterfall.period == p,
    )
    rows = session.scalars(stmt).all()
    active_begin = sum(1 for r in rows if _to_decimal(r.beginning_mrr) > ZERO)
    active_end = sum(1 for r in rows if _to_decimal(r.ending_mrr) > ZERO)
    new = sum(1 for r in rows if r.movement_type == "new")
    churned = sum(1 for r in rows if r.movement_type == "churn")
    return {
        "active_customers_beginning": active_begin,
        "active_customers_ending": active_end,
        "new_customers": new,
        "churned_customers": churned,
    }


def load_pipeline_for_period(
    session: Session, organization_id: uuid.UUID, period_start: date, period_end: date
) -> Decimal:
    """Sum amount_arr across open opportunities closing in [period_start, period_end]."""
    closed_stages = {"Closed Won", "closed_won", "won", "Closed Lost", "closed_lost", "lost"}
    stmt = select(Opportunity).where(
        Opportunity.organization_id == organization_id,
        Opportunity.expected_close_date >= period_start,
        Opportunity.expected_close_date <= period_end,
    )
    total = ZERO
    for row in session.scalars(stmt).all():
        if row.stage in closed_stages:
            continue
        total += _to_decimal(row.amount_arr)
    return total


def new_bookings_arr_for_period(
    session: Session, organization_id: uuid.UUID, period_start: date, period_end: date
) -> Decimal:
    """Sum amount_arr across opportunities marked Closed Won in the period."""
    won = {"Closed Won", "closed_won", "won"}
    stmt = select(Opportunity).where(
        Opportunity.organization_id == organization_id,
        Opportunity.expected_close_date >= period_start,
        Opportunity.expected_close_date <= period_end,
    )
    total = ZERO
    for row in session.scalars(stmt).all():
        if row.stage in won:
            total += _to_decimal(row.amount_arr)
    return total
