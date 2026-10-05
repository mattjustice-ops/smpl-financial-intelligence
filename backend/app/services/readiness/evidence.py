"""Canonical-object evidence from the customer's warehouse for the Readiness Score.

Presence = any mapped table has rows for the org. Confidence = share of expected reporting
periods loaded (for period-grained objects); presence-only objects score 1.0 when populated.
Reads the data as loaded — nothing is inferred, filled in, or adjusted.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.services.reporting.org_reporting_settings import resolve_org_reporting_window
from app.services.reporting.period_utils import period_range, to_period
from app.services.readiness.registry import OBJECTS, ObjectEvidence


def _existing_tables(db: Session, names: set[str]) -> dict[str, bool]:
    """table name → has a ``period`` column, for tables that exist with an organization_id column."""
    rows = db.execute(
        text(
            """
            SELECT c.table_name,
                   bool_or(c2.column_name IS NOT NULL) AS has_period
            FROM information_schema.columns c
            LEFT JOIN information_schema.columns c2
              ON c2.table_schema = c.table_schema AND c2.table_name = c.table_name AND c2.column_name = 'period'
            WHERE c.table_schema = 'public' AND c.column_name = 'organization_id'
              AND c.table_name = ANY(:names)
            GROUP BY c.table_name
            """
        ),
        {"names": sorted(names)},
    ).all()
    return {str(r[0]): bool(r[1]) for r in rows}


def _split_source(source: str) -> tuple[str, str | None]:
    """``gl_actuals#Budget`` → (``gl_actuals``, ``Budget``): one table holding several versions."""
    table, _, version = source.partition("#")
    return table, version or None


def _table_stats(db: Session, source: str, has_period: bool, oid: uuid.UUID) -> tuple[int, set[str]]:
    table, version = _split_source(source)
    where = "organization_id = CAST(:oid AS uuid)"
    params: dict[str, str] = {"oid": str(oid)}
    if version:
        where += " AND lower(version) = lower(:version)"
        params["version"] = version
    count = int(db.execute(text(f'SELECT count(*) FROM "{table}" WHERE {where}'), params).scalar() or 0)
    periods: set[str] = set()
    if count and has_period:
        for (p,) in db.execute(
            text(f'SELECT DISTINCT period::text FROM "{table}" WHERE {where} AND period IS NOT NULL'),
            params,
        ).all():
            try:
                periods.add(to_period(str(p)))
            except ValueError:
                continue
    return count, periods


def expected_periods(db: Session, org: Organization) -> dict[str, list[str]]:
    as_of, start, end = resolve_org_reporting_window(db, org)
    fy = period_range(start, end)
    return {
        "actual": [p for p in fy if p <= as_of],
        "budget": fy,
        "forecast": [p for p in fy if p > as_of],
        "window": {"as_of": as_of, "start": start, "end": end},  # type: ignore[dict-item]
    }


def build_evidence(db: Session, org: Organization) -> tuple[dict[str, ObjectEvidence], dict[str, Any]]:
    oid = org.id
    windows = expected_periods(db, org)
    sources = {t for o in OBJECTS.values() for t in o.tables if not t.startswith("@")}
    existing_tables = _existing_tables(db, {_split_source(s)[0] for s in sources})
    existing = {s: existing_tables[_split_source(s)[0]] for s in sources if _split_source(s)[0] in existing_tables}
    stats: dict[str, tuple[int, set[str]]] = {}
    for t, has_period in existing.items():
        try:
            stats[t] = _table_stats(db, t, has_period, oid)
        except Exception:  # noqa: BLE001 — a malformed table counts as not loaded
            db.rollback()
            stats[t] = (0, set())

    evidence: dict[str, ObjectEvidence] = {}
    for obj in OBJECTS.values():
        if obj.tables == ("@organization",):
            evidence[obj.id] = ObjectEvidence(present=True, confidence=1.0, rows=1, sources=["organizations"])
            continue
        best: ObjectEvidence | None = None
        for t in obj.tables:
            count, periods = stats.get(t, (0, set()))
            if not count:
                continue
            expected = windows.get(obj.period_scope or "", []) if obj.period_scope else []
            if expected and existing.get(t):
                missing = [p for p in expected if p not in periods]  # type: ignore[union-attr]
                conf = (len(expected) - len(missing)) / len(expected)
            else:
                missing, conf = [], 1.0
            cand = ObjectEvidence(present=True, confidence=conf, rows=count, sources=[t], missing_periods=missing)
            if best is None or cand.confidence > best.confidence:
                best = cand
        evidence[obj.id] = best or ObjectEvidence(present=False, confidence=0.0)

    window = windows["window"]
    return evidence, {"reporting_window": window, "tables_checked": sorted(existing)}
