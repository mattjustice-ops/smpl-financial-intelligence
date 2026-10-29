"""HTTP route for the AI commentary service."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.services.organizations import get_organization_or_404
from app.services.commentary.llm_factory import build_commentary_llm_client
from app.services.commentary.openai_client import (
    CommentaryLLMClient,
    LLMError,
)
from app.services.commentary.revenue_rollup import (
    RevenueRollupResult,
    RevenueSectionIn,
    analyze_revenue_rollup,
    attach_stored_events,
)
from app.services.commentary.schemas import CommentaryInputs, CommentaryOutput
from app.services.commentary.service import generate_commentary

commentary_router = APIRouter(prefix="/commentary", tags=["commentary"])


# A module-level slot so tests (and future routes) can inject a fake client.
_llm_client_override: CommentaryLLMClient | None = None


def set_llm_client_override(client: CommentaryLLMClient | None) -> None:
    """Used by tests / programmatic callers to swap in a fake LLM."""
    global _llm_client_override
    _llm_client_override = client


def get_llm_client(settings: Settings = Depends(get_settings)) -> CommentaryLLMClient:
    if _llm_client_override is not None:
        return _llm_client_override
    try:
        return build_commentary_llm_client()
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@commentary_router.post("/generate", response_model=CommentaryOutput)
def generate_commentary_endpoint(
    inputs: CommentaryInputs,
    client: CommentaryLLMClient = Depends(get_llm_client),
) -> CommentaryOutput:
    """Generate CFO-grade commentary from structured finance data."""
    try:
        return generate_commentary(inputs, client)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def customer_events_for(organization_id: str, period: str, kind: str, db: Session) -> dict[str, list]:
    """The same customer briefs the revenue section may name, without calling a model."""
    section = RevenueSectionIn.model_validate(
        {
            "comparison_kind": kind,
            "section_id": "revenue",
            "period": period,
            "organization_id": organization_id,
            "parent": {"label": "Revenue"},
        }
    )
    loaded = _customers_for_member(section, db)
    lost: list = []
    kind_name = (kind or "").strip().lower()
    if kind_name == "mom" and loaded.events is not None and (section.organization_id or ""):
        try:
            org = uuid.UUID(str(section.organization_id or ""))
            get_organization_or_404(db, org)
        except Exception:
            org = None
        if org is not None:
            from app.services.commentary.customer_events import brief_lost
            from app.services.reporting.source_trace import closed_lost_deals

            lost = brief_lost(closed_lost_deals(db, org, period), section.materiality or 10000)
    return {"events": [event.model_dump() for event in loaded.events], "lost": lost}


def _customers_for_member(section: RevenueSectionIn, db: Session) -> RevenueSectionIn:
    """Month and forecast customers load only for a member of that organization."""
    kind = (section.comparison_kind or "").strip().lower()
    if (section.section_id or "revenue") != "revenue" or kind not in {"mom", "forecast"}:
        return section.model_copy(update={"events": []})
    try:
        org = uuid.UUID(str(section.organization_id or ""))
        get_organization_or_404(db, org)
    except Exception:
        return section.model_copy(update={"events": []})
    return attach_stored_events(section, db)


@commentary_router.get("/customer-events")
def customer_events_endpoint(
    organization_id: str,
    period: str,
    kind: str = "mom",
    db: Session = Depends(get_db),
) -> dict[str, list]:
    """Large customers for one month or forecast. Budget and longer windows stay empty."""
    return customer_events_for(organization_id, period, kind, db)


@commentary_router.post("/revenue-rollup", response_model=RevenueRollupResult)
def revenue_rollup_endpoint(
    section: RevenueSectionIn,
    db: Session = Depends(get_db),
) -> RevenueRollupResult:
    """Write the section roll-up from the evidence, or say why it fell back."""
    section = _customers_for_member(section, db)
    client = _llm_client_override
    if client is None:
        try:
            client = build_commentary_llm_client(purpose="interactive")
        except LLMError:
            client = None
    return analyze_revenue_rollup(section, client)
