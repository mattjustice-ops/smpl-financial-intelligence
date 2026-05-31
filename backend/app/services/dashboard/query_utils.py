"""Query helpers for CSV-backed dashboard reporting."""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.reporting.period_utils import scenario_periods, to_period


def decimal_value(value: Any) -> Decimal:
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
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")
    if not parsed.is_finite():
        return Decimal("0")
    return parsed


def value_any(row: dict[str, Any], *keys: str) -> Decimal:
    for key in keys:
        if row.get(key) not in (None, ""):
            return decimal_value(row.get(key))
    return Decimal("0")


def str_any(row: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def table_exists(db: Session, table_name: str) -> bool:
    return db.execute(text("select to_regclass(:name)"), {"name": f"public.{table_name}"}).scalar() is not None


def preferred_table(db: Session, scenario_name: str, suffix: str, fallback: str | None = None) -> str | None:
    versioned = f"{scenario_name.lower()}_{suffix}"
    if table_exists(db, versioned):
        return versioned
    if suffix == "mrr_waterfall" and scenario_name == "Actual" and table_exists(db, "budget_mrr_waterfall"):
        return "budget_mrr_waterfall"
    if fallback and table_exists(db, fallback):
        return fallback
    return None


def fetch_table_rows(db: Session, table_name: str, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    if not table_exists(db, table_name):
        return []
    rows = db.execute(
        text(f'select * from "{table_name}" where organization_id = :organization_id'),
        {"organization_id": str(organization_id)},
    ).mappings()
    return [dict(row) for row in rows]


def filter_row(row: dict[str, Any], filters: dict[str, str | None]) -> bool:
    for key, expected in filters.items():
        if expected and str(row.get(key) or "") != expected:
            return False
    return True


def fetch_scenario_rows(
    db: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    suffix: str,
    start_period: str,
    end_period: str,
    fallback: str | None = None,
    period_key: str = "period",
    filters: dict[str, str | None] | None = None,
    marketing_channel: str | None = None,
    region: str | None = None,
    segment: str | None = None,
    owner: str | None = None,
    waterfall_type: str | None = None,
) -> list[tuple[str, str, str, dict[str, Any]]]:
    del waterfall_type
    combined_filters = {
        "marketing_channel": marketing_channel,
        "region": region,
        "segment": segment,
        "owner": owner,
    }
    if filters:
        combined_filters.update(filters)
    combined_filters = {k: v for k, v in combined_filters.items() if v}
    wanted = set(scenario_periods(scenario, start_period, end_period))
    out: list[tuple[str, str, str, dict[str, Any]]] = []
    for source_scenario in sorted({item[0] for item in wanted}):
        table_name = preferred_table(db, source_scenario, suffix, fallback=fallback)
        if table_name is None:
            continue
        for row in fetch_table_rows(db, table_name, organization_id):
            if suffix == "opportunities":
                raw_period = (
                    row.get(period_key)
                    or row.get("period")
                    or row.get("close_date")
                    or row.get("actual_close_date")
                    or row.get("forecast_period")
                    or row.get("expected_close_date")
                )
            else:
                raw_period = row.get(period_key) or row.get("forecast_period") or row.get("close_date") or row.get("expected_close_date")
            if not raw_period:
                continue
            try:
                period = to_period(raw_period)
            except (TypeError, ValueError):
                continue
            if (source_scenario, period) not in wanted:
                continue
            if combined_filters and not filter_row(row, combined_filters):
                continue
            out.append((source_scenario, period, table_name, row))
    return out


def commentary_prompts() -> dict[str, str]:
    return {
        "what_changed": "What changed?",
        "variance_drivers": "What drove the variance?",
        "leadership_attention": "What should leadership pay attention to?",
        "movement_drivers": "Which customers/channels drove the movement?",
    }
