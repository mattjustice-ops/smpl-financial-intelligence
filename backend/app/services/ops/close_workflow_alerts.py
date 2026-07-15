"""Close-week Ops alerts for Customer Close Workflow stuck / blocked states."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.close_session import CloseSession
from app.models.organization import Organization


# How long FREEZING / post-Lock without cert may sit before Ops is paged.
DEFAULT_FREEZE_STUCK_MINUTES = 30
DEFAULT_LOCK_UNCERTIFIED_MINUTES = 45


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def assess_close_workflow_alerts(
    db: Session,
    *,
    freeze_stuck_minutes: int = DEFAULT_FREEZE_STUCK_MINUTES,
    lock_uncertified_minutes: int = DEFAULT_LOCK_UNCERTIFIED_MINUTES,
) -> dict[str, Any]:
    """Return live Ops checks + per-org issues for close workflow stuck states."""
    now = _utcnow()
    freeze_cutoff = now - timedelta(minutes=max(1, freeze_stuck_minutes))
    lock_cutoff = now - timedelta(minutes=max(1, lock_uncertified_minutes))

    sessions = db.scalars(
        select(CloseSession).where(
            CloseSession.workflow_state.in_(
                (
                    "LOCKED",
                    "FREEZING",
                    "READY_TO_LOCK",
                    "VALIDATING",
                    "LOADING_DATA",
                    "REOPENED",
                    "READY_FOR_EXECUTIVE_REVIEW",
                )
            )
        )
    ).all()

    org_ids = {s.organization_id for s in sessions}
    orgs = {
        o.id: o
        for o in db.scalars(select(Organization).where(Organization.id.in_(org_ids))).all()
    } if org_ids else {}

    issues: list[dict[str, Any]] = []
    stuck_freezing = 0
    stuck_locked = 0
    ready_not_locked = 0
    certified = 0

    for session in sessions:
        org = orgs.get(session.organization_id)
        org_name = org.name if org else None
        state = (session.workflow_state or "").upper()
        updated = session.updated_at or session.created_at
        if updated is not None and updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)

        base = {
            "organization_id": str(session.organization_id),
            "organization_name": org_name,
            "as_of_period": session.as_of_period,
            "close_session_id": str(session.id),
            "workflow_state": state,
            "lock_version": int(session.current_lock_version or 0),
            "updated_at": updated.isoformat() if updated else None,
        }

        if state == "READY_FOR_EXECUTIVE_REVIEW" and session.certified_at:
            certified += 1
            continue

        if state == "FREEZING" and updated and updated < freeze_cutoff:
            stuck_freezing += 1
            issues.append(
                {
                    **base,
                    "severity": "error",
                    "code": "freeze_stuck",
                    "message": (
                        f"Freeze stuck in FREEZING for >{freeze_stuck_minutes}m — "
                        "check freeze job / warehouse; customer may be waiting on Certified Close"
                    ),
                    "runbook": "Inspect Railway API logs for freeze build; retry Lock or Ops prewarm-freeze for org",
                }
            )
        elif (
            state == "LOCKED"
            and not session.certified_at
            and updated
            and updated < lock_cutoff
        ):
            stuck_locked += 1
            issues.append(
                {
                    **base,
                    "severity": "error",
                    "code": "lock_uncertified",
                    "message": (
                        f"Locked (v{session.current_lock_version}) without Certified Close "
                        f"for >{lock_uncertified_minutes}m — freeze likely failed after Lock"
                    ),
                    "runbook": "POST close-workflow/lock again or POST board-platform/freeze-context; check freeze errors",
                }
            )
        elif state == "READY_TO_LOCK":
            ready_not_locked += 1
        elif state in ("VALIDATING", "LOADING_DATA", "REOPENED"):
            # Surface idle load/validation only if stalled past freeze threshold.
            if updated and updated < freeze_cutoff:
                issues.append(
                    {
                        **base,
                        "severity": "warning",
                        "code": "load_stalled",
                        "message": (
                            f"Close workflow idle in {state} for >{freeze_stuck_minutes}m — "
                            "may need load help or validation fix"
                        ),
                        "runbook": (
                            "Review Workspace load receipts / API Push status; ask CS to contact customer"
                        ),
                    }
                )

    error_count = sum(1 for i in issues if i["severity"] == "error")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")

    checks = [
        {
            "name": "close_workflow_freeze_stuck",
            "ok": stuck_freezing == 0,
            "detail": (
                f"{stuck_freezing} org(s) stuck FREEZING >{freeze_stuck_minutes}m"
                if stuck_freezing
                else f"No FREEZING sessions older than {freeze_stuck_minutes}m"
            ),
        },
        {
            "name": "close_workflow_lock_uncertified",
            "ok": stuck_locked == 0,
            "detail": (
                f"{stuck_locked} org(s) LOCKED without certification >{lock_uncertified_minutes}m"
                if stuck_locked
                else f"No uncertified LOCKED sessions older than {lock_uncertified_minutes}m"
            ),
        },
    ]

    return {
        "ok": error_count == 0,
        "generated_at": now.isoformat(),
        "summary": {
            "issues_error": error_count,
            "issues_warning": warning_count,
            "ready_to_lock": ready_not_locked,
            "certified": certified,
            "stuck_freezing": stuck_freezing,
            "stuck_locked": stuck_locked,
        },
        "checks": checks,
        "issues": sorted(
            issues,
            key=lambda i: ({"error": 0, "warning": 1, "info": 2}.get(i["severity"], 9), i.get("organization_name") or ""),
        ),
    }
