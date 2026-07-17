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


def build_mda_package_xlsx_bytes(
    bundle: ReportingBundle,
    *,
    include_commentary: bool = True,
    use_ai_commentary: bool = True,
    ts_data: dict | None = None,
    cash_bridge_data: dict | None = None,
    freeze_context_text: str | None = None,
    freeze_context_as_of: str | None = None,
    freeze_status: str | None = None,
    freeze_stale: bool = False,
) -> tuple[bytes, str]:
    """MD&A Excel package — Claude Prompt 2 commentary + SMPL template."""
    import os

    from app.services.reporting.export.prompt2_mda_package import build_claude_mda_package_xlsx_bytes

    skip = (
        not include_commentary
        or not use_ai_commentary
        or os.environ.get("MDA_DATA_ONLY", "").strip().lower() in ("1", "true", "yes")
    )
    return build_claude_mda_package_xlsx_bytes(
        bundle,
        ts_data=ts_data,
        cash_bridge_data=cash_bridge_data,
        skip_claude=skip,
        freeze_context_text=freeze_context_text,
        freeze_context_as_of=freeze_context_as_of,
        freeze_status=freeze_status,
        freeze_stale=freeze_stale,
    )


def build_mda_deck_pptx_bytes(
    bundle: ReportingBundle,
    *,
    include_commentary: bool = True,
    include_validation_appendix: bool = True,
    use_ai_commentary: bool = False,
    scenario_mode: str | None = None,
    package_mode: PackageMode = "full_board",
    ts_data: dict | None = None,
    cash_bridge_data: dict | None = None,
    freeze_context_text: str | None = None,
    freeze_context_as_of: str | None = None,
    freeze_status: str | None = None,
    freeze_stale: bool = False,
) -> tuple[bytes, str]:
    """MD&A deck — adapt known-good PptxGenJS reference first; fresh Prompt 5 if needed."""
    _ = (include_commentary, include_validation_appendix, use_ai_commentary, scenario_mode, package_mode)
    from app.services.reporting.export.prompt5_deck import build_claude_deck_pptx_bytes

    return build_claude_deck_pptx_bytes(
        bundle,
        ts_data=ts_data,
        cash_bridge_data=cash_bridge_data,
        freeze_context_text=freeze_context_text,
        freeze_context_as_of=freeze_context_as_of,
        freeze_status=freeze_status,
        freeze_stale=freeze_stale,
    )


def build_mda_deck_smoke_result(
    bundle: ReportingBundle,
    *,
    full_render: bool = False,
    package_mode: PackageMode = "executive_summary",
) -> dict[str, object]:
    """Quick smoke: assemble slides only. Full smoke: also render PPTX bytes."""
    mode = "executive_summary" if not full_render else package_mode
    package = build_board_package_from_bundle(
        bundle,
        include_commentary=True,
        include_validation_appendix=full_render,
        use_ai_commentary=False,
        package_mode=mode,
    )
    result: dict[str, object] = {
        "status": "ok",
        "source": "claude_prompt5",
        "deck_kind": "mda",
        "mode": "full" if full_render else "quick",
        "slide_count": len(package.slides),
        "package_mode": mode,
        "validation": bundle.validation.status,
        "period": bundle.as_of_period,
    }
    if full_render:
        content = render_pptx_bytes(package)
        result["bytes"] = len(content)
    return result


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
    return render_pptx_bytes(package), "programmatic"
