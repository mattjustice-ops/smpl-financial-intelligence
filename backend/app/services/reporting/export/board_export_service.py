"""Orchestrate 17-slide board package export (charts, commentary, validation)."""

from __future__ import annotations

from app.services.board_package.pptx_builder import render_pptx_bytes
from app.services.board_package.schemas import BoardPackage
from app.services.reporting.export.board_commentary_service import build_all_slide_commentary
from app.services.reporting.export.board_semantic_mappings import PackageMode
from app.services.reporting.export.board_slides import build_board_package
from app.services.reporting.export.schemas import ReportingBundle


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


def build_board_pptx_bytes(
    bundle: ReportingBundle,
    *,
    include_commentary: bool = True,
    include_validation_appendix: bool = True,
    use_ai_commentary: bool = False,
    scenario_mode: str | None = None,
    package_mode: PackageMode = "full_board",
) -> bytes:
    package = build_board_package_from_bundle(
        bundle,
        include_commentary=include_commentary,
        include_validation_appendix=include_validation_appendix,
        use_ai_commentary=use_ai_commentary,
        scenario_mode=scenario_mode,
        package_mode=package_mode,
    )
    return render_pptx_bytes(package)
