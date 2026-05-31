"""Deterministic executive presentation system (SMPL board export).

AI populates metrics, commentary, and insights into fixed slide archetypes.
Layouts, grids, spacing, and chart primitives are never invented at runtime.

See docs/design-language/ and docs/EXECUTIVE_PRESENTATION_SYSTEM.md.
"""

from app.presentation.design_system.tokens import PRESENTATION_ENGINE_ID
from app.presentation.templates.archetypes import (
    SLIDE_TEMPLATE_REGISTRY,
    SlideTemplateSpec,
    allowed_layouts,
    resolve_template,
)

__all__ = [
    "PRESENTATION_ENGINE_ID",
    "SLIDE_TEMPLATE_REGISTRY",
    "SlideTemplateSpec",
    "allowed_layouts",
    "resolve_template",
]
