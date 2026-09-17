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
    return {
        "organization_id": str(organization_id),
        "as_of_period": as_of_period,
        "freeze_status": blob.status if blob else None,
        "freeze_built_at": blob.built_at.isoformat() if blob and blob.built_at else None,
        "validation_allow": allow,
        "allowed": bool(allow and allow.get("allowed")),
        "mapping_queue": queue,
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


def seed_demo_mapping_queue_if_empty(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
) -> dict[str, Any]:
    """Demo/dev helper: ensure owners see the mapping workflow without live GL ingest."""
    status = get_validation_status(db, organization_id, as_of_period)
    if status.get("mapping_queue"):
        return status
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
    return upsert_mapping_queue(db, organization_id, as_of_period, demo_items)


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
