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
_FINANCE_WORD_RE = re.compile(
    r"\b(?:arr|mrr|revenue|cash|pipeline|gtm|ebitda|headcount|churn|budget|forecast|margin|customer|customers|logo|logos|nrr|grr)\b",
    re.IGNORECASE,
)
_CASUAL_EXACT = {
    "hi",
    "hello",
    "hey",
    "how are you",
    "how are you doing",
    "howre you",
    "how're you",
    "how's it going",
    "hows it going",
    "what's up",
    "whats up",
    "good morning",
    "good afternoon",
    "thanks",
    "thank you",
    "who are you",
    "what can you do",
    "help",
}


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


def is_casual_question(question: str) -> bool:
    """A greeting or other non-finance question. Finance words keep the three sections."""
    if _FINANCE_WORD_RE.search(question or ""):
        return False
    q = re.sub(r"\s+", " ", (question or "").strip().lower())
    q = q.strip(" ?!.,")
    if not q or len(q) > 60:
        return False
    if q in _CASUAL_EXACT:
        return True
    return bool(
        re.match(r"^(?:hi|hello|hey|how are you|how're you|what can you|who are you)\b", q)
    )


def wants_conversation(raw: dict, question: str) -> bool:
    """Three sections are for a question about the books. Anything else is one reply."""
    if is_casual_question(question):
        return True
    mode = str(raw.get("mode") or "").strip().lower()
    if mode == "analysis":
        return False
    return mode == "conversation"


def conversation_reply(raw: dict) -> str:
    value = raw.get("reply")
    if isinstance(value, str):
        return _clean_body(value)
    return ""


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
