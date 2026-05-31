"""Slide viability scoring — drop blank, sparse, or low-value slides before export."""

from __future__ import annotations

import re

from app.services.board_package.schemas import ChartSpec, SlideContent, TableSpec

ALWAYS_KEEP = frozenset({"executive_summary", "mda_summary", "risks_opportunities"})

MERGE_IF_WEAK = {
    "retention_churn": "arr_waterfall",
    "deferred_revenue": "gaap_revenue",
}

MIN_VIABLE_SCORE = 58
PLACEHOLDER_PATTERNS = re.compile(
    r"complete variance|placeholder|n/a only|no data|tbd",
    re.I,
)


def chart_has_decision_value(chart: ChartSpec | None) -> bool:
    if not chart or not chart.categories:
        return False
    return any(abs(v) > 1e-6 for vals in chart.series.values() for v in vals)


def _table_has_rows(table: TableSpec | None) -> bool:
    return bool(table and table.rows)


def _meaningful_bullets(slide: SlideContent) -> int:
    n = 0
    for b in slide.bullets:
        if not b or PLACEHOLDER_PATTERNS.search(b) or len(b.strip()) < 12:
            continue
        n += 1
    return n


def score_slide(slide: SlideContent) -> int:
    if slide.layout in ("section_divider", "section_transition"):
        return 75 if (slide.narrative or slide.kpi_cards) else 30

    score = 0
    if chart_has_decision_value(slide.chart):
        score += 38
    elif _table_has_rows(slide.table):
        score += 32
    elif len(slide.spotlight_cards) >= 2:
        score += 36
    elif slide.layout == "mda_narrative" and _meaningful_bullets(slide) >= 3:
        score += 40
    elif slide.layout == "risk_matrix" and slide.callouts:
        score += 45

    if slide.kpi_cards:
        score += 18
    score += min(16, _meaningful_bullets(slide) * 8)
    if slide.key_takeaway and not PLACEHOLDER_PATTERNS.search(slide.key_takeaway):
        score += 12
    if slide.callouts:
        score += 10

    if not slide.chart and not slide.table and not slide.kpi_cards and not slide.spotlight_cards:
        if slide.layout not in ("mda_narrative", "risk_matrix", "executive_ytd"):
            score -= 25

    return max(0, min(100, score))


def is_viable(slide: SlideContent) -> bool:
    if slide.slide_id in ALWAYS_KEEP:
        return True
    if slide.slide_id.startswith("section_"):
        return score_slide(slide) >= 40
    return score_slide(slide) >= MIN_VIABLE_SCORE


def prune_slide_content(slide: SlideContent) -> SlideContent:
    chart = slide.chart if chart_has_decision_value(slide.chart) else None
    table = slide.table if _table_has_rows(slide.table) else None
    if chart and table and slide.layout in (
        "story_slide",
        "executive_ytd",
        "cash_trend",
        "chart_primary",
    ):
        table = None
    if chart and table and slide.slide_id == "executive_summary":
        table = None

    return slide.model_copy(
        update={
            "chart": chart,
            "table": table,
            "secondary_chart": None,
            "kpi_cards": slide.kpi_cards[:4],
            "bullets": [b for b in slide.bullets if b and not PLACEHOLDER_PATTERNS.search(b)][:3],
        }
    )


def filter_board_slides(slides: list[SlideContent]) -> list[SlideContent]:
    pruned = [prune_slide_content(s) for s in slides]
    content_kept: list[SlideContent] = []

    for slide in pruned:
        if slide.slide_id.startswith("section_"):
            continue
        if slide.slide_id in ALWAYS_KEEP:
            content_kept.append(slide)
            continue
        if not is_viable(slide):
            continue
        merge_target = MERGE_IF_WEAK.get(slide.slide_id)
        if merge_target and any(s.slide_id == merge_target for s in content_kept):
            if score_slide(slide) <= score_slide(next(s for s in pruned if s.slide_id == merge_target)):
                continue
        content_kept.append(slide)

    kept_ids = {s.slide_id for s in content_kept}
    out: list[SlideContent] = []
    for slide in pruned:
        if slide.slide_id.startswith("section_"):
            anchor = slide.slide_id.replace("section_", "", 1)
            if anchor in kept_ids and is_viable(slide):
                out.append(slide)
        elif slide.slide_id in kept_ids:
            out.append(slide)
    return out
