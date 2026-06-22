"""Board Platform live payload + Claude commentary routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps.request_context import get_request_user_id
from app.db.session import get_db
from app.services.board_platform_service import BoardPlatformPayload, build_board_platform_payload
from app.services.commentary.llm_factory import build_commentary_llm_client
from app.services.commentary.openai_client import LLMError
from app.services.organizations import get_organization_or_404
from app.services.reporting.as_of_period import bind_as_of_period, reset_as_of_period
from app.services.reporting.export.board_commentary_service import build_all_slide_commentary
from app.services.reporting.export.data_collector import collect_reporting_bundle
from app.services.reporting.org_reporting_settings import resolve_org_reporting_window
from app.services.reporting.validation_gate import raise_if_validation_blocked

board_platform_router = APIRouter(prefix="/board-platform", tags=["board-platform"])

# Web board tab ids → narrative slide keys (board/index.html + BoardPlatformApp).
BOARD_SLIDE_KEY_ALIASES: dict[str, str] = {
    "exec": "executive_summary",
    "executive": "executive_summary",
    "arr": "arr_waterfall",
    "revenue": "gaap_revenue",
    "gtm": "gtm_performance",
    "cash": "cash_forecast",
    "headcount": "headcount",
    "risks": "risks_opportunities",
    "risk": "risks_opportunities",
}


def normalize_board_slide_key(slide_key: str) -> str:
    key = slide_key.strip()
    return BOARD_SLIDE_KEY_ALIASES.get(key, key)


class BoardCommentaryRequest(BaseModel):
    slide_key: str = Field(min_length=1, max_length=64)


class BoardCommentaryResponse(BaseModel):
    slide_key: str
    commentary: dict[str, str]


class CopilotRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class CopilotResponse(BaseModel):
    answer: str


@board_platform_router.get("/payload", response_model=BoardPlatformPayload)
def board_platform_payload(
    organization_id: uuid.UUID,
    include_commentary: bool = Query(False),
    include_validation: bool = Query(False),
    include_three_statement: bool = Query(False),
    block_on_validation: bool = Query(False),
    db: Session = Depends(get_db),
) -> BoardPlatformPayload:
    try:
        return build_board_platform_payload(
            db,
            organization_id,
            include_commentary=include_commentary,
            include_validation=include_validation,
            include_three_statement=include_three_statement,
            block_on_validation=block_on_validation,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Board platform payload failed: {type(exc).__name__}: {exc}",
        ) from exc


@board_platform_router.post("/commentary/regenerate", response_model=BoardCommentaryResponse)
def regenerate_slide_commentary(
    organization_id: uuid.UUID,
    body: BoardCommentaryRequest,
    db: Session = Depends(get_db),
) -> BoardCommentaryResponse:
    get_organization_or_404(db, organization_id, module="ai_commentary")
    org = get_organization_or_404(db, organization_id, module="board_export")
    as_of, start_period, end_period = resolve_org_reporting_window(db, org)

    token = bind_as_of_period(as_of)
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

    raise_if_validation_blocked(bundle.validation, action="AI commentary")

    slide_key = normalize_board_slide_key(body.slide_key)
    slides = build_all_slide_commentary(bundle, use_ai=True)
    slide = slides.get(slide_key)
    if slide is None:
        raise HTTPException(status_code=404, detail=f"Unknown slide key: {body.slide_key}")

    return BoardCommentaryResponse(
        slide_key=slide_key,
        commentary={
            "what_happened": slide.what_happened,
            "why_it_happened": slide.why_it_happened,
            "impact": slide.impact,
            "favorable": slide.favorable,
            "unfavorable": slide.unfavorable,
            "leadership_watch": slide.leadership_watch,
            "recommended_actions": slide.recommended_actions,
        },
    )


@board_platform_router.post("/copilot", response_model=CopilotResponse)
def board_copilot(
    organization_id: uuid.UUID,
    body: CopilotRequest,
    db: Session = Depends(get_db),
) -> CopilotResponse:
    get_organization_or_404(db, organization_id, module="ai_commentary")
    org = get_organization_or_404(db, organization_id, module="board_export")
    as_of, start_period, end_period = resolve_org_reporting_window(db, org)

    token = bind_as_of_period(as_of)
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

    raise_if_validation_blocked(bundle.validation, action="SMPL Copilot")

    exec_json = bundle.executive_flow.model_dump(mode="json")
    metrics_blob = str(exec_json.get("kpis") or exec_json)[:12000]

    try:
        client = build_commentary_llm_client()
        raw = client.generate(
            system_prompt=(
                "You are SMPL Copilot — the AI financial intelligence layer for a B2B SaaS company. "
                "Answer using ONLY the live metrics provided. Never invent numbers. "
                "Structure every answer in exactly three labeled sections:\n"
                "1. PRIMARY DRIVER + VARIANCE CONTEXT — the key metric/movement with exact variance vs budget or prior period.\n"
                "2. FINANCIAL AND OPERATIONAL ROOT CAUSE — connect operational drivers (ARR, pipeline, headcount, GTM) to the outcome.\n"
                "3. RECOMMENDED ACTION + BOARD SUMMARY — one specific action plus a one-sentence board-ready summary.\n"
                "Keep each section to 2-3 sentences. Use dollar signs and percentages consistently."
            ),
            user_prompt=(
                f"Organization: {org.name}. Close month: {as_of}. FY window: {start_period}–{end_period}.\n"
                f"Live metrics:\n{metrics_blob}\n\nQuestion: {body.question}\n\n"
                'Respond JSON: {"answer": "..."} where answer contains the three numbered sections as plain text.'
            ),
        )
        answer = str(raw.get("answer") or raw.get("response") or "").strip()
        if not answer:
            answer = str(raw)[:2000]
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return CopilotResponse(answer=answer)
