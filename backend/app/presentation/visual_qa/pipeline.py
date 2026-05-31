"""Pre-render QA pipeline — remediate then validate."""

from __future__ import annotations

import logging

from app.presentation.templates.archetypes import apply_template_to_slide
from app.presentation.visual_qa.rules import validate_slide_template
from app.services.board_package.pptx_visual_qa import remediate_slide_content
from app.services.board_package.schemas import BoardPackage, SlideContent

logger = logging.getLogger(__name__)


def prepare_slide_for_render(slide: SlideContent) -> SlideContent:
    slide = apply_template_to_slide(slide)
    slide = remediate_slide_content(slide)
    for msg in validate_slide_template(slide):
        logger.warning("[presentation QA] %s", msg)
    return slide


def prepare_package(slides: list[SlideContent]) -> list[SlideContent]:
    return [prepare_slide_for_render(s) for s in slides]


def prepare_board_package(package: BoardPackage) -> BoardPackage:
    return package.model_copy(update={"slides": prepare_package(package.slides)})
