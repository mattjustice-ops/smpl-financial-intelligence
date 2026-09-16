"""Non-numeric commentary fidelity checks (story quality, not $/%).

Complements claim_verify (numbers) and attribution_verify (causal drivers).
Catches filler, placeholders, directional language that fights the stated
variance sign, and closed-period scenario mislabels.

Policy:
  - ``strict`` (Prompt 2): soft-strip filler/placeholder clauses; warn on
    direction/scenario/structure; hard-block only when every variance cell is
    emptied after strip (caller decides).
  - ``interactive`` / Prompt 5: verify + warn/log; soft-strip filler/placeholder
    only; keep directional prose for human review (log issues).

See docs/soc2/controls/ai_claim_verify.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from app.services.commentary.claim_verify import (
    VerifyPolicy,
    extract_js_string_literal_text,
    extract_numeric_claims,
    split_sentences,
)

NarrativeIssueKind = Literal[
    "filler",
    "placeholder",
    "direction",
    "scenario",
    "structure",
]


# Board-forbidden filler — Prompt 5 craft criteria already bans "significant".
_FILLER_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsignificant(?:ly)?\b", re.IGNORECASE),
    re.compile(r"\bit is worth noting\b", re.IGNORECASE),
    re.compile(r"\bas (?:previously |already )?mentioned\b", re.IGNORECASE),
    re.compile(r"\bin conclusion\b", re.IGNORECASE),
    re.compile(r"\bneedless to say\b", re.IGNORECASE),
)

_PLACEHOLDER_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bTBD\b"),
    re.compile(r"\bTODO\b"),
    re.compile(r"\bFIXME\b"),
    re.compile(r"\blorem ipsum\b", re.IGNORECASE),
    re.compile(r"\[\s*(?:insert|placeholder|metric|number|text)[^\]]*\]", re.IGNORECASE),
    re.compile(r"\{\{[^{}]+\}\}"),
    re.compile(r"^\s*[—–\-_]{1,3}\s*$"),
)

_BEAT_RE = re.compile(
    r"\b(?:beat|above|ahead of|exceeded|outperformed|favorable(?:ly)?)\b",
    re.IGNORECASE,
)
_MISS_RE = re.compile(
    r"\b(?:missed|below|short of|behind|underperformed|unfavorable(?:ly)?)\b",
    re.IGNORECASE,
)
_BUDGET_CTX_RE = re.compile(r"\b(?:budget|plan|target)\b", re.IGNORECASE)

_FORECAST_LABEL_RE = re.compile(r"\bforecast\b", re.IGNORECASE)
_ACTUAL_LABEL_RE = re.compile(r"\bactuals?\b", re.IGNORECASE)
_PERIOD_TOKEN_RE = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\b|\b20\d{2}-\d{2}\b",
    re.IGNORECASE,
)

# Stub takeaways / variance cells — too thin for board narrative depth.
_STUB_MAX_WORDS = 8


@dataclass(frozen=True)
class NarrativeIssue:
    kind: NarrativeIssueKind
    excerpt: str
    detail: str


@dataclass
class NarrativeVerificationResult:
    issues: list[NarrativeIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def summary(self, *, max_issues: int = 8) -> str:
        if self.ok:
            return "all narrative checks passed"
        parts = [f"{i.kind}: {i.detail}" for i in self.issues[: max(0, max_issues)]]
        body = "; ".join(parts)
        n = len(self.issues)
        if n > max_issues > 0:
            body += f"; …+{n - max_issues} more"
        return f"{n} narrative issue(s): {body}"

    @property
    def filler_or_placeholder(self) -> list[NarrativeIssue]:
        return [i for i in self.issues if i.kind in ("filler", "placeholder")]


def _clip(text: str, n: int = 96) -> str:
    t = " ".join((text or "").split())
    return t if len(t) <= n else t[: n - 1] + "…"


def _month_name(period: str) -> str | None:
    """Map YYYY-MM → english month token used in prose."""
    try:
        month = int(period.split("-")[1])
    except (IndexError, ValueError):
        return None
    names = (
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    )
    if 1 <= month <= 12:
        return names[month - 1]
    return None


def verify_narrative_text(
    text: str,
    *,
    close_period: str | None = None,
    require_min_words: int | None = None,
) -> NarrativeVerificationResult:
    """Scan a single narrative string for non-numeric fidelity issues."""
    issues: list[NarrativeIssue] = []
    raw = text or ""
    if not raw.strip():
        return NarrativeVerificationResult(issues=issues)

    for pat in _PLACEHOLDER_RES:
        if pat.search(raw):
            issues.append(
                NarrativeIssue(
                    kind="placeholder",
                    excerpt=_clip(raw),
                    detail=f"placeholder/empty pattern matched ({pat.pattern})",
                )
            )
            break

    for pat in _FILLER_RES:
        m = pat.search(raw)
        if m:
            issues.append(
                NarrativeIssue(
                    kind="filler",
                    excerpt=_clip(raw),
                    detail=f"forbidden filler '{m.group(0)}'",
                )
            )

    if require_min_words is not None:
        words = re.findall(r"[A-Za-z0-9]+", raw)
        if 0 < len(words) < require_min_words and not re.match(
            r"^[\s\$\(\+\-–—\d\.,%xXMmKkBb]*$", raw.strip()
        ):
            issues.append(
                NarrativeIssue(
                    kind="structure",
                    excerpt=_clip(raw),
                    detail=f"stub narrative ({len(words)} words; want ≥{require_min_words})",
                )
            )

    for sentence in split_sentences(raw):
        issues.extend(_direction_issues(sentence))
        if close_period:
            issues.extend(_scenario_issues(sentence, close_period))

    return NarrativeVerificationResult(issues=issues)


def _direction_issues(sentence: str) -> list[NarrativeIssue]:
    """Flag beat/miss language that fights the sign of money claims in-sentence."""
    if not _BUDGET_CTX_RE.search(sentence):
        return []
    beat = bool(_BEAT_RE.search(sentence))
    miss = bool(_MISS_RE.search(sentence))
    if beat == miss:
        return []
    money = [c for c in extract_numeric_claims(sentence) if c.kind == "money"]
    if not money:
        return []
    # Prefer explicitly signed claims (variance cells / "+$0.4M" / "-$1.2M").
    signed = [c for c in money if c.stated.strip()[:1] in "+-" or c.value < 0]
    if not signed:
        return []
    if beat and all(c.value < 0 for c in signed):
        return [
            NarrativeIssue(
                kind="direction",
                excerpt=_clip(sentence),
                detail="favorable/beat language with negative signed variance",
            )
        ]
    if miss and all(c.value > 0 for c in signed):
        return [
            NarrativeIssue(
                kind="direction",
                excerpt=_clip(sentence),
                detail="unfavorable/miss language with positive signed variance",
            )
        ]
    return []


def _scenario_issues(sentence: str, close_period: str) -> list[NarrativeIssue]:
    """Closed month named as Forecast (without Actual) is a mislabel."""
    if not _FORECAST_LABEL_RE.search(sentence):
        return []
    if _ACTUAL_LABEL_RE.search(sentence):
        return []
    month = _month_name(close_period)
    period_hit = close_period in sentence
    month_hit = bool(month and re.search(rf"\b{month}\b", sentence, re.IGNORECASE))
    if not (period_hit or month_hit):
        return []
    # "June Forecast" for a June close is wrong; "H2 Forecast" without June is ok.
    if not _PERIOD_TOKEN_RE.search(sentence) and not period_hit:
        return []
    return [
        NarrativeIssue(
            kind="scenario",
            excerpt=_clip(sentence),
            detail=f"closed period {close_period} labeled Forecast without Actual",
        )
    ]


def soft_strip_filler_and_placeholders(text: str) -> str:
    """Remove sentences that trip filler/placeholder checks; keep the rest."""
    if not (text or "").strip():
        return text
    kept: list[str] = []
    for sentence in split_sentences(text):
        local = verify_narrative_text(sentence)
        if any(i.kind in ("filler", "placeholder") for i in local.issues):
            continue
        kept.append(sentence.strip())
    return " ".join(kept).strip()


def verify_nested_commentary_narrative(
    commentary: Mapping[str, Any] | dict[str, Any],
    *,
    close_period: str | None = None,
    policy: VerifyPolicy = "strict",
    strip: bool = True,
) -> tuple[dict[str, Any], NarrativeVerificationResult]:
    """Walk nested commentary strings; optionally soft-strip filler/placeholders."""
    issues: list[NarrativeIssue] = []

    def _walk(node: Any) -> Any:
        if isinstance(node, dict):
            return {k: _walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_walk(v) for v in node]
        if isinstance(node, str):
            # Nested MD&A cells: filler/placeholder/direction/scenario only.
            # Stub-word structure is enforced on Prompt 5 takeaway literals, not Excel cells.
            result = verify_narrative_text(node, close_period=close_period)
            issues.extend(result.issues)
            if strip and result.filler_or_placeholder:
                return soft_strip_filler_and_placeholders(node)
            return node
        return node

    rewritten = _walk(dict(commentary))
    _ = policy  # reserved for future hard-block thresholds
    return rewritten, NarrativeVerificationResult(issues=issues)


def verify_pptx_script_narrative(
    script: str,
    *,
    close_period: str | None = None,
) -> NarrativeVerificationResult:
    """Non-numeric checks on PPTX GenJS string literals (pre-render)."""
    display = extract_js_string_literal_text(script)
    # Split on common bullet / cell boundaries so one bad cell does not smear.
    chunks = re.split(r"[\n|]+|(?<=[.!?])\s+", display)
    issues: list[NarrativeIssue] = []
    for chunk in chunks:
        if not chunk or not chunk.strip():
            continue
        # Skip pure metric cells for stub-word checks.
        is_metricish = len(re.findall(r"[A-Za-z]+", chunk)) < 2
        local = verify_narrative_text(
            chunk,
            close_period=close_period,
            require_min_words=None if is_metricish else _STUB_MAX_WORDS,
        )
        issues.extend(local.issues)
    return NarrativeVerificationResult(issues=issues)


def apply_narrative_soft_strip_to_pptx_script(
    script: str,
    *,
    close_period: str | None = None,
) -> tuple[str, NarrativeVerificationResult]:
    """Soft-strip filler/placeholder inside JS string literals; keep other issues as warn."""
    from app.services.commentary.claim_verify import _pptx_is_narrative_literal

    issues: list[NarrativeIssue] = []
    pattern = re.compile(r"(['\"])((?:\\.|(?!\1).)*)\1")

    def _replace(match: re.Match[str]) -> str:
        quote = match.group(1)
        inner = match.group(2)
        inner_unesc = (
            inner.replace(r"\'", "'")
            .replace(r'\"', '"')
            .replace(r"\n", "\n")
            .replace(r"\t", "\t")
        )
        if not _pptx_is_narrative_literal(inner_unesc):
            return match.group(0)
        local = verify_narrative_text(inner_unesc, close_period=close_period)
        issues.extend(local.issues)
        if not local.filler_or_placeholder:
            return match.group(0)
        cleaned = soft_strip_filler_and_placeholders(inner_unesc)
        if not cleaned:
            cleaned = "—"
        escaped = (
            cleaned.replace("\\", "\\\\")
            .replace(quote, f"\\{quote}")
            .replace("\n", "\\n")
            .replace("\t", "\\t")
        )
        return f"{quote}{escaped}{quote}"

    rewritten = pattern.sub(_replace, script)
    return rewritten, NarrativeVerificationResult(issues=issues)


def evidence_close_period(payload: Mapping[str, Any] | None) -> str | None:
    if not payload:
        return None
    ctx = payload.get("period_context") if isinstance(payload, Mapping) else None
    if isinstance(ctx, Mapping):
        for key in ("close_period", "as_of_period", "period"):
            val = ctx.get(key)
            if val:
                return str(val)[:7]
    for key in ("close_period", "as_of_period", "close_period_label"):
        val = payload.get(key) if isinstance(payload, Mapping) else None
        if val and re.match(r"^\d{4}-\d{2}", str(val)):
            return str(val)[:7]
    return None
