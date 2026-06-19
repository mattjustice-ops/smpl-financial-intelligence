"""Plan seat limits and module entitlements (login + API authorization)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.user import OrganizationMember

# Keep aligned with frontend/lib/entitlements/plan-modules.ts
PLAN_SEAT_LIMITS: dict[str, int] = {
    "starter": 2,
    "professional": 5,
    "enterprise": 10,
    "growth": 5,  # legacy alias → professional
}

STARTER_MODULES: frozenset[str] = frozenset(
    {
        "executive",
        "arr",
        "revenue",
        "gtm",
        "pipeline",
        "decisions",
        "board_export",
        "ai_commentary",
    }
)

PROFESSIONAL_MODULES: frozenset[str] = STARTER_MODULES | frozenset(
    {"management-pl", "workforce", "cash"}
)

ENTERPRISE_MODULES: frozenset[str] = PROFESSIONAL_MODULES | frozenset({"forecast_engine"})

PLAN_MODULES: dict[str, frozenset[str]] = {
    "starter": STARTER_MODULES,
    "professional": PROFESSIONAL_MODULES,
    "enterprise": ENTERPRISE_MODULES,
}


def normalize_plan(plan: str | None) -> str:
    if not plan:
        return "starter"
    key = plan.strip().lower()
    if key == "growth":
        return "professional"
    return key


def modules_for_plan(plan: str | None) -> frozenset[str]:
    key = normalize_plan(plan)
    return PLAN_MODULES.get(key, STARTER_MODULES)


def modules_for_org(org: Organization) -> list[str]:
    return sorted(modules_for_plan(org.plan))


def org_has_module(org: Organization, module_id: str) -> bool:
    return module_id in modules_for_plan(org.plan)


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
