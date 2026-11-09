"""Keep Copilot answers in three separate sections.

The model sometimes emits markdown headings and skips a section. The reply
the person sees always has all three parts, in order.
"""

from __future__ import annotations

import re

COPILOT_SECTION_MISSING = "This part could not be stated from the close."

_TITLES = (
    "1. Primary Driver + Variance Context",
    "2. Financial and Operational Root Cause",
    "3. Recommended Action + Board Summary",
)

_HEADER_RES = (
    re.compile(
        r"(?:^|\n)\s*#*\s*1[\.\)]\s*primary driver\s*\+\s*variance context\s*:?\s*",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|\n)\s*#*\s*2[\.\)]\s*financial and operational root cause\s*:?\s*",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|\n)\s*#*\s*3[\.\)]\s*recommended action\s*\+\s*board summary\s*:?\s*",
        re.IGNORECASE,
    ),
)

_EVIDENCE_KEY_RE = re.compile(
    r"\s*\((?:ts|bundle|blob|cash_bridge|mrr_waterfall|arr_waterfall)\.[^)]+\)"
)


def _clean_body(text: str) -> str:
    cleaned = _EVIDENCE_KEY_RE.sub("", text or "")
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r" +\n", "\n", cleaned)
    return cleaned.strip()


def split_copilot_sections(text: str) -> tuple[str, str, str]:
    """Pull the three bodies out of a single answer string."""
    raw = text or ""
    hits: list[tuple[int, int, int]] = []
    for num, pat in enumerate(_HEADER_RES, start=1):
        match = pat.search(raw)
        if match:
            hits.append((match.start(), match.end(), num))
    hits.sort()
    bodies = {1: "", 2: "", 3: ""}
    for index, (_start, end, num) in enumerate(hits):
        nxt = hits[index + 1][0] if index + 1 < len(hits) else len(raw)
        bodies[num] = _clean_body(raw[end:nxt])
    return bodies[1], bodies[2], bodies[3]


def assemble_copilot_answer(primary: str, cause: str, action: str) -> str:
    """Three labeled blocks. An empty block says the close did not support it."""
    bodies = (
        _clean_body(primary) or COPILOT_SECTION_MISSING,
        _clean_body(cause) or COPILOT_SECTION_MISSING,
        _clean_body(action) or COPILOT_SECTION_MISSING,
    )
    return "\n\n".join(f"{title}\n{body}" for title, body in zip(_TITLES, bodies, strict=True))


def sections_from_model(raw: dict) -> tuple[str, str, str]:
    """Prefer the three JSON fields. Fall back to splitting one answer string."""

    def pick(*keys: str) -> str:
        for key in keys:
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    primary = pick("primary_driver", "primary")
    cause = pick("root_cause", "cause")
    action = pick("recommended_action", "action")
    if primary or cause or action:
        return primary, cause, action
    answer = raw.get("answer") or raw.get("response") or ""
    if not isinstance(answer, str):
        answer = ""
    return split_copilot_sections(answer)
