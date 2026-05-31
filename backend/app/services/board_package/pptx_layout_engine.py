"""Executive slide layout zones — strict boundaries, no overlap."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.board_package.pptx_chart_archetypes import apply_archetype, infer_archetype
from app.services.board_package.schemas import CalloutBlock, ChartSpec, KpiCard, SlideContent, TableSpec

# 16:9 canvas (inches) — generous margins for executive whitespace
MARGIN_L = 0.75
MARGIN_R = 0.75
CONTENT_W = 11.83
SLIDE_HEIGHT = 7.5
SLIDE_WIDTH = 13.333
SLIDE_WIDTH_IN = SLIDE_WIDTH  # alias used by pptx_builder / pptx_visual_qa
SLIDE_SAFE_BOTTOM = 6.82
FOOTNOTE_TOP = 6.76

# Title block ends ~1.35"
ZONE_TITLE_BOTTOM = 1.35

# KPI band: top 15–20%
ZONE_KPI_TOP = 1.42
ZONE_KPI_HEIGHT = 0.72
ZONE_KPI_BOTTOM = ZONE_KPI_TOP + ZONE_KPI_HEIGHT

# Visual band: middle 55–65%
ZONE_VISUAL_TOP = 2.22
ZONE_VISUAL_HEIGHT = 2.82
ZONE_VISUAL_BOTTOM = ZONE_VISUAL_TOP + ZONE_VISUAL_HEIGHT

# Footer: bottom 20–25%
ZONE_FOOTER_TOP = 5.12
ZONE_FOOTER_HEIGHT = 1.15
ZONE_FOOTER_BOTTOM = ZONE_FOOTER_TOP + ZONE_FOOTER_HEIGHT

MAX_KPI_CARDS = 4
MAX_BULLETS = 3
MAX_CALLOUTS = 2
MAX_TABLE_ROWS = 5
MAX_CHART_CATEGORIES = 7
MAX_CHART_SERIES = 2
KPI_GAP = 0.14
BODY_FONT_PT = 11
CALLOUT_ROW_HEIGHT = 0.48


@dataclass(frozen=True)
class ElementBox:
    left: float
    top: float
    width: float
    height: float

    @property
    def bottom(self) -> float:
        return self.top + self.height

    @property
    def right(self) -> float:
        return self.left + self.width

    def clamped(self, *, max_bottom: float | None = None) -> "ElementBox":
        cap = max_bottom if max_bottom is not None else SLIDE_SAFE_BOTTOM
        top = max(ZONE_KPI_TOP, min(self.top, cap - 0.25))
        h = min(self.height, cap - top)
        return ElementBox(
            left=max(MARGIN_L, self.left),
            top=top,
            width=min(self.width, CONTENT_W),
            height=max(0.3, h),
        )

    def fits_in(self, zone: "ElementBox") -> bool:
        return (
            self.left >= zone.left - 0.02
            and self.top >= zone.top - 0.02
            and self.right <= zone.right + 0.02
            and self.bottom <= zone.bottom + 0.02
        )


def title_zone() -> ElementBox:
    return ElementBox(MARGIN_L, 0.28, CONTENT_W, ZONE_TITLE_BOTTOM).clamped()


def kpi_zone() -> ElementBox:
    return ElementBox(MARGIN_L, ZONE_KPI_TOP, CONTENT_W, ZONE_KPI_HEIGHT).clamped()


def visual_zone() -> ElementBox:
    return ElementBox(MARGIN_L, ZONE_VISUAL_TOP, CONTENT_W, ZONE_VISUAL_HEIGHT).clamped(
        max_bottom=ZONE_VISUAL_BOTTOM
    )


def visual_zone_chart(*, with_table: bool = False) -> ElementBox:
    h = ZONE_VISUAL_HEIGHT - (0.0 if not with_table else 0.0)
    return ElementBox(MARGIN_L, ZONE_VISUAL_TOP, CONTENT_W, h).clamped(max_bottom=ZONE_VISUAL_BOTTOM)


def visual_zone_table() -> ElementBox:
    return visual_zone()


def footer_zone() -> ElementBox:
    return ElementBox(MARGIN_L, ZONE_FOOTER_TOP, CONTENT_W, ZONE_FOOTER_HEIGHT).clamped(
        max_bottom=SLIDE_SAFE_BOTTOM
    )


def footer_bullet_box(*, has_callouts: bool) -> ElementBox:
    """Stack bullets below callouts without crossing visual zone."""
    fz = footer_zone()
    top = fz.top + (CALLOUT_ROW_HEIGHT if has_callouts else 0.0)
    height = min(0.68, SLIDE_SAFE_BOTTOM - top - 0.42)
    return ElementBox(fz.left, top, fz.width, max(0.28, height)).clamped(max_bottom=SLIDE_SAFE_BOTTOM)


def takeaway_box() -> ElementBox:
    return ElementBox(MARGIN_L, SLIDE_SAFE_BOTTOM - 0.38, CONTENT_W, 0.34).clamped()


def compact_bullets(slide: SlideContent) -> list[str]:
    from app.services.reporting.export.board_chart_density import truncate_bullet

    out: list[str] = []
    for b in slide.bullets:
        if not b:
            continue
        line = truncate_bullet(b, max_len=92)
        if line not in out:
            out.append(line)
        if len(out) >= MAX_BULLETS:
            break
    return out


def compact_callouts(callouts: list[CalloutBlock]) -> list[CalloutBlock]:
    return [
        CalloutBlock(kind=c.kind, text=c.text[:88], owner=c.owner)
        for c in callouts[:MAX_CALLOUTS]
    ]


def prepare_slide_chart(chart: ChartSpec | None, *, slide_id: str | None = None) -> ChartSpec | None:
    if not chart:
        return None
    from app.services.reporting.export.board_chart_density import prepare_chart_for_executive

    arch = chart.archetype or infer_archetype(chart, slide_id)
    trimmed = chart.model_copy(
        update={
            "series": {k: v for k, v in list(chart.series.items())[:MAX_CHART_SERIES]},
        }
    )
    prepared = prepare_chart_for_executive(trimmed, max_categories=MAX_CHART_CATEGORIES)
    return apply_archetype(prepared, arch)  # type: ignore[arg-type]


def clamp_table_rows(table: TableSpec | None, *, max_rows: int = MAX_TABLE_ROWS) -> TableSpec | None:
    if not table or not table.rows:
        return None
    if len(table.rows) <= max_rows:
        return table
    rows = table.rows[: max_rows - 1] + [["…", f"+{len(table.rows) - max_rows + 1} more", "Appendix"]]
    return table.model_copy(update={"rows": rows})
