"""Warehouse readiness checks — board / forecast outlook hydration (all customers)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.services.reporting.org_reporting_settings import resolve_org_reporting_window
from app.services.reporting.period_utils import period_range, to_period
from app.services.reporting.three_statement_payload import build_outlook_api_payload

WarehouseStatus = Literal["ready", "incomplete", "empty", "error"]

# Orgs that can sign in and use /app — same gate as auth deps.
ACTIVE_CUSTOMER_STATUSES = ("active", "trialing", "past_due")


def _outlook_hydration_issues(
    *,
    close_month: str,
    start_period: str,
    arr_waterfall: dict[str, list[float | None]],
) -> list[str]:
    """Mirror frontend smpl-outlook.js outlookPayloadValid rules."""
    issues: list[str] = []
    beginning = arr_waterfall.get("Beginning") or []
    ending = arr_waterfall.get("Ending") or []

    if not ending:
        issues.append("ARR_WATERFALL.Ending array missing")
        return issues

    year = close_month[:4]
    close_idx = int(close_month[5:7]) - 1
    if 0 <= close_idx < len(ending) and ending[close_idx] is None:
        issues.append(
            f"Missing ending ARR for close month {close_month} (board shows incomplete warehouse)"
        )

    if str(start_period or "")[:4] == year and beginning and beginning[0] is None:
        issues.append(
            "Missing Jan beginning ARR in actual_mrr_waterfall "
            "(partial upload may have wiped prior months — reload full Actual_MRR_Waterfall.csv)"
        )

    return issues


def _warehouse_footprint_org_ids(db: Session) -> set[uuid.UUID]:
    """Org IDs with any loaded warehouse or ingest activity."""
    rows = db.execute(
        text(
            """
            SELECT DISTINCT organization_id
            FROM (
                SELECT organization_id FROM actual_mrr_waterfall
                UNION
                SELECT organization_id FROM gl_actuals
                UNION
                SELECT organization_id FROM actual_income_statement
                UNION
                SELECT organization_id FROM ingest_batches WHERE rows_imported > 0
            ) AS footprint
            WHERE organization_id IS NOT NULL
            """
        )
    ).all()
    return {uuid.UUID(str(row[0])) for row in rows if row[0]}


def list_customer_organizations(db: Session) -> list[Organization]:
    return list(
        db.scalars(
            select(Organization)
            .where(Organization.status.in_(ACTIVE_CUSTOMER_STATUSES))
            .order_by(Organization.name)
        ).all()
    )


def _actual_mrr_periods(db: Session, organization_id: uuid.UUID) -> tuple[int, list[str]]:
    rows = db.execute(
        text(
            """
            SELECT period
            FROM actual_mrr_waterfall
            WHERE organization_id = CAST(:oid AS uuid)
              AND period IS NOT NULL
              AND trim(period::text) <> ''
            """
        ),
        {"oid": str(organization_id)},
    ).all()
    periods: list[str] = []
    seen: set[str] = set()
    for row in rows:
        normalized = to_period(str(row[0]))
        if normalized and normalized not in seen:
            seen.add(normalized)
            periods.append(normalized)
    periods.sort()
    return len(periods), periods


def _has_warehouse_footprint(db: Session, organization_id: uuid.UUID) -> bool:
    return organization_id in _warehouse_footprint_org_ids(db)


def assess_warehouse_readiness(
    db: Session,
    organization_id: uuid.UUID,
    *,
    has_footprint: bool | None = None,
) -> dict[str, Any]:
    """Return whether /app/board can hydrate from /api/v1/reporting/outlook for one org."""
    oid = organization_id
    org = db.get(Organization, oid)
    if org is None:
        return {
            "ok": False,
            "status": "error",
            "organization_id": str(oid),
            "organization_name": None,
            "plan": None,
            "close_month": None,
            "start_period": None,
            "issues": [f"Organization not found: {oid}"],
            "actual_mrr_row_count": 0,
            "actual_mrr_periods": [],
            "board_hydrate_ready": False,
        }

    footprint = has_footprint if has_footprint is not None else _has_warehouse_footprint(db, oid)
    if not footprint:
        return {
            "ok": True,
            "status": "empty",
            "organization_id": str(oid),
            "organization_name": org.name,
            "plan": org.plan,
            "close_month": org.close_month,
            "start_period": None,
            "issues": ["No warehouse data loaded yet"],
            "actual_mrr_row_count": 0,
            "actual_mrr_periods": [],
            "board_hydrate_ready": False,
        }

    as_of, start_period, end_period = resolve_org_reporting_window(db, org)
    row_count, mrr_periods = _actual_mrr_periods(db, oid)

    try:
        outlook = build_outlook_api_payload(db, oid)
        arr_wf = outlook.get("ARR_WATERFALL") or {}
    except Exception as exc:
        return {
            "ok": False,
            "status": "error",
            "organization_id": str(oid),
            "organization_name": org.name,
            "plan": org.plan,
            "close_month": as_of,
            "start_period": start_period,
            "issues": [f"Outlook payload build failed: {exc}"],
            "actual_mrr_row_count": row_count,
            "actual_mrr_periods": mrr_periods,
            "board_hydrate_ready": False,
        }

    issues = _outlook_hydration_issues(
        close_month=as_of,
        start_period=start_period,
        arr_waterfall=arr_wf,
    )

    expected_actual = [p for p in period_range(start_period, end_period) if p <= as_of]
    missing_periods = [p for p in expected_actual if p not in mrr_periods]
    if missing_periods:
        issues.append(
            f"actual_mrr_waterfall missing period(s): {', '.join(missing_periods)} "
            f"(have {row_count} distinct period(s))"
        )

    ending = arr_wf.get("Ending") or []
    close_idx = int(as_of[5:7]) - 1
    close_ending = ending[close_idx] if 0 <= close_idx < len(ending) else None
    ready = len(issues) == 0

    return {
        "ok": ready,
        "status": "ready" if ready else "incomplete",
        "organization_id": str(oid),
        "organization_name": org.name,
        "plan": org.plan,
        "close_month": as_of,
        "start_period": start_period,
        "end_period": end_period,
        "issues": issues,
        "actual_mrr_row_count": row_count,
        "actual_mrr_periods": mrr_periods,
        "close_month_ending_arr": close_ending,
        "board_hydrate_ready": ready,
    }


def assess_all_customer_warehouses(db: Session) -> dict[str, Any]:
    """Assess board hydration for every active customer org."""
    footprint_ids = _warehouse_footprint_org_ids(db)
    orgs = list_customer_organizations(db)

    organizations: list[dict[str, Any]] = []
    for org in orgs:
        try:
            organizations.append(
                assess_warehouse_readiness(
                    db,
                    org.id,
                    has_footprint=org.id in footprint_ids,
                )
            )
        except Exception as exc:
            organizations.append(
                {
                    "ok": False,
                    "status": "error",
                    "organization_id": str(org.id),
                    "organization_name": org.name,
                    "plan": org.plan,
                    "close_month": org.close_month,
                    "issues": [f"Health check error: {exc}"],
                    "actual_mrr_row_count": 0,
                    "actual_mrr_periods": [],
                    "board_hydrate_ready": False,
                }
            )

    ready = [o for o in organizations if o.get("status") == "ready"]
    incomplete = [o for o in organizations if o.get("status") == "incomplete"]
    empty = [o for o in organizations if o.get("status") == "empty"]
    errors = [o for o in organizations if o.get("status") == "error"]
    failing = incomplete + errors

    return {
        "ok": len(failing) == 0,
        "organizations_total": len(organizations),
        "organizations_ready": len(ready),
        "organizations_incomplete": len(incomplete),
        "organizations_empty": len(empty),
        "organizations_error": len(errors),
        "organizations": organizations,
        "failing": failing,
    }


def warehouse_health_check_row(db: Session) -> dict[str, Any]:
    """Single check dict for run_platform_health_checks."""
    summary = assess_all_customer_warehouses(db)
    detail = (
        f"{summary['organizations_ready']}/{summary['organizations_total']} customer warehouse(s) ready"
    )
    if summary["organizations_incomplete"]:
        names = ", ".join(
            o.get("organization_name") or o.get("organization_id", "?")
            for o in summary["failing"]
        )
        detail = f"{detail} — incomplete: {names}"
    elif summary["organizations_error"]:
        names = ", ".join(
            o.get("organization_name") or o.get("organization_id", "?") for o in summary["failing"]
        )
        detail = f"{detail} — error: {names}"

    return {
        "name": "customer_warehouse_board",
        "ok": summary["ok"],
        "detail": detail,
        "warehouse": summary,
    }
