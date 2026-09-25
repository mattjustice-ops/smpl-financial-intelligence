"""Validation Engine — owner Allow, mapping queue, import hard-ID helpers.

Board shows validated outcomes; this module persists owner workshop state on the
freeze pack (sections_json) so Monthly Align survives freeze rebuilds.
Not SOC 2 certified.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.close_context_blob import CloseContextBlob

MANAGEMENT_LINES: tuple[str, ...] = (
    "revenue",
    "cogs",
    "gross_profit",
    "sm",
    "rd",
    "ga",
    "ebitda",
    "net_income",
    "cash",
    "deferred_revenue",
    "ar",
    "ap",
    "arr_bridge",
    "exclude",
    "unassigned",
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_blob(
    db: Session, organization_id: uuid.UUID, as_of_period: str
) -> CloseContextBlob | None:
    return db.scalars(
        select(CloseContextBlob).where(
            CloseContextBlob.organization_id == organization_id,
            CloseContextBlob.as_of_period == as_of_period,
        )
    ).first()


def _sections(blob: CloseContextBlob | None) -> dict[str, Any]:
    if blob is None or not isinstance(blob.sections_json, dict):
        return {}
    return dict(blob.sections_json)


def get_validation_status(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
) -> dict[str, Any]:
    blob = _get_blob(db, organization_id, as_of_period)
    sections = _sections(blob)
    allow = sections.get("validation_allow") if isinstance(sections.get("validation_allow"), dict) else None
    queue = sections.get("mapping_queue") if isinstance(sections.get("mapping_queue"), list) else []
    open_items = [q for q in queue if isinstance(q, dict) and q.get("status") == "open"]
    material_open = [
        q for q in open_items if abs(float(q.get("amount") or 0)) >= 1.0
    ]
    queue_source = sections.get("mapping_queue_source")
    if not isinstance(queue_source, str) or not queue_source:
        if queue:
            queue_source = "manual_or_demo"
        else:
            # Empty queue is not proof of clean mapping — ingest does not auto-fill yet.
            queue_source = "empty_not_ingest_fed"
    return {
        "organization_id": str(organization_id),
        "as_of_period": as_of_period,
        "freeze_status": blob.status if blob else None,
        "freeze_built_at": blob.built_at.isoformat() if blob and blob.built_at else None,
        "validation_allow": allow,
        "allowed": bool(allow and allow.get("allowed")),
        "mapping_queue": queue,
        "mapping_queue_source": queue_source,
        "mapping_open_count": len(open_items),
        "mapping_material_open_count": len(material_open),
        "management_lines": list(MANAGEMENT_LINES),
        "import_hard_id_blocked": len(material_open) > 0,
        "monthly_align": {
            "ties": "owner_reviews_in_engine",
            "mapping_clear": len(material_open) == 0,
            "allow": bool(allow and allow.get("allowed")),
            "ready_for_board": bool(
                blob
                and blob.status == "COMPLETE"
                and allow
                and allow.get("allowed")
                and len(material_open) == 0
            ),
        },
        "honesty": {
            "mapping_ingest_wired": True,
            "note": (
                "Mapping queue syncs from gl_actuals when statement/category cannot "
                "be classified into a management line. Empty queue after sync means "
                "no unclassified material accounts for the period (or no GL rows)."
            ),
        },
    }


def record_allow(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
    *,
    allowed_by: str,
    notes: str | None = None,
) -> dict[str, Any]:
    blob = _get_blob(db, organization_id, as_of_period)
    if blob is None:
        raise ValueError("no_freeze_pack")
    if blob.status not in ("COMPLETE", "STALE"):
        raise ValueError("freeze_not_complete")

    sections = _sections(blob)
    open_material = [
        q
        for q in (sections.get("mapping_queue") or [])
        if isinstance(q, dict)
        and q.get("status") == "open"
        and abs(float(q.get("amount") or 0)) >= 1.0
    ]
    if open_material:
        raise ValueError("mapping_queue_open")

    allow = {
        "allowed": True,
        "allowed_by": (allowed_by or "owner").strip()[:256],
        "allowed_at": _utcnow().isoformat(),
        "as_of_period": as_of_period,
        "notes": (notes or "").strip()[:2000] or None,
        "freeze_status": blob.status,
    }
    sections["validation_allow"] = allow
    blob.sections_json = sections
    blob.updated_at = _utcnow()
    db.add(blob)
    db.commit()
    db.refresh(blob)
    return get_validation_status(db, organization_id, as_of_period)


def revoke_allow(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
    *,
    revoked_by: str | None = None,
) -> dict[str, Any]:
    blob = _get_blob(db, organization_id, as_of_period)
    if blob is None:
        raise ValueError("no_freeze_pack")
    sections = _sections(blob)
    sections["validation_allow"] = {
        "allowed": False,
        "revoked_by": (revoked_by or "owner").strip()[:256],
        "revoked_at": _utcnow().isoformat(),
        "as_of_period": as_of_period,
    }
    blob.sections_json = sections
    blob.updated_at = _utcnow()
    db.add(blob)
    db.commit()
    return get_validation_status(db, organization_id, as_of_period)


def upsert_mapping_queue(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge inbound unmapped accounts into the freeze mapping queue."""
    blob = _get_blob(db, organization_id, as_of_period)
    if blob is None:
        # Create a stub COMPLETE-less row is wrong — require freeze. Store on metadata file? 
        # Prefer creating minimal blob sections only when freeze exists.
        raise ValueError("no_freeze_pack")

    sections = _sections(blob)
    existing = [
        q for q in (sections.get("mapping_queue") or []) if isinstance(q, dict)
    ]
    by_key = {
        str(q.get("account_id") or q.get("account_number") or q.get("name") or ""): q
        for q in existing
    }
    for raw in items:
        if not isinstance(raw, dict):
            continue
        key = str(
            raw.get("account_id")
            or raw.get("account_number")
            or raw.get("name")
            or ""
        ).strip()
        if not key:
            continue
        prev = by_key.get(key) or {}
        status = prev.get("status") if prev.get("status") in ("open", "mapped", "excluded") else "open"
        if raw.get("status") in ("open", "mapped", "excluded"):
            status = raw["status"]
        entry = {
            "account_id": key,
            "account_number": str(raw.get("account_number") or prev.get("account_number") or key),
            "name": str(raw.get("name") or prev.get("name") or key),
            "amount": float(raw.get("amount") if raw.get("amount") is not None else prev.get("amount") or 0),
            "statement_hint": str(raw.get("statement_hint") or prev.get("statement_hint") or "unassigned"),
            "status": status,
            "mapped_to": prev.get("mapped_to"),
            "detected_at": prev.get("detected_at") or _utcnow().isoformat(),
            "new_since_allow": True,
        }
        if status == "mapped":
            entry["mapped_to"] = raw.get("mapped_to") or prev.get("mapped_to")
        by_key[key] = entry

    sections["mapping_queue"] = list(by_key.values())
    sections["mapping_queue_source"] = "manual"
    blob.sections_json = sections
    blob.updated_at = _utcnow()
    db.add(blob)
    db.commit()
    return get_validation_status(db, organization_id, as_of_period)


def map_account(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
    *,
    account_id: str,
    mapped_to: str,
    mapped_by: str | None = None,
) -> dict[str, Any]:
    line = (mapped_to or "").strip().lower()
    if line not in MANAGEMENT_LINES:
        raise ValueError("invalid_management_line")
    blob = _get_blob(db, organization_id, as_of_period)
    if blob is None:
        raise ValueError("no_freeze_pack")
    sections = _sections(blob)
    queue = [q for q in (sections.get("mapping_queue") or []) if isinstance(q, dict)]
    found = False
    for q in queue:
        key = str(q.get("account_id") or q.get("account_number") or "")
        if key == account_id:
            found = True
            if line == "exclude":
                q["status"] = "excluded"
                q["mapped_to"] = "exclude"
            else:
                q["status"] = "mapped"
                q["mapped_to"] = line
            q["mapped_by"] = (mapped_by or "owner").strip()[:256]
            q["mapped_at"] = _utcnow().isoformat()
            break
    if not found:
        raise ValueError("account_not_in_queue")
    decisions = list(sections.get("mapping_decisions") or [])
    decisions.append(
        {
            "account_id": account_id,
            "mapped_to": line,
            "mapped_by": (mapped_by or "owner").strip()[:256],
            "mapped_at": _utcnow().isoformat(),
            "as_of_period": as_of_period,
        }
    )
    sections["mapping_queue"] = queue
    sections["mapping_decisions"] = decisions[-200:]
    # New mapping after Allow invalidates Allow (owner must re-align).
    if sections.get("validation_allow") and sections["validation_allow"].get("allowed"):
        sections["validation_allow"] = {
            "allowed": False,
            "revoked_at": _utcnow().isoformat(),
            "revoked_reason": "mapping_changed",
            "as_of_period": as_of_period,
        }
    blob.sections_json = sections
    blob.updated_at = _utcnow()
    db.add(blob)
    db.commit()
    return get_validation_status(db, organization_id, as_of_period)


def unmap_account(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
    *,
    account_id: str,
    unmapped_by: str | None = None,
) -> dict[str, Any]:
    """Re-open a mapped/excluded queue item so the owner can remap."""
    blob = _get_blob(db, organization_id, as_of_period)
    if blob is None:
        raise ValueError("no_freeze_pack")
    sections = _sections(blob)
    queue = [q for q in (sections.get("mapping_queue") or []) if isinstance(q, dict)]
    found = False
    prior = None
    for q in queue:
        key = str(q.get("account_id") or q.get("account_number") or "")
        if key == account_id:
            found = True
            prior = q.get("mapped_to")
            q["status"] = "open"
            q["mapped_to"] = None
            q["unmapped_by"] = (unmapped_by or "owner").strip()[:256]
            q["unmapped_at"] = _utcnow().isoformat()
            q.pop("mapped_by", None)
            q.pop("mapped_at", None)
            break
    if not found:
        raise ValueError("account_not_in_queue")
    decisions = list(sections.get("mapping_decisions") or [])
    decisions.append(
        {
            "account_id": account_id,
            "action": "unmap",
            "prior_mapped_to": prior,
            "unmapped_by": (unmapped_by or "owner").strip()[:256],
            "unmapped_at": _utcnow().isoformat(),
            "as_of_period": as_of_period,
        }
    )
    sections["mapping_queue"] = queue
    sections["mapping_decisions"] = decisions[-200:]
    # Unmap after Allow invalidates Allow (owner must re-align).
    if sections.get("validation_allow") and sections["validation_allow"].get("allowed"):
        sections["validation_allow"] = {
            "allowed": False,
            "revoked_at": _utcnow().isoformat(),
            "revoked_reason": "mapping_changed",
            "as_of_period": as_of_period,
        }
    blob.sections_json = sections
    blob.updated_at = _utcnow()
    db.add(blob)
    db.commit()
    return get_validation_status(db, organization_id, as_of_period)


def _hint_management_line(*, statement: str | None, category: str | None, account_name: str | None) -> str:
    """Best-effort management-line hint from GL labels (never invents a firm map)."""
    from app.services.financial_statements.mapping import (
        BALANCE_SHEET,
        INCOME_STATEMENT,
        UNKNOWN,
        normalize_is_bucket,
        normalize_statement,
    )

    stmt = normalize_statement(statement)
    cat = (category or "").strip().lower()
    name = (account_name or "").strip().lower()
    blob = f"{cat} {name}"

    if any(t in blob for t in ("deferred revenue", "deferred_revenue", "unearned")):
        return "deferred_revenue"
    if cat in {"cash", "cash and equivalents"} or name.startswith("cash"):
        return "cash"
    if "receivable" in blob or cat in {"ar", "accounts receivable"}:
        return "ar"
    if "payable" in blob or cat in {"ap", "accounts payable"}:
        return "ap"
    if stmt == INCOME_STATEMENT or cat:
        bucket = normalize_is_bucket(category, account_name)
        if bucket == "revenue":
            return "revenue"
        if bucket == "cogs":
            return "cogs"
        if ("sales" in blob and "marketing" in blob) or cat in {
            "sm",
            "s&m",
            "sales & marketing",
        }:
            return "sm"
        if "research" in blob or "r&d" in blob or cat in {"rd", "r&d"}:
            return "rd"
        if "admin" in blob or "g&a" in blob or cat in {"ga", "g&a"}:
            return "ga"
        if bucket == "operating_expense":
            return "unassigned"
    if stmt == BALANCE_SHEET:
        return "unassigned"
    if stmt == UNKNOWN and not cat and not name:
        return "unassigned"
    return "unassigned"


def _gl_row_needs_mapping(*, statement: str | None, category: str | None, account_name: str | None) -> bool:
    """True when GL labels are missing or cannot be classified into a firm line."""
    from app.services.financial_statements.mapping import UNKNOWN, normalize_statement

    stmt = normalize_statement(statement)
    cat = (category or "").strip()
    name = (account_name or "").strip()
    if not cat and not name:
        return True
    if stmt == UNKNOWN and not cat:
        return True
    hint = _hint_management_line(statement=statement, category=category, account_name=account_name)
    return hint == "unassigned" and (not cat or stmt == UNKNOWN)


def sync_mapping_queue_from_gl_actuals(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
) -> dict[str, Any]:
    """Pull unclassified gl_actuals for the close month into the mapping queue.

    Only opens new queue items for accounts not already mapped/excluded.
    Sets mapping_queue_source=ingest when any GL-derived items are merged.
    """
    from calendar import monthrange
    from datetime import date
    from decimal import Decimal

    from sqlalchemy import func

    from app.models.demo_finance import GlActual
    from app.services.dashboard.query_utils import table_exists

    blob = _get_blob(db, organization_id, as_of_period)
    if blob is None:
        raise ValueError("no_freeze_pack")
    if not table_exists(db, "gl_actuals"):
        return get_validation_status(db, organization_id, as_of_period)

    year, month = int(as_of_period[:4]), int(as_of_period[5:7])
    period_start = date(year, month, 1)
    period_end = date(year, month, monthrange(year, month)[1])

    rows = db.execute(
        select(
            GlActual.account_number,
            GlActual.account_name,
            GlActual.statement,
            GlActual.category,
            func.coalesce(func.sum(GlActual.amount), 0),
        )
        .where(
            GlActual.organization_id == organization_id,
            GlActual.version == "Actual",
            GlActual.period >= period_start,
            GlActual.period <= period_end,
        )
        .group_by(
            GlActual.account_number,
            GlActual.account_name,
            GlActual.statement,
            GlActual.category,
        )
    ).all()

    items: list[dict[str, Any]] = []
    for account_number, account_name, statement, category, amount in rows:
        acct = str(account_number or "").strip()
        if not acct:
            continue
        if not _gl_row_needs_mapping(
            statement=statement, category=category, account_name=account_name
        ):
            continue
        amt = float(amount if isinstance(amount, Decimal) else (amount or 0))
        if abs(amt) < 1.0:
            continue
        items.append(
            {
                "account_id": acct,
                "account_number": acct,
                "name": str(account_name or acct),
                "amount": amt,
                "statement_hint": _hint_management_line(
                    statement=statement, category=category, account_name=account_name
                ),
                "status": "open",
            }
        )

    if not items:
        status = get_validation_status(db, organization_id, as_of_period)
        # Record that ingest ran even when nothing was unclassified.
        sections = _sections(blob)
        if sections.get("mapping_queue_source") not in {"manual", "demo_seed", "ingest"}:
            sections["mapping_queue_source"] = "ingest_empty"
            blob.sections_json = sections
            blob.updated_at = _utcnow()
            db.add(blob)
            db.commit()
            return get_validation_status(db, organization_id, as_of_period)
        return status

    # Preserve mapped/excluded decisions: only merge open/new accounts.
    sections = _sections(blob)
    existing = [q for q in (sections.get("mapping_queue") or []) if isinstance(q, dict)]
    decided = {
        str(q.get("account_id") or q.get("account_number") or "")
        for q in existing
        if q.get("status") in ("mapped", "excluded")
    }
    to_upsert = [i for i in items if i["account_id"] not in decided]
    if not to_upsert:
        return get_validation_status(db, organization_id, as_of_period)

    result = upsert_mapping_queue(db, organization_id, as_of_period, to_upsert)
    blob = _get_blob(db, organization_id, as_of_period)
    if blob is not None:
        sections = _sections(blob)
        sections["mapping_queue_source"] = "ingest"
        blob.sections_json = sections
        blob.updated_at = _utcnow()
        db.add(blob)
        db.commit()
        return get_validation_status(db, organization_id, as_of_period)
    return result


def seed_demo_mapping_queue_if_empty(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
) -> dict[str, Any]:
    """Demo/dev helper when GL ingest has nothing to show yet.

    Prefer sync_mapping_queue_from_gl_actuals for production orgs.
    """
    status = get_validation_status(db, organization_id, as_of_period)
    if status.get("mapping_queue"):
        return status
    # Try real GL first — only fall back to canned demo accounts if empty.
    try:
        synced = sync_mapping_queue_from_gl_actuals(db, organization_id, as_of_period)
        if synced.get("mapping_queue"):
            return synced
    except ValueError:
        pass
    demo_items = [
        {
            "account_id": "6105",
            "account_number": "6105",
            "name": "AI Infrastructure — New",
            "amount": 42500.0,
            "statement_hint": "ga",
            "status": "open",
        },
        {
            "account_id": "1220",
            "account_number": "1220",
            "name": "Customer Deposits Clearing",
            "amount": 180000.0,
            "statement_hint": "deferred_revenue",
            "status": "open",
        },
        {
            "account_id": "8050",
            "account_number": "8050",
            "name": "Partner Referral Fees",
            "amount": 12500.0,
            "statement_hint": "sm",
            "status": "open",
        },
    ]
    result = upsert_mapping_queue(db, organization_id, as_of_period, demo_items)
    blob = _get_blob(db, organization_id, as_of_period)
    if blob is not None:
        sections = _sections(blob)
        sections["mapping_queue_source"] = "demo_seed"
        blob.sections_json = sections
        blob.updated_at = _utcnow()
        db.add(blob)
        db.commit()
        return get_validation_status(db, organization_id, as_of_period)
    return result


def assert_import_mapping_clear(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
    *,
    fail_closed: bool = True,
) -> dict[str, Any]:
    """Import/close hard-ID: block when material unmapped accounts remain open."""
    status = get_validation_status(db, organization_id, as_of_period)
    blocked = bool(status.get("import_hard_id_blocked"))
    if blocked and fail_closed:
        raise ValueError(
            "validation_engine_mapping_open:"
            f"{status.get('mapping_material_open_count')} material unmapped account(s) "
            f"for {as_of_period} — map in Validation Engine before import/close"
        )
    return status
