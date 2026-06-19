"""Forecast version lifecycle — drafts, promote-to-final, active registry."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.request_context import get_request_user_id
from app.models.forecast_version import ForecastVersion
from app.models.organization import Organization
from app.services.auth.service import AuthService
from app.services.demo_csv.loader import PROMOTABLE_FORECAST_TABLES, promote_forecast_tables
from app.services.organizations import get_organization_or_404
from app.services.reporting.org_reporting_settings import resolve_org_reporting_window
from app.services.reporting.validation_gate import raise_if_validation_blocked
from app.services.reporting.export.data_collector import collect_reporting_bundle
from app.services.reporting.as_of_period import bind_as_of_period, reset_as_of_period


PROMOTER_ROLES = frozenset({"admin", "owner"})


def require_org_promoter(db: Session, organization_id: uuid.UUID) -> tuple[Organization, uuid.UUID]:
    user_id = get_request_user_id()
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required to modify forecast versions.")
    auth = AuthService(db)
    member_org = auth.get_member(user_id=user_id, organization_id=organization_id)
    if member_org is None:
        raise HTTPException(status_code=403, detail="You do not have access to this organization.")
    member, org = member_org
    if member.role not in PROMOTER_ROLES:
        raise HTTPException(status_code=403, detail="Only organization admins can save or promote forecast versions.")
    return org, user_id


def list_forecast_versions(db: Session, organization_id: uuid.UUID) -> list[ForecastVersion]:
    get_organization_or_404(db, organization_id, module="forecast_engine")
    return list(
        db.scalars(
            select(ForecastVersion)
            .where(ForecastVersion.organization_id == organization_id)
            .order_by(ForecastVersion.created_at.desc())
        ).all()
    )


def get_forecast_version(db: Session, organization_id: uuid.UUID, version_id: uuid.UUID) -> ForecastVersion:
    get_organization_or_404(db, organization_id, module="forecast_engine")
    version = db.get(ForecastVersion, version_id)
    if version is None or version.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Forecast version not found.")
    return version


def get_active_forecast_version(db: Session, org: Organization) -> ForecastVersion | None:
    if org.active_forecast_version_id is None:
        return None
    version = db.get(ForecastVersion, org.active_forecast_version_id)
    if version is None or version.status != "final":
        return None
    return version


def save_forecast_draft(
    db: Session,
    organization_id: uuid.UUID,
    *,
    version_name: str,
    as_of_period: str | None = None,
    horizon: str | None = None,
    levers: dict[str, Any] | None = None,
    req_active: dict[str, Any] | None = None,
    results: dict[str, Any] | None = None,
    tables: dict[str, list[dict[str, Any]]] | None = None,
    version_id: uuid.UUID | None = None,
) -> ForecastVersion:
    org, user_id = require_org_promoter(db, organization_id)
    get_organization_or_404(db, organization_id, module="forecast_engine")
    as_of, _, _ = resolve_org_reporting_window(db, org, as_of_period=as_of_period)

    if version_id:
        version = get_forecast_version(db, organization_id, version_id)
        if version.status == "final":
            raise HTTPException(status_code=409, detail="Cannot edit a final forecast version.")
    else:
        version = ForecastVersion(
            organization_id=organization_id,
            version_name=version_name.strip(),
            status="draft",
            as_of_period=as_of,
            created_by_user_id=user_id,
        )
        db.add(version)

    version.version_name = version_name.strip()
    version.horizon = horizon
    version.as_of_period = as_of
    version.levers = levers
    version.req_active = req_active
    version.results = results
    if tables:
        version.table_manifest = sorted(tables.keys())
        version.results = {**(version.results or {}), "tables": tables}
    db.flush()
    db.commit()
    db.refresh(version)
    return version


def promote_forecast_version(
    db: Session,
    organization_id: uuid.UUID,
    version_id: uuid.UUID,
) -> ForecastVersion:
    org, _user_id = require_org_promoter(db, organization_id)
    get_organization_or_404(db, organization_id, module="forecast_engine")
    version = get_forecast_version(db, organization_id, version_id)

    if version.status == "final":
        raise HTTPException(status_code=409, detail="Version is already final.")

    tables_payload = _extract_tables_from_version(version)
    if not tables_payload:
        raise HTTPException(
            status_code=400,
            detail="No forecast table data on this version. Save a draft with table rows before promoting.",
        )

    as_of, start_period, end_period = resolve_org_reporting_window(db, org, as_of_period=version.as_of_period)

    for prior in db.scalars(
        select(ForecastVersion).where(
            ForecastVersion.organization_id == organization_id,
            ForecastVersion.status == "final",
        )
    ).all():
        prior.status = "superseded"
        db.add(prior)

    loaded = promote_forecast_tables(
        db,
        organization_id,
        tables=tables_payload,
        forecast_version_id=version.id,
        as_of_period=version.as_of_period,
    )

    token = bind_as_of_period(version.as_of_period)
    try:
        bundle = collect_reporting_bundle(
            db,
            organization_id,
            scenario="Combined",
            start_period=start_period,
            end_period=end_period,
            as_of_period=as_of,
        )
    finally:
        reset_as_of_period(token)

    raise_if_validation_blocked(bundle.validation, action="Promote to final")

    version.status = "final"
    version.promoted_at = datetime.now(timezone.utc)
    version.table_manifest = sorted(loaded.keys())
    db.add(version)

    org.active_forecast_version_id = version.id
    db.add(org)
    db.commit()
    db.refresh(version)
    return version


def _extract_tables_from_version(version: ForecastVersion) -> dict[str, list[dict[str, str]]]:
    results = version.results or {}
    raw_tables = results.get("tables") if isinstance(results, dict) else None
    if not isinstance(raw_tables, dict):
        return {}
    out: dict[str, list[dict[str, str]]] = {}
    for table_name, rows in raw_tables.items():
        if table_name not in PROMOTABLE_FORECAST_TABLES or not isinstance(rows, list):
            continue
        out[table_name] = [
            {str(k): "" if v is None else str(v) for k, v in row.items()}
            for row in rows
            if isinstance(row, dict)
        ]
    return out
