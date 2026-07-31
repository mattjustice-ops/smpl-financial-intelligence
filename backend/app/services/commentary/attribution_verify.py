"""P15 attribution / driver claim verification.

Numeric claim-verify catches invented dollars. This helper catches **right math,
wrong causal story** — narrative that names an operational cause not present in
an engine-backed allowlist for the package.

v1 scope:
  - Detect causal / attribution language (driven by, due to, because of, …).
  - Match asserted driver phrases against structured `allowed_drivers`.
  - Fail-closed or surgical strip: unnamed / off-allowlist drivers → omit.
  - Forward-looking ("watch out", future impact) must ground in forecast /
    pipeline allowlist evidence — inventing future drivers → strip clause.
  - Empty allowlist + causal claims → fail closed / strip.
  - Numeric-only text with no causal language is unaffected.

Interactive surfaces (regenerate / Copilot / commentary generate) prefer
surgical clause strip over nuking the whole answer. Deck Prompt 2/5 stay
stricter. See docs/soc2/controls/ai_attribution_verify.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Iterable, Literal, Mapping, Sequence

from app.services.commentary.claim_verify import (
    CommentaryIntegrityError,
    VerifyPolicy,
    join_sentences,
    split_sentences,
)
from app.services.commentary.schemas import CommentaryInputs, CommentaryOutput

AttributionStatus = Literal[
    "pass",
    "off_allowlist",
    "empty_allowlist",
    "unnamed_driver",
    "partial_allowlist",
    "ungrounded_forward",
]

DONT_KNOW_ATTRIBUTION = (
    "I don't know — one or more causal / driver claims in this section could not be "
    "verified against engine-backed attribution evidence for the current package. "
    "Unsupported attribution was omitted."
)

DONT_KNOW_FORWARD = (
    "I don't know — one or more forward-looking / predictive claims in this section "
    "could not be grounded in forecast or pipeline evidence for the current package. "
    "Unsupported outlook was omitted."
)

# Sources / labels that count as forecast / pipeline grounding for predictive claims.
_FORECAST_PIPELINE_HINTS = (
    "forecast",
    "pipeline",
    "bookings",
    "scenario",
    "coverage",
    "weighted",
    "quota",
    "outlook",
    "opportunity",
    "opportunities",
)

_FORWARD_CUE_RE = re.compile(
    r"\b(?:"
    r"watch\s+out|watch\s+for|looking\s+ahead|going\s+forward|"
    r"next\s+(?:month|quarter|period)|"
    r"will\s+(?:impact|drive|pressur\w*|increase|decrease|erode|improve|weigh|be)|"
    r"expect(?:ed|s)?|forecast(?:s|ed|ing)?|"
    r"pipeline\s+(?:will|coverage|risk|pressure)|"
    r"risk\s+that|could\s+(?:impact|erode|drive|weigh)|"
    r"projected|outlook"
    r")\b",
    re.IGNORECASE,
)

_FORWARD_DRIVER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:watch\s+out\s+for|watch\s+for|risk\s+(?:from|of)|pressure\s+from)\s+"
        r"(.+?)(?=[.;:\n]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwill\s+(?:be\s+)?(?:driven by|due to|pressured by|impacted by)\s+"
        r"(.+?)(?=[.;:\n]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:expect(?:ed)?|projected|forecast(?:ed)?)\s+"
        r"(?:to\s+be\s+)?(?:driven by|due to|from)\s+(.+?)(?=[.;:\n]|$)",
        re.IGNORECASE,
    ),
)

# Causal cue → capture the following driver phrase (light, deterministic).
_CAUSAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:was |were |is |are |been )?(?:primarily |mainly |largely |mostly )?"
        r"(?:driven by|due to|because of|owing to|attributed to|caused by|"
        r"resulting from|as a result of|on the back of|thanks to|led by|"
        r"offset by|offsetting)\s+(.+?)(?=[.;:\n]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:growth|increase|decrease|decline|variance|overspend|underspend|"
        r"churn|expansion|ARR|MRR|cash|burn)\s+(?:was |were )?"
        r"(?:driven by|due to|because of)\s+(.+?)(?=[.;:\n]|$)",
        re.IGNORECASE,
    ),
    # "X drove Y" — skip interrogatives (handled in extract_attribution_claims).
    re.compile(
        r"\b(?!(?:which|what|who|how|why|where)\b)([A-Za-z][A-Za-z0-9 &\-/']{1,80}?)\s+drove\b",
        re.IGNORECASE,
    ),
    # Negation / exclusion: "not logo loss; it was contraction"
    re.compile(
        r"\b(?:not|wasn't|was not)\s+([^;,]{2,60}?);\s*(?:it was|rather)\s+(.+?)(?=[.;:\n]|$)",
        re.IGNORECASE,
    ),
)

# Stop words / filler trimmed from extracted phrases.
_FILLER_PREFIX = re.compile(
    r"^(?:the |a |an |primarily |mainly |largely |mostly |strong |continued |higher |"
    r"lower |increased |decreased )+",
    re.IGNORECASE,
)
_TRAILING_CLAUSE = re.compile(
    r"\s+(?:which|that|who|while|when|as well as|and also)\b.*$",
    re.IGNORECASE,
)

# Canonical MRR / ARR bridge component labels (engine field → human labels).
# Keep aliases close to engine vocabulary — do not treat free-text deal stories
# ("three enterprise upsells") as synonyms of component buckets.
_MRR_COMPONENT_LABELS: dict[str, tuple[str, ...]] = {
    "new_mrr": ("new mrr", "new business", "new business mrr"),
    "expansion_mrr": ("expansion", "expansion mrr", "expansion arr"),
    "contraction_mrr": ("contraction", "contraction mrr", "contraction arr"),
    "churn_mrr": ("churn", "churn mrr", "churn arr"),
    "reactivation_mrr": ("reactivation", "reactivation mrr", "reactivations"),
    "beginning_mrr": ("beginning mrr", "beginning arr", "bop mrr", "bop arr"),
    "ending_mrr": ("ending mrr", "ending arr", "eop mrr", "eop arr"),
}

_ARR_BRIDGE_LABELS: dict[str, tuple[str, ...]] = {
    "new_business": ("new business", "new business arr"),
    "expansion": ("expansion", "expansion arr"),
    "reactivation": ("reactivation", "reactivation arr", "reactivations"),
    "contraction": ("contraction", "contraction arr"),
    "churn": ("churn", "churn arr"),
    "net_new": ("net new", "net new arr", "net-new arr"),
    "beginning_arr": ("beginning arr", "bop arr"),
    "ending_arr": ("ending arr", "eop arr"),
}

_CASH_BRIDGE_LABELS: dict[str, tuple[str, ...]] = {
    "beginning_cash": ("beginning cash", "cash bop", "opening cash"),
    "collections": ("collections", "cash collections"),
    "payroll": ("payroll", "payroll cash"),
    "vendor_payments": ("vendor payments", "vendor cash", "vendors"),
    "commissions": ("commissions", "commission cash"),
    "capex": ("capex", "capital expenditure", "capital expenditures"),
    "ending_cash": ("ending cash", "cash eop", "closing cash"),
}

# Small integers → words for deal-count aliases ("three new customers").
_COUNT_WORDS: dict[int, str] = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
}

# Share of absolute bridge magnitude to tag a component as dominant.
_DOMINANCE_SHARE = Decimal("0.50")


def _count_aliases(count: int, noun: str) -> tuple[str, ...]:
    """Build deal-count phrases only when count is an evidenced integer."""
    if count <= 0:
        return ()
    noun = noun.strip().lower()
    if not noun:
        return ()
    aliases = [f"{count} {noun}", f"{count} {noun.rstrip('s')}"]
    word = _COUNT_WORDS.get(count)
    if word:
        aliases.append(f"{word} {noun}")
        aliases.append(f"{word} {noun.rstrip('s')}")
    return tuple(dict.fromkeys(aliases))


def apply_magnitude_dominance(
    drivers: Sequence[AllowedDriver],
    *,
    share_threshold: Decimal = _DOMINANCE_SHARE,
) -> list[AllowedDriver]:
    """Tag the largest |amount| driver when it dominates peer magnitudes.

    Peers = drivers that share the same source prefix before the last dotted
    segment (e.g. comparison_waterfalls.arr.*). Adds aliases so attribution
    verify does not over-strip 'primarily expansion' / 'largest bridge' claims
    when the engine amounts support dominance.
    """
    by_family: dict[str, list[AllowedDriver]] = {}
    for d in drivers:
        src = d.source or "unknown"
        family = src.rsplit(".", 1)[0] if "." in src else src
        by_family.setdefault(family, []).append(d)

    dominant_ids: dict[str, tuple[str, ...]] = {}
    for family, group in by_family.items():
        with_amt = [(d, abs(d.amount)) for d in group if d.amount is not None]
        if len(with_amt) < 2:
            continue
        total = sum((a for _, a in with_amt), Decimal("0"))
        if total <= 0:
            continue
        top_d, top_amt = max(with_amt, key=lambda t: t[1])
        if top_amt / total < share_threshold:
            continue
        label = top_d.label.lower()
        dominant_ids[top_d.id] = (
            f"primarily {label}",
            f"mainly {label}",
            f"largely {label}",
            f"largest {label}",
            "largest bridge component",
            "magnitude dominance",
            "dominant driver",
        )

    out: list[AllowedDriver] = []
    for d in drivers:
        extra = dominant_ids.get(d.id)
        if not extra:
            out.append(d)
            continue
        merged_aliases = tuple(dict.fromkeys(tuple(d.aliases) + extra))
        out.append(
            AllowedDriver(
                id=d.id,
                label=d.label,
                amount=d.amount,
                source=d.source,
                aliases=merged_aliases,
            )
        )
    return out


@dataclass(frozen=True)
class AllowedDriver:
    id: str
    label: str
    amount: Decimal | None = None
    source: str | None = None
    aliases: tuple[str, ...] = ()

    def match_tokens(self) -> tuple[str, ...]:
        tokens = {self.id.lower().replace("_", " "), self.label.lower()}
        for a in self.aliases:
            if a:
                tokens.add(a.lower())
        return tuple(sorted(t for t in tokens if t.strip()))


@dataclass(frozen=True)
class AttributionClaim:
    stated: str
    phrase: str
    pattern: str


@dataclass(frozen=True)
class AttributionCheck:
    claim: AttributionClaim
    status: AttributionStatus
    matched_driver_id: str | None = None


@dataclass
class AttributionVerificationResult:
    checks: list[AttributionCheck] = field(default_factory=list)
    allowlist_size: int = 0

    @property
    def ok(self) -> bool:
        return not self.failures

    @property
    def failures(self) -> list[AttributionCheck]:
        return [c for c in self.checks if c.status != "pass"]

    def summary(self, *, max_failures: int = 8) -> str:
        if self.ok:
            if not self.checks:
                return "no causal / attribution claims detected"
            return "all attribution claims verified against allowlist"
        failures = self.failures
        n = len(failures)
        parts = [
            f"{c.claim.phrase!r} ({c.status}"
            + (f", matched={c.matched_driver_id}" if c.matched_driver_id else "")
            + ")"
            for c in failures[: max(0, max_failures)]
        ]
        body = "; ".join(parts)
        if n > max_failures > 0:
            body += f"; …+{n - max_failures} more"
        return f"{n} failed attribution(s): {body}"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _clean_phrase(raw: str) -> str:
    phrase = raw.strip().strip("\"'“”‘’")
    phrase = _TRAILING_CLAUSE.sub("", phrase)
    phrase = _FILLER_PREFIX.sub("", phrase).strip(" ,;")
    # Drop trailing money / percent that belong to the effect, not the cause name.
    phrase = re.sub(r"\s+of\s+\$[\d,.]+[KkMmBb]?\s*$", "", phrase)
    phrase = re.sub(r"\s+of\s+[\d.]+\s*%\s*$", "", phrase)
    return phrase.strip(" ,;")


def extract_attribution_claims(text: str) -> list[AttributionClaim]:
    """Extract causal / driver phrases from narrative text."""
    if not text or not text.strip():
        return []
    claims: list[AttributionClaim] = []
    seen: set[str] = set()

    def _sentence_at(start: int, end: int) -> str:
        left = max(text.rfind(".", 0, start), text.rfind("!", 0, start), text.rfind("?", 0, start), text.rfind("\n", 0, start))
        right_candidates = [text.find(ch, end) for ch in ".!?\n"]
        right_candidates = [i for i in right_candidates if i != -1]
        right = min(right_candidates) if right_candidates else len(text)
        return text[left + 1 : right + 1].strip()

    def _add(stated: str, phrase: str, pattern: str, *, start: int, end: int) -> None:
        cleaned = _clean_phrase(phrase)
        if len(cleaned) < 2:
            return
        sentence = _sentence_at(start, end)
        # Questions ask about drivers; they do not assert a closed-period cause.
        if (
            stated.strip().endswith("?")
            or sentence.endswith("?")
            or re.match(r"^(?:which|what|who|how|why|where)\b", sentence, re.IGNORECASE)
            or re.match(r"^(?:which|what|who|how|why|where)\b", cleaned, re.IGNORECASE)
        ):
            return
        key = _normalize(cleaned)
        if key in seen:
            return
        seen.add(key)
        claims.append(AttributionClaim(stated=stated.strip(), phrase=cleaned, pattern=pattern))

    for pat in _CAUSAL_PATTERNS:
        for m in pat.finditer(text):
            groups = [g for g in m.groups() if g]
            if not groups:
                continue
            # Negation pattern yields two causes (rejected + asserted); check both.
            for g in groups:
                _add(m.group(0), g, pat.pattern[:48], start=m.start(), end=m.end())

    return claims


def _phrase_matches_driver(phrase: str, driver: AllowedDriver) -> bool:
    p = _normalize(phrase)
    if not p:
        return False
    for token in driver.match_tokens():
        t = _normalize(token)
        if not t:
            continue
        # Substring either way for short canonical labels ("expansion", "churn").
        if t in p or p in t:
            return True
        # Token overlap for multi-word ("new business ARR" vs "new business").
        p_words = set(re.findall(r"[a-z0-9]+", p))
        t_words = set(re.findall(r"[a-z0-9]+", t))
        if t_words and t_words.issubset(p_words):
            return True
    return False


def _split_driver_conjuncts(phrase: str) -> list[str]:
    """Split multi-driver phrases joined by ``and`` / commas into named parts."""
    raw = (phrase or "").strip()
    if not raw:
        return []
    parts = re.split(r"\s+and\s+|\,\s*(?:and\s+)?", raw, flags=re.IGNORECASE)
    cleaned: list[str] = []
    for part in parts:
        c = _clean_phrase(part)
        if len(c) < 2:
            continue
        if not re.search(r"[A-Za-z]{3,}", c):
            continue
        cleaned.append(c)
    if cleaned:
        return cleaned
    fallback = _clean_phrase(raw)
    return [fallback] if fallback else []


def _match_single_phrase(
    phrase: str,
    allowlist: Sequence[AllowedDriver],
) -> str | None:
    for driver in allowlist:
        if _phrase_matches_driver(phrase, driver):
            return driver.id
    return None


def _match_claim(
    claim: AttributionClaim,
    allowlist: Sequence[AllowedDriver],
) -> AttributionCheck:
    if not allowlist:
        return AttributionCheck(claim=claim, status="empty_allowlist")

    parts = _split_driver_conjuncts(claim.phrase)
    # Multi-driver "and"/comma lists: EVERY named driver must be allowlisted.
    if len(parts) > 1:
        matched_ids: list[str] = []
        unmatched: list[str] = []
        for part in parts:
            hit = _match_single_phrase(part, allowlist)
            if hit:
                matched_ids.append(hit)
            else:
                unmatched.append(part)
        if not unmatched:
            return AttributionCheck(
                claim=claim,
                status="pass",
                matched_driver_id="+".join(matched_ids),
            )
        if matched_ids:
            return AttributionCheck(
                claim=claim,
                status="partial_allowlist",
                matched_driver_id="+".join(matched_ids),
            )
        if not re.search(r"[A-Za-z]{3,}", claim.phrase):
            return AttributionCheck(claim=claim, status="unnamed_driver")
        return AttributionCheck(claim=claim, status="off_allowlist")

    phrase = parts[0] if parts else claim.phrase
    hit = _match_single_phrase(phrase, allowlist)
    if hit:
        return AttributionCheck(
            claim=claim,
            status="pass",
            matched_driver_id=hit,
        )

    # Extremely vague phrases with no noun substance → unnamed.
    if not re.search(r"[A-Za-z]{3,}", claim.phrase):
        return AttributionCheck(claim=claim, status="unnamed_driver")

    return AttributionCheck(claim=claim, status="off_allowlist")


def verify_text_attribution(
    text: str,
    allowlist: Sequence[AllowedDriver] | Mapping[str, Any] | None,
) -> AttributionVerificationResult:
    """Check causal claims in text against an allowlist of engine drivers."""
    drivers = normalize_allowlist(allowlist)
    claims = extract_attribution_claims(text)
    checks = [_match_claim(c, drivers) for c in claims]
    return AttributionVerificationResult(checks=checks, allowlist_size=len(drivers))


def _sentence_touches_failed_claim(sentence: str, failures: Sequence[AttributionCheck]) -> bool:
    s = sentence.lower()
    for check in failures:
        phrase = (check.claim.phrase or "").strip().lower()
        stated = (check.claim.stated or "").strip().lower()
        if phrase and phrase in s:
            return True
        if stated and stated in s:
            return True
    return False


def strip_failed_attribution_sentences(
    text: str,
    result: AttributionVerificationResult,
    *,
    empty_fallback: str = DONT_KNOW_ATTRIBUTION,
) -> str:
    """Remove only sentences that carry failed attribution / forward claims."""
    if result.ok:
        return text
    failures = result.failures
    kept = [
        s
        for s in split_sentences(text)
        if not _sentence_touches_failed_claim(s, failures)
    ]
    joined = join_sentences(kept)
    return joined if joined.strip() else empty_fallback


def fail_closed_attribution_text(
    text: str,
    result: AttributionVerificationResult | None = None,
    *,
    allowlist: Sequence[AllowedDriver] | Mapping[str, Any] | None = None,
    policy: VerifyPolicy = "strict",
) -> str:
    """``strict`` → whole-text don't-know; ``interactive`` → surgical sentence strip."""
    if result is None:
        result = verify_text_attribution(text, allowlist)
    if result.ok:
        return text
    if policy == "interactive":
        return strip_failed_attribution_sentences(text, result)
    return DONT_KNOW_ATTRIBUTION


def is_forecast_pipeline_driver(driver: AllowedDriver) -> bool:
    blob = " ".join(
        [
            driver.id,
            driver.label,
            driver.source or "",
            " ".join(driver.aliases),
        ]
    ).lower()
    return any(h in blob for h in _FORECAST_PIPELINE_HINTS)


def forecast_pipeline_allowlist(
    allowlist: Sequence[AllowedDriver] | Mapping[str, Any] | None,
) -> list[AllowedDriver]:
    return [d for d in normalize_allowlist(allowlist) if is_forecast_pipeline_driver(d)]


def extract_forward_looking_claims(text: str) -> list[AttributionClaim]:
    """Extract predictive / outlook driver phrases that need forecast/pipeline grounding."""
    if not text or not text.strip():
        return []
    claims: list[AttributionClaim] = []
    seen: set[str] = set()

    def _add(stated: str, phrase: str, pattern: str) -> None:
        cleaned = _clean_phrase(phrase)
        if len(cleaned) < 2 or not re.search(r"[A-Za-z]{3,}", cleaned):
            return
        key = _normalize(cleaned)
        if key in seen:
            return
        seen.add(key)
        claims.append(
            AttributionClaim(stated=stated.strip(), phrase=cleaned, pattern=pattern)
        )

    for pat in _FORWARD_DRIVER_PATTERNS:
        for m in pat.finditer(text):
            groups = [g for g in m.groups() if g]
            for g in groups:
                _add(m.group(0), g, "forward:" + pat.pattern[:40])

    # Forward cue + existing causal extract in the same sentence.
    for sentence in split_sentences(text):
        if not _FORWARD_CUE_RE.search(sentence):
            continue
        for claim in extract_attribution_claims(sentence):
            key = _normalize(claim.phrase)
            if key in seen:
                continue
            seen.add(key)
            claims.append(
                AttributionClaim(
                    stated=claim.stated,
                    phrase=claim.phrase,
                    pattern="forward+causal:" + claim.pattern[:32],
                )
            )
    return claims


def verify_text_forward_looking(
    text: str,
    allowlist: Sequence[AllowedDriver] | Mapping[str, Any] | None,
) -> AttributionVerificationResult:
    """Forward-looking driver claims must match forecast/pipeline allowlist entries."""
    fp_drivers = forecast_pipeline_allowlist(allowlist)
    claims = extract_forward_looking_claims(text)
    checks: list[AttributionCheck] = []
    for claim in claims:
        if not fp_drivers:
            checks.append(
                AttributionCheck(claim=claim, status="ungrounded_forward")
            )
            continue
        hit = _match_claim(claim, fp_drivers)
        if hit.status == "pass":
            checks.append(hit)
        else:
            checks.append(
                AttributionCheck(
                    claim=claim,
                    status="ungrounded_forward",
                    matched_driver_id=hit.matched_driver_id,
                )
            )
    return AttributionVerificationResult(checks=checks, allowlist_size=len(fp_drivers))


def apply_forward_looking_policy_to_text(
    text: str,
    allowlist: Sequence[AllowedDriver] | Mapping[str, Any] | None,
    *,
    policy: VerifyPolicy = "interactive",
) -> tuple[str, AttributionVerificationResult]:
    result = verify_text_forward_looking(text, allowlist)
    if result.ok:
        return text, result
    if policy == "interactive":
        return (
            strip_failed_attribution_sentences(
                text, result, empty_fallback=DONT_KNOW_FORWARD
            ),
            result,
        )
    return DONT_KNOW_FORWARD, result


def normalize_allowlist(
    allowlist: Sequence[AllowedDriver] | Mapping[str, Any] | None,
) -> list[AllowedDriver]:
    """Accept list[AllowedDriver], attribution package dict, or raw driver list."""
    if allowlist is None:
        return []
    if isinstance(allowlist, Mapping):
        raw = allowlist.get("allowed_drivers", allowlist.get("drivers", []))
        if isinstance(raw, Mapping):
            raw = list(raw.values())
        return normalize_allowlist(raw if isinstance(raw, Sequence) else [])

    out: list[AllowedDriver] = []
    for item in allowlist:
        if isinstance(item, AllowedDriver):
            out.append(item)
            continue
        if isinstance(item, Mapping):
            did = str(item.get("id") or item.get("key") or "").strip()
            label = str(item.get("label") or item.get("name") or did).strip()
            if not did and not label:
                continue
            aliases_raw = item.get("aliases") or ()
            aliases = tuple(str(a) for a in aliases_raw) if isinstance(aliases_raw, (list, tuple)) else ()
            amount = item.get("amount")
            amt: Decimal | None = None
            if amount is not None and not isinstance(amount, bool):
                try:
                    amt = Decimal(str(amount))
                except Exception:
                    amt = None
            out.append(
                AllowedDriver(
                    id=did or _slug(label),
                    label=label or did,
                    amount=amt,
                    source=str(item.get("source") or "") or None,
                    aliases=aliases,
                )
            )
            continue
        if isinstance(item, str) and item.strip():
            out.append(AllowedDriver(id=_slug(item), label=item.strip(), aliases=()))
    return out


def _slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_") or "driver"


def _driver(
    did: str,
    label: str,
    *,
    amount: Any = None,
    source: str | None = None,
    aliases: Iterable[str] = (),
) -> AllowedDriver:
    amt: Decimal | None = None
    if amount is not None and not isinstance(amount, bool):
        try:
            amt = amount if isinstance(amount, Decimal) else Decimal(str(amount))
        except Exception:
            amt = None
    return AllowedDriver(
        id=did,
        label=label,
        amount=amt,
        source=source,
        aliases=tuple(a for a in aliases if a),
    )


def build_attribution_package(
    *,
    metric: str | None = None,
    period: str | None = None,
    value: Any = None,
    drivers: Sequence[AllowedDriver] | None = None,
) -> dict[str, Any]:
    """Serialize an attribution package (engine → prompt + post-verify)."""
    allowed = list(drivers or [])
    val: str | None = None
    if value is not None and not isinstance(value, bool):
        try:
            val = str(value if isinstance(value, Decimal) else Decimal(str(value)))
        except Exception:
            val = str(value)
    return {
        "metric": metric,
        "period": period,
        "value": val,
        "allowed_drivers": [
            {
                "id": d.id,
                "label": d.label,
                "amount": str(d.amount) if d.amount is not None else None,
                "source": d.source,
                "aliases": list(d.aliases),
            }
            for d in allowed
        ],
        "policy": (
            "May only name drivers whose id/label/aliases appear in allowed_drivers. "
            "When a causal phrase joins multiple drivers with 'and' or commas, "
            "EVERY named driver must be on the allowlist (not just one). "
            "Empty allowlist means no causal claims are permitted. "
            "Numeric claims still governed by claim_verify TOL_ACTUALS=$1.00."
        ),
    }


def build_attribution_package_from_commentary_inputs(
    inputs: CommentaryInputs | Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Extract allowlist from CommentaryInputs structured fields (v1).

    Sources today:
      - MRR waterfall component names (+ canonical aliases)
      - actuals_vs_forecast metric names
      - pipeline_changes labels
      - customer_movement counts / notable customers
      - quota_attainment segments / rep names
      - cash aging bucket keys

    Deal-count / named-logo enrichment: customer_movement counts and
    notable_customers become allowlisted phrases. Invented counts still fail.
    """
    drivers: list[AllowedDriver] = []
    period: str | None = None
    metric = "commentary_package"
    value: Any = None

    data: Mapping[str, Any]
    if inputs is None:
        data = {}
    elif isinstance(inputs, CommentaryInputs):
        period = inputs.period_label
        data = inputs.model_dump(mode="python", exclude_none=True)
    else:
        period = str(inputs.get("period_label") or inputs.get("close_period") or "") or None
        data = inputs

    wf = data.get("mrr_waterfall") if isinstance(data, Mapping) else None
    if isinstance(wf, Mapping):
        value = wf.get("ending_mrr")
        for key, aliases in _MRR_COMPONENT_LABELS.items():
            if key not in wf:
                continue
            label = key.replace("_", " ")
            drivers.append(
                _driver(
                    key,
                    label.title(),
                    amount=wf.get(key),
                    source=f"mrr_waterfall.{key}",
                    aliases=aliases,
                )
            )

    for row in data.get("actuals_vs_forecast") or []:
        if not isinstance(row, Mapping):
            continue
        metric_name = str(row.get("metric") or "").strip()
        if not metric_name:
            continue
        drivers.append(
            _driver(
                _slug(metric_name),
                metric_name,
                amount=row.get("variance_absolute"),
                source="actuals_vs_forecast.metric",
                aliases=(metric_name.lower(),),
            )
        )

    for change in data.get("pipeline_changes") or []:
        if not isinstance(change, Mapping):
            continue
        label = str(change.get("label") or "").strip()
        if not label:
            continue
        drivers.append(
            _driver(
                _slug(label),
                label,
                amount=change.get("delta_arr"),
                source="pipeline_changes.label",
                aliases=(label.lower(),),
            )
        )

    cm = data.get("customer_movement")
    if isinstance(cm, Mapping):
        for key, base_aliases in (
            ("new_customers", ("new customers", "new logos", "new logo")),
            ("churned_customers", ("churned customers", "logo churn", "churned logos")),
            # Avoid bare "upsells" — substring-matches invented "enterprise upsells".
            ("expanded_customers", ("expanded customers", "expansion logos")),
            ("contracted_customers", ("contracted customers",)),
            ("reactivated_customers", ("reactivated customers", "reactivations")),
        ):
            if key not in cm:
                continue
            raw_count = cm.get(key)
            count_aliases: tuple[str, ...] = ()
            try:
                count_i = int(Decimal(str(raw_count)))
                noun = key.replace("_", " ")
                count_aliases = _count_aliases(count_i, noun) + _count_aliases(
                    count_i, base_aliases[0]
                )
            except Exception:
                count_i = None
            drivers.append(
                _driver(
                    key,
                    key.replace("_", " ").title(),
                    amount=raw_count,
                    source=f"customer_movement.{key}",
                    aliases=base_aliases + count_aliases,
                )
            )
            if count_i is not None and count_i > 0:
                drivers.append(
                    _driver(
                        f"deal_count_{key}_{count_i}",
                        f"{count_i} {key.replace('_', ' ')}",
                        amount=count_i,
                        source=f"customer_movement.{key}.deal_count",
                        aliases=count_aliases,
                    )
                )
        for name in cm.get("notable_customers") or []:
            if not str(name).strip():
                continue
            logo = str(name).strip()
            drivers.append(
                _driver(
                    _slug(logo),
                    logo,
                    source="customer_movement.notable_customers",
                    aliases=(logo.lower(), f"{logo.lower()} logo"),
                )
            )

    for qa in data.get("quota_attainment") or []:
        if not isinstance(qa, Mapping):
            continue
        for field_name in ("rep_name", "segment"):
            val = str(qa.get(field_name) or "").strip()
            if val:
                drivers.append(
                    _driver(
                        _slug(val),
                        val,
                        source=f"quota_attainment.{field_name}",
                        aliases=(val.lower(),),
                    )
                )

    cash = data.get("cash_forecast")
    if isinstance(cash, Mapping):
        aging = cash.get("aging_buckets") or {}
        if isinstance(aging, Mapping):
            for bucket in aging.keys():
                label = str(bucket).strip()
                if label:
                    drivers.append(
                        _driver(
                            _slug(label),
                            f"AR aging {label}",
                            amount=aging.get(bucket),
                            source=f"cash_forecast.aging_buckets.{label}",
                            aliases=(label.lower(), f"aging {label.lower()}"),
                        )
                    )

    # Deduplicate by id keeping first.
    seen: set[str] = set()
    uniq: list[AllowedDriver] = []
    for d in drivers:
        if d.id in seen:
            continue
        seen.add(d.id)
        uniq.append(d)
    uniq = apply_magnitude_dominance(uniq)

    return build_attribution_package(
        metric=metric,
        period=period,
        value=value,
        drivers=uniq,
    )


def build_attribution_package_from_mda_payload(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Extract allowlist from MD&A / deck payload structured fields (v1).

    Sources:
      - arr_analysis.bridge_table row labels + known ARR component keys
      - cash_liquidity.bridge_table row labels
      - variance_commentary_display / sheets metric names
      - GTM channel names when present
    """
    if not payload:
        return build_attribution_package(metric="mda_package", drivers=[])

    drivers: list[AllowedDriver] = []
    period = str(payload.get("close_period") or payload.get("close_period_label") or "") or None
    deck = payload.get("deck_payload") or {}
    if not isinstance(deck, Mapping):
        deck = {}

    arr = deck.get("arr_analysis") or payload.get("arr_analysis") or {}
    if isinstance(arr, Mapping):
        bridge = arr.get("bridge_table") or {}
        for row in (bridge.get("rows") or []) if isinstance(bridge, Mapping) else []:
            if not isinstance(row, Mapping):
                continue
            label = str(row.get("label") or "").strip()
            if not label:
                continue
            slug = _slug(label)
            extra_aliases = _ARR_BRIDGE_LABELS.get(slug, ())
            # Also map common table labels to component aliases.
            for key, aliases in _ARR_BRIDGE_LABELS.items():
                if key.replace("_", " ") in label.lower() or label.lower() in aliases:
                    extra_aliases = aliases
                    slug = key
                    break
            amt = row.get("amount")
            if amt is None:
                amt = row.get("actual")
            if amt is None:
                amt = row.get("value")
            drivers.append(
                _driver(
                    slug,
                    label,
                    amount=amt,
                    source="arr_analysis.bridge_table",
                    aliases=extra_aliases + (label.lower(),),
                )
            )
        for key, aliases in _ARR_BRIDGE_LABELS.items():
            if key in arr or f"{key}_budget" in arr:
                drivers.append(
                    _driver(
                        key,
                        key.replace("_", " ").title(),
                        amount=arr.get(key),
                        source=f"arr_analysis.{key}",
                        aliases=aliases,
                    )
                )

    cash = deck.get("cash_liquidity") or payload.get("cash_liquidity") or {}
    if isinstance(cash, Mapping):
        bridge = cash.get("bridge_table") or {}
        for row in (bridge.get("rows") or []) if isinstance(bridge, Mapping) else []:
            if not isinstance(row, Mapping):
                continue
            label = str(row.get("label") or "").strip()
            if not label:
                continue
            slug = _slug(label)
            aliases = _CASH_BRIDGE_LABELS.get(slug, ())
            for key, als in _CASH_BRIDGE_LABELS.items():
                if key.replace("_", " ") in label.lower() or label.lower() in als:
                    aliases = als
                    slug = key
                    break
            amt = row.get("amount")
            if amt is None:
                amt = row.get("actual")
            if amt is None:
                amt = row.get("value")
            drivers.append(
                _driver(
                    slug,
                    label,
                    amount=amt,
                    source="cash_liquidity.bridge_table",
                    aliases=aliases + (label.lower(),),
                )
            )

    display = payload.get("variance_commentary_display") or {}
    if isinstance(display, Mapping):
        for row in display.get("rows") or []:
            if not isinstance(row, Mapping):
                continue
            metric_name = str(row.get("metric") or "").strip()
            if metric_name:
                drivers.append(
                    _driver(
                        _slug(metric_name),
                        metric_name,
                        source="variance_commentary_display.metric",
                        aliases=(metric_name.lower(),),
                    )
                )

    sheets = payload.get("sheets") or {}
    if isinstance(sheets, Mapping):
        for sheet_name, sheet in sheets.items():
            if not isinstance(sheet, Mapping):
                continue
            for row in sheet.get("rows") or []:
                if not isinstance(row, Mapping):
                    continue
                for field_name in ("metric", "category", "channel", "label"):
                    val = str(row.get(field_name) or "").strip()
                    if val:
                        drivers.append(
                            _driver(
                                _slug(val),
                                val,
                                source=f"sheets.{sheet_name}.{field_name}",
                                aliases=(val.lower(),),
                            )
                        )

    # Marketing / GTM channels from deck if present.
    for path_key in ("gtm", "marketing", "channels"):
        block = deck.get(path_key) or payload.get(path_key)
        if isinstance(block, Mapping):
            for ch in block.get("channels") or block.get("by_channel") or []:
                if isinstance(ch, Mapping):
                    name = str(ch.get("channel") or ch.get("name") or "").strip()
                else:
                    name = str(ch).strip()
                if name:
                    drivers.append(
                        _driver(
                            _slug(name),
                            name,
                            source=f"deck.{path_key}",
                            aliases=(name.lower(),),
                        )
                    )

    seen: set[str] = set()
    uniq: list[AllowedDriver] = []
    for d in drivers:
        if d.id in seen:
            continue
        seen.add(d.id)
        uniq.append(d)
    uniq = apply_magnitude_dominance(uniq)

    return build_attribution_package(
        metric="mda_package",
        period=period,
        drivers=uniq,
    )


def verify_commentary_attribution(
    output: CommentaryOutput,
    allowlist: Sequence[AllowedDriver] | Mapping[str, Any] | None,
) -> AttributionVerificationResult:
    blobs: list[str] = []
    for section in (
        output.executive_summary,
        output.revenue_commentary,
        output.mrr_waterfall_commentary,
        output.bookings_forecast_commentary,
        output.cash_forecast_commentary,
    ):
        blobs.append(section.narrative)
        for c in section.citations:
            blobs.append(c.value)
    for item in output.risks_and_opportunities:
        blobs.append(item.description)
        blobs.append(item.evidence)
    for item in output.followup_questions:
        blobs.append(item.question)
        blobs.append(item.rationale)

    return verify_text_attribution("\n".join(blobs), allowlist)


def _apply_story_policy_to_text(
    text: str,
    allowlist: Sequence[AllowedDriver] | Mapping[str, Any] | None,
    *,
    policy: VerifyPolicy,
) -> tuple[str, list[AttributionCheck]]:
    """Attribution + forward-looking policy for one narrative blob."""
    checks: list[AttributionCheck] = []
    local = verify_text_attribution(text, allowlist)
    checks.extend(local.checks)
    fwd = verify_text_forward_looking(text, allowlist)
    checks.extend(fwd.checks)
    out = text
    if policy == "interactive":
        if not local.ok:
            out = strip_failed_attribution_sentences(out, local)
        if out not in (DONT_KNOW_ATTRIBUTION, DONT_KNOW_FORWARD) and not fwd.ok:
            out = strip_failed_attribution_sentences(
                out, fwd, empty_fallback=DONT_KNOW_FORWARD
            )
        return out, checks
    if not local.ok:
        return DONT_KNOW_ATTRIBUTION, checks
    if not fwd.ok:
        return DONT_KNOW_FORWARD, checks
    return text, checks


def apply_fail_closed_attribution_to_commentary(
    output: CommentaryOutput,
    allowlist: Sequence[AllowedDriver] | Mapping[str, Any] | None,
    *,
    policy: VerifyPolicy = "strict",
) -> tuple[CommentaryOutput, AttributionVerificationResult]:
    """Strip bad causal / ungrounded forward claims; prefer surgical strip when interactive."""
    data = output.model_dump(mode="python")
    drivers = normalize_allowlist(allowlist)
    all_checks: list[AttributionCheck] = []

    def _rewrite_section(key: str) -> None:
        section = data[key]
        narr, checks = _apply_story_policy_to_text(
            section.get("narrative", ""), drivers, policy=policy
        )
        all_checks.extend(checks)
        if narr != section.get("narrative", ""):
            section["narrative"] = narr
            if narr in (DONT_KNOW_ATTRIBUTION, DONT_KNOW_FORWARD) and policy != "interactive":
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
        desc = item.get("description", "")
        rewritten, checks = _apply_story_policy_to_text(desc, drivers, policy=policy)
        all_checks.extend(checks)
        if rewritten == desc:
            cleaned_risks.append(item)
        elif rewritten in (DONT_KNOW_ATTRIBUTION, DONT_KNOW_FORWARD) and policy != "interactive":
            cleaned_risks.append(
                {
                    **item,
                    "description": rewritten,
                    "evidence": "Unverified attribution claim omitted (P15 fail-closed).",
                }
            )
        else:
            cleaned_risks.append({**item, "description": rewritten})
    data["risks_and_opportunities"] = cleaned_risks

    cleaned_qs = []
    for item in data.get("followup_questions") or []:
        blob = f"{item.get('question', '')}\n{item.get('rationale', '')}"
        local = verify_text_attribution(blob, drivers)
        all_checks.extend(local.checks)
        if local.ok or policy == "interactive":
            cleaned_qs.append(item)
        else:
            cleaned_qs.append(
                {
                    **item,
                    "question": "Which engine-backed drivers should replace the unverified attribution above?",
                    "rationale": "Prior question referenced causes that failed P15 attribution allowlist verify.",
                }
            )
    data["followup_questions"] = cleaned_qs

    return CommentaryOutput.model_validate(data), AttributionVerificationResult(
        checks=all_checks,
        allowlist_size=len(drivers),
    )


def verify_nested_commentary_attribution(
    commentary: Mapping[str, Any],
    allowlist: Sequence[AllowedDriver] | Mapping[str, Any] | None,
) -> tuple[dict[str, Any], AttributionVerificationResult]:
    """Walk MD&A-style nested commentary JSON; fail-closed rewrite string leaves."""
    all_checks: list[AttributionCheck] = []
    drivers = normalize_allowlist(allowlist)

    def _walk(node: Any) -> Any:
        if isinstance(node, Mapping):
            return {k: _walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_walk(v) for v in node]
        if isinstance(node, str):
            result = verify_text_attribution(node, drivers)
            all_checks.extend(result.checks)
            return fail_closed_attribution_text(node, result)
        return node

    rewritten = _walk(dict(commentary))
    return rewritten, AttributionVerificationResult(
        checks=all_checks,
        allowlist_size=len(drivers),
    )


def raise_if_attribution_fully_unverifiable(
    commentary: Mapping[str, Any],
    result: AttributionVerificationResult,
    *,
    sheet_key: str = "variance_commentary",
) -> None:
    """Hard-block MD&A emit when every variance cell was wiped for attribution."""
    vc = commentary.get(sheet_key) or {}
    marker = "could not be verified against engine-backed attribution"
    vc_texts: list[str] = []
    if isinstance(vc, Mapping):
        for row in vc.values():
            if isinstance(row, dict):
                vc_texts.extend(str(v) for v in row.values() if isinstance(v, str))
            elif isinstance(row, str):
                vc_texts.append(row)
    if vc_texts and all(marker in t for t in vc_texts):
        raise CommentaryIntegrityError(
            "P15 fail-closed: MD&A variance commentary had no verifiable attribution claims; "
            "blocking package emit. " + result.summary(),
        )


def build_attribution_package_from_deck_payload(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Allowlist from Prompt 5 / board deck payload structured fields.

    Reuses MDA bridge/sheet extraction and adds period_matrix metrics + GTM channels.
    """
    if not payload:
        return build_attribution_package(metric="deck_package", drivers=[])

    # MDA helper already walks arr_analysis / cash_liquidity / sheets / channels
    # on both top-level and nested deck_payload shapes.
    base = build_attribution_package_from_mda_payload(payload)
    drivers = normalize_allowlist(base)
    seen = {d.id for d in drivers}

    def _add(did: str, label: str, *, source: str, aliases: Iterable[str] = ()) -> None:
        if did in seen:
            return
        seen.add(did)
        drivers.append(_driver(did, label, source=source, aliases=aliases))

    matrix = payload.get("period_matrix") or {}
    if isinstance(matrix, Mapping):
        for row in matrix.get("rows") or []:
            if not isinstance(row, Mapping):
                continue
            metric_name = str(row.get("metric") or "").strip()
            if metric_name:
                _add(
                    _slug(metric_name),
                    metric_name,
                    source="period_matrix.metric",
                    aliases=(metric_name.lower(),),
                )

    gtm = payload.get("gtm_performance") or {}
    if isinstance(gtm, Mapping):
        for ch in gtm.get("channels") or gtm.get("by_channel") or []:
            if isinstance(ch, Mapping):
                name = str(ch.get("channel") or ch.get("name") or "").strip()
            else:
                name = str(ch).strip()
            if name:
                _add(_slug(name), name, source="gtm_performance.channels", aliases=(name.lower(),))

    # Waterfall / bridge component keys already on arr_analysis without table rows.
    arr = payload.get("arr_analysis") or {}
    if isinstance(arr, Mapping):
        for key, aliases in _ARR_BRIDGE_LABELS.items():
            if key in arr or f"{key}_budget" in arr:
                _add(key, key.replace("_", " ").title(), source=f"arr_analysis.{key}", aliases=aliases)

    # Forecast / pipeline forward-looking keys so outlook narrative can ground.
    for did, label, source, aliases in (
        ("pipeline_coverage", "Pipeline coverage", "gtm_performance.pipeline_coverage", ("pipeline coverage", "coverage")),
        ("slipped_pipeline", "Slipped pipeline", "pipeline.slipped", ("slipped pipeline", "slipped")),
        ("pipeline_created", "Pipeline created", "pipeline.created", ("pipeline created", "pipeline")),
        ("forecast_arr", "Forecast ARR", "fy_outlook.forecast", ("forecast arr", "arr outlook", "outlook arr")),
        ("fy_outlook", "FY outlook", "fy_outlook", ("fy outlook", "full year outlook", "outlook")),
        ("bookings_forecast", "Bookings forecast", "forecast.bookings", ("bookings forecast", "bookings outlook")),
        ("cash_forecast", "Cash forecast", "forecast.cash", ("cash forecast", "cash outlook", "collections outlook")),
        ("deferred_pipeline", "Deferred pipeline", "pipeline.deferred", ("deferred pipeline",)),
    ):
        _add(did, label, source=source, aliases=aliases)

    deals = payload.get("deal_highlights") or {}
    if isinstance(deals, Mapping):
        for bucket in ("top_new_customers", "top_expansion", "top_churn", "top_slipped"):
            rows = deals.get(bucket) or []
            if not isinstance(rows, list):
                continue
            source = f"deal_highlights.{bucket}"
            # Slipped / expansion deals count as pipeline grounding for forward claims.
            if bucket in {"top_slipped", "top_expansion"}:
                source = f"pipeline.{bucket}"
            for row in rows:
                if not isinstance(row, Mapping):
                    continue
                name = str(row.get("name") or "").strip()
                if not name:
                    continue
                _add(
                    _slug(name),
                    name,
                    source=source,
                    aliases=(name.lower(),),
                )

    risks = payload.get("risks_and_opportunities") or {}
    if isinstance(risks, Mapping):
        for side in ("risks", "opportunities"):
            for item in risks.get(side) or []:
                if not isinstance(item, Mapping):
                    continue
                title = str(item.get("title") or item.get("name") or "").strip()
                if not title:
                    continue
                # Tag opportunities / pipeline-ish risks as forecast/pipeline sources.
                src = (
                    f"pipeline.risks_and_opportunities.{side}"
                    if side == "opportunities"
                    or any(h in title.lower() for h in ("pipeline", "forecast", "outlook", "coverage"))
                    else f"risks_and_opportunities.{side}"
                )
                _add(_slug(title), title, source=src, aliases=(title.lower(),))

    cash = payload.get("cash_liquidity") or {}
    if isinstance(cash, Mapping) and cash:
        for key, aliases in _CASH_BRIDGE_LABELS.items():
            _add(
                key,
                key.replace("_", " ").title(),
                source=f"cash_liquidity.{key}",
                aliases=aliases,
            )

    period = str(
        (payload.get("period_context") or {}).get("close_period")
        if isinstance(payload.get("period_context"), Mapping)
        else payload.get("close_period") or base.get("period") or ""
    ) or None

    pkg = build_attribution_package(
        metric="deck_package",
        period=period,
        drivers=apply_magnitude_dominance(drivers),
    )
    pkg["policy"] = (
        "May only name drivers whose id/label/aliases appear in allowed_drivers. "
        "When a causal phrase joins multiple drivers with 'and' or commas, "
        "EVERY named driver must be on the allowlist (not just one). "
        "Empty allowlist means no causal claims are permitted. "
        "Forward-looking / watch-out language must ground in forecast or pipeline "
        "allowlist entries (source/label containing forecast, pipeline, outlook, "
        "opportunity, coverage, etc.). "
        "Numeric claims still governed by claim_verify TOL_ACTUALS=$1.00. "
        "Rich narrative from allowlisted drivers is encouraged — do not invent causes."
    )
    return pkg


def apply_fail_closed_attribution_to_bullet_list(
    bullets: list[str],
    allowlist: Sequence[AllowedDriver] | Mapping[str, Any] | None,
    *,
    policy: VerifyPolicy = "strict",
) -> tuple[list[str], AttributionVerificationResult]:
    """Per-bullet story policy for board slide regenerate."""
    all_checks: list[AttributionCheck] = []
    drivers = normalize_allowlist(allowlist)
    cleaned: list[str] = []
    for bullet in bullets:
        rewritten, checks = _apply_story_policy_to_text(
            bullet, drivers, policy=policy
        )
        all_checks.extend(checks)
        cleaned.append(rewritten)
    return cleaned, AttributionVerificationResult(
        checks=all_checks,
        allowlist_size=len(drivers),
    )


def apply_fail_closed_attribution_to_pptx_script(
    script: str,
    allowlist: Sequence[AllowedDriver] | Mapping[str, Any] | None,
) -> tuple[str, AttributionVerificationResult]:
    """Soft-strip off-allowlist causal claims inside PPTX JS string literals.

    Layout / chart array code outside strings is ignored. Failed metric cells
    become ``—``; longer narrative literals become DONT_KNOW_ATTRIBUTION.
    Prompt 5 exports the rewritten script; optional
    ``raise_if_pptx_attribution_fully_unverifiable`` remains for strict callers.
    """
    from app.services.commentary.claim_verify import (
        _JS_STRING_RE,
        pptx_soft_strip_literal_replacement,
    )

    drivers = normalize_allowlist(allowlist)
    all_checks: list[AttributionCheck] = []

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
        local = verify_text_attribution(inner_unesc, drivers)
        all_checks.extend(local.checks)
        if local.ok:
            return raw
        replacement = pptx_soft_strip_literal_replacement(
            inner_unesc, dont_know=DONT_KNOW_ATTRIBUTION
        )
        escaped = (
            replacement.replace("\\", "\\\\")
            .replace(quote, f"\\{quote}")
            .replace("\n", "\\n")
        )
        return f"{quote}{escaped}{quote}"

    rewritten = _JS_STRING_RE.sub(_replace, script or "")
    return rewritten, AttributionVerificationResult(
        checks=all_checks,
        allowlist_size=len(drivers),
    )


def raise_if_pptx_attribution_fully_unverifiable(
    result: AttributionVerificationResult,
) -> None:
    """Optional hard-block when every causal claim in the script failed.

    Prompt 5 deck export no longer calls this (prefers soft-strip + export).
    Kept for callers that still want a strict gate; error text leads with samples.
    """
    if not result.checks:
        return
    if any(c.status == "pass" for c in result.checks):
        return
    raise CommentaryIntegrityError(
        "P15 fail-closed: Prompt 5 / PPTX script had no verifiable attribution claims; "
        f"blocking deck emit. {result.summary(max_failures=8)}",
    )


def build_attribution_package_from_text_blob(
    text: str,
    *,
    metric: str = "copilot_context_blob",
) -> dict[str, Any]:
    """Thin / weak allowlist for Copilot: known bridge labels that appear in context text.

    Honesty: this is **not** structured `_sources`. Only canonical ARR/MRR/cash component
    labels (and a few common metric names) that literally appear in the freeze/metrics
    blob are allowlisted. Invented deal stories still fail closed; many legitimate
    free-text drivers in the blob that are not in the canonical catalog will also
    fail — prefer don't-know over wrong-story packaging.
    """
    blob = (text or "").lower()
    drivers: list[AllowedDriver] = []
    seen: set[str] = set()

    catalogs: list[tuple[str, tuple[str, ...]]] = []
    for key, aliases in _MRR_COMPONENT_LABELS.items():
        catalogs.append((key, aliases))
    for key, aliases in _ARR_BRIDGE_LABELS.items():
        catalogs.append((key, aliases))
    for key, aliases in _CASH_BRIDGE_LABELS.items():
        catalogs.append((key, aliases))
    # Common board metrics that often appear as causal nouns in freeze prose.
    for key, aliases in (
        ("revenue", ("revenue",)),
        ("ending_arr", ("ending arr", "arr")),
        ("gross_margin", ("gross margin",)),
        ("ebitda", ("ebitda",)),
        ("ending_cash", ("ending cash", "cash")),
        ("pipeline", ("pipeline", "pipeline coverage")),
        ("paid_search", ("paid search",)),
        ("payroll", ("payroll",)),
    ):
        catalogs.append((key, aliases))

    for key, aliases in catalogs:
        tokens = (key.replace("_", " "),) + tuple(aliases)
        if any(t and t in blob for t in tokens):
            if key in seen:
                continue
            seen.add(key)
            drivers.append(
                _driver(
                    key,
                    key.replace("_", " ").title(),
                    source="context_blob_label",
                    aliases=aliases,
                )
            )

    return build_attribution_package(metric=metric, drivers=drivers)


def merge_attribution_packages(
    *packages: Mapping[str, Any] | None,
    metric: str = "copilot_package",
    period: str | None = None,
) -> dict[str, Any]:
    """Union attribution allowlists; first driver id wins."""
    drivers: list[AllowedDriver] = []
    seen: set[str] = set()
    resolved_period = period
    for pkg in packages:
        if not pkg:
            continue
        if resolved_period is None:
            resolved_period = str(pkg.get("period") or "") or None
        for d in normalize_allowlist(pkg):
            if d.id in seen:
                continue
            seen.add(d.id)
            drivers.append(d)
    return build_attribution_package(
        metric=metric,
        period=resolved_period,
        drivers=drivers,
    )


def build_attribution_package_from_copilot_structures(
    *,
    bundle: Any | None = None,
    cash_bridge_table: Mapping[str, Any] | None = None,
    metrics_blob: str | None = None,
    focus_period: str | None = None,
) -> dict[str, Any]:
    """Structured Copilot attribution allowlist from the same freeze/live structures.

    Sources (when present):
      - comparison_waterfalls ARR / pipeline / cash / deferred component types + amounts
      - cash_bridge_table field labels for the focus period
      - marketing channel names on the bundle
      - thin blob-label catalog as a supplement (legacy freezes)

    Named logos / deal counts come from opportunity_attribution when present;
    magnitude dominance tags the largest bridge component when share ≥ 50%.
    """
    drivers: list[AllowedDriver] = []
    period = focus_period
    seen: set[str] = set()

    def _add(
        did: str,
        label: str,
        *,
        amount: Any = None,
        source: str,
        aliases: Iterable[str] = (),
    ) -> None:
        if did in seen:
            return
        seen.add(did)
        drivers.append(
            _driver(did, label, amount=amount, source=source, aliases=aliases)
        )

    dump: Mapping[str, Any] = {}
    if bundle is not None:
        if hasattr(bundle, "model_dump"):
            dump = bundle.model_dump(mode="python", exclude_none=True)
        elif isinstance(bundle, Mapping):
            dump = bundle
        period = period or str(dump.get("as_of_period") or "") or None

        waterfalls = dump.get("comparison_waterfalls") or {}
        if isinstance(waterfalls, Mapping):
            catalog_by_key = {
                "arr": _ARR_BRIDGE_LABELS,
                "pipeline": {
                    "beginning_pipeline": ("beginning pipeline",),
                    "pipeline_created": ("pipeline created", "pipeline"),
                    "closed_won": ("closed won",),
                    "closed_lost": ("closed lost",),
                    "slipped_pipeline": ("slipped pipeline", "slipped"),
                    "ending_pipeline": ("ending pipeline",),
                },
                "cash_flow": _CASH_BRIDGE_LABELS,
                "deferred_revenue": {
                    "beginning_deferred_revenue": ("beginning deferred revenue",),
                    "billings": ("billings", "new billings"),
                    "revenue_recognized": ("revenue recognized",),
                    "ending_deferred_revenue": ("ending deferred revenue",),
                },
            }
            for wf_key, rows in waterfalls.items():
                if not isinstance(rows, list):
                    continue
                label_map = catalog_by_key.get(str(wf_key), {})
                for row in rows:
                    if not isinstance(row, Mapping):
                        continue
                    wtype = str(
                        row.get("waterfall_type") or row.get("type") or ""
                    ).strip()
                    if not wtype:
                        continue
                    row_period = str(row.get("period") or "")[:7]
                    if period and row_period and row_period != period:
                        continue
                    aliases = label_map.get(wtype, ())
                    if not aliases:
                        # Map common ARR short names.
                        aliases = _ARR_BRIDGE_LABELS.get(wtype, ()) or _MRR_COMPONENT_LABELS.get(
                            wtype, ()
                        )
                    _add(
                        _slug(wtype),
                        wtype.replace("_", " ").title(),
                        amount=row.get("amount"),
                        source=f"comparison_waterfalls.{wf_key}.{wtype}",
                        aliases=aliases + (wtype.replace("_", " ").lower(),),
                    )

        logo_names: list[str] = []
        movement_counts: dict[str, int] = {}
        for attr in dump.get("opportunity_attribution") or []:
            if not isinstance(attr, Mapping):
                continue
            for field_name in (
                "movement_type",
                "label",
                "name",
                "channel",
                "stage",
                "marketing_channel",
                "segment",
            ):
                val = str(attr.get(field_name) or "").strip()
                if val:
                    _add(
                        _slug(val),
                        val,
                        amount=attr.get("amount") or attr.get("arr_impact"),
                        source=f"opportunity_attribution.{field_name}",
                        aliases=(val.lower(),),
                    )
            for logo_field in (
                "customer_name",
                "opportunity_name",
                "account_name",
            ):
                logo = str(attr.get(logo_field) or "").strip()
                if not logo:
                    continue
                logo_names.append(logo)
                _add(
                    _slug(logo),
                    logo,
                    amount=attr.get("amount") or attr.get("arr_impact"),
                    source=f"opportunity_attribution.{logo_field}",
                    aliases=(logo.lower(), f"{logo.lower()} logo"),
                )
            move = str(
                attr.get("movement_type") or attr.get("stage") or "opportunity"
            ).strip()
            if move:
                movement_counts[move] = movement_counts.get(move, 0) + 1

        for move, count in movement_counts.items():
            move_l = move.lower()
            noun = f"{move_l} deals"
            count_aliases = list(_count_aliases(count, noun))
            count_aliases.extend(_count_aliases(count, "deals"))
            if "closed won" in move_l or move_l in {"won", "closed_won"}:
                count_aliases.extend(_count_aliases(count, "closed won deals"))
            if any(tok in move_l for tok in ("expansion", "upsell", "expand")):
                # Prefer explicit "N expansion deals" — avoid bare "upsells" substring traps.
                count_aliases.extend(_count_aliases(count, "expansion deals"))
                count_aliases.extend(_count_aliases(count, "enterprise expansion deals"))
            count_aliases = list(dict.fromkeys(count_aliases))
            if count_aliases:
                _add(
                    f"deal_count_{_slug(move)}_{count}",
                    f"{count} {move} deals",
                    amount=count,
                    source="opportunity_attribution.deal_count",
                    aliases=tuple(count_aliases),
                )

        if logo_names:
            n_logos = len(set(logo_names))
            logo_aliases = _count_aliases(n_logos, "logos") + _count_aliases(
                n_logos, "named logos"
            )
            if logo_aliases:
                _add(
                    f"named_logo_count_{n_logos}",
                    f"{n_logos} named logos",
                    amount=n_logos,
                    source="opportunity_attribution.named_logo_count",
                    aliases=logo_aliases,
                )

        mkt = dump.get("marketing_comparison") or dump.get("marketing_channel_comparison")
        if isinstance(mkt, Mapping):
            for ch in mkt.get("channels") or mkt.get("by_channel") or mkt.get("rows") or []:
                if isinstance(ch, Mapping):
                    name = str(
                        ch.get("channel") or ch.get("name") or ch.get("category") or ""
                    ).strip()
                else:
                    name = str(ch).strip()
                if name:
                    _add(
                        _slug(name),
                        name,
                        source="marketing_channels",
                        aliases=(name.lower(),),
                    )

    if isinstance(cash_bridge_table, Mapping):
        focus = period
        for scenario, periods in cash_bridge_table.items():
            if not isinstance(periods, Mapping):
                continue
            rows = periods.get(focus) if focus and focus in periods else None
            if rows is None and periods:
                rows = list(periods.values())[-1]
            if not isinstance(rows, Mapping):
                continue
            for field_name, amount in rows.items():
                key = str(field_name)
                aliases = _CASH_BRIDGE_LABELS.get(key, ())
                # Normalize cash_collections → collections etc.
                for canon, als in _CASH_BRIDGE_LABELS.items():
                    if key == canon or key.replace("_cash_out", "") in als or key in als:
                        key = canon
                        aliases = als
                        break
                _add(
                    _slug(key),
                    key.replace("_", " ").title(),
                    amount=amount,
                    source=f"cash_bridge.{scenario}.{field_name}",
                    aliases=aliases + (str(field_name).replace("_", " ").lower(),),
                )

    structured = build_attribution_package(
        metric="copilot_package",
        period=period,
        drivers=apply_magnitude_dominance(drivers),
    )
    if metrics_blob:
        blob_pkg = build_attribution_package_from_text_blob(metrics_blob)
        return merge_attribution_packages(
            structured,
            blob_pkg,
            metric="copilot_package",
            period=period,
        )
    return structured


def attribution_package_for_prompt(package: Mapping[str, Any] | None) -> dict[str, Any]:
    """LLM-facing attribution package (same allowlist post-verify uses)."""
    if not package:
        return {
            "allowed_drivers": [],
            "policy": (
                "Empty allowlist — no causal / driver claims are permitted."
            ),
        }
    return {
        "metric": package.get("metric"),
        "period": package.get("period"),
        "allowed_drivers": package.get("allowed_drivers") or [],
        "policy": package.get("policy")
        or (
            "May only name drivers whose id/label/aliases appear in allowed_drivers. "
            "Multi-driver 'and'/comma lists require EVERY named driver on the allowlist. "
            "Empty allowlist means no causal claims are permitted."
        ),
    }
