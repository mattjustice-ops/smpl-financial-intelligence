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

    # Prefer interactive-speed collect for freeze packs so MD&A/Copilot aren't
    # blocked for minutes on GL/drilldown. Ops can re-prewarm for richer packs.
    bundle = collect_copilot_bundle(
        db,
        organization_id,
        scenario="Combined",
        start_period=start_period,
        end_period=end_period,
        as_of_period=period,
        focus_period=period,
        lightweight=False,
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

    # Persist structured packages alongside prose so Copilot freeze path can
    # verify without re-collecting (commentary/MD&A parity). Packages include
    # `_sources` tags on values (catalog + ENGINE_PATH); not DOM overlay.
    evidence_package: dict[str, Any] | None = None
    attribution_package: dict[str, Any] | None = None
    try:
        from app.services.commentary.attribution_verify import (
            build_attribution_package_from_copilot_structures,
        )
        from app.services.commentary.claim_verify import (
            build_evidence_package_from_copilot_structures,
        )

        evidence_package = build_evidence_package_from_copilot_structures(
            bundle=bundle,
            ts_data=ts_data,
            cash_bridge_table=cash_bridge_table,
            metrics_blob=context_text,
            focus_period=period,
            freeze_id=f"freeze:{organization_id}:{period}",
            period_label=period,
            org_id=str(organization_id),
            loaded_at=datetime.now(timezone.utc).isoformat(),
            is_final=True,
        )
        # JSONB-safe: drop Decimal map (values string map is enough to rebuild).
        evidence_package = {
            k: v for k, v in evidence_package.items() if k != "values_decimal"
        }
        attribution_package = build_attribution_package_from_copilot_structures(
            bundle=bundle,
            cash_bridge_table=cash_bridge_table,
            metrics_blob=context_text,
            focus_period=period,
        )
    except Exception:
        logger.debug("Freeze structured evidence/attribution packages skipped", exc_info=True)

    validation_status = None
    validation_check_ids: list[str] = []
    if bundle.validation is not None:
        validation_status = getattr(bundle.validation, "status", None)
        try:
            checks = getattr(bundle.validation, "checks", None) or []
            validation_check_ids = [
                str(getattr(c, "validation_name", "") or "")
                for c in checks
                if getattr(c, "validation_name", None)
            ]
        except Exception:
            validation_check_ids = []

    sections: dict[str, Any] = {
        "kpis": True,
        "arr": True,
        "cfs": True,
        "gtm": True,
        "pipeline": True,
        "validation": validation_status,
    }
    if evidence_package is not None:
        sections["evidence_package"] = evidence_package
    if attribution_package is not None:
        sections["attribution_package"] = attribution_package
    built_at = _utcnow()
    metadata = {
        "start_period": start_period,
        "end_period": end_period,
        "char_count": len(context_text),
        "organization_name": bundle.organization_name,
        "validation_check_ids": validation_check_ids,
        "has_structured_evidence": evidence_package is not None,
        "has_structured_attribution": attribution_package is not None,
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

    try:
        from app.services.close_context.close_session_service import mark_freeze_complete

        session = mark_freeze_complete(db, organization_id, period)
        metadata = dict(metadata or {})
        metadata["close_session_id"] = str(session.id)
        row.metadata_json = metadata
    except Exception:
        logger.debug("Close session stamp on freeze skipped", exc_info=True)

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


def prewarm_freeze_blobs(
    db: Session,
    *,
    organization_id: uuid.UUID | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Night-before / ops freeze rebuild for active orgs with a close month.

    Rebuilds COMPLETE packs so close morning is not cold. Per-org failures are
    isolated — one bad org does not abort the batch.
    """
    from app.models.organization import Organization
    from app.services.reporting.org_reporting_settings import resolve_org_reporting_window

    query = select(Organization).where(
        Organization.status.in_(("active", "trialing", "past_due")),
        Organization.close_month.is_not(None),
    )
    if organization_id is not None:
        query = query.where(Organization.id == organization_id)
    orgs = db.scalars(query.order_by(Organization.name)).all()

    results: list[dict[str, Any]] = []
    succeeded = 0
    failed = 0
    for org in orgs:
        try:
            as_of, start, end = resolve_org_reporting_window(db, org)
            entry: dict[str, Any] = {
                "organization_id": str(org.id),
                "organization_name": org.name,
                "as_of_period": as_of,
                "start_period": start,
                "end_period": end,
            }
            if dry_run:
                entry["status"] = "dry_run"
                results.append(entry)
                succeeded += 1
                continue
            freeze = build_and_store_freeze_blob(
                db,
                org.id,
                as_of_period=as_of,
                start_period=start,
                end_period=end,
            )
            entry["status"] = "complete"
            entry["freeze_status"] = freeze.status
            entry["built_at"] = freeze.context_as_of_iso
            entry["validation_status"] = freeze.validation_status
            results.append(entry)
            succeeded += 1
        except Exception as exc:
            failed += 1
            logger.exception("Prewarm freeze failed for org=%s", org.id)
            results.append(
                {
                    "organization_id": str(org.id),
                    "organization_name": org.name,
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            try:
                db.rollback()
            except Exception:
                pass

    return {
        "ok": failed == 0,
        "dry_run": dry_run,
        "total": len(orgs),
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
        "generated_at": _utcnow().isoformat(),
    }
