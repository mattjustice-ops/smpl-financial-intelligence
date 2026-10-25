"""Org-level close month + fiscal year resolution."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.services.reporting.as_of_period import infer_as_of_period, list_gl_actual_periods, resolve_as_of_period
from app.services.reporting.fiscal_year import fiscal_year_end_period, fiscal_year_start_period
from app.services.reporting.period_utils import period_range, sort_periods, to_period


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


def close_periods_for_review(found: list[str], org_close: str, fiscal_start: str) -> list[str]:
    """Months a person can open. Loaded actuals through the close, or the fiscal year when none are stored."""
    through = to_period(org_close)
    loaded = [to_period(period) for period in found if to_period(period) <= through]
    if loaded:
        return sort_periods(loaded)
    return period_range(fiscal_start, through)


def chosen_close_period(requested: str | None, periods: list[str], default: str) -> str:
    """The month to show. The stored close stays put."""
    if not requested:
        return to_period(default)
    chosen = to_period(requested)
    if chosen not in periods:
        raise ValueError("That close period is not loaded")
    return chosen


def review_reporting_window(
    db: Session,
    org: Organization,
    *,
    as_of_period: str | None = None,
) -> tuple[str, str, str, list[str], str]:
    """Return the viewed month, its fiscal window, every choosable month, and the stored close."""
    org_close, _, _ = resolve_org_reporting_window(db, org)
    fy_end_month = resolve_org_fiscal_year_end_month(org)
    periods = close_periods_for_review(
        list_gl_actual_periods(db, org.id),
        org_close,
        fiscal_year_start_period(org_close, fiscal_year_end_month=fy_end_month),
    )
    chosen = chosen_close_period(as_of_period, periods, org_close)
    start = fiscal_year_start_period(chosen, fiscal_year_end_month=fy_end_month)
    end = fiscal_year_end_period(chosen, fiscal_year_end_month=fy_end_month)
    return chosen, start, end, periods, org_close


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
