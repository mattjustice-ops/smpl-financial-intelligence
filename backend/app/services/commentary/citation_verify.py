"""P15 citation verify — material claims should cite ``_sources``.

Runs after numeric claim_verify / attribution_verify. Accepted citation formats
(framework Part 1 + evidence_package policy):

  $110,000 (mrr_waterfall.ending_mrr)
  $86.1M (arr_waterfall.ending_arr, period 2026-06)
  $7.4M (income_statement.revenue)
  citations[].label = evidence key / table.column / formula_id / path

``strict`` (Prompt 2 / Prompt 5): missing or unknown citation → don't-know / omit.
``interactive`` (board regenerate, Copilot, commentary generate): verify + warn;
do not replace whole answers for missing cites alone — board numbers are trusted.
See docs/soc2/controls/ai_claim_verify.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence

from app.services.commentary.claim_verify import VerifyPolicy, extract_numeric_claims
from app.services.commentary.schemas import CommentaryOutput

CitationStatus = Literal["pass", "missing_citation", "unknown_source", "empty_sources"]

DONT_KNOW_CITATION = (
    "I don't know — one or more material numeric claims in this section were stated "
    "without a verifiable _sources citation for the current package. Unsupported "
    "claims were omitted."
)

_INLINE_CITATION_RE = re.compile(r"\(([^)]{2,160})\)|\[([^\]\[]{2,160})\]")
_PERIOD_CLAUSE_RE = re.compile(
    r",?\s*period\s+[0-9]{4}-[0-9]{2}\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CitationClaim:
    stated: str
    claim_kind: str
    sentence: str


@dataclass(frozen=True)
class CitationCheck:
    claim: CitationClaim
    status: CitationStatus
    cited_token: str | None = None


@dataclass
class CitationVerificationResult:
    checks: list[CitationCheck] = field(default_factory=list)
    sources_size: int = 0

    @property
    def ok(self) -> bool:
        return not self.failures

    @property
    def failures(self) -> list[CitationCheck]:
        return [c for c in self.checks if c.status != "pass"]

    def summary(self, *, max_failures: int = 8) -> str:
        if self.ok:
            if not self.checks:
                return "no material numeric claims requiring citation"
            return "all material numeric claims cited against _sources"
        failures = self.failures
        n = len(failures)
        parts = [
            f"{c.claim.stated!r} ({c.status}"
            + (f", cited={c.cited_token}" if c.cited_token else "")
            + ")"
            for c in failures[: max(0, max_failures)]
        ]
        body = "; ".join(parts)
        if n > max_failures > 0:
            body += f"; …+{n - max_failures} more"
        return f"{n} failed citation(s): {body}"


def _normalize_cite_token(token: str) -> str:
    text = re.sub(r"\s+", " ", (token or "").strip().lower())
    text = _PERIOD_CLAUSE_RE.sub("", text).strip(" ,;")
    text = text.replace("source:", "").replace("sources:", "").strip()
    return text


def _leaf_field(key: str) -> str:
    leaf = str(key).rsplit(".", 1)[-1]
    return leaf.split("[", 1)[0].strip()


def citable_tokens_from_sources(sources: Mapping[str, Any] | None) -> set[str]:
    """Tokens that count as a valid citation for a ``_sources`` entry."""
    out: set[str] = set()
    if not isinstance(sources, Mapping):
        return out
    for key, meta in sources.items():
        key_n = _normalize_cite_token(str(key))
        if key_n:
            out.add(key_n)
            leaf = _leaf_field(str(key))
            if leaf:
                out.add(_normalize_cite_token(leaf))
        if not isinstance(meta, Mapping):
            continue
        path = meta.get("path")
        if path:
            out.add(_normalize_cite_token(str(path)))
        table = meta.get("table")
        column = meta.get("column")
        if table and column:
            out.add(_normalize_cite_token(f"{table}.{column}"))
            out.add(_normalize_cite_token(str(column)))
        formula_id = meta.get("formula_id")
        if formula_id:
            out.add(_normalize_cite_token(str(formula_id)))
        field_name = meta.get("field")
        if field_name:
            out.add(_normalize_cite_token(str(field_name)))
    return out


def extract_inline_citation_tokens(text: str) -> list[str]:
    if not text:
        return []
    tokens: list[str] = []
    for m in _INLINE_CITATION_RE.finditer(text):
        body = m.group(1) or m.group(2) or ""
        if re.fullmatch(r"\$?\s*[\d,]+(?:\.\d+)?\s*[KkMmBb]?", body.strip()):
            continue
        if re.fullmatch(r"[\d.]+\s*%", body.strip()):
            continue
        norm = _normalize_cite_token(body)
        if norm:
            tokens.append(norm)
    return tokens


def _sources_from_package_or_map(sources: Mapping[str, Any] | None) -> dict[str, Any]:
    if not sources:
        return {}
    if "values" in sources or "values_decimal" in sources or "_sources" in sources:
        raw = sources.get("_sources")
        return dict(raw) if isinstance(raw, Mapping) else {}
    return dict(sources)


_SENTENCE_END_RE = re.compile(r"[.!?](?=\s|$)|\n")


def _sentence_for_span(text: str, start: int, end: int) -> str:
    """Slice the sentence containing [start:end].

    Do not treat dotted identifiers (``mrr_waterfall.ending_mrr``) as sentence ends —
    only ``.`` / ``!`` / ``?`` followed by whitespace or EOS count.
    """
    left = -1
    for m in _SENTENCE_END_RE.finditer(text[:start]):
        left = m.end() - 1 if m.group(0) == "\n" else m.start()
    right = len(text)
    for m in _SENTENCE_END_RE.finditer(text[end:]):
        right = end + (m.end() if m.group(0) == "\n" else m.end())
        break
    return text[left + 1 : right].strip()


def _citation_token_matches(token: str, citables: set[str]) -> str | None:
    t = _normalize_cite_token(token)
    if not t or not citables:
        return None
    if t in citables:
        return t
    for c in citables:
        if len(c) < 3:
            continue
        if c in t or t in c:
            return c
        t_tail = ".".join(t.split(".")[-2:])
        c_tail = ".".join(c.split(".")[-2:])
        if t_tail and t_tail == c_tail:
            return c
    return None


def _structured_citation_labels(structured_citations: Sequence[Any] | None) -> list[str]:
    labels: list[str] = []
    if not structured_citations:
        return labels
    for item in structured_citations:
        if isinstance(item, str) and item.strip():
            labels.append(item.strip())
            continue
        if isinstance(item, Mapping):
            label = str(item.get("label") or item.get("source") or item.get("key") or "").strip()
            value = str(item.get("value") or "").strip()
        else:
            # Pydantic Citation models (attribute access, not Mapping).
            label = str(getattr(item, "label", "") or "").strip()
            value = str(getattr(item, "value", "") or "").strip()
        if label:
            labels.append(label)
        if value and not re.match(r"^\$?[\d,.]+", value):
            labels.append(value)
    return labels


def verify_text_citations(
    text: str,
    sources: Mapping[str, Any] | None,
    *,
    structured_citations: Sequence[Any] | None = None,
) -> CitationVerificationResult:
    """Fail-closed: material money/%/Nx claims must cite a ``_sources`` key."""
    source_map = _sources_from_package_or_map(sources)
    citables = citable_tokens_from_sources(source_map)
    material = [
        c
        for c in extract_numeric_claims(text or "")
        if c.kind in ("money", "percent")
        or (c.kind == "ratio" and "x" in c.stated.lower())
    ]
    if not material:
        return CitationVerificationResult(checks=[], sources_size=len(source_map))

    if not source_map:
        return CitationVerificationResult(
            checks=[
                CitationCheck(
                    claim=CitationClaim(
                        stated=c.stated, claim_kind=c.kind, sentence=text or ""
                    ),
                    status="empty_sources",
                )
                for c in material
            ],
            sources_size=0,
        )

    structured_labels = _structured_citation_labels(structured_citations)
    checks: list[CitationCheck] = []

    for claim in material:
        idx = (text or "").find(claim.stated)
        start, end = (idx, idx + len(claim.stated)) if idx >= 0 else (0, 0)
        sentence = (
            _sentence_for_span(text or "", start, end) if end > start else (text or "")
        )
        scope_tokens = extract_inline_citation_tokens(sentence)
        candidate_tokens = scope_tokens or [
            _normalize_cite_token(x) for x in structured_labels
        ]
        matched: str | None = None
        unknown = False
        for tok in candidate_tokens:
            hit = _citation_token_matches(tok, citables)
            if hit:
                matched = hit
                break
            if tok:
                unknown = True
        claim_meta = CitationClaim(
            stated=claim.stated, claim_kind=claim.kind, sentence=sentence
        )
        if matched:
            checks.append(
                CitationCheck(claim=claim_meta, status="pass", cited_token=matched)
            )
        elif unknown and candidate_tokens:
            checks.append(CitationCheck(claim=claim_meta, status="unknown_source"))
        else:
            checks.append(CitationCheck(claim=claim_meta, status="missing_citation"))

    return CitationVerificationResult(checks=checks, sources_size=len(source_map))


def fail_closed_citation_text(
    text: str,
    result: CitationVerificationResult | None = None,
    *,
    sources: Mapping[str, Any] | None = None,
    structured_citations: Sequence[Any] | None = None,
    policy: VerifyPolicy = "strict",
) -> str:
    if result is None:
        result = verify_text_citations(
            text, sources, structured_citations=structured_citations
        )
    if result.ok or policy == "interactive":
        return text
    return DONT_KNOW_CITATION


def apply_fail_closed_citations_to_bullet_list(
    bullets: list[str],
    sources: Mapping[str, Any] | None,
    *,
    policy: VerifyPolicy = "strict",
) -> tuple[list[str], CitationVerificationResult]:
    """Per-bullet citation policy. ``interactive`` keeps bullets (warn upstream)."""
    all_checks: list[CitationCheck] = []
    source_map = _sources_from_package_or_map(sources)
    cleaned: list[str] = []
    for bullet in bullets:
        local = verify_text_citations(bullet, source_map)
        all_checks.extend(local.checks)
        if local.ok or policy == "interactive":
            cleaned.append(bullet)
        else:
            cleaned.append(DONT_KNOW_CITATION)
    return cleaned, CitationVerificationResult(
        checks=all_checks, sources_size=len(source_map)
    )


def apply_fail_closed_citations_to_pptx_script(
    script: str,
    sources: Mapping[str, Any] | None,
) -> tuple[str, CitationVerificationResult]:
    """Soft-strip uncited material money/%/Nx inside PPTX JS string literals.

    Layout / chart array code outside strings is ignored. Failed literals
    become ``—`` (never a multi-sentence don't-know essay). Prompt 5 export
    prefers warn-only citation (see ``_verify_prompt5_script_or_raise``);
    optional ``raise_if_pptx_citation_fully_unverifiable`` remains for strict callers.
    """
    from app.services.commentary.claim_verify import (
        _JS_STRING_RE,
        pptx_soft_strip_literal_replacement,
    )

    source_map = _sources_from_package_or_map(sources)
    all_checks: list[CitationCheck] = []

    def _replace(match: re.Match[str]) -> str:
        quote = match.group(1)
        raw = match.group(0)
        inner = raw[1:-1]
        inner_unesc = (
            inner.replace(r"\'", "'")
            .replace(r'\"', '"')
            .replace(r"\n", " ")
            .replace(r"\t", " ")
        )
        local = verify_text_citations(inner_unesc, source_map)
        all_checks.extend(local.checks)
        if local.ok:
            return raw
        replacement = pptx_soft_strip_literal_replacement(
            inner_unesc, dont_know=DONT_KNOW_CITATION
        )
        escaped = (
            replacement.replace("\\", "\\\\")
            .replace(quote, f"\\{quote}")
            .replace("\n", "\\n")
        )
        return f"{quote}{escaped}{quote}"

    rewritten = _JS_STRING_RE.sub(_replace, script or "")
    return rewritten, CitationVerificationResult(
        checks=all_checks, sources_size=len(source_map)
    )


def raise_if_pptx_citation_fully_unverifiable(
    result: CitationVerificationResult,
) -> None:
    """Optional hard-block when every material citation check failed.

    Prompt 5 deck export no longer calls this (prefers soft-strip + export).
    Kept for callers that still want a strict gate; error text leads with samples.
    """
    from app.services.commentary.claim_verify import CommentaryIntegrityError

    if not result.checks:
        return
    if any(c.status == "pass" for c in result.checks):
        return
    raise CommentaryIntegrityError(
        "P15 fail-closed: Prompt 5 / PPTX script had no verifiable _sources citations; "
        f"blocking deck emit. {result.summary(max_failures=8)}",
    )


def verify_commentary_citations(
    output: CommentaryOutput,
    sources: Mapping[str, Any] | None,
) -> CitationVerificationResult:
    source_map = _sources_from_package_or_map(sources)
    all_checks: list[CitationCheck] = []
    for section in (
        output.executive_summary,
        output.revenue_commentary,
        output.mrr_waterfall_commentary,
        output.bookings_forecast_commentary,
        output.cash_forecast_commentary,
    ):
        local = verify_text_citations(
            section.narrative,
            source_map,
            structured_citations=section.citations,
        )
        all_checks.extend(local.checks)
    for item in output.risks_and_opportunities:
        local = verify_text_citations(
            f"{item.description}\n{item.evidence}",
            source_map,
        )
        all_checks.extend(local.checks)
    return CitationVerificationResult(checks=all_checks, sources_size=len(source_map))


def apply_fail_closed_citations_to_commentary(
    output: CommentaryOutput,
    sources: Mapping[str, Any] | None,
    *,
    policy: VerifyPolicy = "strict",
) -> tuple[CommentaryOutput, CitationVerificationResult]:
    """Apply citation verify; ``strict`` don't-knows, ``interactive`` keeps text."""
    overall = verify_commentary_citations(output, sources)
    if overall.ok or policy == "interactive":
        return output, overall

    data = output.model_dump(mode="python")
    source_map = _sources_from_package_or_map(sources)

    def _rewrite_section(key: str) -> None:
        section = data[key]
        local = verify_text_citations(
            section.get("narrative", ""),
            source_map,
            structured_citations=section.get("citations") or [],
        )
        if not local.ok:
            section["narrative"] = DONT_KNOW_CITATION
            section["citations"] = []

    for key in (
        "executive_summary",
        "revenue_commentary",
        "mrr_waterfall_commentary",
        "bookings_forecast_commentary",
        "cash_forecast_commentary",
    ):
        _rewrite_section(key)

    cleaned_risks = []
    for item in data.get("risks_and_opportunities") or []:
        local = verify_text_citations(
            f"{item.get('description', '')}\n{item.get('evidence', '')}",
            source_map,
        )
        if local.ok:
            cleaned_risks.append(item)
        else:
            cleaned_risks.append(
                {
                    **item,
                    "description": DONT_KNOW_CITATION,
                    "evidence": "Unverified citation omitted (P15 fail-closed).",
                }
            )
    data["risks_and_opportunities"] = cleaned_risks

    return CommentaryOutput.model_validate(data), overall


def verify_nested_commentary_citations(
    commentary: Mapping[str, Any],
    sources: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], CitationVerificationResult]:
    """Walk MD&A-style nested commentary JSON; fail-closed rewrite string leaves."""
    all_checks: list[CitationCheck] = []
    source_map = _sources_from_package_or_map(sources)

    def _walk(node: Any) -> Any:
        if isinstance(node, Mapping):
            return {k: _walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_walk(v) for v in node]
        if isinstance(node, str):
            result = verify_text_citations(node, source_map)
            all_checks.extend(result.checks)
            return fail_closed_citation_text(node, result)
        return node

    rewritten = _walk(dict(commentary))
    return rewritten, CitationVerificationResult(
        checks=all_checks, sources_size=len(source_map)
    )
