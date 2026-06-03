"""Inbound quote request persistence (marketing site)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.quote_submission import QuoteSubmission

quote_router = APIRouter(prefix="/quotes", tags=["quotes"])


class QuoteSubmissionCreate(BaseModel):
    email: EmailStr
    payload: dict[str, Any]
    lead_score: int = Field(ge=0, le=100)
    recommended_package: str = Field(min_length=1, max_length=64)
    hubspot_contact_id: str | None = None
    hubspot_company_id: str | None = None
    hubspot_deal_id: str | None = None
    hubspot_sync_status: str = "pending"
    hubspot_error: str | None = None


class QuoteSubmissionUpdate(BaseModel):
    hubspot_contact_id: str | None = None
    hubspot_company_id: str | None = None
    hubspot_deal_id: str | None = None
    hubspot_sync_status: str | None = None
    hubspot_error: str | None = None


class QuoteSubmissionResponse(BaseModel):
    id: uuid.UUID
    email: str
    lead_score: int
    recommended_package: str
    hubspot_sync_status: str


@quote_router.post("/submit", response_model=QuoteSubmissionResponse)
def submit_quote(body: QuoteSubmissionCreate, db: Session = Depends(get_db)) -> QuoteSubmissionResponse:
    row = QuoteSubmission(
        email=str(body.email).lower(),
        payload=body.payload,
        lead_score=body.lead_score,
        recommended_package=body.recommended_package,
        hubspot_contact_id=body.hubspot_contact_id,
        hubspot_company_id=body.hubspot_company_id,
        hubspot_deal_id=body.hubspot_deal_id,
        hubspot_sync_status=body.hubspot_sync_status,
        hubspot_error=body.hubspot_error,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return QuoteSubmissionResponse(
        id=row.id,
        email=row.email,
        lead_score=row.lead_score,
        recommended_package=row.recommended_package,
        hubspot_sync_status=row.hubspot_sync_status,
    )


@quote_router.patch("/submit/{submission_id}", response_model=QuoteSubmissionResponse)
def update_quote_submission(
    submission_id: uuid.UUID,
    body: QuoteSubmissionUpdate,
    db: Session = Depends(get_db),
) -> QuoteSubmissionResponse:
    row = db.get(QuoteSubmission, submission_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)

    db.commit()
    db.refresh(row)
    return QuoteSubmissionResponse(
        id=row.id,
        email=row.email,
        lead_score=row.lead_score,
        recommended_package=row.recommended_package,
        hubspot_sync_status=row.hubspot_sync_status,
    )
