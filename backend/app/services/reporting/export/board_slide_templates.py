"""Populate fixed slide templates — content slots only, no layout composition."""

from __future__ import annotations

from app.presentation.templates.archetypes import apply_template_to_slide, resolve_template
from app.services.board_package.schemas import CalloutBlock, SlideContent
from app.services.reporting.export.board_commentary_service import SlideCommentary
from app.services.reporting.export.board_story_chain import key_takeaway_from_commentary, story_subtitle
from app.services.reporting.export.schemas import ReportingBundle


def _compact_bullets(comm: SlideCommentary, bullets: list[str] | None, *, max_n: int = 3) -> list[str]:
    if bullets:
        return [b for b in bullets if b][:max_n]
    out: list[str] = []
    if comm.what_happened:
        out.append(comm.what_happened)
    if comm.why_it_happened and len(out) < max_n:
        out.append(comm.why_it_happened)
    if comm.impact and len(out) < max_n:
        out.append(comm.impact)
    return out[:max_n]


def assemble_slide(
    slide_id: str,
    title: str,
    bundle: ReportingBundle,
    comm: SlideCommentary,
    *,
    section_label: str | None = None,
    commentary_heading: str | None = None,
    subtitle: str | None = None,
    narrative: str | None = None,
    bullets: list[str] | None = None,
    callouts: list[CalloutBlock] | None = None,
    kpi_cards=None,
    spotlight_cards=None,
    chart=None,
    table=None,
    footnote: str | None = None,
    key_takeaway: str | None = None,
    max_table_rows: int = 5,
    max_kpis: int = 4,
) -> SlideContent:
    """Fill template slots for slide_id. Layout comes from presentation/templates/archetypes."""
    spec = resolve_template(slide_id)
    layout = spec.layout if spec else "story_slide"
    story_sub = story_subtitle(slide_id, subtitle or bundle.period_label)
    bullet_lines = _compact_bullets(comm, bullets)
    takeaway = key_takeaway or key_takeaway_from_commentary(comm) or None

    if table and table.rows:
        from app.services.reporting.export.board_format_utils import truncate_table_rows

        table = table.model_copy(
            update={"rows": truncate_table_rows(table.rows, max_table_rows)}
        )

    kpis = (kpi_cards or [])[:max_kpis]
    sec_label = section_label or (spec.section_label if spec else None)

    slide = SlideContent(
        slide_id=slide_id,
        title=title,
        subtitle=story_sub,
        section_label=sec_label,
        commentary_heading=commentary_heading,
        layout=layout,  # type: ignore[arg-type]
        narrative=narrative or comm.narrative_block() or None,
        bullets=bullet_lines,
        callouts=callouts or [],
        kpi_cards=kpis,
        spotlight_cards=spotlight_cards or [],
        chart=chart,
        secondary_chart=None,
        table=table,
        footnote=footnote
        or (f"Key takeaway: {takeaway}" if takeaway and layout not in ("executive_scorecard", "executive_ytd") else None),
        key_takeaway=takeaway,
        max_table_rows=max_table_rows,
    )
    return apply_template_to_slide(slide)
