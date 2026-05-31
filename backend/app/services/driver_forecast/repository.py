"""Repository helpers over split Actual/Budget/Forecast warehouse tables."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.driver_forecast.common import month_start


def _to_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, str):
        cleaned = value.strip().replace("$", "").replace(",", "")
        if not cleaned:
            return Decimal("0")
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = f"-{cleaned[1:-1]}"
        if cleaned.endswith("%"):
            return Decimal(cleaned[:-1]) / Decimal("100")
        value = cleaned
    return Decimal(str(value))


def _to_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return month_start(value)
    s = str(value)
    if len(s) == 7 and s[4] == "-":
        return date(int(s[:4]), int(s[5:7]), 1)
    return month_start(date.fromisoformat(s[:10]))


def table_exists(session: Session, table_name: str) -> bool:
    bind = session.get_bind()
    if bind.dialect.name == "sqlite":
        return (
            session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
                {"name": table_name},
            ).scalar()
            is not None
        )
    return session.execute(
        text("select to_regclass(:name)"),
        {"name": f"public.{table_name}"},
    ).scalar() is not None


def fetch_table_rows(
    session: Session,
    table_name: str,
    organization_id: uuid.UUID,
) -> list[dict[str, Any]]:
    if not table_exists(session, table_name):
        return []
    org_key: str | uuid.UUID = organization_id
    bind = session.get_bind()
    if bind.dialect.name == "sqlite":
        org_key = str(organization_id)
    rows = session.execute(
        text(f'select * from "{table_name}" where organization_id = :organization_id'),
        {"organization_id": org_key},
    ).mappings()
    return [dict(r) for r in rows]


def fetch_period_rows(
    session: Session,
    *,
    table_name: str,
    organization_id: uuid.UUID,
    period_column: str = "period",
    start_period: date,
    end_period: date,
) -> list[dict[str, Any]]:
    rows = fetch_table_rows(session, table_name, organization_id)
    out: list[dict[str, Any]] = []
    start = month_start(start_period)
    end = month_start(end_period)
    for row in rows:
        period = _to_date(row.get(period_column))
        if period is None or period < start or period > end:
            continue
        row[period_column] = period
        out.append(row)
    return out


def decimal_value(row: dict[str, Any], key: str) -> Decimal:
    return _to_decimal(row.get(key))


def latest_period_value(rows: list[dict[str, Any]], key: str, period_key: str = "period") -> Decimal:
    if not rows:
        return Decimal("0")
    row = sorted(rows, key=lambda r: r.get(period_key) or date.min)[-1]
    return decimal_value(row, key)
