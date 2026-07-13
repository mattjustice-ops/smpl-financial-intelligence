"""Board Platform live payload + Claude commentary routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps.request_context import get_request_user_id
from app.db.session import get_db
from app.services.board_platform_service import BoardPlatformPayload, build_board_platform_payload
from app.services.commentary.llm_factory import build_commentary_llm_client, LLMError
from app.services.organizations import get_organization_or_404
from app.services.ops.usage_context import reset_usage_context, set_usage_context
from app.services.ops.usage_limits import assert_within_usage_limits
from app.services.reporting.as_of_period import bind_as_of_period, reset_as_of_period
from app.services.reporting.export.board_commentary_service import (
    build_slide_commentary,
    copilot_context_blob,
    enrich_slide_with_ai,
    parse_focus_period_from_question,
)
from app.services.reporting.export.data_collector import collect_board_platform_bundle, collect_copilot_bundle
from app.services.reporting.org_reporting_settings import resolve_org_reporting_window
from app.services.reporting.three_statement_payload import build_cash_bridge_data, build_ts_data
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
    prefer_live: bool = False


class CopilotResponse(BaseModel):
    answer: str
    as_of_period: str
    context_as_of: str
    context_source: str  # freeze | live
    stale: bool = False
    focus_period: str | None = None


class FreezeBlobResponse(BaseModel):
    organization_id: str
    as_of_period: str
    status: str
    context_as_of: str
    stale: bool
    validation_status: str | None = None
    char_count: int | None = None


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
    org = get_organization_or_404(db, organization_id, module="board_export")
    assert_within_usage_limits(db, org, require_ai=True)
    usage_tokens = set_usage_context(organization_id=organization_id, feature="board_commentary_regenerate")
    as_of, start_period, end_period = resolve_org_reporting_window(db, org)

    token = bind_as_of_period(as_of)
    try:
        bundle = collect_board_platform_bundle(
            db,
            organization_id,
            scenario="Combined",
            start_period=start_period,
            end_period=end_period,
            as_of_period=as_of,
            include_validation=False,
        )
    finally:
        reset_as_of_period(token)
        reset_usage_context(usage_tokens)

    # Board regenerate is best-effort; do not block on pipeline_waterfall_ties fails.
    # Export routes still honor block_on_failure for PPTX/XLSX.

    slide_key = normalize_board_slide_key(body.slide_key)
    allowed = frozenset(BOARD_SLIDE_KEY_ALIASES.values())
    if slide_key not in allowed:
        raise HTTPException(status_code=404, detail=f"Unknown slide key: {body.slide_key}")
    base = build_slide_commentary(bundle, slide_key)
    slide = enrich_slide_with_ai(bundle, slide_key, base)
    if slide.what_happened and not slide.recommended_actions and not slide.leadership_watch:
        narrative = slide.what_happened
    else:
        narrative = slide.narrative_block() or base.narrative_block() or base.what_happened

    return BoardCommentaryResponse(
        slide_key=slide_key,
        commentary={
            "narrative": narrative,
            "what_happened": slide.what_happened or narrative,
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
    from datetime import datetime, timezone

    from app.services.close_context.freeze_blob_service import get_servable_freeze

    org = get_organization_or_404(db, organization_id, module="board_export")
    assert_within_usage_limits(db, org, require_ai=True)
    usage_tokens = set_usage_context(organization_id=organization_id, feature="board_copilot")
    as_of, start_period, end_period = resolve_org_reporting_window(db, org)

    focus_period = parse_focus_period_from_question(
        body.question,
        default=as_of,
        start_period=start_period,
        end_period=end_period,
    )

    context_source = "live"
    stale = False
    context_built_at = datetime.now(timezone.utc)
    metrics_blob = ""

    freeze = None if body.prefer_live else get_servable_freeze(db, organization_id, as_of)
    if freeze is not None:
        context_source = "freeze"
        stale = freeze.stale
        context_built_at = freeze.built_at
        metrics_blob = freeze.context_text
        if focus_period != as_of:
            metrics_blob = (
                f"Copilot focus month: {focus_period} (frozen close pack is {as_of}). "
                "Prefer focus-month detail if present in the pack; otherwise say coverage is limited.\n\n"
                + metrics_blob
            )
    else:
        token = bind_as_of_period(as_of)
        try:
            bundle = collect_copilot_bundle(
                db,
                organization_id,
                scenario="Combined",
                start_period=start_period,
                end_period=end_period,
                as_of_period=as_of,
                focus_period=focus_period,
            )
        except Exception as exc:
            reset_usage_context(usage_tokens)
            raise HTTPException(
                status_code=503,
                detail=f"Could not load warehouse metrics for Copilot: {type(exc).__name__}: {exc}",
            ) from exc
        finally:
            reset_as_of_period(token)

        cash_bridge_table = build_cash_bridge_data(
            db,
            organization_id,
            start_period=start_period,
            end_period=end_period,
        )
        ts_data = build_ts_data(
            db,
            organization_id,
            as_of=as_of,
            start_period=start_period,
            end_period=end_period,
        )
        metrics_blob = copilot_context_blob(
            bundle,
            cash_bridge_table=cash_bridge_table,
            ts_data=ts_data,
            focus_period=focus_period,
            max_chars=24000,
        )
        try:
            exec_json = bundle.executive_flow.model_dump(mode="json")
            kpis = exec_json.get("kpis")
            if kpis:
                metrics_blob += "\n\nExecutive KPIs JSON:\n" + str(kpis)[:3000]
        except Exception:
            pass
        context_built_at = datetime.now(timezone.utc)

    if context_built_at.tzinfo is None:
        context_built_at = context_built_at.replace(tzinfo=timezone.utc)
    context_as_of = context_built_at.astimezone(timezone.utc).isoformat()
    freshness_label = "stale freeze" if stale else ("freeze pack" if context_source == "freeze" else "live warehouse")

    try:
        client = build_commentary_llm_client()
        raw = client.generate(
            system_prompt=(
                "You are SMPL Copilot for a B2B SaaS board platform. "
                "Answer using ONLY the metrics provided. Never invent numbers. "
                "When the question names a month, use that month's sections — especially "
                "'Monthly operational cash bridges' and 'Monthly Actual trends'. "
                "Structure every answer in exactly three labeled sections:\n"
                "1. PRIMARY DRIVER + VARIANCE CONTEXT\n"
                "2. FINANCIAL AND OPERATIONAL ROOT CAUSE\n"
                "3. RECOMMENDED ACTION + BOARD SUMMARY\n"
                "Keep each section to 2-3 sentences. Use $ and % consistently. "
                f"Data freshness for this answer: {freshness_label}, context as of {context_as_of}, "
                f"close period {as_of}."
            ),
            user_prompt=(
                f"Organization: {org.name}. Org close month: {as_of}. FY window: {start_period}–{end_period}.\n"
                f"Question focus month: {focus_period}.\n"
                f"Context source: {context_source}"
                f"{' (STALE — last complete freeze)' if stale else ''}. "
                f"Context as of: {context_as_of}.\n"
                f"Metrics:\n{metrics_blob}\n\nQuestion: {body.question}\n\n"
                'Respond JSON: {"answer": "..."} where answer contains the three numbered sections as plain text.'
            ),
            max_tokens=1200,
        )
        answer = str(raw.get("answer") or raw.get("response") or "").strip()
        if not answer and isinstance(raw, dict):
            answer = " ".join(str(v) for v in raw.values() if isinstance(v, str)).strip()
        if not answer:
            raise LLMError("Copilot returned an empty response.")
    except LLMError as exc:
        reset_usage_context(usage_tokens)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        reset_usage_context(usage_tokens)
        raise HTTPException(
            status_code=503,
            detail=f"SMPL Copilot failed: {type(exc).__name__}: {exc}",
        ) from exc

    reset_usage_context(usage_tokens)
    return CopilotResponse(
        answer=answer,
        as_of_period=as_of,
        context_as_of=context_as_of,
        context_source=context_source,
        stale=stale,
        focus_period=focus_period,
    )


@board_platform_router.post("/freeze-context", response_model=FreezeBlobResponse)
def freeze_close_context(
    organization_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> FreezeBlobResponse:
    """Build/store a COMPLETE close-context freeze pack for the org close period."""
    from app.services.close_context.freeze_blob_service import build_and_store_freeze_blob

    org = get_organization_or_404(db, organization_id, module="board_export")
    as_of, start_period, end_period = resolve_org_reporting_window(db, org)
    token = bind_as_of_period(as_of)
    try:
        freeze = build_and_store_freeze_blob(
            db,
            organization_id,
            as_of_period=as_of,
            start_period=start_period,
            end_period=end_period,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Freeze context failed: {type(exc).__name__}: {exc}",
        ) from exc
    finally:
        reset_as_of_period(token)

    return FreezeBlobResponse(
        organization_id=str(organization_id),
        as_of_period=freeze.as_of_period,
        status=freeze.status,
        context_as_of=freeze.context_as_of_iso,
        stale=freeze.stale,
        validation_status=freeze.validation_status,
        char_count=len(freeze.context_text) if freeze.context_text else 0,
    )


@board_platform_router.get("/freeze-context", response_model=FreezeBlobResponse)
def get_freeze_close_context(
    organization_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> FreezeBlobResponse:
    """Inspect the servable freeze pack (COMPLETE or labeled STALE)."""
    from app.services.close_context.freeze_blob_service import get_servable_freeze

    org = get_organization_or_404(db, organization_id, module="board_export")
    as_of, _, _ = resolve_org_reporting_window(db, org)
    freeze = get_servable_freeze(db, organization_id, as_of)
    if freeze is None:
        raise HTTPException(status_code=404, detail="No COMPLETE/STALE freeze pack for this close period")
    return FreezeBlobResponse(
        organization_id=str(organization_id),
        as_of_period=freeze.as_of_period,
        status=freeze.status,
        context_as_of=freeze.context_as_of_iso,
        stale=freeze.stale,
        validation_status=freeze.validation_status,
        char_count=len(freeze.context_text) if freeze.context_text else 0,
    )
