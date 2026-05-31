"""Marketing channel drilldown service."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.services.marketing.service import channel_performance
from app.services.marketing.schemas import MarketingResponse


def channel_drilldown(db: Session, organization_id: uuid.UUID, **params) -> MarketingResponse:
    return channel_performance(db, organization_id, **params)
