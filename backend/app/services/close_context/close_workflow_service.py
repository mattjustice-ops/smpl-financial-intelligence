"""Customer Close Workflow — state machine, Ready-to-Lock, Lock/Reopen, receipts.

See docs/CUSTOMER_CLOSE_WORKFLOW.md. Extends Close Session lineage; no new platform service.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.close_session import CloseSession
from app.models.close_workflow import CloseLoadReceipt, CloseLockEvent
from app.services.close_context.close_session_service import (
    get_or_create_close_session,
    mark_freeze_complete,
    mark_validation_complete,
)
from app.services.reporting.period_utils import to_period

logger = logging.getLogger(__name__)

WorkflowState = Literal[
    "OPEN",
    "LOADING_DATA",
    "VALIDATING",
    "READY_TO_LOCK",
    "LOCKED",
    "FREEZING",
    "READY_FOR_EXECUTIVE_REVIEW",
    "PUBLISHED",
    "REOPENED",
]

CUSTOMER_LADDER_FOR_STATE: dict[str, str] = {
    "OPEN": "Preparing Close",
    "LOADING_DATA": "Preparing Close",
    "VALIDATING": "Close Validation",
    "READY_TO_LOCK": "Close Validation",
    "LOCKED": "Close Validation",
    "FREEZING": "Close Validation",
    "READY_FOR_EXECUTIVE_REVIEW": "Ready for Executive Review",
    "PUBLISHED": "Close Certified",
    "REOPENED": "Preparing Close",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def record_load_receipt(
    db: Session,
    *,
    organization_id: uuid.UUID,
    as_of_period: str,
    source: str,
    status: str,
    rows_staged: int,
    rows_applied: int,
    rows_rejected: int,
    entity_type: str | None = None,
    ingest_batch_id: uuid.UUID | None = None,
    filename: str | None = None,
    error_summary: Any = None,
) -> CloseLoadReceipt:
    """Persist a customer-visible load receipt and nudge workflow toward LOADING_DATA."""
    period = to_period(as_of_period)
    session = get_or_create_close_session(db, organization_id, period)
    receipt = CloseLoadReceipt(
        organization_id=organization_id,
        close_session_id=session.id,
        ingest_batch_id=ingest_batch_id,
        as_of_period=period,
        entity_type=entity_type,
        source=source,
        status=status,
        rows_staged=int(rows_staged or 0),
        rows_applied=int(rows_applied or 0),
        rows_rejected=int(rows_rejected or 0),
        error_summary=error_summary,
        filename=filename,
    )
    db.add(receipt)

    if session.workflow_state in ("OPEN", "REOPENED"):
        session.workflow_state = "LOADING_DATA"
    elif session.workflow_state == "READY_TO_LOCK":
        # New load invalidates ready-to-lock until recomputed.
        session.workflow_state = "LOADING_DATA"
    session.updated_at = _utcnow()
    db.flush()
    return receipt


def list_load_receipts(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    period = to_period(as_of_period)
    rows = db.scalars(
        select(CloseLoadReceipt)
        .where(
            CloseLoadReceipt.organization_id == organization_id,
            CloseLoadReceipt.as_of_period == period,
        )
        .order_by(CloseLoadReceipt.created_at.desc())
        .limit(limit)
    ).all()
    return [_receipt_payload(r) for r in rows]


def _receipt_payload(r: CloseLoadReceipt) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "organization_id": str(r.organization_id),
        "close_session_id": str(r.close_session_id) if r.close_session_id else None,
        "ingest_batch_id": str(r.ingest_batch_id) if r.ingest_batch_id else None,
        "as_of_period": r.as_of_period,
        "entity_type": r.entity_type,
        "source": r.source,
        "status": r.status,
        "rows_staged": r.rows_staged,
        "rows_applied": r.rows_applied,
        "rows_rejected": r.rows_rejected,
        "error_summary": r.error_summary,
        "filename": r.filename,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def build_lock_checklist(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
) -> dict[str, Any]:
    """Compute Ready-to-Lock eligibility with explained blockers."""
    period = to_period(as_of_period)
    receipts = db.scalars(
        select(CloseLoadReceipt).where(
            CloseLoadReceipt.organization_id == organization_id,
            CloseLoadReceipt.as_of_period == period,
        )
    ).all()

    items: list[dict[str, Any]] = []
    blockers: list[str] = []
    warnings: list[str] = []

    successful = [r for r in receipts if r.rows_applied > 0 and r.status in ("complete", "partial")]
    failed = [r for r in receipts if r.status == "failed" or (r.rows_applied == 0 and r.rows_rejected > 0)]
    partial = [r for r in receipts if r.status == "partial" and r.rows_rejected > 0]

    if successful:
        entities = sorted({r.entity_type or "unknown" for r in successful})
        items.append(
            {
                "id": "loads_applied",
                "label": "Data loaded for this close period",
                "status": "completed",
                "detail": f"{len(successful)} successful load(s): {', '.join(entities)}",
            }
        )
    else:
        items.append(
            {
                "id": "loads_applied",
                "label": "Data loaded for this close period",
                "status": "blocking",
                "detail": "No successful load receipt for this period yet",
            }
        )
        blockers.append("No successful data load for this close period")

    unresolved_rejects = sum(r.rows_rejected for r in partial) + sum(r.rows_rejected for r in failed)
    if failed:
        items.append(
            {
                "id": "load_integrity",
                "label": "Load integrity (no failed batches)",
                "status": "blocking",
                "detail": f"{len(failed)} failed load(s); {unresolved_rejects} rejected row(s)",
            }
        )
        blockers.append(
            f"{len(failed)} failed load(s) with {unresolved_rejects} rejected row(s) — unload/correct and re-upload"
        )
    elif partial:
        items.append(
            {
                "id": "load_integrity",
                "label": "Load integrity (row errors)",
                "status": "warning",
                "detail": f"{unresolved_rejects} rejected row(s) across partial loads",
            }
        )
        warnings.append(f"{unresolved_rejects} rejected row(s) remain — review receipts before lock")
    else:
        items.append(
            {
                "id": "load_integrity",
                "label": "Load integrity (no critical row errors)",
                "status": "completed",
                "detail": "No failed loads for this period",
            }
        )

    # Financial integrity — best-effort from latest freeze / export validation
    financial_status = "unknown"
    financial_detail = "Financial validation not run yet"
    try:
        from app.models.close_context_blob import CloseContextBlob

        blob = db.scalars(
            select(CloseContextBlob).where(
                CloseContextBlob.organization_id == organization_id,
                CloseContextBlob.as_of_period == period,
            )
        ).first()
        if blob and blob.validation_status:
            financial_status = blob.validation_status
            financial_detail = f"Last freeze validation: {financial_status}"
    except Exception:
        logger.debug("financial integrity probe failed", exc_info=True)

    if financial_status == "fail":
        items.append(
            {
                "id": "financial_integrity",
                "label": "Financial integrity (tie-outs)",
                "status": "blocking",
                "detail": financial_detail,
            }
        )
        blockers.append("Financial validation failed — fix tie-outs before lock")
    elif financial_status in ("pass", "warning"):
        items.append(
            {
                "id": "financial_integrity",
                "label": "Financial integrity (tie-outs)",
                "status": "completed" if financial_status == "pass" else "warning",
                "detail": financial_detail,
            }
        )
        if financial_status == "warning":
            warnings.append("Financial validation has warnings")
    else:
        # Soft: allow lock without prior freeze validation; freeze will run on lock
        items.append(
            {
                "id": "financial_integrity",
                "label": "Financial integrity (tie-outs)",
                "status": "remaining",
                "detail": "Will run as part of Lock → freeze",
            }
        )

    ready = len(blockers) == 0 and bool(successful)
    return {
        "ready_to_lock": ready,
        "items": items,
        "blockers": blockers,
        "warnings": warnings,
        "receipt_count": len(receipts),
        "rows_applied_total": sum(r.rows_applied for r in receipts),
        "rows_rejected_total": sum(r.rows_rejected for r in receipts),
    }


def derive_workflow_state(session: CloseSession, checklist: dict[str, Any], freeze_status: str) -> str:
    """Map session + checklist + freeze onto customer-visible workflow state."""
    stored = (session.workflow_state or "OPEN").upper()
    if stored in ("LOCKED", "FREEZING", "PUBLISHED"):
        return stored
    if stored == "REOPENED":
        if checklist.get("ready_to_lock"):
            return "READY_TO_LOCK"
        if checklist.get("receipt_count", 0) > 0:
            return "LOADING_DATA"
        return "REOPENED"
    if session.current_lock_version and freeze_status == "COMPLETE" and session.certified_at:
        return "READY_FOR_EXECUTIVE_REVIEW"
    if checklist.get("ready_to_lock"):
        return "READY_TO_LOCK"
    if any(i.get("status") == "blocking" for i in checklist.get("items") or []):
        return "VALIDATING"
    if checklist.get("receipt_count", 0) > 0:
        return "LOADING_DATA"
    return stored if stored else "OPEN"


def get_close_workflow(
    db: Session,
    organization_id: uuid.UUID,
    *,
    as_of_period: str | None = None,
) -> dict[str, Any]:
    from app.models.close_context_blob import CloseContextBlob
    from app.models.organization import Organization
    from app.services.reporting.org_reporting_settings import resolve_org_reporting_window

    org = db.get(Organization, organization_id)
    if org is None:
        raise ValueError("organization not found")
    if as_of_period:
        period = to_period(as_of_period)
        start = end = period
    else:
        period, start, end = resolve_org_reporting_window(db, org)

    session = get_or_create_close_session(db, organization_id, period)
    checklist = build_lock_checklist(db, organization_id, period)
    blob = db.scalars(
        select(CloseContextBlob).where(
            CloseContextBlob.organization_id == organization_id,
            CloseContextBlob.as_of_period == period,
        )
    ).first()
    freeze_status = blob.status if blob else "missing"
    state = derive_workflow_state(session, checklist, freeze_status)
    if state != session.workflow_state and state not in ("LOCKED", "FREEZING"):
        # Persist derived pre-lock states for Ops visibility
        if session.workflow_state not in ("LOCKED", "FREEZING", "PUBLISHED"):
            session.workflow_state = state

    certified = bool(
        session.current_lock_version
        and session.certified_at
        and freeze_status == "COMPLETE"
    )
    receipts = list_load_receipts(db, organization_id, period, limit=20)
    lock_events = db.scalars(
        select(CloseLockEvent)
        .where(CloseLockEvent.close_session_id == session.id)
        .order_by(CloseLockEvent.created_at.desc())
        .limit(10)
    ).all()

    return {
        "organization_id": str(organization_id),
        "as_of_period": period,
        "start_period": start,
        "end_period": end,
        "close_session_id": str(session.id),
        "workflow_state": state,
        "customer_ladder": CUSTOMER_LADDER_FOR_STATE.get(state, "Preparing Close"),
        "current_lock_version": session.current_lock_version,
        "close_session_status": session.status,
        "checklist": checklist,
        "ready_to_lock": bool(checklist.get("ready_to_lock")),
        "blockers": checklist.get("blockers") or [],
        "warnings": checklist.get("warnings") or [],
        "freeze_status": freeze_status,
        "certified_close": certified,
        "certified_period": period if certified else None,
        "certification_timestamp": session.certified_at.isoformat() if session.certified_at else None,
        "load_receipts": receipts,
        "lock_events": [
            {
                "id": str(e.id),
                "lock_version": e.lock_version,
                "event_type": e.event_type,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "locked_by": e.locked_by,
            }
            for e in lock_events
        ],
    }


def lock_close(
    db: Session,
    organization_id: uuid.UUID,
    *,
    as_of_period: str | None = None,
    locked_by: str | None = None,
    run_freeze: bool = True,
) -> dict[str, Any]:
    """Customer Lock → versioned event → freeze → Certified Close (Phase 1)."""
    from app.models.organization import Organization
    from app.services.close_context.freeze_blob_service import build_and_store_freeze_blob
    from app.services.reporting.org_reporting_settings import resolve_org_reporting_window

    org = db.get(Organization, organization_id)
    if org is None:
        raise ValueError("organization not found")
    if as_of_period:
        period = to_period(as_of_period)
        start = end = period
    else:
        period, start, end = resolve_org_reporting_window(db, org)

    session = get_or_create_close_session(db, organization_id, period)
    checklist = build_lock_checklist(db, organization_id, period)
    if not checklist.get("ready_to_lock"):
        return {
            "ok": False,
            "code": "not_ready_to_lock",
            "message": "Cannot lock — resolve blockers first",
            "blockers": checklist.get("blockers") or [],
            "checklist": checklist,
            "workflow_state": session.workflow_state,
        }

    next_version = int(session.current_lock_version or 0) + 1
    event = CloseLockEvent(
        close_session_id=session.id,
        organization_id=organization_id,
        as_of_period=period,
        lock_version=next_version,
        event_type="lock",
        checklist_snapshot=checklist,
        locked_by=locked_by,
    )
    db.add(event)
    session.current_lock_version = next_version
    session.workflow_state = "LOCKED"
    session.certified_at = None
    session.updated_at = _utcnow()
    db.flush()

    freeze_payload: dict[str, Any] | None = None
    if run_freeze:
        session.workflow_state = "FREEZING"
        db.flush()
        try:
            freeze = build_and_store_freeze_blob(
                db,
                organization_id,
                as_of_period=period,
                start_period=start,
                end_period=end,
            )
            # Stamp lock lineage onto freeze metadata
            from app.models.close_context_blob import CloseContextBlob

            blob = db.scalars(
                select(CloseContextBlob).where(
                    CloseContextBlob.organization_id == organization_id,
                    CloseContextBlob.as_of_period == period,
                )
            ).first()
            if blob is not None:
                meta = dict(blob.metadata_json) if isinstance(blob.metadata_json, dict) else {}
                meta["close_session_id"] = str(session.id)
                meta["lock_version"] = next_version
                meta["certified_by_customer_lock"] = True
                blob.metadata_json = meta
            if freeze.validation_status in ("pass", "warning"):
                mark_validation_complete(
                    db, organization_id, period, validation_status=freeze.validation_status
                )
            mark_freeze_complete(db, organization_id, period)
            session.workflow_state = "READY_FOR_EXECUTIVE_REVIEW"
            session.certified_at = _utcnow()
            freeze_payload = {
                "status": freeze.status,
                "validation_status": freeze.validation_status,
                "context_as_of": freeze.context_as_of_iso,
                "stale": freeze.stale,
            }
        except Exception as exc:
            logger.exception("Freeze after lock failed org=%s period=%s", organization_id, period)
            session.workflow_state = "LOCKED"
            db.commit()
            return {
                "ok": False,
                "code": "freeze_failed",
                "message": f"Lock recorded (v{next_version}) but freeze failed: {type(exc).__name__}: {exc}",
                "lock_version": next_version,
                "close_session_id": str(session.id),
                "workflow_state": session.workflow_state,
            }

    db.commit()
    return {
        "ok": True,
        "lock_version": next_version,
        "close_session_id": str(session.id),
        "as_of_period": period,
        "workflow_state": session.workflow_state,
        "certified_close": session.certified_at is not None,
        "certification_timestamp": session.certified_at.isoformat() if session.certified_at else None,
        "freeze": freeze_payload,
        "customer_ladder": CUSTOMER_LADDER_FOR_STATE.get(
            session.workflow_state, "Ready for Executive Review"
        ),
    }


def reopen_close(
    db: Session,
    organization_id: uuid.UUID,
    *,
    as_of_period: str | None = None,
    locked_by: str | None = None,
) -> dict[str, Any]:
    """Reopen for further loads. Prior freeze packs/decks stay immutable (STALE label)."""
    from app.models.organization import Organization
    from app.services.close_context.freeze_blob_service import mark_blob_stale
    from app.services.reporting.org_reporting_settings import resolve_org_reporting_window

    org = db.get(Organization, organization_id)
    if org is None:
        raise ValueError("organization not found")
    if as_of_period:
        period = to_period(as_of_period)
    else:
        period, _, _ = resolve_org_reporting_window(db, org)

    session = get_or_create_close_session(db, organization_id, period)
    version = int(session.current_lock_version or 0)
    if version <= 0:
        return {
            "ok": False,
            "code": "not_locked",
            "message": "Nothing to reopen — no Lock version exists yet",
        }

    event = CloseLockEvent(
        close_session_id=session.id,
        organization_id=organization_id,
        as_of_period=period,
        lock_version=version,
        event_type="reopen",
        checklist_snapshot={"note": "reopen leaves prior freeze pack immutable"},
        locked_by=locked_by,
    )
    db.add(event)
    session.workflow_state = "REOPENED"
    # Keep certified_at for audit of last certification; Clear Ready until re-lock
    session.updated_at = _utcnow()
    mark_blob_stale(db, organization_id, period)
    db.commit()
    return {
        "ok": True,
        "close_session_id": str(session.id),
        "as_of_period": period,
        "prior_lock_version": version,
        "workflow_state": "REOPENED",
        "message": (
            f"Reopened Lock v{version}. Prior freeze pack is STALE and decks stamped "
            f"with that version remain unchanged. Re-lock to build a new pack."
        ),
    }
