"""Orchestrate 17-slide board package export (charts, commentary, validation)."""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.services.board_package.pptx_builder import render_pptx_bytes
from app.services.board_package.schemas import BoardPackage
from app.services.reporting.export.board_semantic_mappings import PackageMode
from app.services.reporting.export.board_slides import build_board_package
from app.services.reporting.export.schemas import ReportingBundle

logger = logging.getLogger(__name__)


def build_board_package_from_bundle(
    bundle: ReportingBundle,
    *,
    include_commentary: bool = True,
    include_validation_appendix: bool = True,
    use_ai_commentary: bool = False,
    scenario_mode: str | None = None,
    package_mode: PackageMode = "full_board",
) -> BoardPackage:
    """Build canonical BoardPackage for pptx rendering."""
    from app.services.reporting.export.board_commentary_service import build_all_slide_commentary

    _ = scenario_mode  # reserved for future scenario-specific slide variants
    commentary = (
        build_all_slide_commentary(bundle, use_ai=use_ai_commentary)
        if include_commentary
        else {}
    )
    if not commentary:
        from app.services.reporting.export.board_commentary_service import build_slide_commentary

        keys = [
            "executive_summary",
            "mda_summary",
            "gtm_performance",
            "marketing_channels",
            "funnel_conversion",
            "pipeline_health",
            "pipeline_movement",
            "opportunity_drilldown",
            "arr_waterfall",
            "retention_churn",
            "gaap_revenue",
            "deferred_revenue",
            "cash_forecast",
            "headcount",
            "department_spend",
            "risks_opportunities",
            "validation",
        ]
        commentary = {k: build_slide_commentary(bundle, k) for k in keys}

    return build_board_package(
        bundle,
        commentary,
        include_validation_appendix=include_validation_appendix,
        package_mode=package_mode,
    )


def build_mda_deck_pptx_bytes(
    bundle: ReportingBundle,
    *,
    include_commentary: bool = True,
    include_validation_appendix: bool = True,
    use_ai_commentary: bool = False,
    scenario_mode: str | None = None,
    package_mode: PackageMode = "full_board",
) -> tuple[bytes, str]:
    """MD&A deck — always programmatic layout (no template shape patching)."""
    _ = scenario_mode
    package = build_board_package_from_bundle(
        bundle,
        include_commentary=include_commentary,
        include_validation_appendix=include_validation_appendix,
        use_ai_commentary=use_ai_commentary,
        scenario_mode=scenario_mode,
        package_mode=package_mode,
    )
    skip_filter = package_mode == "full_board"
    return (
        render_pptx_bytes(package, skip_viability_filter=skip_filter),
        "programmatic",
    )


def build_board_pptx_bytes(
    bundle: ReportingBundle,
    *,
    include_commentary: bool = True,
    include_validation_appendix: bool = True,
    use_ai_commentary: bool = False,
    scenario_mode: str | None = None,
    package_mode: PackageMode = "full_board",
) -> tuple[bytes, str]:
    """Build board PPTX bytes and return (bytes, source) where source is template|programmatic."""
    from app.services.reporting.export.pptx_template_export import (
        build_pptx_from_template,
        resolve_board_pptx_template,
    )

    settings = get_settings()
    export_mode = (getattr(settings, "board_pptx_export_mode", None) or "template_first").lower()
    use_ai = use_ai_commentary

    if export_mode in ("template_first", "template_only"):
        template_path = resolve_board_pptx_template()
        if template_path is not None:
            template_bytes = build_pptx_from_template(bundle, use_ai_commentary=use_ai)
            if template_bytes:
                return template_bytes, "template"
            if export_mode == "template_only":
                raise RuntimeError(
                    f"Board PPTX template at {template_path} could not be processed. "
                    "Check backend logs for python-pptx errors."
                )
            logger.warning(
                "Board PPTX template at %s failed — falling back to programmatic export.",
                template_path,
            )
        elif export_mode == "template_only":
            raise FileNotFoundError(
                "Board PPTX template not found. Place your reference deck at "
                "backend/templates/board/SMPL_Board_Review_Template.pptx or set BOARD_PPTX_TEMPLATE."
            )
        else:
            logger.warning(
                "Board PPTX template missing — falling back to programmatic export. "
                "Copy SMPL_Board_Review_Q2_2026.pptx to backend/templates/board/SMPL_Board_Review_Template.pptx "
                "and redeploy Railway (Dockerfile must COPY templates/)."
            )

    package = build_board_package_from_bundle(
        bundle,
        include_commentary=include_commentary,
        include_validation_appendix=include_validation_appendix,
        use_ai_commentary=use_ai,
        scenario_mode=scenario_mode,
        package_mode=package_mode,
    )
    skip_filter = package_mode == "full_board"
    return (
        render_pptx_bytes(package, skip_viability_filter=skip_filter),
        "programmatic",
    )
