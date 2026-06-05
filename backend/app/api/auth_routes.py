"""Customer auth — session sync from Next.js / Auth.js."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps.auth import require_internal_auth_key
from app.db.session import get_db
from app.services.auth.service import AuthService, AuthSyncError

auth_router = APIRouter(prefix="/auth", tags=["auth"])


class SessionSyncRequest(BaseModel):
    email: EmailStr
    name: str | None = Field(default=None, max_length=255)
    auth_subject: str | None = Field(default=None, max_length=255)


@auth_router.post("/session-sync")
def session_sync(
    body: SessionSyncRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_auth_key),
) -> dict:
    service = AuthService(db)
    try:
        return service.sync_session(
            email=str(body.email),
            name=body.name,
            auth_subject=body.auth_subject,
        )
    except AuthSyncError as exc:
        status = 403 if exc.code in ("no_access", "seats_full") else 400
        raise HTTPException(status_code=status, detail={"code": exc.code, "message": exc.message}) from exc


@auth_router.get("/organizations/{organization_id}/seats")
def organization_seat_usage(
    organization_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_auth_key),
) -> dict:
    from app.models.organization import Organization
    from app.services.entitlements import count_active_seats, seat_limit_for_org

    org = db.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found.")
    limit = seat_limit_for_org(org)
    used = count_active_seats(db, org.id)
    return {
        "organizationId": str(org.id),
        "plan": org.plan,
        "seatLimit": limit,
        "seatsUsed": used,
        "seatsAvailable": max(0, limit - used),
    }
