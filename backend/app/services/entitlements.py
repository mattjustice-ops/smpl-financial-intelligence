"""Plan seat limits and entitlements (used at login and API authorization)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.user import OrganizationMember

# Keep aligned with frontend/lib/billing/plans.ts PRICING_TIERS.*.usersIncluded
PLAN_SEAT_LIMITS: dict[str, int] = {
    "starter": 2,
    "professional": 5,
    "enterprise": 10,
    "growth": 5,  # legacy alias → professional
}


def normalize_plan(plan: str | None) -> str:
    if not plan:
        return "starter"
    key = plan.strip().lower()
    if key == "growth":
        return "professional"
    return key


def seat_limit_for_org(org: Organization) -> int:
    plan = normalize_plan(org.plan)
    return PLAN_SEAT_LIMITS.get(plan, PLAN_SEAT_LIMITS["starter"])


def count_active_seats(db: Session, organization_id) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(OrganizationMember)
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.status == "active",
            )
        )
        or 0
    )


def seats_available(db: Session, org: Organization) -> int:
    return max(0, seat_limit_for_org(org) - count_active_seats(db, org.id))
