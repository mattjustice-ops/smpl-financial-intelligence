"""Close-context freeze blob service — build, serve, and mark stale.

Rev 4 rules:
- Serve COMPLETE (or last COMPLETE text when STALE) only — never a partial pack
- Always expose built_at as context as-of for Copilot / Prompt 5
- Pack is sectioned text rich enough for MD&A + Q&A, not headline KPIs alone
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.close_context_blob import CloseContextBlob
from app.services.reporting.period_utils import to_period

logger = logging.getLogger(__name__)

BlobStatus = Literal["COMPLETE", "STALE"]
ContextSource = Literal["freeze", "live"]

_AUTO_FREEZE_DEBOUNCE_SECONDS = 120
_auto_freeze_lock = threading.Lock()
_auto_freeze_inflight: set[str] = set()


@dataclass
class FreezeContext:
    organization_id: uuid.UUID
    as_of_period: str
    status: BlobStatus
    context_text: str
    built_at: datetime
    validation_status: str | None = None
    sections: dict[str, Any] | None = None
    source: ContextSource = "freeze"
    stale: bool = False

    @property
    def context_as_of_iso(self) -> str:
        built = self.built_at
        if built.tzinfo is None:
            built = built.replace(tzinfo=timezone.utc)
        return built.astimezone(timezone.utc).isoformat()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_servable_freeze(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
) -> FreezeContext | None:
    """Return COMPLETE or STALE (last complete text) blob — never partial."""
    period = to_period(as_of_period)
    row = db.scalars(
        select(CloseContextBlob).where(
            CloseContextBlob.organization_id == organization_id,
            CloseContextBlob.as_of_period == period,
            CloseContextBlob.status.in_(("COMPLETE", "STALE")),
            CloseContextBlob.context_text.is_not(None),
        )
    ).first()
    if row is None or not row.context_text:
        return None
    status: BlobStatus = "STALE" if row.status == "STALE" else "COMPLETE"
    return FreezeContext(
        organization_id=organization_id,
        as_of_period=period,
        status=status,
        context_text=row.context_text,
        built_at=row.built_at,
        validation_status=row.validation_status,
        sections=row.sections_json,
        source="freeze",
        stale=status == "STALE",
    )


def mark_blob_stale(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
) -> CloseContextBlob | None:
    """Mark existing COMPLETE pack STALE when new ingest starts for the period."""
    period = to_period(as_of_period)
    row = db.scalars(
        select(CloseContextBlob).where(
            CloseContextBlob.organization_id == organization_id,
            CloseContextBlob.as_of_period == period,
            CloseContextBlob.status == "COMPLETE",
        )
    ).first()
    if row is None:
        return None
    row.status = "STALE"
    row.updated_at = _utcnow()
    db.commit()
    db.refresh(row)
    return row


def build_and_store_freeze_blob(
    db: Session,
    organization_id: uuid.UUID,
    *,
    as_of_period: str,
    start_period: str,
    end_period: str,
) -> FreezeContext:
    """Collect live warehouse context and upsert a COMPLETE freeze pack.

    Failures leave any prior COMPLETE/STALE row untouched (never store a partial).
    """
    from app.services.reporting.export.board_commentary_service import copilot_context_blob
    from app.services.reporting.export.data_collector import collect_copilot_bundle
    from app.services.reporting.three_statement_payload import build_cash_bridge_data, build_ts_data

    period = to_period(as_of_period)

    bundle = collect_copilot_bundle(
        db,
        organization_id,
        scenario="Combined",
        start_period=start_period,
        end_period=end_period,
        as_of_period=period,
        focus_period=period,
    )
    cash_bridge_table = build_cash_bridge_data(
        db,
        organization_id,
        start_period=start_period,
        end_period=end_period,
    )
    ts_data = build_ts_data(
        db,
        organization_id,
        as_of=period,
        start_period=start_period,
        end_period=end_period,
    )
    context_text = copilot_context_blob(
        bundle,
        cash_bridge_table=cash_bridge_table,
        ts_data=ts_data,
        focus_period=period,
        max_chars=48000,
    )
    try:
        exec_json = bundle.executive_flow.model_dump(mode="json")
        kpis = exec_json.get("kpis")
        if kpis:
            context_text += "\n\nExecutive KPIs JSON:\n" + str(kpis)[:3000]
    except Exception:
        pass

    validation_status = None
    if bundle.validation is not None:
        validation_status = getattr(bundle.validation, "status", None)

    sections = {
        "kpis": True,
        "arr": True,
        "cfs": True,
        "gtm": True,
        "pipeline": True,
        "validation": validation_status,
    }
    built_at = _utcnow()
    metadata = {
        "start_period": start_period,
        "end_period": end_period,
        "char_count": len(context_text),
        "organization_name": bundle.organization_name,
    }

    existing = db.scalars(
        select(CloseContextBlob).where(
            CloseContextBlob.organization_id == organization_id,
            CloseContextBlob.as_of_period == period,
        )
    ).first()

    if existing is None:
        row = CloseContextBlob(
            organization_id=organization_id,
            as_of_period=period,
            status="COMPLETE",
            sections_json=sections,
            context_text=context_text,
            validation_status=validation_status,
            metadata_json=metadata,
            built_at=built_at,
        )
        db.add(row)
    else:
        row = existing
        row.status = "COMPLETE"
        row.sections_json = sections
        row.context_text = context_text
        row.validation_status = validation_status
        row.metadata_json = metadata
        row.built_at = built_at
        row.updated_at = built_at

    db.commit()
    db.refresh(row)

    return FreezeContext(
        organization_id=organization_id,
        as_of_period=period,
        status="COMPLETE",
        context_text=context_text,
        built_at=row.built_at,
        validation_status=validation_status,
        sections=sections,
        source="freeze",
        stale=False,
    )


def _org_period_key(organization_id: uuid.UUID, as_of_period: str) -> str:
    return f"{organization_id}:{to_period(as_of_period)}"


def should_auto_freeze_for_validation(status: str | None) -> bool:
    """Freeze after a clean pass; skip fail. Warnings still freeze (usable close pack)."""
    return status in ("pass", "warning")


def _recent_complete_exists(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
    *,
    within_seconds: int = _AUTO_FREEZE_DEBOUNCE_SECONDS,
) -> bool:
    period = to_period(as_of_period)
    row = db.scalars(
        select(CloseContextBlob).where(
            CloseContextBlob.organization_id == organization_id,
            CloseContextBlob.as_of_period == period,
            CloseContextBlob.status == "COMPLETE",
        )
    ).first()
    if row is None or row.built_at is None:
        return False
    built = row.built_at
    if built.tzinfo is None:
        built = built.replace(tzinfo=timezone.utc)
    age = (_utcnow() - built.astimezone(timezone.utc)).total_seconds()
    return age < within_seconds


def _run_auto_freeze_job(
    organization_id: uuid.UUID,
    *,
    as_of_period: str,
    start_period: str,
    end_period: str,
) -> None:
    from app.db.session import SessionLocal
    from app.services.reporting.as_of_period import bind_as_of_period, reset_as_of_period

    key = _org_period_key(organization_id, as_of_period)
    db = SessionLocal()
    token = bind_as_of_period(as_of_period)
    try:
        build_and_store_freeze_blob(
            db,
            organization_id,
            as_of_period=as_of_period,
            start_period=start_period,
            end_period=end_period,
        )
        logger.info(
            "Auto-freeze COMPLETE for org=%s period=%s",
            organization_id,
            as_of_period,
        )
    except Exception:
        logger.exception(
            "Auto-freeze failed for org=%s period=%s (non-blocking)",
            organization_id,
            as_of_period,
        )
    finally:
        reset_as_of_period(token)
        db.close()
        with _auto_freeze_lock:
            _auto_freeze_inflight.discard(key)


def schedule_auto_freeze_after_validation(
    db: Session,
    organization_id: uuid.UUID,
    *,
    validation_status: str | None,
    as_of_period: str,
    start_period: str,
    end_period: str,
) -> bool:
    """Best-effort background freeze after validation pass/warning.

    Returns True if a rebuild was scheduled. Never raises to the caller.
    Debounces recent COMPLETE packs and prevents duplicate in-flight jobs
    for the same (org, period).
    """
    try:
        if not should_auto_freeze_for_validation(validation_status):
            return False
        period = to_period(as_of_period)
        if _recent_complete_exists(db, organization_id, period):
            logger.info(
                "Auto-freeze skipped (debounce) org=%s period=%s",
                organization_id,
                period,
            )
            return False
        key = _org_period_key(organization_id, period)
        with _auto_freeze_lock:
            if key in _auto_freeze_inflight:
                return False
            _auto_freeze_inflight.add(key)
        threading.Thread(
            target=_run_auto_freeze_job,
            kwargs={
                "organization_id": organization_id,
                "as_of_period": period,
                "start_period": start_period,
                "end_period": end_period,
            },
            name=f"auto-freeze-{period}",
            daemon=True,
        ).start()
        return True
    except Exception:
        logger.exception("Failed to schedule auto-freeze for org=%s", organization_id)
        return False
