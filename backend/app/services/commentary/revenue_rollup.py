"""Revenue roll-up analysis.

The engine marks the relationships that are true inside the revenue section.
The model may say those relationships. A paragraph that adds a cause, a
"largely," or a number from outside the section is rejected, and the row
keeps the calculated sentence.
"""

from __future__ import annotations

import copy
import json
import math
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.commentary.attribution_verify import verify_text_attribution
from app.services.commentary.openai_client import LLMError

MATERIALITY_DEFAULT = 10_000

ROLLUP_SYSTEM = """You write one paragraph of revenue analysis for a close review.

Use only the JSON evidence. The relationships are already decided:
- with_total: that line moved with revenue. You may cite its variance and its facts.
- offset: that line moved against revenue. Say it offset revenue. Say "largely" or "nearly flat" only when largely is true. When partly is true, say the offset is partial.
- unexplained: include that amount and say it is unexplained. Do not invent a reason for it.

State the revenue variance in whole dollars. Write every amount in whole dollars with commas. Do not use millions, billions, or percentages. You may leave out a line marked immaterial. Do not add a future period, or a cause whose name is not a label in the evidence. Do not mention hiring, pipeline, or anything absent from the evidence.

Return only JSON: {"paragraph": "..."}"""


class RevenueFactIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str = ""
    current: float | None = None
    base: float | None = None
    amount: float | None = None
    heads: float | None = None
    paid: float | None = None
    quota: float | None = None


class RevenueDriverIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str = ""
    variance: float | None = None


class RevenueLineIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str
    current: float | None = None
    comparison_amount: float | None = None
    variance: float | None = None
    facts: list[RevenueFactIn] = Field(default_factory=list)
    drivers: list[RevenueDriverIn] = Field(default_factory=list)


class RevenueParentIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str = "Revenue"
    current: float | None = None
    comparison_amount: float | None = None
    variance: float | None = None


class RevenueSectionIn(BaseModel):
    comparison: str = ""
    materiality: float = MATERIALITY_DEFAULT
    parent: RevenueParentIn
    lines: list[RevenueLineIn] = Field(default_factory=list)


class RevenueRollupResult(BaseModel):
    status: str
    paragraph: str = ""
    reason: str = ""
    evidence: dict[str, Any]


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _aliases(label: str) -> list[str]:
    text = label.lower()
    aliases = [label]
    if "subscription" in text:
        aliases.extend(["subscription", "subscription revenue"])
    if "recurring" in text or "service" in text:
        aliases.extend(["recurring services", "services", "services revenue"])
    if "implementation" in text or "onboarding" in text:
        aliases.extend(["implementation", "onboarding", "implementation and onboarding"])
    return list(dict.fromkeys(aliases))


def _fact_payload(fact: RevenueFactIn) -> dict[str, Any]:
    payload: dict[str, Any] = {"label": fact.label}
    for key in ("current", "base", "amount", "heads", "paid", "quota"):
        value = _number(getattr(fact, key))
        if value is not None:
            payload[key] = value
    return payload


def _remember(allowed: set[float], value: Any) -> None:
    number = _number(value)
    if number is None:
        return
    allowed.add(round(abs(number), 4))
    allowed.add(float(abs(round(number))))


def build_revenue_evidence(section: RevenueSectionIn) -> dict[str, Any]:
    materiality = section.materiality if section.materiality and section.materiality > 0 else MATERIALITY_DEFAULT
    parent_variance = _number(section.parent.variance)
    lines_out: list[dict[str, Any]] = []
    allowed: set[float] = set()
    _remember(allowed, section.parent.current)
    _remember(allowed, section.parent.comparison_amount)
    _remember(allowed, parent_variance)
    for year in re.findall(r"\d{4}", section.comparison or ""):
        allowed.add(float(year))

    prepared: list[dict[str, Any]] = []
    child_sum = 0.0
    counted = 0
    for line in section.lines:
        variance = _number(line.variance)
        facts = [_fact_payload(fact) for fact in line.facts if fact.label]
        drivers = []
        for driver in line.drivers:
            driver_variance = _number(driver.variance)
            if not driver.label or driver_variance is None:
                continue
            drivers.append({"label": driver.label, "variance": driver_variance})
            _remember(allowed, driver_variance)
        for fact in facts:
            for key in ("current", "base", "amount", "heads", "paid", "quota"):
                if key in fact:
                    _remember(allowed, fact[key])
        _remember(allowed, line.current)
        _remember(allowed, line.comparison_amount)
        _remember(allowed, variance)
        unexplained = _unexplained(variance, facts, drivers, materiality)
        if variance is not None:
            child_sum += variance
            counted += 1
        if unexplained is not None:
            _remember(allowed, unexplained)
        prepared.append(
            {
                "label": line.label,
                "aliases": _aliases(line.label),
                "current": _number(line.current),
                "comparison_amount": _number(line.comparison_amount),
                "variance": variance,
                "material": variance is not None and abs(variance) >= materiality,
                "facts": facts,
                "drivers": drivers,
                "unexplained": unexplained,
            }
        )

    material = [line for line in prepared if line["material"] and line["variance"] is not None]
    primary = 0
    if material:
        primary = _sign(max(material, key=lambda line: abs(line["variance"]))["variance"])
    elif parent_variance:
        primary = _sign(parent_variance)

    offset_abs = sum(abs(line["variance"]) for line in material if _sign(line["variance"]) not in (0, primary))
    largely = bool(offset_abs >= materiality and parent_variance is not None and abs(parent_variance) <= offset_abs * 0.25)
    partly = bool(offset_abs >= materiality and not largely)

    relationships: list[dict[str, Any]] = []
    for line in sorted(material, key=lambda item: abs(item["variance"]), reverse=True):
        kind = "with_total" if _sign(line["variance"]) in (0, primary) else "offset"
        item = {
            "kind": kind,
            "label": line["label"],
            "variance": line["variance"],
            "facts": line["facts"],
        }
        if kind == "offset":
            item["largely"] = largely
            item["partly"] = partly
        relationships.append(item)
        if line["unexplained"] is not None and abs(line["unexplained"]) >= materiality:
            relationships.append(
                {
                    "kind": "unexplained",
                    "label": line["label"],
                    "amount": line["unexplained"],
                    "must_name": True,
                }
            )

    if parent_variance is not None and counted:
        gap = parent_variance - child_sum
        _remember(allowed, gap)
        if abs(gap) >= materiality:
            relationships.append(
                {
                    "kind": "unexplained",
                    "label": "Other revenue",
                    "amount": gap,
                    "must_name": True,
                }
            )

    for line in prepared:
        lines_out.append({key: value for key, value in line.items() if key != "unexplained" or value is not None})

    return {
        "comparison": section.comparison,
        "materiality": materiality,
        "parent": {
            "label": section.parent.label or "Revenue",
            "current": _number(section.parent.current),
            "comparison_amount": _number(section.parent.comparison_amount),
            "variance": parent_variance,
        },
        "lines": lines_out,
        "relationships": relationships,
        "largely": largely,
        "allowed_numbers": sorted(allowed),
    }


def _unexplained(
    variance: float | None,
    facts: list[dict[str, Any]],
    drivers: list[dict[str, Any]],
    materiality: float,
) -> float | None:
    if variance is None:
        return None
    if facts:
        return None
    if drivers:
        cited = sum(driver["variance"] for driver in drivers)
        rest = variance - cited
        if abs(rest) >= 1:
            return rest
        return None
    if abs(variance) >= materiality:
        return variance
    return None


_NUMBER_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
_LARGELY_RE = re.compile(r"\b(?:largely|nearly flat|almost flat)\b", re.IGNORECASE)


def _stated_numbers(paragraph: str) -> list[float]:
    cleaned = paragraph.replace("−", "-").replace("–", "-")
    found = []
    for match in _NUMBER_RE.finditer(cleaned):
        raw = match.group(0).replace(",", "")
        try:
            found.append(abs(float(raw)))
        except ValueError:
            continue
    return found


def _number_allowed(stated: float, allowed: set[float]) -> bool:
    for item in allowed:
        if abs(stated - item) <= 0.51:
            return True
    return False


def _amount_named(paragraph: str, amount: float) -> bool:
    whole = int(abs(round(amount)))
    compact = paragraph.replace("−", "-").replace("–", "-").replace(",", "")
    return re.search(rf"(?<!\d){whole}(?!\d)", compact) is not None


def check_revenue_paragraph(paragraph: str, evidence: dict[str, Any]) -> tuple[bool, str]:
    text = (paragraph or "").strip()
    if not text:
        return False, "The analysis did not return a paragraph."
    parent_variance = _number((evidence.get("parent") or {}).get("variance"))
    if parent_variance is not None and abs(round(parent_variance)) >= 1 and not _amount_named(text, parent_variance):
        return False, "The analysis leaves out the revenue variance."
    allowed = {float(item) for item in evidence.get("allowed_numbers") or []}
    for stated in _stated_numbers(text):
        if not _number_allowed(stated, allowed):
            return False, f"The analysis uses {stated:g}, which is not in the revenue evidence."
    if not evidence.get("largely") and _LARGELY_RE.search(text):
        return False, "The analysis calls the move largely offset, and the evidence does not."
    for relationship in evidence.get("relationships") or []:
        if relationship.get("kind") != "unexplained" or not relationship.get("must_name"):
            continue
        amount = _number(relationship.get("amount"))
        if amount is not None and abs(amount) >= 1 and not _amount_named(text, amount):
            return False, f"The analysis leaves out the unexplained {abs(round(amount)):,.0f}."
    drivers = []
    for line in evidence.get("lines") or []:
        label = str(line.get("label") or "")
        if label:
            drivers.append({"id": label, "label": label, "aliases": line.get("aliases") or []})
        for fact in line.get("facts") or []:
            fact_label = str(fact.get("label") or "")
            if fact_label:
                drivers.append({"id": fact_label, "label": fact_label, "aliases": []})
        for driver in line.get("drivers") or []:
            driver_label = str(driver.get("label") or "")
            if driver_label:
                drivers.append({"id": driver_label, "label": driver_label, "aliases": []})
    attribution = verify_text_attribution(text, {"allowed_drivers": drivers})
    if not attribution.ok:
        return False, "The analysis names a cause the revenue evidence does not support."
    return True, ""


def _display_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    shown = copy.deepcopy(evidence)
    shown.pop("allowed_numbers", None)
    for line in shown.get("lines") or []:
        line.pop("aliases", None)
    return shown


def analyze_revenue_rollup(section: RevenueSectionIn, client: Any | None) -> RevenueRollupResult:
    evidence = build_revenue_evidence(section)
    shown = _display_evidence(evidence)
    if client is None:
        return RevenueRollupResult(
            status="fallback",
            reason="No analysis model is configured. Showing the calculated sentence.",
            evidence=shown,
        )
    try:
        raw = client.generate(system_prompt=ROLLUP_SYSTEM, user_prompt=json.dumps(shown, default=str))
    except (LLMError, Exception):
        return RevenueRollupResult(
            status="fallback",
            reason="The analysis is unavailable. Showing the calculated sentence.",
            evidence=shown,
        )
    paragraph = str(raw.get("paragraph") or "").strip() if isinstance(raw, dict) else ""
    ok, reason = check_revenue_paragraph(paragraph, evidence)
    if not ok:
        return RevenueRollupResult(status="fallback", reason=reason, evidence=shown)
    return RevenueRollupResult(status="ai", paragraph=paragraph, evidence=shown)
