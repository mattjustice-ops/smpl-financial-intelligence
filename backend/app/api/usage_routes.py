"""Organization monthly usage vs plan limits."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.ops.usage_limits import monthly_usage_status_payload
from app.services.organizations import get_organization_or_404

usage_router = APIRouter(prefix="/usage", tags=["usage"])


@usage_router.get("/monthly-status")
def get_monthly_usage_status(
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    org = get_organization_or_404(db, organization_id)
    return monthly_usage_status_payload(db, org)
