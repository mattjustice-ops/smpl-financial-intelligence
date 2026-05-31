"""Post-render and pre-render visual QA for executive decks."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.services.board_package.pptx_layout_engine import (
    SLIDE_HEIGHT,
    SLIDE_SAFE_BOTTOM,
    SLIDE_WIDTH_IN,
    clamp_table_rows,
    compact_bullets,
    compact_callouts,
    prepare_slide_chart,
)
from app.services.board_package.schemas import SlideContent
from app.services.reporting.export.board_slide_viability import chart_has_decision_value
from app.services.reporting.export.executive_reporting_governance import (
    LIMITS,
    should_escalate_to_appendix,
)

logger = logging.getLogger(__name__)

EMU_PER_INCH = 914400


@dataclass
class QAIssue:
    code: str
    message: str
    slide_index: int | None = None
    severity: str = "warning"


@dataclass
class QAResult:
    issues: list[QAIssue] = field(default_factory=list)
    auto_fixed: int = 0

    @property
    def ok(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)


def remediate_slide_content(slide: SlideContent) -> SlideContent:
    """Pre-render fixes: drop empty visuals, enforce single primary, cap density."""
    chart = prepare_slide_chart(slide.chart) if chart_has_decision_value(slide.chart) else None
    table = clamp_table_rows(slide.table)
    if chart and table and slide.layout in (
        "story_slide",
        "executive_ytd",
        "cash_trend",
        "chart_primary",
    ):
        table = None
    if chart and table and slide.layout == "executive_scorecard":
        chart = None
    if chart and slide.secondary_chart:
        slide = slide.model_copy(update={"secondary_chart": None})
    bullets = compact_bullets(slide)
    callouts = compact_callouts(slide.callouts)
    narrative = slide.narrative
    if narrative and len(narrative) > 320:
        narrative = narrative[:317] + "…"
    return slide.model_copy(
        update={
            "chart": chart,
            "table": table,
            "secondary_chart": None,
            "kpi_cards": slide.kpi_cards[:4],
            "bullets": bullets,
            "callouts": callouts,
            "narrative": narrative,
        }
    )


def _shape_bounds_inches(shape) -> tuple[float, float, float, float]:
    left = shape.left / EMU_PER_INCH
    top = shape.top / EMU_PER_INCH
    width = shape.width / EMU_PER_INCH
    height = shape.height / EMU_PER_INCH
    return left, top, left + width, top + height


def _boxes_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def audit_presentation(prs) -> QAResult:
    """Inspect rendered shapes for clipping and overlap."""
    result = QAResult()
    for idx, slide in enumerate(prs.slides):
        boxes: list[tuple[float, float, float, float]] = []
        for shape in slide.shapes:
            try:
                box = _shape_bounds_inches(shape)
            except Exception:
                continue
            l, t, r, b = box
            if r > SLIDE_WIDTH_IN + 0.05 or b > SLIDE_HEIGHT + 0.05:
                result.issues.append(
                    QAIssue(
                        "off_slide",
                        f"Shape extends beyond slide bounds (r={r:.2f}, b={b:.2f})",
                        slide_index=idx,
                        severity="error",
                    )
                )
            if b > SLIDE_SAFE_BOTTOM + 0.12:
                result.issues.append(
                    QAIssue(
                        "footer_clip",
                        f"Shape below safe zone (b={b:.2f})",
                        slide_index=idx,
                        severity="warning",
                    )
                )
            for prev in boxes:
                if _boxes_overlap(prev, box):
                    result.issues.append(
                        QAIssue(
                            "overlap",
                            "Shapes overlap on slide",
                            slide_index=idx,
                            severity="warning",
                        )
                    )
                    break
            boxes.append(box)
    if result.issues:
        logger.warning(
            "Board PPTX visual QA: %d issue(s) — %s",
            len(result.issues),
            "; ".join(i.code for i in result.issues[:5]),
        )
    return result


def audit_slide_content(slide: SlideContent) -> QAResult:
    """Lightweight pre-render checks."""
    result = QAResult()
    if slide.layout in ("story_slide", "executive_ytd") and slide.chart and slide.table:
        result.issues.append(
            QAIssue("stacked_visuals", "Chart and table on same executive slide", severity="warning")
        )
    if len(slide.bullets) > LIMITS.max_bullets:
        result.issues.append(
            QAIssue("bullet_overflow", f"{len(slide.bullets)} bullets (max {LIMITS.max_bullets})", severity="warning")
        )
    if slide.chart and len(slide.chart.categories) > LIMITS.max_chart_categories_executive:
        result.issues.append(QAIssue("dense_chart", "Too many chart categories", severity="warning"))
    if should_escalate_to_appendix(slide):
        result.issues.append(
            QAIssue("appendix_recommended", "Detail should move to appendix", severity="warning")
        )
    if not slide.chart and not slide.table and not slide.kpi_cards and slide.layout == "story_slide":
        result.issues.append(QAIssue("sparse_slide", "No primary visual", severity="error"))
    return result
