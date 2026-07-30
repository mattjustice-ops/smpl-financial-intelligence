"""P15 fail-closed numeric claim verification against engine evidence.

Extracts material numeric claims from AI narrative and checks them against a
structured evidence package (freeze / engine numbers). Actuals tolerance is
TOL_ACTUALS = $1.00 (cents–$1) — do not loosen.

Fail-closed behavior: omit / replace with an explicit don't-know — never emit
unsupported material claims. See docs/soc2/policies/P15_ai_llm_data_handling.md
and docs/soc2/controls/data_integrity_framework.md Part 5.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Literal, Mapping

from app.services.commentary.schemas import CommentaryInputs, CommentaryOutput, CommentarySection

# Closed-actuals / customer-visible money bar — do not weaken.
TOL_ACTUALS = Decimal("1.00")
# Rates / percentages: absolute band on the ratio form (1.05 or 0.10).
TOL_RATIO = Decimal("0.0005")
# Display percent points when evidence stores whole percents (e.g. 10 for 10%).
TOL_PERCENT_POINTS = Decimal("0.05")

DONT_KNOW_NARRATIVE = (
    "I don't know — one or more numeric claims in this section could not be verified "
    "against engine evidence for the current package. Unsupported figures were omitted."
)

ClaimKind = Literal["money", "percent", "ratio", "count"]
CheckStatus = Literal["pass", "mismatch", "missing_evidence"]


@dataclass(frozen=True)
class NumericClaim:
    stated: str
    value: Decimal
    kind: ClaimKind


@dataclass(frozen=True)
class ClaimCheck:
    claim: NumericClaim
    status: CheckStatus
    matched_key: str | None = None
    matched_value: Decimal | None = None
    diff: Decimal | None = None


@dataclass
class VerificationResult:
    checks: list[ClaimCheck] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    @property
    def failures(self) -> list[ClaimCheck]:
        return [c for c in self.checks if c.status != "pass"]

    @property
    def mismatch_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "mismatch")

    @property
    def missing_evidence_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "missing_evidence")

    def summary(self) -> str:
        if self.ok:
            return "all material numeric claims verified"
        parts: list[str] = []
        for c in self.failures:
            mv = c.matched_value
            parts.append(
                f"{c.claim.stated} ({c.status}"
                + (f", nearest={mv}" if mv is not None else "")
                + ")"
            )
        return "; ".join(parts)


# Prefer explicit currency / compact forms first.
_MONEY_WITH_SUFFIX = re.compile(
    r"(?<![A-Za-z0-9])\$?\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?\s*([KkMmBb])\b"
)
_MONEY_DOLLAR = re.compile(r"\$\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?\b")
_PERCENT_RE = re.compile(r"(?<![A-Za-z0-9])(\d+(?:\.\d+)?)\s*%")
_MULTIPLIER_RE = re.compile(r"(?<![A-Za-z0-9\$])(\d+(?:\.\d+)?)\s*x\b", re.IGNORECASE)
_RATIO_RE = re.compile(r"(?<![A-Za-z0-9\$])(\d+\.\d{2,4})(?!\s*[%MmBbKkXx])\b")
_YEAR_RE = re.compile(r"^(19|20)\d{2}$")


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        text = value.strip().replace(",", "").replace("$", "").replace("%", "")
        if not text:
            return None
        mult = Decimal("1")
        if text[-1:] in "KkMmBb" and text[:-1].replace(".", "", 1).isdigit():
            suffix = text[-1].upper()
            text = text[:-1]
            mult = {"K": Decimal("1000"), "M": Decimal("1000000"), "B": Decimal("1000000000")}[suffix]
        try:
            return Decimal(text) * mult
        except InvalidOperation:
            return None
    return None


def _scale_suffix(suffix: str | None) -> Decimal:
    if not suffix:
        return Decimal("1")
    return {
        "K": Decimal("1000"),
        "M": Decimal("1000000"),
        "B": Decimal("1000000000"),
    }[suffix.upper()]


def flatten_evidence_values(
    obj: Any,
    *,
    prefix: str = "",
    out: dict[str, Decimal] | None = None,
) -> dict[str, Decimal]:
    """Recursively collect numeric leaves into a flat key → Decimal map."""
    if out is None:
        out = {}
    if obj is None:
        return out
    if isinstance(obj, Mapping):
        for key, val in obj.items():
            # Skip nested provenance blobs that duplicate values under metadata-only keys.
            if str(key) in {"_sources", "sources", "loaded_at", "table", "column", "org_id", "note"}:
                if str(key) == "_sources" and isinstance(val, Mapping):
                    flatten_evidence_values(val, prefix=f"{prefix}_sources" if prefix else "_sources", out=out)
                continue
            child = f"{prefix}.{key}" if prefix else str(key)
            flatten_evidence_values(val, prefix=child, out=out)
        return out
    if isinstance(obj, (list, tuple)):
        for idx, val in enumerate(obj):
            flatten_evidence_values(val, prefix=f"{prefix}[{idx}]", out=out)
        return out
    # Pydantic models
    model_dump = getattr(obj, "model_dump", None)
    if callable(model_dump):
        return flatten_evidence_values(model_dump(mode="python"), prefix=prefix, out=out)
    num = _to_decimal(obj)
    if num is not None and prefix:
        out[prefix] = num
    return out


def build_evidence_package(
    inputs: CommentaryInputs | Mapping[str, Any] | None,
    *,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Structured evidence dict passed to the LLM and reused for post-verify.

    Shape:
      {
        "values": {dotted_key: number, ...},
        "freeze_id": optional,
        "period_label": optional,
        "tolerance_actuals": "1.00",
      }
    """
    values: dict[str, Decimal] = {}
    period_label: str | None = None
    freeze_id: str | None = None

    if isinstance(inputs, CommentaryInputs):
        period_label = inputs.period_label
        flatten_evidence_values(inputs.model_dump(mode="python", exclude_none=True), out=values)
    elif isinstance(inputs, Mapping):
        period_label = str(inputs.get("period_label") or inputs.get("close_period") or "") or None
        freeze_id = (
            str(inputs.get("freeze_id") or inputs.get("freezeId") or "").strip() or None
        )
        flatten_evidence_values(inputs, out=values)

    if extra:
        freeze_id = freeze_id or (str(extra.get("freeze_id") or "").strip() or None)
        flatten_evidence_values(extra, prefix="extra", out=values)

    # Drop non-financial identifiers that look numeric (e.g. bare years in labels).
    cleaned = {
        k: v
        for k, v in values.items()
        if not (v == v.to_integral_value() and _YEAR_RE.match(str(int(v))))
    }

    return {
        "values": {k: str(v) for k, v in cleaned.items()},
        "values_decimal": cleaned,
        "period_label": period_label,
        "freeze_id": freeze_id,
        "tolerance_actuals": str(TOL_ACTUALS),
        "tolerance_ratio": str(TOL_RATIO),
    }


def evidence_values_from_package(package: Mapping[str, Any]) -> dict[str, Decimal]:
    raw = package.get("values_decimal")
    if isinstance(raw, dict) and raw:
        return {str(k): (v if isinstance(v, Decimal) else Decimal(str(v))) for k, v in raw.items()}
    values = package.get("values") or {}
    out: dict[str, Decimal] = {}
    if isinstance(values, Mapping):
        for k, v in values.items():
            num = _to_decimal(v)
            if num is not None:
                out[str(k)] = num
    return out


def _parse_money_groups(whole: str, frac: str | None, suffix: str | None) -> Decimal | None:
    try:
        raw = Decimal(whole.replace(",", ""))
        if frac:
            raw = Decimal(f"{whole.replace(',', '')}.{frac}")
        return raw * _scale_suffix(suffix)
    except InvalidOperation:
        return None


def extract_numeric_claims(text: str) -> list[NumericClaim]:
    """Extract material numeric claims ($ amounts, percents, financial ratios)."""
    if not text:
        return []
    claims: list[NumericClaim] = []
    occupied: list[tuple[int, int]] = []

    def _overlap(start: int, end: int) -> bool:
        return any(not (end <= a or start >= b) for a, b in occupied)

    def _add(stated: str, value: Decimal, kind: ClaimKind, start: int, end: int) -> None:
        if _overlap(start, end):
            return
        occupied.append((start, end))
        claims.append(NumericClaim(stated=stated.strip(), value=value, kind=kind))

    for m in _PERCENT_RE.finditer(text):
        try:
            pct = Decimal(m.group(1))
        except InvalidOperation:
            continue
        _add(m.group(0), pct, "percent", m.start(), m.end())

    for m in _MONEY_WITH_SUFFIX.finditer(text):
        value = _parse_money_groups(m.group(1), m.group(2), m.group(3))
        if value is None:
            continue
        _add(m.group(0), value, "money", m.start(), m.end())

    for m in _MONEY_DOLLAR.finditer(text):
        value = _parse_money_groups(m.group(1), m.group(2), None)
        if value is None:
            continue
        _add(m.group(0), value, "money", m.start(), m.end())

    for m in _MULTIPLIER_RE.finditer(text):
        try:
            value = Decimal(m.group(1))
        except InvalidOperation:
            continue
        _add(m.group(0), value, "ratio", m.start(), m.end())

    for m in _RATIO_RE.finditer(text):
        token = m.group(1)
        if _YEAR_RE.match(token.split(".")[0]) and len(token.split(".")[0]) == 4:
            continue
        try:
            value = Decimal(token)
        except InvalidOperation:
            continue
        # Likely financial ratio / rate (NRR 1.05, magic number 0.73).
        if value > Decimal("100"):
            continue
        _add(m.group(0), value, "ratio", m.start(), m.end())

    return claims


def _candidates_for_claim(claim: NumericClaim) -> list[tuple[Decimal, Decimal]]:
    """Return (candidate_value, tolerance) pairs to try against evidence."""
    if claim.kind == "money":
        return [(claim.value, TOL_ACTUALS)]
    if claim.kind == "percent":
        ratio = claim.value / Decimal("100")
        return [
            (ratio, TOL_RATIO),
            (claim.value, TOL_PERCENT_POINTS),  # evidence stored as 10 for 10%
        ]
    if claim.kind == "ratio":
        return [
            (claim.value, TOL_RATIO),
            (claim.value * Decimal("100"), TOL_PERCENT_POINTS),  # stated 1.05 vs evidence 105
        ]
    # count
    return [(claim.value, TOL_ACTUALS)]


def _best_match(
    claim: NumericClaim,
    evidence: Mapping[str, Decimal],
) -> ClaimCheck:
    if not evidence:
        return ClaimCheck(claim=claim, status="missing_evidence")

    best_key: str | None = None
    best_val: Decimal | None = None
    best_diff: Decimal | None = None
    matched = False

    for candidate, tol in _candidates_for_claim(claim):
        for key, ev in evidence.items():
            diff = abs(ev - candidate)
            if diff <= tol:
                matched = True
                if best_diff is None or diff < best_diff:
                    best_key, best_val, best_diff = key, ev, diff
        # Also accept scaled money display (evidence 110000 vs claim 110 when stated as $110k already scaled).
        if claim.kind == "money":
            for scale in (Decimal("1000"), Decimal("1000000"), Decimal("1000000000")):
                scaled = claim.value  # already scaled in extract
                for key, ev in evidence.items():
                    diff = abs(ev - scaled)
                    if diff <= tol and (best_diff is None or diff < best_diff):
                        matched = True
                        best_key, best_val, best_diff = key, ev, diff

    if matched:
        return ClaimCheck(
            claim=claim,
            status="pass",
            matched_key=best_key,
            matched_value=best_val,
            diff=best_diff,
        )

    # Nearest for diagnostics
    nearest_key = None
    nearest_val = None
    nearest_diff = None
    for candidate, _tol in _candidates_for_claim(claim):
        for key, ev in evidence.items():
            diff = abs(ev - candidate)
            if nearest_diff is None or diff < nearest_diff:
                nearest_key, nearest_val, nearest_diff = key, ev, diff

    return ClaimCheck(
        claim=claim,
        status="mismatch",
        matched_key=nearest_key,
        matched_value=nearest_val,
        diff=nearest_diff,
    )


def verify_text_against_evidence(
    text: str,
    evidence: Mapping[str, Decimal] | Mapping[str, Any],
    *,
    money_tolerance: Decimal = TOL_ACTUALS,
) -> VerificationResult:
    """Check material numeric claims in text against evidence values."""
    if money_tolerance != TOL_ACTUALS:
        # Guardrail: callers must not silently loosen the actuals bar.
        raise ValueError(
            f"money_tolerance must remain TOL_ACTUALS ({TOL_ACTUALS}); got {money_tolerance}"
        )

    if hasattr(evidence, "get") and "values_decimal" in evidence:
        values = evidence_values_from_package(evidence)  # type: ignore[arg-type]
    else:
        values = {}
        for k, v in evidence.items():
            num = v if isinstance(v, Decimal) else _to_decimal(v)
            if num is not None:
                values[str(k)] = num

    checks = [_best_match(claim, values) for claim in extract_numeric_claims(text)]
    return VerificationResult(checks=checks)


def fail_closed_text(text: str, result: VerificationResult | None = None, *, evidence: Mapping[str, Any] | None = None) -> str:
    """If any claim fails, replace the whole text with don't-know (omit unsupported claims)."""
    if result is None:
        if evidence is None:
            raise ValueError("fail_closed_text requires result or evidence")
        result = verify_text_against_evidence(text, evidence)
    if result.ok:
        return text
    return DONT_KNOW_NARRATIVE


def _section_texts(section: CommentarySection) -> Iterable[str]:
    yield section.narrative
    for c in section.citations:
        yield c.value


def verify_commentary_output(
    output: CommentaryOutput,
    evidence: Mapping[str, Decimal] | Mapping[str, Any],
) -> VerificationResult:
    """Verify all customer-visible narrative fields on CommentaryOutput."""
    blobs: list[str] = []
    for section in (
        output.executive_summary,
        output.revenue_commentary,
        output.mrr_waterfall_commentary,
        output.bookings_forecast_commentary,
        output.cash_forecast_commentary,
    ):
        blobs.extend(_section_texts(section))
    for item in output.risks_and_opportunities:
        blobs.append(item.description)
        blobs.append(item.evidence)
    for item in output.followup_questions:
        blobs.append(item.question)
        blobs.append(item.rationale)

    combined = "\n".join(blobs)
    return verify_text_against_evidence(combined, evidence)


def apply_fail_closed_to_commentary(
    output: CommentaryOutput,
    evidence: Mapping[str, Decimal] | Mapping[str, Any],
) -> tuple[CommentaryOutput, VerificationResult]:
    """Strip / don't-know any section whose material claims fail verification.

    Returns the (possibly rewritten) output plus the aggregate verification result.
    Empty evidence + material claims → don't-know (missing evidence).
    """
    overall = verify_commentary_output(output, evidence)
    if overall.ok:
        return output, overall

    data = output.model_dump(mode="python")

    def _rewrite_section(key: str) -> None:
        section = data[key]
        text_blob = section.get("narrative", "") + "\n" + "\n".join(
            c.get("value", "") for c in (section.get("citations") or [])
        )
        local = verify_text_against_evidence(text_blob, evidence)
        if not local.ok:
            section["narrative"] = DONT_KNOW_NARRATIVE
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
        local = verify_text_against_evidence(
            f"{item.get('description', '')}\n{item.get('evidence', '')}",
            evidence,
        )
        if local.ok:
            cleaned_risks.append(item)
        else:
            cleaned_risks.append(
                {
                    **item,
                    "description": DONT_KNOW_NARRATIVE,
                    "evidence": "Unverified numeric claim omitted (P15 fail-closed).",
                }
            )
    data["risks_and_opportunities"] = cleaned_risks

    cleaned_qs = []
    for item in data.get("followup_questions") or []:
        local = verify_text_against_evidence(
            f"{item.get('question', '')}\n{item.get('rationale', '')}",
            evidence,
        )
        if local.ok:
            cleaned_qs.append(item)
        else:
            cleaned_qs.append(
                {
                    **item,
                    "question": "Which engine-backed figures should replace the unverified claims above?",
                    "rationale": "Prior question referenced numbers that failed P15 evidence verification.",
                }
            )
    data["followup_questions"] = cleaned_qs

    return CommentaryOutput.model_validate(data), overall


def verify_nested_commentary_strings(
    commentary: Mapping[str, Any],
    evidence: Mapping[str, Decimal] | Mapping[str, Any],
) -> tuple[dict[str, Any], VerificationResult]:
    """Walk MD&A-style nested commentary JSON; fail-closed rewrite string leaves."""
    all_checks: list[ClaimCheck] = []

    def _walk(node: Any) -> Any:
        if isinstance(node, Mapping):
            return {k: _walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_walk(v) for v in node]
        if isinstance(node, str):
            result = verify_text_against_evidence(node, evidence)
            all_checks.extend(result.checks)
            return fail_closed_text(node, result)
        return node

    rewritten = _walk(dict(commentary))
    return rewritten, VerificationResult(checks=all_checks)


# JS string literals in PptxGenJS scripts (single- or double-quoted).
_JS_STRING_RE = re.compile(r"""(['"])(?:\\.|(?!\1).)*?\1""", re.DOTALL)
# Bare integers / decimals common in freeze / metrics blobs (no $ required).
_BLOB_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9])(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+\.\d{2,4}|-?\d{4,})(?!\s*[%Xx])"
)


def extract_js_string_literal_text(script: str) -> str:
    """Concatenate JS string literal contents for claim extraction (skip layout code)."""
    if not script:
        return ""
    parts: list[str] = []
    for m in _JS_STRING_RE.finditer(script):
        raw = m.group(0)
        # Strip surrounding quotes; unescape common sequences lightly.
        inner = raw[1:-1]
        inner = (
            inner.replace(r"\'", "'")
            .replace(r'\"', '"')
            .replace(r"\n", " ")
            .replace(r"\t", " ")
        )
        parts.append(inner)
    return "\n".join(parts)


def evidence_values_from_text_blob(text: str) -> dict[str, Decimal]:
    """Build an evidence allowlist from a metrics/freeze text blob.

    Used when Copilot (or similar) has prose context rather than structured JSON.
    Every material numeric token in the blob is treated as allowable evidence.
    """
    out: dict[str, Decimal] = {}
    if not text:
        return out
    for i, claim in enumerate(extract_numeric_claims(text)):
        out[f"blob_claim[{i}].{claim.kind}"] = claim.value
    for i, m in enumerate(_BLOB_NUMBER_RE.finditer(text)):
        num = _to_decimal(m.group(1))
        if num is None:
            continue
        # Skip bare calendar years.
        if num == num.to_integral_value() and _YEAR_RE.match(str(int(num))):
            continue
        out[f"blob_num[{i}]"] = num
    return out


def _package_from_values(
    values: dict[str, Decimal],
    *,
    period_label: str | None = None,
    freeze_id: str | None = None,
) -> dict[str, Any]:
    cleaned = {
        k: v
        for k, v in values.items()
        if not (v == v.to_integral_value() and _YEAR_RE.match(str(int(v))))
    }
    return {
        "values": {k: str(v) for k, v in cleaned.items()},
        "values_decimal": cleaned,
        "period_label": period_label,
        "freeze_id": freeze_id,
        "tolerance_actuals": str(TOL_ACTUALS),
        "tolerance_ratio": str(TOL_RATIO),
    }


def merge_evidence_values(
    *maps: Mapping[str, Decimal] | None,
) -> dict[str, Decimal]:
    """Union evidence maps; later maps overwrite on key collision."""
    out: dict[str, Decimal] = {}
    for m in maps:
        if not m:
            continue
        for k, v in m.items():
            out[str(k)] = v if isinstance(v, Decimal) else Decimal(str(v))
    return out


def build_evidence_package_from_copilot_structures(
    *,
    bundle: Any | None = None,
    ts_data: Mapping[str, Any] | None = None,
    cash_bridge_table: Mapping[str, Any] | None = None,
    metrics_blob: str | None = None,
    focus_period: str | None = None,
    freeze_id: str | None = None,
    period_label: str | None = None,
) -> dict[str, Any]:
    """Structured evidence for Copilot — flatten freeze/live metric structures.

    Prefer dotted metric keys from ReportingBundle / TS_DATA / cash bridge (same
    structures used to render the metrics blob). Optionally union blob-scrape
    numbers so display formatting already present in prose still verifies.

    Honest gap: still not full per-metric warehouse ``_sources`` provenance —
    keys are engine field paths, not table/column citations.
    """
    values: dict[str, Decimal] = {}
    period = focus_period
    label = period_label

    if bundle is not None:
        dump: Mapping[str, Any]
        if hasattr(bundle, "model_dump"):
            dump = bundle.model_dump(mode="python", exclude_none=True)
        elif isinstance(bundle, Mapping):
            dump = bundle
        else:
            dump = {}
        period = period or str(dump.get("as_of_period") or dump.get("focus_period") or "") or None
        label = label or str(dump.get("period_label") or period or "") or None
        # Executive KPIs + waterfalls + statements — skip heavy GL/headcount lists.
        for key in (
            "executive_flow",
            "financial_statements",
            "comparison_financial_statements",
            "opportunity_attribution",
        ):
            block = dump.get(key)
            if block is not None:
                flatten_evidence_values(block, prefix=f"bundle.{key}", out=values)

        # Waterfalls: use waterfall_type in the key so evidence paths are readable
        # (arr.expansion.amount) rather than anonymous list indices only.
        waterfalls = dump.get("comparison_waterfalls") or {}
        if isinstance(waterfalls, Mapping):
            for wf_key, rows in waterfalls.items():
                if not isinstance(rows, list):
                    flatten_evidence_values(
                        rows, prefix=f"bundle.comparison_waterfalls.{wf_key}", out=values
                    )
                    continue
                for idx, row in enumerate(rows):
                    if not isinstance(row, Mapping):
                        continue
                    wtype = str(row.get("waterfall_type") or row.get("type") or idx)
                    period_key = str(row.get("period") or "")[:7] or "period"
                    scenario = str(row.get("scenario") or "Actual")
                    prefix = (
                        f"bundle.comparison_waterfalls.{wf_key}."
                        f"{wtype}.{scenario}.{period_key}"
                    )
                    flatten_evidence_values(row, prefix=prefix, out=values)

    if isinstance(ts_data, Mapping):
        actual = ts_data.get("Actual") or {}
        if isinstance(actual, Mapping):
            focus = period
            for stmt in ("is", "bs", "cfs"):
                rows = actual.get(stmt) or {}
                if not isinstance(rows, Mapping):
                    continue
                if focus and focus in rows:
                    flatten_evidence_values(
                        rows[focus],
                        prefix=f"ts.Actual.{stmt}.{focus}",
                        out=values,
                    )
                else:
                    # Keep a bounded flatten when focus missing (close month only).
                    for p, row in list(rows.items())[-3:]:
                        flatten_evidence_values(
                            row,
                            prefix=f"ts.Actual.{stmt}.{p}",
                            out=values,
                        )

    if isinstance(cash_bridge_table, Mapping):
        focus = period
        # Shape: {scenario: {period: {field: amount}}}
        for scenario, periods in cash_bridge_table.items():
            if not isinstance(periods, Mapping):
                continue
            if focus and focus in periods:
                flatten_evidence_values(
                    periods[focus],
                    prefix=f"cash_bridge.{scenario}.{focus}",
                    out=values,
                )
            elif focus is None:
                for p, row in list(periods.items())[-2:]:
                    flatten_evidence_values(
                        row,
                        prefix=f"cash_bridge.{scenario}.{p}",
                        out=values,
                    )

    if metrics_blob:
        blob_vals = evidence_values_from_text_blob(metrics_blob)
        for k, v in blob_vals.items():
            values[f"blob.{k}"] = v

    return _package_from_values(values, period_label=label, freeze_id=freeze_id)


def evidence_package_for_prompt(package: Mapping[str, Any] | None) -> dict[str, Any]:
    """LLM-facing evidence (omit Decimal map). Cap size for interactive prompts."""
    if not package:
        return {"values": {}, "tolerance_actuals": str(TOL_ACTUALS)}
    values = package.get("values") or {}
    if isinstance(values, Mapping) and len(values) > 400:
        # Prefer structured keys over anonymous blob scrape when capping.
        structured = {k: v for k, v in values.items() if not str(k).startswith("blob.")}
        blob = {k: v for k, v in values.items() if str(k).startswith("blob.")}
        keep = dict(list(structured.items())[:350])
        keep.update(dict(list(blob.items())[:50]))
        values = keep
    return {
        "period_label": package.get("period_label"),
        "freeze_id": package.get("freeze_id"),
        "tolerance_actuals": package.get("tolerance_actuals") or str(TOL_ACTUALS),
        "values": values,
        "policy": (
            "State only numeric values present in values (within $1.00 for money). "
            "Post-LLM verify uses this same package. Not full warehouse _sources."
        ),
    }


def verify_pptx_script_against_evidence(
    script: str,
    evidence: Mapping[str, Decimal] | Mapping[str, Any],
    *,
    fail_closed: bool = True,
) -> VerificationResult:
    """Verify money/%/multiplier claims in PPTX script *string literals* vs evidence.

    Layout coordinates and chart array literals are ignored (they are not customer
    narrative). Invented display figures in addText / titles are caught.
    With ``fail_closed=True``, raises ``CommentaryIntegrityError`` on any failure.
    """
    display_text = extract_js_string_literal_text(script)
    # Prefer money / percent / multiplier — drop bare ratio tokens that often appear
    # as font sizes or layout fractions inside stringified CSS-ish snippets.
    claims = [
        c
        for c in extract_numeric_claims(display_text)
        if c.kind in ("money", "percent") or (c.kind == "ratio" and "x" in c.stated.lower())
    ]
    if hasattr(evidence, "get") and "values_decimal" in evidence:
        values = evidence_values_from_package(evidence)  # type: ignore[arg-type]
    else:
        values = {}
        for k, v in evidence.items():
            num = v if isinstance(v, Decimal) else _to_decimal(v)
            if num is not None:
                values[str(k)] = num

    checks = [_best_match(claim, values) for claim in claims]
    result = VerificationResult(checks=checks)
    if fail_closed and not result.ok:
        raise CommentaryIntegrityError(
            "P15 fail-closed: Prompt 5 / PPTX script numeric claims failed evidence verify: "
            + result.summary(),
            result=result,
        )
    return result


def apply_fail_closed_to_bullet_list(
    bullets: list[str],
    evidence: Mapping[str, Decimal] | Mapping[str, Any],
) -> tuple[list[str], VerificationResult]:
    """Per-bullet don't-know rewrite for board slide regenerate."""
    all_checks: list[ClaimCheck] = []
    cleaned: list[str] = []
    for bullet in bullets:
        local = verify_text_against_evidence(bullet, evidence)
        all_checks.extend(local.checks)
        if local.ok:
            cleaned.append(bullet)
        else:
            cleaned.append(DONT_KNOW_NARRATIVE)
    return cleaned, VerificationResult(checks=all_checks)


class CommentaryIntegrityError(Exception):
    """Raised when fail-closed policy blocks emit entirely (hard gate)."""

    def __init__(self, message: str, *, result: VerificationResult | None = None) -> None:
        super().__init__(message)
        self.result = result
