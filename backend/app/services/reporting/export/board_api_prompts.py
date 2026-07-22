"""Static Claude prompts for board deck Key Takeaways (Prompt 1 from SMPL API templates)."""

from __future__ import annotations

import json
import re
from typing import Any

BOARD_DECK_SLIDE_SYSTEM_PROMPT = """You are SMPL's AI financial analyst generating board-level slide commentary for a SaaS company.

COMPANY CONTEXT
Use the company name and stage from the user message payload when provided.
Business model: Annual and monthly SaaS subscriptions, mid-market CFO buyer.
Industry: B2B SaaS — Financial Intelligence Platform.
Primary metrics: ARR, N$R (Net Revenue Retention), G$R (Gross Revenue Retention), EBITDA.

NOMENCLATURE — use exactly these terms, never alternatives
- "N$R" not "NRR", "Net Revenue Retention", or "NDR"
- "G$R" not "GRR", "Gross Revenue Retention", or "Gross Dollar Retention"
- "ARR" not "MRR" (company reports in ARR)
- "Net New ARR" not "Net New MRR"
- "Ending ARR" not "EOP ARR" or "Closing ARR"
- "vs budget" not "vs plan" or "vs target"
- "bps" for basis points (e.g. "+220bps")
- Dollar amounts in $M with 2 decimal places (e.g. "$86.10M")
- Percentages to 1 decimal place (e.g. "79.2%")

OUTPUT FORMAT RULES — CRITICAL
- Generate commentary ONLY for the single slide in the user message
- Return exactly ONE "Key Takeaways" block as a JSON array of bullet strings
- Each bullet must start with "•"
- Respect max_bullets and max_words_per_bullet from the slide object
- No bullet may repeat information from another bullet on the same slide
- Lead with the most important signal, not chronology
- Always include: current period actual, budget, variance ($), and one forward-looking implication when metrics support it
- Reference periods using close_period_label from the payload (current month), QTD, YTD, H2 as appropriate
- Never use the word "significant" — use the actual number instead
- Never start two consecutive bullets with the same word
- Favorable variances: lead with the positive signal
- Unfavorable variances: state the driver and the next-quarter expectation in the same bullet

DO NOT
- Copy or lightly edit prior-month example commentary from templates
- Invent metrics not present in the slide metrics object
- Output slide titles, headers, or markdown fences
- Treat the deck as a layout template — you are writing fresh variance commentary only

BENCHMARKS FOR CONTEXT (use to frame good/concerning signals)
- N$R healthy: >105% | watch: <100%
- G$R healthy: >90% | concern: <87%
- Gross margin healthy: >75% for SaaS at this stage
- EBITDA: company is in investment mode, negative EBITDA is expected
- Cash floor: $10M minimum; headroom >$50M is strong
- Pipeline coverage: 3x+ H2 quota is healthy

TONE
Board-level. Direct. Data-driven. No hedging. No filler phrases like "it is worth noting."
A sentence that does not contain a number is probably not earning its place.
"""

_SINGLE_SLIDE_INSTRUCTIONS = (
    "Generate Key Takeaways bullet points for this slide only. "
    'Return JSON only: {"bullets": ["• ...", ...]}. '
    "Strictly enforce max_bullets and max_words_per_bullet. "
    "Do not include slide titles or headers — only the bullet array."
)


def board_deck_single_slide_user_message(
    payload: dict[str, Any],
    *,
    freeze_context_text: str | None = None,
    freeze_context_as_of: str | None = None,
    freeze_status: str | None = None,
    freeze_stale: bool = False,
) -> str:
    """Serialize the dynamic user message for a single-slide API call."""
    from app.services.reporting.export.freeze_prompt import format_freeze_prompt_block

    freeze_block = format_freeze_prompt_block(
        context_text=freeze_context_text,
        context_as_of=freeze_context_as_of,
        status=freeze_status,
        stale=freeze_stale,
        number_guidance=(
            "Use this freeze for operational drivers and period framing. "
            "Bullet numbers must come from the slide payload JSON only — never invent figures."
        ),
    )
    body = {
        "task": "board_slide_commentary",
        **payload,
        "instructions": _SINGLE_SLIDE_INSTRUCTIONS,
    }
    payload_json = json.dumps(body, indent=2)
    if freeze_block:
        return (
            f"{freeze_block}"
            "SLIDE PAYLOAD (JSON) — primary number source for Key Takeaways:\n"
            f"{payload_json}"
        )
    return payload_json


def parse_board_deck_bullets_response(raw: Any, slide_key: str) -> list[str]:
    """Extract bullet strings from LLM JSON (several response shapes)."""
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]

    if not isinstance(raw, dict):
        return []

    for key in ("bullets", "key_takeaways", "commentary"):
        val = raw.get(key)
        if isinstance(val, list):
            return [str(item).strip() for item in val if str(item).strip()]

    slide_block = raw.get("slide")
    if isinstance(slide_block, dict):
        for key in ("bullets", "key_takeaways"):
            val = slide_block.get(key)
            if isinstance(val, list):
                return [str(item).strip() for item in val if str(item).strip()]

    # Map keyed by slide number string e.g. {"2": ["• ..."]}
    for val in raw.values():
        if isinstance(val, list) and val and isinstance(val[0], str):
            return [str(item).strip() for item in val if str(item).strip()]

    _ = slide_key
    return []


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _clip_bullet_body(body: str, max_chars: int) -> str:
    """Prefer a complete sentence; else last whole word. Ellipsis only as last resort."""
    body = body.strip()
    if max_chars <= 0:
        return ""
    if len(body) <= max_chars:
        return body
    if max_chars <= 2:
        return body[:max_chars]

    # Room for optional ellipsis when we cannot land on a clean sentence end.
    budget = max_chars - 1
    clipped = body[:budget].rstrip()

    # Prefer any complete sentence that is long enough to stand alone as a bullet.
    min_sentence = max(16, int(budget * 0.25))
    for sep in (". ", "; ", "! ", "? "):
        idx = clipped.rfind(sep)
        if idx >= min_sentence:
            return clipped[: idx + 1].strip()

    if clipped.endswith((".", ";", "!", "?")) and len(clipped) >= min_sentence:
        return clipped

    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip(".,;:")
    else:
        clipped = clipped.rstrip(".,;:")
    return clipped + "…"


def validate_and_trim_bullets(
    bullets: list[str],
    *,
    max_bullets: int,
    max_words_per_bullet: int,
    max_chars_per_bullet: int | None = None,
) -> list[str]:
    """Enforce bullet count, word, and character limits.

    Character clipping prefers sentence boundaries so board commentary does not
    end mid-clause with an ellipsis whenever a complete sentence fits the cap.
    """
    trimmed: list[str] = []
    for bullet in bullets[:max_bullets]:
        text = bullet.strip()
        if not text:
            continue
        if not text.startswith("•"):
            text = f"• {text.lstrip('-• ')}"
        words = text.lstrip("•").strip().split()
        if len(words) > max_words_per_bullet:
            # Prefer ending on a sentence within the word budget when possible.
            kept = words[:max_words_per_bullet]
            joined = " ".join(kept)
            for sep in (". ", "; ", "! ", "? "):
                idx = joined.rfind(sep)
                if idx >= 24:
                    joined = joined[: idx + 1].strip()
                    break
            text = "• " + joined
        if max_chars_per_bullet is not None and len(text) > max_chars_per_bullet:
            body = text.lstrip("•").strip()
            text = "• " + _clip_bullet_body(body, max_chars_per_bullet - 2)
        trimmed.append(text)
    return trimmed


def format_key_takeaway_bullets(bullets: list[str]) -> str:
    """Join bullets for HTML/PPTX text boxes."""
    lines: list[str] = []
    for bullet in bullets:
        text = bullet.strip()
        if not text:
            continue
        if not text.startswith("•"):
            text = f"• {text.lstrip('-• ')}"
        lines.append(text)
    return "\n".join(lines)
