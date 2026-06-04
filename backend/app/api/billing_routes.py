"""Billing API — called from Next.js Stripe routes."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.billing import BillingCheckoutSession
from app.services.billing.service import BillingService

billing_router = APIRouter(prefix="/billing", tags=["billing"])


def _require_internal_key(x_billing_internal_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("BILLING_INTERNAL_API_KEY", "").strip()
    if not expected:
        return
    if x_billing_internal_key != expected:
        raise HTTPException(status_code=401, detail="Invalid billing internal API key")


class CheckoutSessionRecord(BaseModel):
    stripe_checkout_session_id: str = Field(min_length=1, max_length=255)
    customer_email: EmailStr
    plan: str = Field(pattern=r"^(starter|professional|growth)$")
    billing_interval: str = Field(pattern=r"^(monthly|annual)$")
    organization_id: uuid.UUID | None = None


class StripeEventProcess(BaseModel):
    stripe_event_id: str
    event_type: str
    payload: dict[str, Any]


class AccountQuery(BaseModel):
    organization_id: uuid.UUID | None = None
    stripe_customer_id: str | None = None
    email: EmailStr | None = None


@billing_router.post("/checkout-sessions")
def record_checkout_session(
    body: CheckoutSessionRecord,
    db: Session = Depends(get_db),
    _: None = Depends(_require_internal_key),
) -> dict[str, str]:
    service = BillingService(db)
    row = service.record_checkout_session(
        stripe_checkout_session_id=body.stripe_checkout_session_id,
        customer_email=str(body.customer_email),
        plan=body.plan,
        billing_interval=body.billing_interval,
        organization_id=body.organization_id,
    )
    return {"id": str(row.id)}


@billing_router.post("/stripe-events")
def process_stripe_event(
    body: StripeEventProcess,
    db: Session = Depends(get_db),
    _: None = Depends(_require_internal_key),
) -> dict[str, Any]:
    service = BillingService(db)
    event_row = service.begin_event(body.stripe_event_id, body.event_type, body.payload)
    if event_row is None:
        return {"ok": True, "duplicate": True}

    try:
        org_id = service.process_stripe_event(body.event_type, body.payload, event_row)
        return {"ok": True, "organization_id": str(org_id) if org_id else None}
    except Exception as exc:
        service.fail_event(event_row, str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@billing_router.get("/account")
def get_billing_account(
    organization_id: uuid.UUID | None = None,
    stripe_customer_id: str | None = None,
    email: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    service = BillingService(db)
    summary = service.get_account_summary(
        organization_id=organization_id,
        stripe_customer_id=stripe_customer_id,
        email=email,
    )
    if summary is None:
        raise HTTPException(status_code=404, detail="Billing account not found")
    return summary


@billing_router.get("/checkout-rate-limit")
def checkout_rate_limit(email: str, db: Session = Depends(get_db)) -> dict[str, bool]:
    """Return allowed=false if too many open checkout sessions in the last hour."""
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    count = db.scalar(
        select(func.count())
        .select_from(BillingCheckoutSession)
        .where(
            BillingCheckoutSession.customer_email == email.lower(),
            BillingCheckoutSession.created_at >= since,
        )
    )
    allowed = int(count or 0) < 10
    return {"allowed": allowed}
