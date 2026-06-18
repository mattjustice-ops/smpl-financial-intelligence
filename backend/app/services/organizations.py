"""Organization helpers — existence, plan entitlements, and membership (poc-4)."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationOut
from app.services.auth.service import AuthService
from app.services.entitlements import normalize_plan, org_has_module
from app.api.deps.request_context import get_request_user_id


def list_organizations(db: Session) -> list[OrganizationOut]:
    rows = db.scalars(select(Organization).order_by(Organization.created_at)).all()
    return [OrganizationOut(id=r.id, name=r.name) for r in rows]


def create_organization(db: Session, body: OrganizationCreate) -> OrganizationOut:
    org = Organization(name=body.name.strip())
    db.add(org)
    db.commit()
    db.refresh(org)
    return OrganizationOut(id=org.id, name=org.name)


def get_organization_or_404(
    db: Session,
    organization_id: uuid.UUID,
    *,
    module: str | None = None,
) -> Organization:
    org = db.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if module and not org_has_module(org, module):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "module_not_entitled",
                "module": module,
                "plan": normalize_plan(org.plan),
            },
        )
    user_id = get_request_user_id()
    if user_id is not None:
        auth = AuthService(db)
        if auth.get_member(user_id=user_id, organization_id=organization_id) is None:
            raise HTTPException(
                status_code=403,
                detail="You do not have access to this organization.",
            )
    return org
