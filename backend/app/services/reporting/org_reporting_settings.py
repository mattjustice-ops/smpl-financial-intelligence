"""Org-level close month + fiscal year resolution."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.services.reporting.as_of_period import infer_as_of_period, resolve_as_of_period
from app.services.reporting.fiscal_year import fiscal_year_end_period, fiscal_year_start_period
from app.services.reporting.period_utils import to_period


def resolve_org_fiscal_year_end_month(org: Organization) -> int:
    month = getattr(org, "fiscal_year_end_month", None) or 12
    return max(1, min(12, int(month)))


def resolve_org_close_month(
    db: Session,
    org: Organization,
    *,
    as_of_period: str | None = None,
    end_period: str | None = None,
) -> str:
    if org.close_month:
        return to_period(org.close_month)
    return resolve_as_of_period(
        db,
        org.id,
        as_of_period=as_of_period,
        end_period=end_period,
    )


def resolve_org_reporting_window(
    db: Session,
    org: Organization,
    *,
    as_of_period: str | None = None,
) -> tuple[str, str, str]:
    """Return (as_of_period, start_period, end_period) for monthly roll through current FY."""
    fy_end_month = resolve_org_fiscal_year_end_month(org)
    as_of = resolve_org_close_month(db, org, as_of_period=as_of_period)
    start = fiscal_year_start_period(as_of, fiscal_year_end_month=fy_end_month)
    end = fiscal_year_end_period(as_of, fiscal_year_end_month=fy_end_month)
    return as_of, start, end


def ensure_org_reporting_defaults(db: Session, org: Organization) -> None:
    """Set calendar-year defaults for demo orgs when unset."""
    changed = False
    if not org.close_month:
        inferred = infer_as_of_period(db, org.id)
        if inferred:
            org.close_month = inferred
            changed = True
    if getattr(org, "fiscal_year_end_month", None) in (None, 0):
        org.fiscal_year_end_month = 12
        changed = True
    if changed:
        db.add(org)
        db.flush()
