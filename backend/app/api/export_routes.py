"""Reporting export endpoints (Excel close package, board PPTX, validation pre-check)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.dashboard_routes import dashboard_params
from app.db.session import get_db
from app.services.organizations import get_organization_or_404
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
    collect_bundle,
    run_export_validation,
)
from app.services.reporting.period_utils import to_period

export_router = APIRouter(prefix="/export", tags=["export"])


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


def _check_validation(bundle: ReportingBundle, block_on_failure: bool) -> None:
    if block_on_failure and bundle.validation.failed_count > 0:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Export blocked: validation checks failed. Review Validation Checks or pass block_on_failure=false.",
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
    use_ai: bool = Query(True, description="Enrich commentary via OpenAI when API key is set"),
    db: Session = Depends(get_db),
) -> dict:
    """Executive + MD&A narrative for dashboard preview (same engine as board/Excel exports)."""
    get_organization_or_404(db, organization_id)
    settings = get_settings()
    ai_configured = bool(settings.openai_api_key)
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
        "openai_model": settings.openai_model,
        "executive_summary": _commentary_to_dict(exec_sc),
        "mda_summary": _commentary_to_dict(mda_sc),
        "narrative": _narrative_from_commentary(exec_sc),
        "mda_narrative": _narrative_from_commentary(mda_sc),
    }


@export_router.get("/validation", response_model=ExportValidationSummary)
def export_validation_precheck(
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
        return run_export_validation(db, organization_id, **params)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export validation failed: {exc}") from exc


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
) -> Response:
    try:
        content = build_pptx_board_presentation(
            bundle,
            include_commentary=include_commentary,
            include_validation_appendix=include_validation_appendix,
            use_ai_commentary=use_ai_commentary,
            scenario_mode=scenario_mode,
            package_mode=package_mode,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to render board presentation: {exc}") from exc
    filename = f"board_package_{bundle.as_of_period}.pptx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Validation": bundle.validation.status,
            "X-Board-Package-Engine": "smpl-board-v2",
        },
    )


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
    include_ai_commentary: bool = Query(False),
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
    get_organization_or_404(db, organization_id)
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
            include_ai_commentary=include_ai_commentary,
            **params,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export bundle failed: {exc}") from exc
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
