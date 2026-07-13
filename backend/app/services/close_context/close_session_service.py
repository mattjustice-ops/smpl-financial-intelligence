"""Close Session lineage + Month-End Readiness aggregator (Close Peak §4E / §6)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.close_context_blob import CloseContextBlob
from app.models.close_session import CloseSession
from app.models.export_job import ExportJobRecord
from app.models.organization import Organization
from app.services.reporting.export.validation_labels import trust_status_for
from app.services.reporting.period_utils import to_period

logger = logging.getLogger(__name__)

CloseSessionStatus = Literal["open", "validation_complete", "freeze_complete", "archived"]

_STATUS_RANK: dict[str, int] = {
    "open": 0,
    "validation_complete": 1,
    "freeze_complete": 2,
    "archived": 3,
}


def get_or_create_close_session(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
) -> CloseSession:
    """Return the immutable close-session row for (org, period), creating if needed."""
    period = to_period(as_of_period)
    existing = db.scalars(
        select(CloseSession).where(
            CloseSession.organization_id == organization_id,
            CloseSession.as_of_period == period,
        )
    ).first()
    if existing is not None:
        return existing
    row = CloseSession(
        id=uuid.uuid4(),
        organization_id=organization_id,
        as_of_period=period,
        status="open",
    )
    db.add(row)
    db.flush()
    return row


def get_close_session(db: Session, session_id: uuid.UUID) -> CloseSession | None:
    return db.get(CloseSession, session_id)


def advance_close_session_status(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
    *,
    target_status: CloseSessionStatus,
) -> CloseSession:
    """Advance session status monotonically (never regress)."""
    row = get_or_create_close_session(db, organization_id, as_of_period)
    current_rank = _STATUS_RANK.get(row.status, 0)
    target_rank = _STATUS_RANK.get(target_status, 0)
    if target_rank > current_rank:
        row.status = target_status
        db.flush()
    return row


def mark_validation_complete(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
    *,
    validation_status: str | None,
) -> CloseSession | None:
    if validation_status not in ("pass", "warning"):
        return get_or_create_close_session(db, organization_id, as_of_period)
    return advance_close_session_status(
        db,
        organization_id,
        as_of_period,
        target_status="validation_complete",
    )


def mark_freeze_complete(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
) -> CloseSession:
    return advance_close_session_status(
        db,
        organization_id,
        as_of_period,
        target_status="freeze_complete",
    )


def _queue_status_for_org(db: Session, organization_id: uuid.UUID) -> dict[str, Any]:
    try:
        rows = db.scalars(
            select(ExportJobRecord)
            .where(ExportJobRecord.organization_id == organization_id)
            .where(ExportJobRecord.status.in_(("queued", "running", "failed", "complete")))
            .order_by(ExportJobRecord.created_at.desc())
            .limit(10)
        ).all()
    except Exception:
        logger.debug("Export jobs unavailable for readiness queue", exc_info=True)
        return {
            "active_count": 0,
            "queued": 0,
            "running": 0,
            "failed_recent": 0,
            "status": "idle",
            "latest_job_id": None,
            "latest_kind": None,
            "latest_status": None,
        }

    queued = sum(1 for r in rows if r.status == "queued")
    running = sum(1 for r in rows if r.status == "running")
    failed_recent = sum(1 for r in rows if r.status == "failed")
    active = queued + running
    latest = rows[0] if rows else None
    if running:
        label = "running"
    elif queued:
        label = "queued"
    elif failed_recent and (latest is None or latest.status == "failed"):
        label = "failed"
    else:
        label = "idle"
    return {
        "active_count": active,
        "queued": queued,
        "running": running,
        "failed_recent": failed_recent,
        "status": label,
        "latest_job_id": str(latest.id) if latest else None,
        "latest_kind": latest.kind if latest else None,
        "latest_status": latest.status if latest else None,
        "latest_close_session_id": (
            (latest.metadata_json or {}).get("close_session_id") if latest and latest.metadata_json else None
        ),
    }


def _blob_row(db: Session, organization_id: uuid.UUID, period: str) -> CloseContextBlob | None:
    return db.scalars(
        select(CloseContextBlob).where(
            CloseContextBlob.organization_id == organization_id,
            CloseContextBlob.as_of_period == period,
        )
    ).first()


def build_org_close_readiness(
    db: Session,
    organization_id: uuid.UUID,
    *,
    as_of_period: str,
    organization_name: str | None = None,
    plan: str | None = None,
    ensure_session: bool = True,
) -> dict[str, Any]:
    """Compose Month-End Readiness row from existing freeze / session / queue signals."""
    period = to_period(as_of_period)
    session = (
        get_or_create_close_session(db, organization_id, period)
        if ensure_session
        else db.scalars(
            select(CloseSession).where(
                CloseSession.organization_id == organization_id,
                CloseSession.as_of_period == period,
            )
        ).first()
    )
    blob = _blob_row(db, organization_id, period)
    freeze_status = blob.status if blob else "missing"
    validation_status = blob.validation_status if blob else None
    trust_status, trust_label = (
        trust_status_for(validation_status) if validation_status else (None, None)
    )
    close_ready_phase1 = bool(
        validation_status in ("pass", "warning") and freeze_status == "COMPLETE"
    )
    as_of_timestamp = None
    if blob and blob.built_at is not None:
        as_of_timestamp = blob.built_at.isoformat()
    last_refresh = as_of_timestamp
    queue = _queue_status_for_org(db, organization_id)

    if close_ready_phase1 and session is not None and session.status != "archived":
        # Keep session aligned with Phase 1 formula when freeze already COMPLETE.
        if session.status != "freeze_complete":
            session = advance_close_session_status(
                db,
                organization_id,
                period,
                target_status="freeze_complete",
            )

    operational_confidence = "high" if close_ready_phase1 else (
        "medium" if freeze_status in ("COMPLETE", "STALE") or validation_status else "low"
    )

    return {
        "organization_id": str(organization_id),
        "organization_name": organization_name,
        "plan": plan,
        "as_of_period": period,
        "close_session_id": str(session.id) if session else None,
        "close_session_status": session.status if session else None,
        "validation_status": validation_status or "unknown",
        "trust_status": trust_status,
        "trust_label": trust_label,
        "calculation_status": "not_applicable",
        "narrative_status": "not_applicable",
        "freeze_status": freeze_status,
        "queue_status": queue,
        "operational_confidence": operational_confidence,
        "close_ready_phase1": close_ready_phase1,
        "close_ready": close_ready_phase1,
        "last_successful_refresh": last_refresh,
        "as_of_timestamp": as_of_timestamp,
        "customer_ladder": (
            "Close Certified"
            if close_ready_phase1
            else "Close Validation"
            if validation_status in ("pass", "warning", "fail")
            else "Preparing Close"
        ),
    }


def list_close_readiness(
    db: Session,
    *,
    as_of_period: str,
    ensure_sessions: bool = False,
) -> dict[str, Any]:
    """Ops Month-End Readiness Dashboard payload — one row per organization."""
    period = to_period(as_of_period)
    orgs = db.scalars(select(Organization).order_by(Organization.name)).all()
    rows: list[dict[str, Any]] = []
    ready = 0
    for org in orgs:
        row = build_org_close_readiness(
            db,
            org.id,
            as_of_period=period,
            organization_name=org.name,
            plan=getattr(org, "plan", None),
            ensure_session=ensure_sessions,
        )
        if row["close_ready_phase1"]:
            ready += 1
        rows.append(row)
    if ensure_sessions:
        db.commit()
    return {
        "as_of_period": period,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "organizations_total": len(rows),
        "organizations_ready": ready,
        "organizations": rows,
    }


def close_session_lineage(db: Session, session_id: uuid.UUID) -> dict[str, Any] | None:
    """Support lookup: session + related export jobs stamped with this id."""
    session = get_close_session(db, session_id)
    if session is None:
        return None
    org = db.get(Organization, session.organization_id)
    readiness = build_org_close_readiness(
        db,
        session.organization_id,
        as_of_period=session.as_of_period,
        organization_name=org.name if org else None,
        plan=getattr(org, "plan", None) if org else None,
        ensure_session=False,
    )
    jobs: list[dict[str, Any]] = []
    try:
        sid = str(session.id)
        records = db.scalars(
            select(ExportJobRecord)
            .where(ExportJobRecord.organization_id == session.organization_id)
            .order_by(ExportJobRecord.created_at.desc())
            .limit(50)
        ).all()
        for row in records:
            meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
            if meta.get("close_session_id") != sid:
                continue
            jobs.append(
                {
                    "job_id": str(row.id),
                    "kind": row.kind,
                    "status": row.status,
                    "message": row.message,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "error": row.error,
                }
            )
    except Exception:
        logger.debug("Could not load export jobs for close session lineage", exc_info=True)

    return {
        "close_session_id": str(session.id),
        "organization_id": str(session.organization_id),
        "organization_name": org.name if org else None,
        "as_of_period": session.as_of_period,
        "status": session.status,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "readiness": readiness,
        "export_jobs": jobs,
    }
