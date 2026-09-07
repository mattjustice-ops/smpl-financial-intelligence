"""Post-render layout repair for the Claude-authored MD&A deck.

Prompt 5 has Claude emit a PptxGenJS script, so every shape coordinate is model output.
The Key Takeaways block is a stack of full-width text boxes on a fixed pitch, and the
boxes are declared far taller than the text they hold — roughly 0.55" of box for 0.20"
of type. Three bullets on that pitch walk off the bottom of the slide: in the June-2026
deck the last ARR bullet sat at 7.45" on a 7.5" slide, invisible, with the one above it
printed through the footer.

This runs on the rendered file, so it holds whatever the model emits. It re-pitches an
overflowing stack onto the height its text actually needs, keeping the block's starting
position and font size. Anything that still will not fit is reported rather than
quietly overlapped.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field

from pptx import Presentation
from pptx.util import Emu, Pt

logger = logging.getLogger(__name__)

EMU_PER_INCH = 914400

# Footers on this deck sit at ~7.05"; body content must clear them.
SAFE_BOTTOM_IN = 7.02
MIN_GAP_IN = 0.06
TIGHT_GAP_IN = 0.03
# Padding inside a text box, on top of the wrapped line height.
BOX_PADDING_IN = 0.06
DEFAULT_FONT_PT = 8.5
# Below this, body text stops being legible on a projector.
MIN_FONT_PT = 7.0

_FOOTER_RE = re.compile(r"CONFIDENTIAL|Board Operating Review|\b\d{1,2}\s*/\s*\d{1,2}\b", re.I)


@dataclass
class LayoutRepairReport:
    moved: list[str] = field(default_factory=list)
    unfixable: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.moved)

    def summary(self) -> str:
        return f"{len(self.moved)} re-pitched, {len(self.unfixable)} unfixable"


def _bounds_in(shape) -> tuple[float, float, float, float] | None:
    if None in (shape.left, shape.top, shape.width, shape.height):
        return None
    left = shape.left / EMU_PER_INCH
    top = shape.top / EMU_PER_INCH
    return left, top, left + shape.width / EMU_PER_INCH, top + shape.height / EMU_PER_INCH


def _font_pt(shape) -> float:
    for para in shape.text_frame.paragraphs:
        for run in para.runs:
            if run.font.size is not None:
                return float(run.font.size.pt)
    return DEFAULT_FONT_PT


def _text_height_in(text: str, width_in: float, font_pt: float) -> float:
    """Height the wrapped text actually needs, as opposed to the box it was given."""
    if width_in <= 0 or font_pt <= 0:
        return 0.0
    # Average glyph advance runs about half the point size for this deck's body face.
    chars_per_line = max(1.0, width_in * 144.0 / font_pt)
    lines = max(1, int(len(text) / chars_per_line) + (1 if len(text) % chars_per_line else 0))
    line_height = 1.25 * font_pt / 72.0
    return lines * line_height + BOX_PADDING_IN


def _set_font(shape, pt: float) -> None:
    for para in shape.text_frame.paragraphs:
        for run in para.runs:
            run.font.size = Pt(round(pt, 1))


def _is_footer(shape, text: str, slide_h: float) -> bool:
    box = _bounds_in(shape)
    if box is None:
        return False
    return bool(_FOOTER_RE.search(text)) and box[1] > slide_h - 0.9


def repair_deck_layout(pptx_bytes: bytes) -> tuple[bytes, LayoutRepairReport]:
    """Re-pitch overflowing commentary stacks into the safe area. Returns (bytes, report)."""
    report = LayoutRepairReport()
    try:
        prs = Presentation(io.BytesIO(pptx_bytes))
    except Exception as exc:  # a corrupt deck is the renderer's problem, not ours
        logger.warning("Deck layout repair skipped, could not open presentation: %s", exc)
        return pptx_bytes, report

    slide_h = prs.slide_height / EMU_PER_INCH
    safe_bottom = min(SAFE_BOTTOM_IN, slide_h - 0.05)

    for idx, slide in enumerate(prs.slides, start=1):
        body = []
        for shape in slide.shapes:
            box = _bounds_in(shape)
            if box is None or not shape.has_text_frame:
                continue
            text = shape.text_frame.text.strip()
            if not text or _is_footer(shape, text, slide_h):
                continue
            body.append((box, shape, text))

        overflowing = [e for e in body if e[0][3] > safe_bottom + 0.01]
        if not overflowing:
            continue

        # Re-pitch the whole column the overflow belongs to, not just the tail — the
        # spacing is what is wrong, so the run has to be rebuilt from its first box.
        left_edge = min(e[0][0] for e in overflowing)
        width = max(e[0][2] - e[0][0] for e in overflowing)
        run = [
            e for e in body
            if abs(e[0][0] - left_edge) < 0.05 and abs((e[0][2] - e[0][0]) - width) < 0.05
        ]
        run.sort(key=lambda e: e[0][1])
        if len(run) < 2:
            report.unfixable.append(
                f"slide {idx}: lone box past the safe area, no stack to re-pitch "
                f"({overflowing[0][2][:40]!r})"
            )
            continue

        start_top = run[0][0][1]
        available = safe_bottom - start_top

        # Try the least invasive fit first: natural height on a normal gap. Then tighten
        # the gap, and only then step the type down. Shrinking font is last because it is
        # the one change a reader can see.
        fit = None
        for gap in (MIN_GAP_IN, TIGHT_GAP_IN):
            for scale in (1.0, 0.92, 0.85):
                fonts = [max(MIN_FONT_PT, _font_pt(shape) * scale) for _, shape, _ in run]
                if scale < 1.0 and all(f <= MIN_FONT_PT for f in fonts):
                    continue
                heights = [
                    _text_height_in(text, box[2] - box[0], font)
                    for (box, _, text), font in zip(run, fonts)
                ]
                if sum(heights) + gap * (len(run) - 1) <= available + 0.01:
                    fit = (gap, scale, fonts, heights)
                    break
            if fit:
                break

        if fit is None:
            natural = sum(
                _text_height_in(text, box[2] - box[0], _font_pt(shape)) for box, shape, text in run
            ) + MIN_GAP_IN * (len(run) - 1)
            report.unfixable.append(
                f"slide {idx}: commentary needs {natural:.2f}\" below {start_top:.2f}\" but only "
                f"{available:.2f}\" is clear of the footer"
            )
            continue

        gap, scale, fonts, heights = fit
        cursor = start_top
        for (box, shape, text), height, font in zip(run, heights, fonts):
            if abs(cursor - box[1]) > 0.01 or abs(height - (box[3] - box[1])) > 0.01:
                shape.top = Emu(int(round(cursor * EMU_PER_INCH)))
                shape.height = Emu(int(round(height * EMU_PER_INCH)))
                if scale < 1.0:
                    _set_font(shape, font)
                report.moved.append(
                    f"slide {idx}: {text[:44]!r} {box[1]:.2f}-{box[3]:.2f}\" -> "
                    f"{cursor:.2f}-{cursor + height:.2f}\""
                    + (f" @{font:.1f}pt" if scale < 1.0 else "")
                )
            cursor += height + gap

    if not report.changed:
        return pptx_bytes, report

    buf = io.BytesIO()
    prs.save(buf)
    logger.warning("Deck layout repair: %s", report.summary())
    return buf.getvalue(), report
