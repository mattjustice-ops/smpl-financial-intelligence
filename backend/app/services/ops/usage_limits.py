"""Plan usage caps and calendar-month enforcement (SMPL Ops Phase 3)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.organization import Organization
from app.models.usage_event import UsageEvent
from app.services.entitlements import normalize_plan
from app.services.ops.ops_period import format_calendar_month, parse_calendar_month

# Keep aligned with frontend/lib/entitlements/usage-limits.ts
# Flat monthly caps for all plans (no tiered ranges).
DEFAULT_USAGE_LIMITS: dict[str, int | float] = {
    "ai_cost_usd_monthly": 10.0,
    "exports_monthly": 10,
    "llm_calls_monthly": 10,
}

# Soft regenerate cap for Prompt 5 (MD&A deck) per org × close period.
DEFAULT_PROMPT5_DECK_PER_CLOSE = 5


@dataclass(frozen=True)
class MonthlyUsageTotals:
    month: str
    ai_cost_usd: float
    llm_calls: int
    exports_complete: int


def limits_for_plan(plan: str | None) -> dict[str, int | float | None]:
    _ = normalize_plan(plan)
    return dict(DEFAULT_USAGE_LIMITS)


def _current_month_bounds() -> tuple[datetime, datetime, str]:
    month = format_calendar_month(datetime.now(timezone.utc))
    start, end = parse_calendar_month(month)
    return start, end, month


def monthly_usage_totals(db: Session, organization_id: uuid.UUID) -> MonthlyUsageTotals:
    start, end, month = _current_month_bounds()

    ai_row = db.execute(
        select(
            func.coalesce(func.sum(UsageEvent.estimated_cost_usd), 0),
            func.count(),
        ).where(
            UsageEvent.organization_id == organization_id,
            UsageEvent.created_at >= start,
            UsageEvent.created_at < end,
            UsageEvent.event_type == "llm_call",
        )
    ).one()

    exports = db.scalar(
        select(func.count())
        .select_from(UsageEvent)
        .where(
            UsageEvent.organization_id == organization_id,
            UsageEvent.created_at >= start,
            UsageEvent.created_at < end,
            UsageEvent.event_type == "export_complete",
        )
    )

    return MonthlyUsageTotals(
        month=month,
        ai_cost_usd=round(float(ai_row[0] or 0), 4),
        llm_calls=int(ai_row[1] or 0),
        exports_complete=int(exports or 0),
    )


def count_mda_deck_runs_for_close(
    db: Session,
    organization_id: uuid.UUID,
    as_of_period: str,
) -> int:
    """Count Prompt 5 deck starts for this org/period (durable usage ledger)."""
    from app.services.reporting.period_utils import to_period

    period = to_period(as_of_period)
    rows = db.scalars(
        select(UsageEvent).where(
            UsageEvent.organization_id == organization_id,
            UsageEvent.feature == "mda_deck",
            UsageEvent.event_type == "export_start",
        )
    ).all()
    count = 0
    for row in rows:
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        if str(meta.get("as_of_period") or "") == period:
            count += 1
    return count


def assert_prompt5_regen_cap(
    db: Session,
    org: Organization,
    as_of_period: str,
) -> None:
    """Soft cap Prompt 5 deck regenerations for one close period (HTTP 429)."""
    settings = get_settings()
    if not getattr(settings, "smpl_usage_limits_enabled", True):
        return
    from app.services.reporting.period_utils import to_period

    period = to_period(as_of_period)
    limit = int(
        getattr(settings, "smpl_prompt5_deck_per_close", DEFAULT_PROMPT5_DECK_PER_CLOSE)
        or DEFAULT_PROMPT5_DECK_PER_CLOSE
    )
    if limit <= 0:
        return
    used = count_mda_deck_runs_for_close(db, org.id, period)
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "prompt5_regen_cap_exceeded",
                "metric": "prompt5_deck_per_close",
                "plan": normalize_plan(org.plan),
                "limit": limit,
                "used": used,
                "as_of_period": period,
                "message": (
                    f"MD&A deck regenerate limit reached for {period} "
                    f"({used}/{limit}). Wait for the next close period or contact SMPL support."
                ),
            },
        )


def _usage_limit_error(
    *,
    org: Organization,
    metric: str,
    limit: int | float,
    used: int | float,
    month: str,
) -> HTTPException:
    _, end = parse_calendar_month(month)
    return HTTPException(
        status_code=403,
        detail={
            "code": "usage_limit_exceeded",
            "metric": metric,
            "plan": normalize_plan(org.plan),
            "limit": limit,
            "used": used,
            "month": month,
            "resets_at": end.isoformat(),
            "message": (
                f"Monthly {metric.replace('_', ' ')} limit reached for "
                f"{normalize_plan(org.plan)} plan ({used}/{limit}). "
                f"Resets on {month} rollover."
            ),
        },
    )


def assert_within_usage_limits(
    db: Session,
    org: Organization,
    *,
    require_export: bool = False,
    require_ai: bool = False,
) -> None:
    settings = get_settings()
    if not getattr(settings, "smpl_usage_limits_enabled", True):
        return
    # Demo/fast path: do not hard-block Copilot / regenerate / board AI on the
    # tiny default monthly LLM caps (10 calls) — those were demo-stoppers.
    if bool(getattr(settings, "smpl_fast_ai", True)) and require_ai and not require_export:
        return

    limits = limits_for_plan(org.plan)
    usage = monthly_usage_totals(db, org.id)

    if require_export:
        cap = limits.get("exports_monthly")
        if cap is not None and usage.exports_complete >= int(cap):
            raise _usage_limit_error(
                org=org,
                metric="exports_monthly",
                limit=int(cap),
                used=usage.exports_complete,
                month=usage.month,
            )

    if require_ai:
        ai_cap = limits.get("ai_cost_usd_monthly")
        if ai_cap is not None and usage.ai_cost_usd >= float(ai_cap):
            raise _usage_limit_error(
                org=org,
                metric="ai_cost_usd_monthly",
                limit=float(ai_cap),
                used=usage.ai_cost_usd,
                month=usage.month,
            )
        llm_cap = limits.get("llm_calls_monthly")
        if llm_cap is not None and usage.llm_calls >= int(llm_cap):
            raise _usage_limit_error(
                org=org,
                metric="llm_calls_monthly",
                limit=int(llm_cap),
                used=usage.llm_calls,
                month=usage.month,
            )


def monthly_usage_status_payload(db: Session, org: Organization) -> dict[str, Any]:
    usage = monthly_usage_totals(db, org.id)
    limits = limits_for_plan(org.plan)
    _, end = parse_calendar_month(usage.month)

    def _pct(used: float | int, cap: int | float | None) -> float | None:
        if cap is None or cap == 0:
            return None
        return round(min(100.0, (float(used) / float(cap)) * 100.0), 1)

    return {
        "organization_id": str(org.id),
        "plan": normalize_plan(org.plan),
        "month": usage.month,
        "resets_at": end.isoformat(),
        "usage": {
            "ai_cost_usd": usage.ai_cost_usd,
            "llm_calls": usage.llm_calls,
            "exports_complete": usage.exports_complete,
        },
        "limits": limits,
        "percent_used": {
            "ai_cost_usd_monthly": _pct(usage.ai_cost_usd, limits.get("ai_cost_usd_monthly")),
            "exports_monthly": _pct(usage.exports_complete, limits.get("exports_monthly")),
            "llm_calls_monthly": _pct(usage.llm_calls, limits.get("llm_calls_monthly")),
        },
        "limits_enabled": getattr(get_settings(), "smpl_usage_limits_enabled", True),
    }
