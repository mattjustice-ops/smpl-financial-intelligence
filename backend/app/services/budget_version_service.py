"""Budget version lifecycle — drafts, promote-to-final, active registry."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.request_context import get_request_user_id
from app.models.budget_version import BudgetVersion
from app.models.organization import Organization
from app.services.auth.service import AuthService
from app.services.demo_csv.loader import PROMOTABLE_BUDGET_TABLES, promote_budget_tables
from app.services.organizations import get_organization_or_404
from app.services.reporting.org_reporting_settings import resolve_org_reporting_window


PROMOTER_ROLES = frozenset({"admin", "owner"})


def require_org_promoter(db: Session, organization_id: uuid.UUID) -> tuple[Organization, uuid.UUID]:
    user_id = get_request_user_id()
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required to modify budget versions.")
    auth = AuthService(db)
    member_org = auth.get_member(user_id=user_id, organization_id=organization_id)
    if member_org is None:
        raise HTTPException(status_code=403, detail="You do not have access to this organization.")
    member, org = member_org
    if member.role not in PROMOTER_ROLES:
        raise HTTPException(status_code=403, detail="Only organization admins can save or promote budget versions.")
    return org, user_id


def list_budget_versions(db: Session, organization_id: uuid.UUID) -> list[BudgetVersion]:
    get_organization_or_404(db, organization_id)
    return list(
        db.scalars(
            select(BudgetVersion)
            .where(BudgetVersion.organization_id == organization_id)
            .order_by(BudgetVersion.created_at.desc())
        ).all()
    )


def get_budget_version(db: Session, organization_id: uuid.UUID, version_id: uuid.UUID) -> BudgetVersion:
    get_organization_or_404(db, organization_id)
    version = db.get(BudgetVersion, version_id)
    if version is None or version.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Budget version not found.")
    return version


def get_active_budget_version(db: Session, org: Organization) -> BudgetVersion | None:
    """Return the org's active final budget, else the most recently promoted final."""
    if org.active_budget_version_id is not None:
        version = db.get(BudgetVersion, org.active_budget_version_id)
        if (
            version is not None
            and version.organization_id == org.id
            and version.status == "final"
        ):
            return version
    return db.scalars(
        select(BudgetVersion)
        .where(
            BudgetVersion.organization_id == org.id,
            BudgetVersion.status == "final",
        )
        .order_by(
            BudgetVersion.promoted_at.desc().nulls_last(),
            BudgetVersion.created_at.desc(),
        )
        .limit(1)
    ).first()


def save_budget_draft(
    db: Session,
    organization_id: uuid.UUID,
    *,
    version_name: str,
    as_of_period: str | None = None,
    budget_year: int | None = None,
    levers: dict[str, Any] | None = None,
    results: dict[str, Any] | None = None,
    tables: dict[str, list[dict[str, Any]]] | None = None,
    version_id: uuid.UUID | None = None,
) -> BudgetVersion:
    org, user_id = require_org_promoter(db, organization_id)
    get_organization_or_404(db, organization_id)
    as_of, _, _ = resolve_org_reporting_window(db, org, as_of_period=as_of_period)

    if version_id:
        version = get_budget_version(db, organization_id, version_id)
        if version.status == "final":
            raise HTTPException(status_code=409, detail="Cannot edit a final budget version.")
    else:
        version = BudgetVersion(
            organization_id=organization_id,
            version_name=version_name.strip(),
            status="draft",
            as_of_period=as_of,
            created_by_user_id=user_id,
        )
        db.add(version)

    version.version_name = version_name.strip()
    version.budget_year = budget_year
    version.as_of_period = as_of
    version.levers = levers
    version.results = results
    if tables:
        version.table_manifest = sorted(tables.keys())
        version.results = {**(version.results or {}), "tables": tables}
    db.flush()
    db.commit()
    db.refresh(version)
    return version


def promote_budget_version(
    db: Session,
    organization_id: uuid.UUID,
    version_id: uuid.UUID,
) -> BudgetVersion:
    org, _user_id = require_org_promoter(db, organization_id)
    get_organization_or_404(db, organization_id)
    version = get_budget_version(db, organization_id, version_id)

    if version.status == "final":
        raise HTTPException(status_code=409, detail="Version is already final.")

    tables_payload = _extract_tables_from_version(version)
    if not tables_payload:
        raise HTTPException(
            status_code=400,
            detail="No budget table data on this version. Save a draft with table rows before promoting.",
        )

    for prior in db.scalars(
        select(BudgetVersion).where(
            BudgetVersion.organization_id == organization_id,
            BudgetVersion.status == "final",
        )
    ).all():
        prior.status = "superseded"
        db.add(prior)

    loaded = promote_budget_tables(
        db,
        organization_id,
        tables=tables_payload,
        budget_version_id=version.id,
        as_of_period=version.as_of_period,
    )

    version.status = "final"
    version.promoted_at = datetime.now(timezone.utc)
    version.table_manifest = sorted(loaded.keys())
    db.add(version)

    org.active_budget_version_id = version.id
    db.add(org)
    db.commit()
    db.refresh(version)
    return version


def _extract_tables_from_version(version: BudgetVersion) -> dict[str, list[dict[str, str]]]:
    results = version.results or {}
    raw_tables = results.get("tables") if isinstance(results, dict) else None
    if not isinstance(raw_tables, dict):
        return {}
    out: dict[str, list[dict[str, str]]] = {}
    for table_name, rows in raw_tables.items():
        if table_name not in PROMOTABLE_BUDGET_TABLES or not isinstance(rows, list):
            continue
        out[table_name] = [
            {str(k): "" if v is None else str(v) for k, v in row.items()}
            for row in rows
            if isinstance(row, dict)
        ]
    return out
