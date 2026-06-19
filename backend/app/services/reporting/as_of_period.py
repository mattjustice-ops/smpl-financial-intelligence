"""Resolve Combined-scenario cutover (last closed Actual month) from warehouse data."""

from __future__ import annotations

import uuid
from contextvars import ContextVar, Token
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.reporting.period_utils import to_period

_active_as_of_period: ContextVar[str | None] = ContextVar("active_as_of_period", default=None)

ACTUAL_PROBE_TABLES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("actual_income_statement", "period", ("revenue",)),
    ("actual_balance_sheet", "period", ("cash",)),
    ("actual_mrr_waterfall", "period", ("ending_arr", "ending_mrr")),
    ("actual_marketing_pipeline", "period", ("pipeline_arr_created",)),
)


def _column_exists(session: Session, table_name: str, column_name: str) -> bool:
    row = session.execute(
        text(
            """
            select 1
            from information_schema.columns
            where table_schema = 'public'
              and table_name = :table_name
              and column_name = :column_name
            limit 1
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).scalar()
    return row is not None


def bind_as_of_period(as_of_period: str) -> Token[str | None]:
    return _active_as_of_period.set(to_period(as_of_period))


def reset_as_of_period(token: Token[str | None]) -> None:
    _active_as_of_period.reset(token)


def active_as_of_period(*, fallback: str | None = None) -> str:
    bound = _active_as_of_period.get()
    if bound:
        return bound
    if fallback:
        return to_period(fallback)
    raise ValueError("as_of_period is not set for this request")


def _table_exists(session: Session, table_name: str) -> bool:
    return (
        session.execute(text("select to_regclass(:name)"), {"name": f"public.{table_name}"}).scalar()
        is not None
    )


def infer_as_of_period(session: Session, organization_id: uuid.UUID) -> str | None:
    """Latest period with non-empty Actual rows in core statement tables."""
    org_key = str(organization_id)
    candidates: list[str] = []
    for table, period_col, value_cols in ACTUAL_PROBE_TABLES:
        if not _table_exists(session, table):
            continue
        present_cols = [col for col in value_cols if _column_exists(session, table, col)]
        if not present_cols:
            continue
        metric_exprs = ", ".join(f'"{col}"' for col in present_cols)
        if len(present_cols) == 1:
            metric_filter = f'"{present_cols[0]}" is not null'
        else:
            metric_filter = f"coalesce({metric_exprs}) is not null"
        row = (
            session.execute(
                text(
                    f"""
                    select max("{period_col}") as period
                    from "{table}"
                    where organization_id = :organization_id
                      and {metric_filter}
                    """
                ),
                {"organization_id": org_key},
            )
            .mappings()
            .first()
        )
        if row and row.get("period") not in (None, ""):
            try:
                candidates.append(to_period(row["period"]))
            except (TypeError, ValueError):
                continue
    if not candidates:
        return None
    return max(candidates)


def resolve_as_of_period(
    session: Session,
    organization_id: uuid.UUID,
    *,
    as_of_period: str | date | None = None,
    end_period: str | date | None = None,
) -> str:
    if as_of_period not in (None, ""):
        return to_period(as_of_period)
    inferred = infer_as_of_period(session, organization_id)
    if inferred:
        return inferred
    if end_period not in (None, ""):
        return to_period(end_period)
    return f"{date.today().year:04d}-01"
