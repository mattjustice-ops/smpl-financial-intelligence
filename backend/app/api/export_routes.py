"""Reporting export endpoints (Excel close package, board PPTX, validation pre-check)."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.dashboard_routes import dashboard_params
from app.db.session import get_db
from app.services.organizations import get_organization_or_404
from app.services.ops.usage_limits import assert_prompt5_regen_cap, assert_within_usage_limits
from app.core.config import get_settings
from app.services.reporting.export.board_commentary_service import (
    SlideCommentary,
    build_all_slide_commentary,
)
from app.services.reporting.export.schemas import ExportValidationSummary, ReportingBundle
from app.services.reporting.export.service import (
    build_excel_close_package,
    build_excel_management_review,
    build_excel_variance_commentary,
    build_pptx_board_presentation,
    build_pptx_mda_deck,
    collect_bundle,
    run_export_validation,
)
from app.services.reporting.period_utils import to_period

export_router = APIRouter(prefix="/export", tags=["export"])
logger = logging.getLogger(__name__)


def _export_params(
    scenario: str,
    start_period: str,
    end_period: str,
    period: str | None,
    quarter: str | None,
    fiscal_year: str | None,
    as_of_period: str | None,
    waterfall_type: str | None,
    marketing_channel: str | None,
    region: str | None,
    segment: str | None,
    owner: str | None,
) -> dict:
    params = dashboard_params(
        scenario,
        start_period,
        end_period,
        period,
        quarter,
        fiscal_year,
        waterfall_type,
        marketing_channel,
        region,
        segment,
        owner,
    )
    params["as_of_period"] = to_period(as_of_period or params["end_period"])
    return params


def _org_for_board_export(
    db: Session,
    organization_id: uuid.UUID,
    *,
    include_ai_commentary: bool,
) -> "Organization":
    from app.models.organization import Organization

    org = get_organization_or_404(db, organization_id, module="board_export")
    assert_within_usage_limits(
        db,
        org,
        require_export=True,
        require_ai=include_ai_commentary,
    )
    return org


def _require_servable_freeze_for_mda(db: Session, organization_id: uuid.UUID, as_of_period: str):
    """§4B: allow COMPLETE or STALE; hard-block only when no pack exists."""
    from app.services.close_context.freeze_blob_service import get_servable_freeze

    freeze = get_servable_freeze(db, organization_id, as_of_period)
    if freeze is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "freeze_pack_required",
                "as_of_period": as_of_period,
                "message": (
                    f"No COMPLETE/STALE close-context pack for {as_of_period}. "
                    "Run validation (or ops prewarm-freeze) so the first freeze reaches COMPLETE, "
                    "then regenerate the MD&A deck."
                ),
            },
        )
    return freeze


def _load_board_export_enrichment(
    db: Session,
    organization_id: uuid.UUID,
    bundle: ReportingBundle,
) -> tuple[dict | None, dict | None]:
    """Three-statement + cash bridge tables used by Prompt 2 MD&A package and Prompt 5 deck."""
    ts_data: dict | None = None
    cash_bridge_data: dict | None = None
    try:
        from app.services.reporting.three_statement_payload import build_cash_bridge_data, build_ts_data

        ts_data = build_ts_data(
            db,
            organization_id,
            as_of=bundle.as_of_period,
            start_period=bundle.start_period,
            end_period=bundle.end_period,
        )
        cash_bridge_data = build_cash_bridge_data(
            db,
            organization_id,
            start_period=bundle.start_period,
            end_period=bundle.end_period,
        )
    except Exception:
        logger.warning(
            "Board export enrichment unavailable for org=%s period=%s — using bundle fallbacks",
            organization_id,
            bundle.as_of_period,
            exc_info=True,
        )
    return ts_data, cash_bridge_data


def _check_validation(bundle: ReportingBundle, block_on_failure: bool) -> None:
    if not block_on_failure:
        return
    from app.services.reporting.validation_gate import validation_blocked

    if validation_blocked(bundle.validation, strict=True):
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Export blocked: validation checks failed or have warnings.",
                "validation": bundle.validation.model_dump(mode="json"),
            },
        )


def _commentary_to_dict(sc: SlideCommentary) -> dict[str, str]:
    return {
        "what_happened": sc.what_happened,
        "why_it_happened": sc.why_it_happened,
        "impact": sc.impact,
        "favorable": sc.favorable,
        "unfavorable": sc.unfavorable,
        "recommended_actions": sc.recommended_actions,
        "leadership_watch": sc.leadership_watch,
    }


def _narrative_from_commentary(sc: SlideCommentary) -> str:
    parts: list[str] = []
    if sc.what_happened:
        parts.append(sc.what_happened)
    if sc.why_it_happened:
        parts.append(sc.why_it_happened)
    if sc.impact:
        parts.append(f"So what: {sc.impact}")
    if sc.favorable:
        parts.append(f"Win: {sc.favorable}")
    if sc.unfavorable:
        parts.append(f"Risk: {sc.unfavorable}")
    if sc.recommended_actions:
        parts.append(f"Action: {sc.recommended_actions}")
    return " ".join(parts).strip()


@export_router.get("/ping")
def export_ping_router(response: Response) -> dict[str, str | bool]:
    """Fallback ping on export router (main.py registers the canonical /api/v1/export/ping first)."""
    from app.core.openai_status import openai_ping_payload

    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["X-SFI-Api-Build"] = "openai-ping-v3"
    payload = openai_ping_payload()
    payload["settings_loader"] = "v3-export-router-fallback"
    return payload


@export_router.get("/executive-commentary")
def export_executive_commentary(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    period: str | None = Query(None),
    quarter: str | None = Query(None),
    fiscal_year: str | None = Query(None),
    as_of_period: str | None = Query(None),
    waterfall_type: str | None = Query(None),
    marketing_channel: str | None = Query(None),
    region: str | None = Query(None),
    segment: str | None = Query(None),
    owner: str | None = Query(None),
    use_ai: bool = Query(True, description="Enrich commentary via Claude/OpenAI when API key is set"),
    db: Session = Depends(get_db),
) -> dict:
    """Executive + MD&A narrative for dashboard preview (same engine as board/Excel exports)."""
    get_organization_or_404(db, organization_id)
    settings = get_settings()
    ai_configured = bool(settings.anthropic_api_key or settings.openai_api_key)
    params = _export_params(
        scenario,
        start_period,
        end_period,
        period,
        quarter,
        fiscal_year,
        as_of_period,
        waterfall_type,
        marketing_channel,
        region,
        segment,
        owner,
    )
    try:
        bundle = collect_bundle(db, organization_id, include_ai_commentary=False, **params)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Commentary bundle failed: {exc}") from exc

    slides = build_all_slide_commentary(bundle, use_ai=use_ai and ai_configured)
    exec_sc = slides.get("executive_summary") or SlideCommentary()
    mda_sc = slides.get("mda_summary") or SlideCommentary()
    return {
        "as_of_period": bundle.as_of_period,
        "ai_configured": ai_configured,
        "used_ai": bool(use_ai and ai_configured),
        "llm_provider": "anthropic" if settings.anthropic_api_key else ("openai" if settings.openai_api_key else ""),
        "llm_model": (
            settings.anthropic_model
            if settings.anthropic_api_key
            else (settings.openai_model if settings.openai_api_key else "")
        ),
        "openai_model": settings.openai_model,
        "executive_summary": _commentary_to_dict(exec_sc),
        "mda_summary": _commentary_to_dict(mda_sc),
        "narrative": _narrative_from_commentary(exec_sc),
        "mda_narrative": _narrative_from_commentary(mda_sc),
    }


@export_router.get("/validation", response_model=ExportValidationSummary)
def export_validation_precheck(
    response: Response,
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    period: str | None = Query(None),
    quarter: str | None = Query(None),
    fiscal_year: str | None = Query(None),
    as_of_period: str | None = Query(None),
    waterfall_type: str | None = Query(None),
    marketing_channel: str | None = Query(None),
    region: str | None = Query(None),
    segment: str | None = Query(None),
    owner: str | None = Query(None),
    db: Session = Depends(get_db),
) -> ExportValidationSummary:
    from app.services.close_context.freeze_blob_service import schedule_auto_freeze_after_validation

    get_organization_or_404(db, organization_id)
    params = _export_params(
        scenario,
        start_period,
        end_period,
        period,
        quarter,
        fiscal_year,
        as_of_period,
        waterfall_type,
        marketing_channel,
        region,
        segment,
        owner,
    )
    try:
        summary = run_export_validation(db, organization_id, **params)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export validation failed: {exc}") from exc

    from app.services.reporting.export.validation_labels import apply_customer_validation_labels

    summary = apply_customer_validation_labels(summary, as_of_period=str(params["as_of_period"]))

    try:
        from app.models.close_context_blob import CloseContextBlob
        from app.services.reporting.export.validation_labels import apply_freeze_to_trust
        from sqlalchemy import select

        period = str(params["as_of_period"])
        blob = db.scalars(
            select(CloseContextBlob).where(
                CloseContextBlob.organization_id == organization_id,
                CloseContextBlob.as_of_period == period,
            )
        ).first()
        freeze_status = blob.status if blob else "missing"
        freeze_built_at = blob.built_at.isoformat() if blob and blob.built_at else None
        summary = apply_freeze_to_trust(
            summary,
            freeze_status=freeze_status,
            freeze_built_at=freeze_built_at,
        )
    except Exception:
        logger.debug("Freeze status enrichment for validation skipped", exc_info=True)

    try:
        from app.services.close_context.close_session_service import mark_validation_complete

        mark_validation_complete(
            db,
            organization_id,
            str(params["as_of_period"]),
            validation_status=summary.status,
        )
        db.commit()
    except Exception:
        db.rollback()

    queued = schedule_auto_freeze_after_validation(
        db,
        organization_id,
        validation_status=summary.status,
        as_of_period=params["as_of_period"],
        start_period=params["start_period"],
        end_period=params["end_period"],
    )
    response.headers["X-Freeze-Queued"] = "true" if queued else "false"
    response.headers["X-As-Of-Period"] = str(params["as_of_period"])
    return summary


@export_router.get("/preview", response_model=ReportingBundle)
def export_preview(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    period: str | None = Query(None),
    quarter: str | None = Query(None),
    fiscal_year: str | None = Query(None),
    as_of_period: str | None = Query(None),
    include_ai_commentary: bool = Query(False),
    waterfall_type: str | None = Query(None),
    marketing_channel: str | None = Query(None),
    region: str | None = Query(None),
    segment: str | None = Query(None),
    owner: str | None = Query(None),
    db: Session = Depends(get_db),
) -> ReportingBundle:
    get_organization_or_404(db, organization_id)
    params = _export_params(
        scenario,
        start_period,
        end_period,
        period,
        quarter,
        fiscal_year,
        as_of_period,
        waterfall_type,
        marketing_channel,
        region,
        segment,
        owner,
    )
    return collect_bundle(
        db,
        organization_id,
        include_ai_commentary=include_ai_commentary,
        **params,
    )


@export_router.get("/month-end-close.xlsx")
def export_month_end_close(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    period: str | None = Query(None),
    quarter: str | None = Query(None),
    fiscal_year: str | None = Query(None),
    as_of_period: str | None = Query(None),
    block_on_failure: bool = Query(False),
    include_ai_commentary: bool = Query(False),
    waterfall_type: str | None = Query(None),
    marketing_channel: str | None = Query(None),
    region: str | None = Query(None),
    segment: str | None = Query(None),
    owner: str | None = Query(None),
    db: Session = Depends(get_db),
) -> Response:
    get_organization_or_404(db, organization_id)
    params = _export_params(
        scenario,
        start_period,
        end_period,
        period,
        quarter,
        fiscal_year,
        as_of_period,
        waterfall_type,
        marketing_channel,
        region,
        segment,
        owner,
    )
    try:
        bundle = collect_bundle(db, organization_id, include_ai_commentary=include_ai_commentary, **params)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export bundle failed: {exc}") from exc
    _check_validation(bundle, block_on_failure)
    try:
        content = build_excel_close_package(bundle)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel export failed: {exc}") from exc
    filename = f"month_end_close_{bundle.as_of_period}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Validation": bundle.validation.status,
        },
    )


@export_router.get("/mda-package.xlsx")
def export_mda_package(
    organization_id: uuid.UUID = Query(...),
    reporting_period: str | None = Query(None, description="Alias for as_of_period (close month YYYY-MM)"),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    period: str | None = Query(None),
    quarter: str | None = Query(None),
    fiscal_year: str | None = Query(None),
    as_of_period: str | None = Query(None),
    block_on_failure: bool = Query(False),
    include_ai_commentary: bool = Query(
        True,
        description="Generate Claude Prompt 2 variance commentary when API key is set",
    ),
    waterfall_type: str | None = Query(None),
    marketing_channel: str | None = Query(None),
    region: str | None = Query(None),
    segment: str | None = Query(None),
    owner: str | None = Query(None),
    db: Session = Depends(get_db),
) -> Response:
    """SMPL MD&A Excel package — Prompt 2 template refresh + Claude commentary."""
    from app.services.reporting.export.board_export_service import build_mda_package_xlsx_bytes

    _org_for_board_export(db, organization_id, include_ai_commentary=include_ai_commentary)
    as_of = reporting_period or as_of_period
    params = _export_params(
        scenario,
        start_period,
        end_period,
        period,
        quarter,
        fiscal_year,
        as_of,
        waterfall_type,
        marketing_channel,
        region,
        segment,
        owner,
    )
    try:
        bundle = collect_bundle(
            db,
            organization_id,
            include_ai_commentary=False,
            **params,
        )
    except Exception as exc:
        logger.exception("MD&A package bundle collection failed")
        raise HTTPException(
            status_code=500,
            detail=f"Export bundle failed: {type(exc).__name__}: {exc}",
        ) from exc
    _check_validation(bundle, block_on_failure)
    ts_data, cash_bridge_data = _load_board_export_enrichment(db, organization_id, bundle)
    try:
        content, package_source = build_mda_package_xlsx_bytes(
            bundle,
            include_commentary=include_ai_commentary,
            use_ai_commentary=include_ai_commentary,
            ts_data=ts_data,
            cash_bridge_data=cash_bridge_data,
        )
    except Exception as exc:
        logger.exception("MD&A package export failed")
        raise HTTPException(
            status_code=500,
            detail=f"MD&A package export failed: {type(exc).__name__}: {exc}",
        ) from exc
    if not content:
        raise HTTPException(status_code=500, detail="MD&A package export returned empty content.")
    period_label = bundle.as_of_period.replace("-", "_")
    filename = f"SMPL_MDA_Package_{period_label}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Validation": bundle.validation.status if bundle.validation else "unknown",
            "X-MDA-Package-Source": package_source,
            "X-MDA-Package-Engine": "claude_prompt2",
            "X-MDA-AI-Commentary": "true" if include_ai_commentary else "false",
        },
    )


def _run_mda_package_job(
    job_id: str,
    *,
    organization_id: uuid.UUID,
    bundle_params: dict,
    include_ai_commentary: bool,
    block_on_failure: bool,
) -> None:
    from app.db.session import SessionLocal
    from app.services.ops.usage_context import reset_usage_context, set_usage_context
    from app.services.reporting.export.board_export_service import build_mda_package_xlsx_bytes
    from app.services.reporting.export.export_jobs import complete_export_job, update_export_job_message

    tokens = set_usage_context(organization_id=organization_id, feature="mda_package")
    # Load warehouse data, then close the DB session BEFORE Claude/xlsx work so Neon
    # does not kill us with IdleInTransactionSessionTimeout during long generation.
    db = SessionLocal()
    try:
        get_organization_or_404(db, organization_id)

        update_export_job_message(job_id, "Collecting warehouse bundle…")
        bundle = collect_bundle(
            db,
            organization_id,
            include_ai_commentary=False,
            **bundle_params,
        )
        if block_on_failure:
            _check_validation(bundle, True)
        update_export_job_message(job_id, "Loading three-statement and cash bridge…")
        ts_data, cash_bridge_data = _load_board_export_enrichment(db, organization_id, bundle)
    finally:
        db.close()

    try:
        update_export_job_message(job_id, "Generating SMPL MD&A package (Prompt 2)…")
        content, package_source = build_mda_package_xlsx_bytes(
            bundle,
            include_commentary=include_ai_commentary,
            use_ai_commentary=include_ai_commentary,
            ts_data=ts_data,
            cash_bridge_data=cash_bridge_data,
        )
        period_label = bundle.as_of_period.replace("-", "_")
        complete_export_job(
            job_id,
            content,
            message="MD&A package ready",
            headers_extra={
                "X-Export-Validation": bundle.validation.status if bundle.validation else "unknown",
                "X-MDA-Package-Source": package_source,
                "X-MDA-Package-Engine": "claude_prompt2",
                "X-MDA-AI-Commentary": "true" if include_ai_commentary else "false",
                "X-As-Of-Period": bundle.as_of_period,
                "X-Context-Source": "live",
            },
        )
    finally:
        reset_usage_context(tokens)


def _run_mda_deck_job(
    job_id: str,
    *,
    organization_id: uuid.UUID,
    bundle_params: dict,
    include_ai_commentary: bool,
    include_commentary: bool,
    include_appendix: bool,
    include_validation: bool,
    block_on_failure: bool,
    scenario_mode: str | None,
    package_mode: str,
) -> None:
    from app.db.session import SessionLocal
    from app.services.ops.usage_context import reset_usage_context, set_usage_context
    from app.services.reporting.export.export_jobs import complete_export_job, update_export_job_message

    tokens = set_usage_context(organization_id=organization_id, feature="mda_deck")
    # Close DB before Prompt 5 / PPTX generation — long Claude calls must not sit in an
    # open Neon transaction (IdleInTransactionSessionTimeout).
    db = SessionLocal()
    try:
        get_organization_or_404(db, organization_id)

        update_export_job_message(job_id, "Collecting warehouse bundle…")
        bundle = collect_bundle(
            db,
            organization_id,
            include_ai_commentary=False,
            **bundle_params,
        )
        if include_validation and block_on_failure:
            _check_validation(bundle, True)
        if bundle.validation is not None:
            from app.services.reporting.export.export_jobs import update_export_job_metadata

            total = (
                (bundle.validation.passed_count or 0)
                + (bundle.validation.warning_count or 0)
                + (bundle.validation.failed_count or 0)
            )
            update_export_job_metadata(
                job_id,
                validation_passed=bundle.validation.passed_count or 0,
                validation_total=total,
                validation_status=bundle.validation.status,
            )
            update_export_job_message(
                job_id,
                f"Validation complete ({bundle.validation.passed_count or 0}/{total} checks)…",
            )
        update_export_job_message(job_id, "Loading three-statement and cash bridge…")
        ts_data, cash_bridge_data = _load_board_export_enrichment(db, organization_id, bundle)
    finally:
        db.close()

    try:
        freeze_status = "unknown"
        freeze_as_of = ""
        freeze_stale = False
        freeze_context_text: str | None = None
        from app.db.session import SessionLocal as _SessionLocal
        from app.services.close_context.freeze_blob_service import get_servable_freeze

        _fdb = _SessionLocal()
        try:
            freeze = get_servable_freeze(_fdb, organization_id, bundle.as_of_period)
            if freeze is None:
                raise RuntimeError(
                    f"Freeze pack disappeared for {bundle.as_of_period} before deck generation"
                )
            freeze_status = freeze.status
            freeze_as_of = freeze.context_as_of_iso
            freeze_stale = freeze.stale
            freeze_context_text = freeze.context_text
        finally:
            _fdb.close()

        update_export_job_message(job_id, "Generating MD&A deck (Prompt 5)…")
        content, pptx_source = build_pptx_mda_deck(
            bundle,
            include_commentary=include_commentary,
            include_validation_appendix=include_appendix,
            use_ai_commentary=include_ai_commentary,
            scenario_mode=scenario_mode,
            package_mode=package_mode,
            ts_data=ts_data,
            cash_bridge_data=cash_bridge_data,
            freeze_context_text=freeze_context_text,
            freeze_context_as_of=freeze_as_of,
            freeze_status=freeze_status,
            freeze_stale=freeze_stale,
        )
        complete_export_job(
            job_id,
            content,
            message="MD&A deck ready",
            headers_extra={
                "X-Export-Validation": bundle.validation.status if bundle.validation else "unknown",
                "X-Board-Package-Engine": "smpl-board-v2",
                "X-Board-PPTX-Source": pptx_source,
                "X-Board-AI-Commentary": "true" if include_ai_commentary else "false",
                "X-Board-Deck-Kind": "mda",
                "X-As-Of-Period": bundle.as_of_period,
                "X-Context-Source": "freeze",
                "X-Freeze-Status": freeze_status,
                "X-Context-As-Of": freeze_as_of,
                "X-Freeze-Stale": "true" if freeze_stale else "false",
            },
        )
    finally:
        reset_usage_context(tokens)


@export_router.post("/jobs/mda-package")
def start_mda_package_job(
    organization_id: uuid.UUID = Query(...),
    reporting_period: str | None = Query(None),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    period: str | None = Query(None),
    quarter: str | None = Query(None),
    fiscal_year: str | None = Query(None),
    as_of_period: str | None = Query(None),
    block_on_failure: bool = Query(False),
    include_ai_commentary: bool = Query(True),
    waterfall_type: str | None = Query(None),
    marketing_channel: str | None = Query(None),
    region: str | None = Query(None),
    segment: str | None = Query(None),
    owner: str | None = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    """Start background MD&A package job (avoids Railway 5-minute idle timeout)."""
    from app.services.reporting.export.export_jobs import (
        ExportJobConflictError,
        job_status_payload,
        submit_export_job,
    )

    _org_for_board_export(db, organization_id, include_ai_commentary=include_ai_commentary)
    as_of = reporting_period or as_of_period
    bundle_params = _export_params(
        scenario,
        start_period,
        end_period,
        period,
        quarter,
        fiscal_year,
        as_of,
        waterfall_type,
        marketing_channel,
        region,
        segment,
        owner,
    )
    period_label = (as_of or bundle_params["as_of_period"]).replace("-", "_")
    try:
        job = submit_export_job(
            "mda_package",
            lambda job_id: _run_mda_package_job(
                job_id,
                organization_id=organization_id,
                bundle_params=bundle_params,
                include_ai_commentary=include_ai_commentary,
                block_on_failure=block_on_failure,
            ),
            filename=f"SMPL_MDA_Package_{period_label}.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            organization_id=organization_id,
            as_of_period=bundle_params.get("as_of_period") or as_of,
        )
    except ExportJobConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(exc),
                "active_job_id": exc.active_job_id,
                "code": "export_job_conflict",
            },
        ) from exc
    return job_status_payload(job)


@export_router.post("/jobs/mda-deck")
def start_mda_deck_job(
    organization_id: uuid.UUID = Query(...),
    reporting_period: str | None = Query(None),
    scenario: str = Query("Combined"),
    scenario_mode: str | None = Query(None),
    start_period: str = Query(...),
    end_period: str = Query(...),
    period: str | None = Query(None),
    quarter: str | None = Query(None),
    fiscal_year: str | None = Query(None),
    as_of_period: str | None = Query(None),
    block_on_failure: bool = Query(False),
    include_ai_commentary: bool = Query(True),
    include_commentary: bool = Query(True),
    include_appendix: bool = Query(True),
    include_validation: bool = Query(True),
    package_mode: str = Query("full_board"),
    waterfall_type: str | None = Query(None),
    marketing_channel: str | None = Query(None),
    region: str | None = Query(None),
    segment: str | None = Query(None),
    owner: str | None = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    """Start background MD&A deck job (avoids Railway 5-minute idle timeout)."""
    from app.services.reporting.export.export_jobs import (
        ExportJobConflictError,
        job_status_payload,
        submit_export_job,
    )

    org = _org_for_board_export(db, organization_id, include_ai_commentary=include_ai_commentary)
    as_of = reporting_period or as_of_period
    bundle_params = _export_params(
        scenario,
        start_period,
        end_period,
        period,
        quarter,
        fiscal_year,
        as_of,
        waterfall_type,
        marketing_channel,
        region,
        segment,
        owner,
    )
    deck_period = as_of or bundle_params["as_of_period"]
    assert_prompt5_regen_cap(db, org, deck_period)
    freeze = _require_servable_freeze_for_mda(db, organization_id, deck_period)
    try:
        job = submit_export_job(
            "mda_deck",
            lambda job_id: _run_mda_deck_job(
                job_id,
                organization_id=organization_id,
                bundle_params=bundle_params,
                include_ai_commentary=include_ai_commentary,
                include_commentary=include_commentary,
                include_appendix=include_appendix,
                include_validation=include_validation,
                block_on_failure=block_on_failure,
                scenario_mode=scenario_mode,
                package_mode=package_mode,
            ),
            filename=f"mda_deck_{deck_period}.pptx",
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            organization_id=organization_id,
            as_of_period=bundle_params.get("as_of_period") or as_of,
            metadata={
                "freeze_status": freeze.status,
                "freeze_built_at": freeze.context_as_of_iso,
                "freeze_stale": freeze.stale,
            },
        )
    except ExportJobConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(exc),
                "active_job_id": exc.active_job_id,
                "code": "export_job_conflict",
            },
        ) from exc
    return job_status_payload(job)


@export_router.get("/jobs/{job_id}")
def export_job_status(job_id: uuid.UUID) -> dict:
    from app.services.reporting.export.export_jobs import get_export_job, job_status_payload

    job = get_export_job(str(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Export job not found")
    return job_status_payload(job)


@export_router.get("/jobs/{job_id}/download")
def export_job_download(job_id: uuid.UUID) -> Response:
    from app.services.reporting.export.export_jobs import get_export_job

    job = get_export_job(str(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Export job not found")
    if job.status == "failed":
        raise HTTPException(status_code=500, detail=job.error or "Export job failed")
    if job.status != "complete" or not job.content:
        raise HTTPException(status_code=409, detail=f"Export not ready (status={job.status})")
    headers = {
        "Content-Disposition": f'attachment; filename="{job.filename}"',
        **job.headers_extra,
    }
    return Response(content=job.content, media_type=job.content_type, headers=headers)


@export_router.get("/management-review.xlsx")
def export_management_review(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    period: str | None = Query(None),
    quarter: str | None = Query(None),
    fiscal_year: str | None = Query(None),
    as_of_period: str | None = Query(None),
    block_on_failure: bool = Query(False),
    include_ai_commentary: bool = Query(False),
    waterfall_type: str | None = Query(None),
    marketing_channel: str | None = Query(None),
    region: str | None = Query(None),
    segment: str | None = Query(None),
    owner: str | None = Query(None),
    db: Session = Depends(get_db),
) -> Response:
    get_organization_or_404(db, organization_id)
    params = _export_params(
        scenario,
        start_period,
        end_period,
        period,
        quarter,
        fiscal_year,
        as_of_period,
        waterfall_type,
        marketing_channel,
        region,
        segment,
        owner,
    )
    try:
        bundle = collect_bundle(db, organization_id, include_ai_commentary=include_ai_commentary, **params)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export bundle failed: {exc}") from exc
    _check_validation(bundle, block_on_failure)
    try:
        content = build_excel_management_review(bundle)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel export failed: {exc}") from exc
    filename = f"management_review_{bundle.as_of_period}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Validation": bundle.validation.status,
        },
    )


@export_router.get("/variance-commentary.xlsx")
def export_variance_commentary(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    period: str | None = Query(None),
    quarter: str | None = Query(None),
    fiscal_year: str | None = Query(None),
    as_of_period: str | None = Query(None),
    include_ai_commentary: bool = Query(False),
    waterfall_type: str | None = Query(None),
    marketing_channel: str | None = Query(None),
    region: str | None = Query(None),
    segment: str | None = Query(None),
    owner: str | None = Query(None),
    db: Session = Depends(get_db),
) -> Response:
    get_organization_or_404(db, organization_id)
    params = _export_params(
        scenario,
        start_period,
        end_period,
        period,
        quarter,
        fiscal_year,
        as_of_period,
        waterfall_type,
        marketing_channel,
        region,
        segment,
        owner,
    )
    try:
        bundle = collect_bundle(db, organization_id, include_ai_commentary=include_ai_commentary, **params)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export bundle failed: {exc}") from exc
    try:
        content = build_excel_variance_commentary(bundle)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel export failed: {exc}") from exc
    filename = f"variance_commentary_{bundle.as_of_period}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _board_pptx_response(
    bundle: ReportingBundle,
    *,
    include_commentary: bool,
    include_validation_appendix: bool,
    use_ai_commentary: bool,
    scenario_mode: str | None,
    package_mode: str,
    deck_kind: str = "board",
    ts_data: dict | None = None,
    cash_bridge_data: dict | None = None,
    freeze_context_text: str | None = None,
    freeze_context_as_of: str | None = None,
    freeze_status: str | None = None,
    freeze_stale: bool = False,
) -> Response:
    try:
        if deck_kind == "mda":
            content, pptx_source = build_pptx_mda_deck(
                bundle,
                include_commentary=include_commentary,
                include_validation_appendix=include_validation_appendix,
                use_ai_commentary=use_ai_commentary,
                scenario_mode=scenario_mode,
                package_mode=package_mode,
                ts_data=ts_data,
                cash_bridge_data=cash_bridge_data,
                freeze_context_text=freeze_context_text,
                freeze_context_as_of=freeze_context_as_of,
                freeze_status=freeze_status,
                freeze_stale=freeze_stale,
            )
            filename = f"mda_deck_{bundle.as_of_period}.pptx"
        else:
            content, pptx_source = build_pptx_board_presentation(
                bundle,
                include_commentary=include_commentary,
                include_validation_appendix=include_validation_appendix,
                use_ai_commentary=use_ai_commentary,
                scenario_mode=scenario_mode,
                package_mode=package_mode,
            )
            filename = f"board_package_{bundle.as_of_period}.pptx"
        if not content:
            raise ValueError("Board PPTX render returned empty content.")
        validation_status = bundle.validation.status if bundle.validation else "unknown"
        from app.services.reporting.export.pptx_template_export import resolve_board_pptx_template

        template_path = resolve_board_pptx_template()
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Validation": validation_status,
            "X-Board-Package-Engine": "smpl-board-v2",
            "X-Board-PPTX-Source": pptx_source,
            "X-Board-AI-Commentary": "true" if use_ai_commentary else "false",
            "X-Board-Deck-Kind": deck_kind,
        }
        if template_path and deck_kind != "mda":
            headers["X-Board-PPTX-Template"] = str(template_path)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers=headers,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Board PPTX render failed")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to render board presentation: {type(exc).__name__}: {exc}",
        ) from exc


@export_router.get("/mda-deck-smoke")
def export_mda_deck_smoke(
    organization_id: uuid.UUID = Query(...),
    as_of_period: str = Query("2026-06"),
    level: str = Query(
        "ping",
        description="ping (~2s) | bundle (~2min) | assemble | render (full PPTX, slow)",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """JSON smoke test for MD&A deck. Default level=ping avoids Railway HTTP timeouts."""
    from app.services.reporting.export.board_export_service import build_mda_deck_smoke_result

    org = get_organization_or_404(db, organization_id)
    normalized = (level or "ping").strip().lower()
    if normalized not in {"ping", "bundle", "assemble", "render"}:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid level {level!r}. Use ping, bundle, assemble, or render.",
        )

    if normalized == "ping":
        return {
            "status": "ok",
            "level": "ping",
            "mode": "ping",
            "source": "programmatic",
            "deck_kind": "mda",
            "organization_id": str(organization_id),
            "organization_name": org.name,
            "period": as_of_period,
            "api_build": "mda-smoke-v5",
            "note": "Org reachable. Use level=assemble locally or -LocalSmoke for full pipeline.",
        }

    year = as_of_period[:4]
    try:
        bundle = collect_bundle(
            db,
            organization_id,
            scenario="Combined",
            start_period=f"{year}-01",
            end_period=f"{year}-12",
            as_of_period=as_of_period,
            include_ai_commentary=False,
        )
        if normalized == "bundle":
            return {
                "status": "ok",
                "level": "bundle",
                "mode": "bundle",
                "source": "programmatic",
                "deck_kind": "mda",
                "validation": bundle.validation.status,
                "period": bundle.as_of_period,
                "organization_name": bundle.organization_name,
            }
        result = build_mda_deck_smoke_result(
            bundle,
            full_render=(normalized == "render"),
            package_mode="executive_summary" if normalized == "assemble" else "full_board",
        )
        result["level"] = normalized
        return result
    except Exception as exc:
        logger.exception("MD&A deck smoke failed")
        raise HTTPException(
            status_code=500,
            detail=f"MD&A deck smoke failed: {type(exc).__name__}: {exc}",
        ) from exc


@export_router.get("/board-presentation-smoke")
def export_board_presentation_smoke(
    organization_id: uuid.UUID = Query(...),
    as_of_period: str = Query("2026-06"),
    db: Session = Depends(get_db),
) -> dict:
    """JSON smoke test for board PPTX pipeline (no file download)."""
    get_organization_or_404(db, organization_id)
    year = as_of_period[:4]
    try:
        bundle = collect_bundle(
            db,
            organization_id,
            scenario="Combined",
            start_period=f"{year}-01",
            end_period=f"{year}-12",
            as_of_period=as_of_period,
            include_ai_commentary=False,
        )
        content, source = build_pptx_board_presentation(
            bundle,
            use_ai_commentary=False,
            package_mode="full_board",
        )
        from app.services.reporting.export.pptx_template_export import resolve_board_pptx_template

        template_path = resolve_board_pptx_template()
        return {
            "status": "ok",
            "bytes": len(content),
            "source": source,
            "template_path": str(template_path) if template_path else None,
            "validation": bundle.validation.status,
            "period": bundle.as_of_period,
        }
    except Exception as exc:
        logger.exception("Board PPTX smoke failed")
        raise HTTPException(
            status_code=500,
            detail=f"Board export smoke failed: {type(exc).__name__}: {exc}",
        ) from exc


@export_router.get("/board-package")
@export_router.get("/board-presentation.pptx")
def export_board_presentation(
    organization_id: uuid.UUID = Query(...),
    reporting_period: str | None = Query(None, description="Alias for as_of_period (close month YYYY-MM)"),
    scenario: str = Query("Combined"),
    scenario_mode: str | None = Query(
        None,
        description="Actual | Budget | Forecast | Actual+Forecast | Actual vs Budget | Actual vs Forecast",
    ),
    start_period: str = Query(...),
    end_period: str = Query(...),
    period: str | None = Query(None),
    quarter: str | None = Query(None),
    fiscal_year: str | None = Query(None),
    as_of_period: str | None = Query(None),
    block_on_failure: bool = Query(False),
    include_ai_commentary: bool = Query(
        True,
        description="Generate Claude Key Takeaways per slide (API spec prompts) when API key is set",
    ),
    include_commentary: bool = Query(True),
    include_appendix: bool = Query(True),
    include_validation: bool = Query(True, description="Include validation appendix slide"),
    package_mode: str = Query(
        "full_board",
        description="full_board | executive_summary | gtm_deep_dive | finance_deep_dive | variance_commentary",
    ),
    waterfall_type: str | None = Query(None),
    marketing_channel: str | None = Query(None),
    region: str | None = Query(None),
    segment: str | None = Query(None),
    owner: str | None = Query(None),
    db: Session = Depends(get_db),
) -> Response:
    _org_for_board_export(db, organization_id, include_ai_commentary=include_ai_commentary)
    as_of = reporting_period or as_of_period
    params = _export_params(
        scenario,
        start_period,
        end_period,
        period,
        quarter,
        fiscal_year,
        as_of,
        waterfall_type,
        marketing_channel,
        region,
        segment,
        owner,
    )
    try:
        # Metrics bundle only — Claude narrative runs at PPTX render time (faster, fewer 500s).
        bundle = collect_bundle(
            db,
            organization_id,
            include_ai_commentary=False,
            **params,
        )
    except Exception as exc:
        logger.exception("Board PPTX bundle collection failed")
        raise HTTPException(
            status_code=500,
            detail=f"Export bundle failed: {type(exc).__name__}: {exc}",
        ) from exc
    if include_validation:
        _check_validation(bundle, block_on_failure)
    return _board_pptx_response(
        bundle,
        include_commentary=include_commentary,
        include_validation_appendix=include_appendix,
        use_ai_commentary=include_ai_commentary,
        scenario_mode=scenario_mode,
        package_mode=package_mode,
    )


@export_router.get("/mda-deck.pptx")
def export_mda_deck(
    organization_id: uuid.UUID = Query(...),
    reporting_period: str | None = Query(None, description="Alias for as_of_period (close month YYYY-MM)"),
    scenario: str = Query("Combined"),
    scenario_mode: str | None = Query(
        None,
        description="Actual | Budget | Forecast | Actual+Forecast | Actual vs Budget | Actual vs Forecast",
    ),
    start_period: str = Query(...),
    end_period: str = Query(...),
    period: str | None = Query(None),
    quarter: str | None = Query(None),
    fiscal_year: str | None = Query(None),
    as_of_period: str | None = Query(None),
    block_on_failure: bool = Query(False),
    include_ai_commentary: bool = Query(
        True,
        description="Generate Claude slide commentary when API key is set",
    ),
    include_commentary: bool = Query(True),
    include_appendix: bool = Query(True),
    include_validation: bool = Query(True, description="Include validation appendix slide"),
    package_mode: str = Query(
        "full_board",
        description="full_board | executive_summary | gtm_deep_dive | finance_deep_dive | variance_commentary",
    ),
    waterfall_type: str | None = Query(None),
    marketing_channel: str | None = Query(None),
    region: str | None = Query(None),
    segment: str | None = Query(None),
    owner: str | None = Query(None),
    db: Session = Depends(get_db),
) -> Response:
    """MD&A operating review deck — Claude Prompt 5 full fresh build from data source."""
    _org_for_board_export(db, organization_id, include_ai_commentary=include_ai_commentary)
    as_of = reporting_period or as_of_period
    params = _export_params(
        scenario,
        start_period,
        end_period,
        period,
        quarter,
        fiscal_year,
        as_of,
        waterfall_type,
        marketing_channel,
        region,
        segment,
        owner,
    )
    freeze = _require_servable_freeze_for_mda(db, organization_id, params["as_of_period"])
    try:
        bundle = collect_bundle(
            db,
            organization_id,
            include_ai_commentary=False,
            **params,
        )
    except Exception as exc:
        logger.exception("MD&A deck bundle collection failed")
        raise HTTPException(
            status_code=500,
            detail=f"Export bundle failed: {type(exc).__name__}: {exc}",
        ) from exc
    if include_validation:
        _check_validation(bundle, block_on_failure)
    ts_data, cash_bridge_data = _load_board_export_enrichment(db, organization_id, bundle)
    return _board_pptx_response(
        bundle,
        include_commentary=include_commentary,
        include_validation_appendix=include_appendix,
        use_ai_commentary=include_ai_commentary,
        scenario_mode=scenario_mode,
        package_mode=package_mode,
        deck_kind="mda",
        ts_data=ts_data,
        cash_bridge_data=cash_bridge_data,
        freeze_context_text=freeze.context_text,
        freeze_context_as_of=freeze.context_as_of_iso,
        freeze_status=freeze.status,
        freeze_stale=freeze.stale,
    )
