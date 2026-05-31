"""Emit a Google Slides API `presentations.batchUpdate` request list.

The returned list of dicts can be POSTed verbatim as the `requests` field of
https://developers.google.com/slides/api/reference/rest/v1/presentations/batchUpdate

Charts are not natively created via batchUpdate (they're embedded from Sheets).
For each chart in the canonical package we emit a text placeholder like
"[chart: <title>]" so the slide structure stays faithful and the caller can
swap it for a real embedded chart later.
"""

from __future__ import annotations

from typing import Any

from app.services.board_package.schemas import BoardPackage, SlideContent, TableSpec


def _object_id(prefix: str, index: int, suffix: str = "") -> str:
    base = f"{prefix}_{index}"
    return f"{base}_{suffix}" if suffix else base


def _create_slide_request(object_id: str, layout: str = "BLANK") -> dict[str, Any]:
    return {
        "createSlide": {
            "objectId": object_id,
            "slideLayoutReference": {"predefinedLayout": layout},
        }
    }


def _create_text_box_request(
    object_id: str,
    page_id: str,
    *,
    x_emu: int,
    y_emu: int,
    width_emu: int,
    height_emu: int,
) -> dict[str, Any]:
    return {
        "createShape": {
            "objectId": object_id,
            "shapeType": "TEXT_BOX",
            "elementProperties": {
                "pageObjectId": page_id,
                "size": {
                    "width": {"magnitude": width_emu, "unit": "EMU"},
                    "height": {"magnitude": height_emu, "unit": "EMU"},
                },
                "transform": {
                    "scaleX": 1,
                    "scaleY": 1,
                    "translateX": x_emu,
                    "translateY": y_emu,
                    "unit": "EMU",
                },
            },
        }
    }


def _insert_text_request(object_id: str, text: str) -> dict[str, Any]:
    return {"insertText": {"objectId": object_id, "text": text}}


def _create_table_request(
    object_id: str, page_id: str, rows: int, cols: int
) -> dict[str, Any]:
    return {
        "createTable": {
            "objectId": object_id,
            "elementProperties": {"pageObjectId": page_id},
            "rows": rows,
            "columns": cols,
        }
    }


def _insert_table_cell_text_request(
    table_object_id: str, row: int, col: int, text: str
) -> dict[str, Any]:
    return {
        "insertText": {
            "objectId": table_object_id,
            "cellLocation": {"rowIndex": row, "columnIndex": col},
            "text": text,
        }
    }


# EMU constants for a 10-inch wide / 5.6-inch tall slide region (Google's default).
INCH_EMU = 914400
SLIDE_LEFT = int(0.5 * INCH_EMU)
SLIDE_RIGHT = int(9.5 * INCH_EMU)
SLIDE_WIDTH = SLIDE_RIGHT - SLIDE_LEFT
TITLE_TOP = int(0.3 * INCH_EMU)
TITLE_HEIGHT = int(0.7 * INCH_EMU)
BODY_TOP = int(1.2 * INCH_EMU)
BODY_HEIGHT = int(4.0 * INCH_EMU)


def _slide_to_requests(slide_index: int, slide: SlideContent) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    page_id = _object_id("slide", slide_index)

    requests.append(_create_slide_request(page_id))

    # Title text box
    title_id = _object_id("slide", slide_index, "title")
    requests.append(
        _create_text_box_request(
            title_id,
            page_id,
            x_emu=SLIDE_LEFT,
            y_emu=TITLE_TOP,
            width_emu=SLIDE_WIDTH,
            height_emu=TITLE_HEIGHT,
        )
    )
    title_text = slide.title
    if slide.subtitle:
        title_text = f"{slide.title}\n{slide.subtitle}"
    requests.append(_insert_text_request(title_id, title_text))

    # Body text box (narrative + bullets + chart placeholder)
    body_lines: list[str] = []
    if slide.narrative:
        body_lines.append(slide.narrative)
        body_lines.append("")
    body_lines.extend(f"• {b}" for b in slide.bullets if b)
    if slide.chart:
        body_lines.append("")
        body_lines.append(f"[chart: {slide.chart.title}]")
    if slide.footnote:
        body_lines.append("")
        body_lines.append(slide.footnote)

    if body_lines:
        body_id = _object_id("slide", slide_index, "body")
        body_height = BODY_HEIGHT if slide.table is None else int(BODY_HEIGHT / 2)
        requests.append(
            _create_text_box_request(
                body_id,
                page_id,
                x_emu=SLIDE_LEFT,
                y_emu=BODY_TOP,
                width_emu=SLIDE_WIDTH,
                height_emu=body_height,
            )
        )
        requests.append(_insert_text_request(body_id, "\n".join(body_lines)))

    # Table
    if slide.table:
        table_top = BODY_TOP + (int(BODY_HEIGHT / 2) if body_lines else 0)
        table_id = _object_id("slide", slide_index, "table")
        rows = len(slide.table.rows) + 1
        cols = len(slide.table.headers)
        requests.append(_create_table_request(table_id, page_id, rows, cols))
        for c, header in enumerate(slide.table.headers):
            requests.append(_insert_table_cell_text_request(table_id, 0, c, header))
        for r, row in enumerate(slide.table.rows, start=1):
            for c, value in enumerate(row):
                requests.append(
                    _insert_table_cell_text_request(table_id, r, c, str(value))
                )

    return requests


def to_google_slides_requests(package: BoardPackage) -> dict[str, Any]:
    """Convert a `BoardPackage` to a Google Slides API batchUpdate payload.

    The returned dict has shape::

        {
            "presentation_title": "<org> — Board Package — <period>",
            "requests": [ ... ]
        }

    A caller would create a blank presentation, then POST `requests` to
    presentations.batchUpdate.
    """
    presentation_title = (
        f"{package.organization_name} — Board Package — {package.period_label}"
    )

    requests: list[dict[str, Any]] = []

    # Cover slide
    cover_page = "cover"
    requests.append(_create_slide_request(cover_page, layout="TITLE"))
    cover_title_id = "cover_title"
    requests.append(
        _create_text_box_request(
            cover_title_id,
            cover_page,
            x_emu=SLIDE_LEFT,
            y_emu=int(2.5 * INCH_EMU),
            width_emu=SLIDE_WIDTH,
            height_emu=int(1.2 * INCH_EMU),
        )
    )
    requests.append(
        _insert_text_request(
            cover_title_id, f"{package.organization_name} — Board Package"
        )
    )
    cover_sub_id = "cover_subtitle"
    requests.append(
        _create_text_box_request(
            cover_sub_id,
            cover_page,
            x_emu=SLIDE_LEFT,
            y_emu=int(3.8 * INCH_EMU),
            width_emu=SLIDE_WIDTH,
            height_emu=int(0.6 * INCH_EMU),
        )
    )
    requests.append(
        _insert_text_request(
            cover_sub_id,
            f"{package.period_label}  |  {package.prepared_for}  |  "
            f"{package.prepared_date.isoformat()}",
        )
    )

    for idx, slide in enumerate(package.slides, start=1):
        requests.extend(_slide_to_requests(idx, slide))

    return {"presentation_title": presentation_title, "requests": requests}
