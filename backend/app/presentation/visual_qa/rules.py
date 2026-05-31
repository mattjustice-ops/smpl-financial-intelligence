"""Visual QA rules — deterministic checks before PPTX render."""

from __future__ import annotations

from app.presentation.templates.archetypes import allowed_layouts, resolve_template
from app.services.board_package.schemas import SlideContent

FORBIDDEN_RUNTIME_LAYOUTS = frozenset(
    {
        "chart_primary",
        "dual_metric",
        "narrative_table_split",
        "executive_dashboard",
    }
)


def validate_slide_template(slide: SlideContent) -> list[str]:
    """Return human-readable violations (empty = ok)."""
    issues: list[str] = []
    spec = resolve_template(slide.slide_id)
    if spec and slide.layout != spec.layout:
        issues.append(
            f"{slide.slide_id}: layout {slide.layout!r} != template {spec.layout!r}"
        )
    if slide.layout in FORBIDDEN_RUNTIME_LAYOUTS:
        issues.append(f"{slide.slide_id}: deprecated dynamic layout {slide.layout!r}")
    if slide.layout not in allowed_layouts():
        issues.append(f"{slide.slide_id}: unknown layout {slide.layout!r}")
    if slide.secondary_chart:
        issues.append(f"{slide.slide_id}: secondary_chart not allowed on executive templates")
    if len(slide.bullets) > 3 and slide.layout in ("story_slide", "cash_trend", "executive_scorecard"):
        issues.append(f"{slide.slide_id}: bullets exceed footer band (max 3)")
    return issues
