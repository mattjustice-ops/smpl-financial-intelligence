"""Appendix overflow — executive slides stay sparse; detail moves to appendix."""

from __future__ import annotations

from app.presentation.templates.archetypes import apply_template_to_slide
from app.services.board_package.schemas import ChartSpec, SlideContent, TableSpec
from app.services.reporting.export.board_chart_density import rank_table_top_movers
from app.services.reporting.export.executive_reporting_governance import LIMITS

APPENDIX_TABLE_ROW_LIMIT = LIMITS.max_table_rows_trigger_appendix
APPENDIX_CHART_CATEGORY_LIMIT = LIMITS.max_chart_categories_trigger_appendix
EXECUTIVE_TABLE_ROWS = LIMITS.max_table_rows_executive


def _overflow_table_rows(table: TableSpec) -> tuple[TableSpec | None, TableSpec | None]:
    if len(table.rows) <= EXECUTIVE_TABLE_ROWS:
        return table, None
    executive = rank_table_top_movers(table.headers, table.rows, max_rows=EXECUTIVE_TABLE_ROWS)
    if len(table.rows) <= APPENDIX_TABLE_ROW_LIMIT:
        return executive, None
    appendix = TableSpec(headers=table.headers, rows=table.rows[EXECUTIVE_TABLE_ROWS:])
    return executive, appendix


def _overflow_chart_categories(chart: ChartSpec) -> tuple[ChartSpec | None, ChartSpec | None]:
    if len(chart.categories) <= APPENDIX_CHART_CATEGORY_LIMIT:
        return chart, None
    from app.services.reporting.export.board_chart_density import prepare_chart_for_executive

    exec_chart = prepare_chart_for_executive(chart, max_categories=APPENDIX_CHART_CATEGORY_LIMIT)
    return exec_chart, chart


def split_slide_overflow(slide: SlideContent) -> tuple[SlideContent, SlideContent | None]:
    """Return executive slide and optional appendix slide."""
    table = slide.table
    chart = slide.chart
    appendix_table: TableSpec | None = None
    appendix_chart: ChartSpec | None = None

    if table and table.rows:
        table, appendix_table = _overflow_table_rows(table)
    if chart and chart.categories:
        chart, appendix_chart = _overflow_chart_categories(chart)

    executive = slide.model_copy(update={"table": table, "chart": chart})
    if not appendix_table and not appendix_chart:
        return executive, None

    appendix = apply_template_to_slide(
        SlideContent(
            slide_id=f"appendix_{slide.slide_id}",
            title=f"{slide.title} — Detail",
            subtitle="Appendix",
            layout="compact_table",
            section_label="APPENDIX",
            table=appendix_table,
            chart=appendix_chart if not appendix_table else None,
            bullets=[f"Supporting detail for {slide.title}."],
            footnote="Full export available in data room / BI.",
        )
    )
    return executive, appendix


def inject_appendix_slides(slides: list[SlideContent]) -> list[SlideContent]:
    """Insert appendix slides after their parent executive slide."""
    out: list[SlideContent] = []
    seen_appendix: set[str] = set()
    for slide in slides:
        exec_slide, appendix = split_slide_overflow(slide)
        out.append(exec_slide)
        if appendix and appendix.slide_id not in seen_appendix:
            out.append(appendix)
            seen_appendix.add(appendix.slide_id)
    return out
