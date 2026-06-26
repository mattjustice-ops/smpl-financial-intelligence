"""Fill an existing board PPTX template — roll period labels and inject Claude commentary.

The reference deck (ClarityFP / SMPL Board Review) keeps layout, charts, and visuals.
We update month/quarter labels and replace narrative text blocks per slide.
"""

from __future__ import annotations

import calendar
import io
import json
import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterator

from app.core.config import _BACKEND_ROOT, get_settings
from app.services.commentary.llm_factory import build_commentary_llm_client
from app.services.reporting.export.board_commentary_service import (
    build_all_slide_commentary,
    copilot_context_blob,
)
from app.services.reporting.export.export_sheet_registry import requirements_prompt_block
from app.services.reporting.export.schemas import ReportingBundle

logger = logging.getLogger(__name__)

_REPO_ROOT = _BACKEND_ROOT.parent

# Search order for the gold-standard deck (user-provided template).
_CANONICAL_TEMPLATE_NAME = "SMPL_Board_Review_Template.pptx"
_CANONICAL_TEMPLATE = _BACKEND_ROOT / "templates" / "board" / _CANONICAL_TEMPLATE_NAME
_TEMPLATE_SEARCH_GLOBS: tuple[tuple[Path, str], ...] = (
    (_BACKEND_ROOT / "templates" / "board", "SMPL_Board_Review*.pptx"),
    (_REPO_ROOT / "docs" / "reference-decks", "SMPL_Board_Review*.pptx"),
    (_REPO_ROOT / "frontend" / "public" / "board" / "exports", "SMPL_Board_Review*.pptx"),
)

_ONEDRIVE_TEMPLATE = Path.home() / "OneDrive" / "SMPL_Board_Review_Q2_2026.pptx"


@dataclass(frozen=True)
class TemplateSlideOutline:
    index: int
    title: str
    preview: str


def resolve_board_pptx_template() -> Path | None:
    settings = get_settings()
    explicit = getattr(settings, "board_pptx_template", None)
    if explicit:
        path = Path(explicit)
        if path.is_file():
            logger.info("Board PPTX template (BOARD_PPTX_TEMPLATE): %s", path)
            return path

    if _CANONICAL_TEMPLATE.is_file():
        logger.info("Board PPTX template (canonical): %s", _CANONICAL_TEMPLATE)
        return _CANONICAL_TEMPLATE

    if _ONEDRIVE_TEMPLATE.is_file():
        logger.info("Board PPTX template (OneDrive dev): %s", _ONEDRIVE_TEMPLATE)
        return _ONEDRIVE_TEMPLATE

    best: Path | None = None
    best_slides = 0
    from pptx import Presentation

    for folder, pattern in _TEMPLATE_SEARCH_GLOBS:
        if not folder.is_dir():
            continue
        for candidate in sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                slide_count = len(Presentation(str(candidate)).slides)
            except Exception:
                continue
            if slide_count >= 10 and slide_count >= best_slides:
                best = candidate
                best_slides = slide_count
    if best is not None:
        logger.info("Board PPTX template (glob): %s (%s slides)", best, best_slides)
    return best


def _month_label(period: str) -> str:
    dt = date(int(period[:4]), int(period[5:7]), 1)
    return dt.strftime("%B %Y")


def _prior_month(period: str) -> str:
    year = int(period[:4])
    month = int(period[5:7])
    if month == 1:
        return f"{year - 1}-12"
    return f"{year}-{month - 1:02d}"


def _quarter_label(period: str) -> str:
    month = int(period[5:7])
    quarter = (month - 1) // 3 + 1
    return f"Q{quarter} {period[:4]}"


def _ytd_range_label(period: str) -> str:
    month = int(period[5:7])
    short = calendar.month_abbr[month]
    return f"Jan-{short} {period[:4]}"


def _period_replacements(bundle: ReportingBundle) -> list[tuple[re.Pattern[str], str]]:
    as_of = bundle.as_of_period
    close = _month_label(as_of)
    prior = _month_label(_prior_month(as_of))
    quarter = _quarter_label(as_of)
    ytd = _ytd_range_label(as_of)
    year = as_of[:4]

    patterns: list[tuple[str, str]] = [
        (
            r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+20\d{2}\b",
            close,
        ),
        (r"\bQ[1-4]\s+20\d{2}\b", quarter),
        (r"\bJan-[A-Za-z]{3}\s+20\d{2}\b", ytd),
        (r"\b20\d{2}\s+Q[1-4]\b", f"{year} {quarter.split()[0]}"),
        (r"\bClose:\s*[A-Za-z]+\s+20\d{2}\b", f"Close: {close}"),
        (r"\bClose\s+[A-Za-z]+\s+20\d{2}\b", f"Close {close}"),
    ]
    out: list[tuple[re.Pattern[str], str]] = []
    for pattern, repl in patterns:
        out.append((re.compile(pattern, re.I), repl))
    out.append((re.compile(re.escape(prior), re.I), close))
    return out


def _iter_shapes(shapes) -> Iterator[Any]:
    """Walk slide shapes including grouped children."""
    try:
        from pptx.enum.shapes import MSO_SHAPE_TYPE
    except ImportError:
        MSO_SHAPE_TYPE = None  # type: ignore[assignment,misc]

    for shape in shapes:
        try:
            if MSO_SHAPE_TYPE is not None and getattr(shape, "shape_type", None) == MSO_SHAPE_TYPE.GROUP:
                yield from _iter_shapes(shape.shapes)
                continue
        except Exception:
            pass
        yield shape


def _shape_text(shape) -> str:
    try:
        if not hasattr(shape, "text"):
            return ""
        return (shape.text or "").strip()
    except Exception:
        return ""


def _slide_text_blob(slide) -> str:
    parts = [_shape_text(s) for s in _iter_shapes(slide.shapes) if _shape_text(s)]
    return " ".join(parts)


_EXEC_NAV_LINKS: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (re.compile(r"view\s+waterfall", re.I), ("arr / mrr waterfall", "mrr waterfall", "arr waterfall", "arr roll")),
    (re.compile(r"view\s+driver", re.I), ("driver", "net new arr", "why it happened", "decomposition")),
    (re.compile(r"view\s+p\s*&?\s*l", re.I), ("department spend", "management p&l", "p&l", "income statement")),
    (re.compile(r"view\s+cash", re.I), ("cash forecast", "cash flow", "liquidity", "cash bridge")),
)


def _is_exec_nav_text(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in ("view waterfall", "view driver", "view p&l", "view pl", "view cash")
    )


def _paragraph_has_slide_link(paragraph) -> bool:
    for run in paragraph.runs:
        r_pr = run._r.rPr
        if r_pr is None or r_pr.hlinkClick is None:
            continue
        hlink = r_pr.hlinkClick
        action = (hlink.action or "").lower()
        if "hlinksldjump" in action or hlink.rId:
            return True
    return False


def _shape_has_slide_link(shape) -> bool:
    try:
        from pptx.enum.action import PP_ACTION

        if shape.click_action.action != PP_ACTION.NONE:
            return True
    except Exception:
        pass
    if not hasattr(shape, "text_frame") or shape.text_frame is None:
        return False
    return any(_paragraph_has_slide_link(para) for para in shape.text_frame.paragraphs)


def _is_protected_nav_shape(shape) -> bool:
    text = _shape_text(shape)
    if _is_exec_nav_text(text):
        return True
    return _shape_has_slide_link(shape)


def _slide_keyword_index(prs) -> list[tuple[int, str]]:
    return [(idx, _slide_text_blob(slide).lower()) for idx, slide in enumerate(prs.slides)]


def _find_slide_by_keywords(
    prs,
    keywords: tuple[str, ...],
    *,
    exclude_indices: set[int] | None = None,
) -> int | None:
    exclude = exclude_indices or set()
    best_idx: int | None = None
    best_score = 0
    for idx, blob in _slide_keyword_index(prs):
        if idx in exclude:
            continue
        score = sum(1 for keyword in keywords if keyword in blob)
        if score > best_score:
            best_score = score
            best_idx = idx
    return best_idx if best_score > 0 else None


def _find_executive_summary_slide(prs) -> tuple[Any | None, int | None]:
    best_slide: Any | None = None
    best_idx: int | None = None
    best_score = 0
    for idx, slide in enumerate(prs.slides):
        blob = _slide_text_blob(slide).lower()
        link_hits = sum(1 for pattern, _ in _EXEC_NAV_LINKS if pattern.search(blob))
        score = link_hits
        if "executive" in blob or "operating summary" in blob:
            score += 2
        if "where we stand" in blob:
            score += 1
        if score > best_score:
            best_score = score
            best_slide = slide
            best_idx = idx
    if best_score >= 2:
        return best_slide, best_idx
    return None, None


def _set_run_target_slide(run, target_slide) -> None:
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT

    r_pr = run._r.get_or_add_rPr()
    hlink = r_pr.hlinkClick
    if hlink is not None:
        rid = hlink.rId
        if rid:
            run.part.drop_rel(rid)
        r_pr._remove_hlinkClick()  # pyright: ignore[reportPrivateUsage]
    hlink = r_pr.get_or_add_hlinkClick()
    hlink.action = "ppaction://hlinksldjump"
    hlink.rId = run.part.relate_to(target_slide.part, RT.SLIDE)


def repair_executive_nav_links(prs) -> int:
    """Re-bind executive summary 'View …' links to the correct deck slides."""
    exec_slide, exec_idx = _find_executive_summary_slide(prs)
    if exec_slide is None or exec_idx is None:
        return 0

    exclude = {exec_idx}
    repaired = 0
    for pattern, keywords in _EXEC_NAV_LINKS:
        target_idx = _find_slide_by_keywords(prs, keywords, exclude_indices=exclude)
        if target_idx is None:
            logger.warning("Board PPTX: could not resolve nav target for %s", pattern.pattern)
            continue
        target_slide = prs.slides[target_idx]
        for shape in _iter_shapes(exec_slide.shapes):
            if not hasattr(shape, "text_frame") or shape.text_frame is None:
                continue
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    if not pattern.search(run.text or ""):
                        continue
                    _set_run_target_slide(run, target_slide)
                    repaired += 1
    if repaired:
        logger.info("Board PPTX: repaired %d executive nav hyperlinks", repaired)
    return repaired


def _replace_periods_in_shape(shape, replacements: list[tuple[re.Pattern[str], str]]) -> bool:
    if not hasattr(shape, "text_frame") or shape.text_frame is None:
        return False
    if _is_protected_nav_shape(shape):
        return False

    changed = False
    for paragraph in shape.text_frame.paragraphs:
        if _paragraph_has_slide_link(paragraph):
            continue
        raw = paragraph.text
        if not raw.strip() or _is_exec_nav_text(raw):
            continue
        updated = raw
        for pattern, repl in replacements:
            updated = pattern.sub(repl, updated)
        if updated != raw:
            paragraph.text = updated
            changed = True
    return changed


def _set_shape_text(shape, text: str) -> None:
    if not hasattr(shape, "text_frame") or shape.text_frame is None:
        return
    tf = shape.text_frame
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        if tf.paragraphs:
            tf.paragraphs[0].text = ""
        else:
            shape.text = ""
        return
    for idx, line in enumerate(lines):
        if idx < len(tf.paragraphs):
            tf.paragraphs[idx].text = line
        else:
            tf.add_paragraph().text = line
    for extra in tf.paragraphs[len(lines) :]:
        extra.text = ""


def _commentary_text_from_slide(slide_comm) -> str:
    from app.services.reporting.export.board_api_prompts import format_key_takeaway_bullets

    if slide_comm.bullets:
        formatted = format_key_takeaway_bullets(slide_comm.bullets)
        if formatted.strip():
            return formatted.strip()
    return (slide_comm.what_happened or slide_comm.narrative_block() or "").strip()


# Semantic map: board deck slide_key -> keywords found in template slide text.
_TEMPLATE_SLIDE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "executive_summary": (
        "executive summary",
        "executive operating",
        "operating summary",
        "where we stand",
    ),
    "arr_waterfall": (
        "arr analysis",
        "arr / mrr",
        "mrr waterfall",
        "arr waterfall",
        "arr roll",
        "net new arr",
    ),
    "gaap_revenue": (
        "p&l review",
        "income statement",
        "department spend",
        "gaap revenue",
        "management p&l",
    ),
    "cash_forecast": (
        "cash & liquidity",
        "cash and liquidity",
        "cash forecast",
        "cash flow",
        "liquidity",
        "cash bridge",
    ),
    "gtm_performance": (
        "gtm & marketing",
        "gtm and marketing",
        "marketing efficiency",
        "channel efficiency",
        "gtm performance",
    ),
    "headcount": (
        "workforce",
        "headcount",
        "hiring plan",
        "quota capacity",
    ),
    "risks_opportunities": (
        "risks & opportunities",
        "risks and opportunities",
        "risk / opportunity",
        "key risks",
    ),
}


def map_template_slides_to_slide_keys(prs) -> dict[str, int]:
    """Map board slide_key -> 1-based PPTX slide index using title/body keywords."""
    mapping: dict[str, int] = {}
    used_zero_based: set[int] = set()
    for slide_key, keywords in _TEMPLATE_SLIDE_KEYWORDS.items():
        idx0 = _find_slide_by_keywords(prs, keywords, exclude_indices=used_zero_based)
        if idx0 is None:
            continue
        mapping[slide_key] = idx0 + 1
        used_zero_based.add(idx0)
    return mapping


def _build_template_commentary_updates(
    bundle: ReportingBundle,
    prs,
    *,
    use_ai_commentary: bool,
) -> dict[int, str]:
    """Build commentary text per template slide index (API-spec path when AI enabled)."""
    from app.services.reporting.export.board_commentary_service import (
        build_slide_commentary,
        enrich_slide_with_ai,
    )

    key_to_idx = map_template_slides_to_slide_keys(prs)
    if not key_to_idx:
        logger.warning("Board PPTX: no keyword slide mapping — using outline fallback")
        outline = extract_template_outline(prs)
        return _fallback_commentary_by_slide(bundle, outline, use_ai=use_ai_commentary)

    updates: dict[int, str] = {}
    for slide_key, slide_idx in key_to_idx.items():
        base = build_slide_commentary(bundle, slide_key)
        comm = enrich_slide_with_ai(bundle, slide_key, base) if use_ai_commentary else base
        text = _commentary_text_from_slide(comm)
        if text:
            updates[slide_idx] = text

    logger.info(
        "Board PPTX template commentary: %d slides (%s, ai=%s)",
        len(updates),
        ", ".join(sorted(key_to_idx.keys())),
        use_ai_commentary,
    )
    return updates


def _safe_set_shape_text(shape, text: str) -> bool:
    try:
        _set_shape_text(shape, text)
        return True
    except Exception:
        return False


def roll_template_period_labels(prs, bundle: ReportingBundle) -> int:
    replacements = _period_replacements(bundle)
    changed = 0
    for slide in prs.slides:
        for shape in _iter_shapes(slide.shapes):
            if _replace_periods_in_shape(shape, replacements):
                changed += 1
    return changed


def extract_template_outline(prs) -> list[TemplateSlideOutline]:
    outline: list[TemplateSlideOutline] = []
    for idx, slide in enumerate(prs.slides, start=1):
        texts = [_shape_text(s) for s in _iter_shapes(slide.shapes) if _shape_text(s)]
        title = texts[0][:120] if texts else f"Slide {idx}"
        preview = " | ".join(texts[:3])[:400]
        outline.append(TemplateSlideOutline(index=idx, title=title, preview=preview))
    return outline


def _fallback_commentary_by_slide(
    bundle: ReportingBundle,
    outline: list[TemplateSlideOutline],
    *,
    use_ai: bool,
) -> dict[int, str]:
    """Legacy outline-index fallback when keyword mapping finds no slides."""
    from app.services.reporting.export.board_commentary_service import build_all_slide_commentary

    commentary = build_all_slide_commentary(bundle, use_ai=use_ai)
    slide_keys = list(commentary.keys())
    updates: dict[int, str] = {}
    for i, item in enumerate(outline):
        key = slide_keys[i % len(slide_keys)] if slide_keys else "executive_summary"
        comm = commentary.get(key)
        if not comm:
            continue
        text = _commentary_text_from_slide(comm)
        if text:
            updates[item.index] = text
    return updates


def _generate_claude_template_commentary(
    bundle: ReportingBundle,
    outline: list[TemplateSlideOutline],
) -> dict[int, str]:
    settings = get_settings()
    if not (settings.anthropic_api_key or settings.openai_api_key):
        return {}

    outline_json = [
        {"index": o.index, "title": o.title, "preview": o.preview[:240]} for o in outline
    ]
    try:
        metrics_blob = ""
        try:
            metrics_blob = copilot_context_blob(bundle)[:28000]
        except Exception as exc:
            logger.warning("Template export metrics context failed: %s", exc)

        client = build_commentary_llm_client()
        slide_count = max(len(outline), 1)
        raw = client.generate(
            system_prompt=(
                requirements_prompt_block("mda_deck_pptx")
                + "\n\nYou update an existing board deck template for a new close month. "
                "Keep each slide's purpose aligned to its title. Evidence-only metrics. "
                "Do not remove chart placeholders — only provide narrative commentary text."
            ),
            user_prompt=(
                f"Close: {bundle.period_label} ({bundle.as_of_period}). "
                f"Organization: {bundle.organization_name or 'SMPL'}.\n\n"
                f"Template slides:\n{json.dumps(outline_json, indent=2)}\n\n"
                f"Live metrics:\n{metrics_blob}\n\n"
                'Respond JSON only: {"slides": [{"index": 1, "commentary": "..."}, ...]} '
                "One entry per template slide index. Each commentary 2-4 sentences, board-ready."
            ),
            max_tokens=min(4096, slide_count * 220),
        )
        if not isinstance(raw, dict):
            return {}
        slides = raw.get("slides") or raw.get("slide_commentary") or []
        updates: dict[int, str] = {}
        for block in slides:
            if not isinstance(block, dict):
                continue
            idx = int(block.get("index") or block.get("slide") or 0)
            text = str(block.get("commentary") or block.get("narrative") or "").strip()
            if idx and text:
                updates[idx] = text
        return updates
    except Exception as exc:
        logger.warning("Template Claude commentary failed: %s", exc)
        return {}


def _pick_commentary_shape(slide) -> Any | None:
    candidates: list[tuple[int, Any]] = []
    for shape in _iter_shapes(slide.shapes):
        if _is_protected_nav_shape(shape):
            continue
        text = _shape_text(shape)
        if _is_exec_nav_text(text):
            continue
        if len(text) < 40:
            continue
        score = len(text)
        if any(k in text.lower() for k in ("what changed", "why", "impact", "commentary", "driver")):
            score += 500
        candidates.append((score, shape))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def apply_template_commentary(prs, updates: dict[int, str]) -> int:
    applied = 0
    for idx, commentary in updates.items():
        if idx < 1 or idx > len(prs.slides):
            continue
        slide = prs.slides[idx - 1]
        shape = _pick_commentary_shape(slide)
        if shape is None:
            continue
        existing = _shape_text(shape)
        lines = existing.splitlines()
        header = lines[0].strip() if lines and len(lines[0]) < 80 else ""
        body = commentary.strip()
        if header and header.lower() not in body.lower():
            if _safe_set_shape_text(shape, f"{header}\n{body}"):
                applied += 1
        elif _safe_set_shape_text(shape, body):
            applied += 1
    return applied


def build_pptx_from_template(
    bundle: ReportingBundle,
    *,
    use_ai_commentary: bool = True,
) -> bytes | None:
    """Return filled template bytes, or None if template missing or processing fails."""
    template_path = resolve_board_pptx_template()
    if template_path is None:
        return None

    from pptx import Presentation

    try:
        prs = Presentation(str(template_path))
        roll_template_period_labels(prs, bundle)

        updates = _build_template_commentary_updates(
            bundle,
            prs,
            use_ai_commentary=use_ai_commentary,
        )

        apply_template_commentary(prs, updates)
        repair_executive_nav_links(prs)

        buf = io.BytesIO()
        prs.save(buf)
        logger.info(
            "Board PPTX from template %s (%d slides, %d commentary updates)",
            template_path.name,
            len(prs.slides),
            len(updates),
        )
        return buf.getvalue()
    except Exception as exc:
        logger.exception("Board PPTX template processing failed (%s): %s", template_path, exc)
        return None
