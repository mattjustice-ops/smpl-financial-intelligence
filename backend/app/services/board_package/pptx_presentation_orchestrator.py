"""Prepare board package for executive PPTX rendering — deterministic templates only."""

from __future__ import annotations

from app.presentation.orchestration.appendix import inject_appendix_slides
from app.presentation.templates.archetypes import apply_template_to_slide
from app.presentation.visual_qa.pipeline import prepare_slide_for_render
from app.services.board_package.schemas import BoardPackage, SlideContent
from app.services.reporting.export.board_slide_viability import filter_board_slides
from app.services.reporting.export.executive_reporting_governance import apply_density_governance


def enforce_executive_layout(slide: SlideContent) -> SlideContent:
    """Map slide_id → fixed template; remediate density (no runtime layout invention)."""
    slide = apply_template_to_slide(slide)
    slide = apply_density_governance(slide)
    return prepare_slide_for_render(slide)


def prepare_package_for_render(package: BoardPackage, *, include_appendix: bool = True) -> BoardPackage:
    """Filter, apply templates, remediate, and optionally append overflow slides before PPTX build."""
    slides = filter_board_slides(package.slides)
    slides = [enforce_executive_layout(s) for s in slides]
    if include_appendix:
        slides = inject_appendix_slides(slides)
        slides = [enforce_executive_layout(s) for s in slides]
    return package.model_copy(update={"slides": slides})
