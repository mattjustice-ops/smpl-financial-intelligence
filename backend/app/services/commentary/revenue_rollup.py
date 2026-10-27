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

Use only the JSON evidence. Name every relationship and its variance, including a smaller line. Those lines are how the total was reached.
- with_total: that line moved with revenue. You may cite its variance and its facts.
- offset: that line moved against revenue. Say it offset revenue. Say "largely" or "nearly flat" only when largely is true. When partly is true, say the offset is partial.
- unexplained: include that amount and say it is unexplained. Do not invent a reason for it.

Write a variance, a period total, or an unexplained amount with the phrase already on that field, such as "95 thousand" or "7.4 million". Do not write those as the unrounded dollars. A thousands phrase has no decimal. A per-unit dollar amount, such as an average fee, stays a whole number with no cents. A count, including customers and implementations, stays a whole number and is never written in thousands. Do not add a future period, or a cause whose name is not a label in the evidence. Do not mention hiring, pipeline, or anything absent from the evidence.

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


def _track_statement_money(allowed: set[float], plain: set[float], value: Any) -> None:
    """Big dollar amounts are said in thousands or millions. Small ones stay whole dollars."""
    number = _number(value)
    if number is None:
        return
    _remember(allowed, number)
    if abs(number) < 1000:
        plain.add(float(abs(round(number))))


def _track_stated_fact(plain: set[float], value: Any) -> None:
    number = _number(value)
    if number is None:
        return
    plain.add(float(abs(round(number))))


def _money_phrase(value: float) -> str | int:
    amount = abs(value)
    sign = "-" if value < 0 else ""
    if amount >= 1_000_000:
        scaled = round(amount / 1_000_000, 1)
        body = f"{int(scaled)} million" if float(scaled).is_integer() else f"{scaled:.1f} million"
        return sign + body
    if amount >= 1_000:
        return sign + f"{int(round(amount / 1_000))} thousand"
    return int(round(value))


def build_revenue_evidence(section: RevenueSectionIn) -> dict[str, Any]:
    materiality = section.materiality if section.materiality and section.materiality > 0 else MATERIALITY_DEFAULT
    parent_variance = _number(section.parent.variance)
    lines_out: list[dict[str, Any]] = []
    allowed: set[float] = set()
    plain: set[float] = set()
    _track_statement_money(allowed, plain, section.parent.current)
    _track_statement_money(allowed, plain, section.parent.comparison_amount)
    _track_statement_money(allowed, plain, parent_variance)
    for year in re.findall(r"\d{4}", section.comparison or ""):
        plain.add(float(year))

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
            _track_statement_money(allowed, plain, driver_variance)
        for fact in facts:
            for key in ("current", "base", "amount", "heads", "paid", "quota"):
                if key in fact:
                    _track_stated_fact(plain, fact[key])
        _track_statement_money(allowed, plain, line.current)
        _track_statement_money(allowed, plain, line.comparison_amount)
        _track_statement_money(allowed, plain, variance)
        unexplained = _unexplained(variance, facts, drivers, materiality)
        if variance is not None:
            child_sum += variance
            counted += 1
        if unexplained is not None:
            _track_statement_money(allowed, plain, unexplained)
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

    story = [line for line in prepared if line["variance"] is not None and abs(line["variance"]) >= 1]
    primary = 0
    if story:
        primary = _sign(max(story, key=lambda line: abs(line["variance"]))["variance"])
    elif parent_variance:
        primary = _sign(parent_variance)

    offset_abs = sum(abs(line["variance"]) for line in story if _sign(line["variance"]) not in (0, primary))
    largely = bool(offset_abs >= materiality and parent_variance is not None and abs(parent_variance) <= offset_abs * 0.25)
    partly = bool(offset_abs >= 1 and not largely)

    relationships: list[dict[str, Any]] = []
    for line in sorted(story, key=lambda item: abs(item["variance"]), reverse=True):
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
        _track_statement_money(allowed, plain, gap)
        if abs(gap) >= materiality:
            relationships.append(
                {
                    "kind": "unexplained",
                    "label": "Other revenue",
                    "amount": gap,
                    "must_name": True,
                }
            )

    if parent_variance is not None and section.parent.comparison_amount:
        base = _number(section.parent.comparison_amount)
        if base:
            plain.add(float(round(abs(parent_variance / base) * 100, 1)))

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
        "plain_numbers": sorted(plain),
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


def _scaled_amount(stated: float, allowed: set[float]) -> bool:
    if stated <= 0 or stated >= 10000:
        return False
    for scale, floor in ((1_000, 1_000), (1_000_000, 100_000)):
        for item in allowed:
            if item < floor:
                continue
            digits = 1 if scale == 1_000_000 else 0
            if abs(round(item / scale, digits) - stated) <= 0.05:
                return True
    return False


def _number_allowed(stated: float, allowed: set[float]) -> bool:
    for item in allowed:
        gap = 0.51 if stated >= 100 or item >= 100 else 0.05
        if abs(stated - item) <= gap:
            return True
    return False


def _amount_named(paragraph: str, amount: float) -> bool:
    whole = int(abs(round(amount)))
    compact = paragraph.replace("−", "-").replace("–", "-").replace(",", "")
    if re.search(rf"(?<!\d){whole}(?!\d)", compact):
        return True
    if whole >= 1000 and re.search(r"\bthousand\b", paragraph, re.IGNORECASE):
        thousands = int(round(whole / 1000))
        if re.search(rf"(?<!\d){thousands}(?!\d)", compact):
            return True
    if whole >= 100_000 and re.search(r"\bmillion\b", paragraph, re.IGNORECASE):
        scaled = round(whole / 1_000_000, 1)
        token = str(int(scaled)) if float(scaled).is_integer() else f"{scaled:.1f}"
        if re.search(rf"(?<!\d){re.escape(token)}(?!\d)", compact):
            return True
    return False


def _has_cents(stated: float) -> bool:
    return stated >= 100 and abs(stated - round(stated)) > 1e-9


def check_revenue_paragraph(paragraph: str, evidence: dict[str, Any]) -> tuple[bool, str]:
    text = (paragraph or "").strip()
    if not text:
        return False, "The analysis did not return a paragraph."
    allowed = {float(item) for item in evidence.get("allowed_numbers") or []}
    plain = {float(item) for item in evidence.get("plain_numbers") or []}
    mentions_scale = bool(re.search(r"\b(?:million|thousand)\b", text, re.IGNORECASE))
    for stated in _stated_numbers(text):
        if _has_cents(stated):
            return False, f"The analysis uses {stated:g}. Dollar amounts are written without cents."
        if _number_allowed(stated, plain):
            continue
        if mentions_scale and _scaled_amount(stated, allowed):
            if stated >= 100 and abs(stated - round(stated)) > 1e-9:
                return False, "The analysis uses a decimal on a thousands amount."
            continue
        if stated >= 10000:
            return False, f"The analysis writes {stated:g} in dollars. Use thousands or millions."
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
    shown.pop("plain_numbers", None)
    for line in shown.get("lines") or []:
        line.pop("aliases", None)
    return shown


def _phrase_value(value: Any, *, per_unit: bool) -> Any:
    number = _number(value)
    if number is None:
        return value
    if per_unit or abs(number) < 1000:
        return int(round(number))
    return _money_phrase(number)


def _phrase_fact(fact: dict[str, Any]) -> dict[str, Any]:
    """Counts and per-unit fees stay whole numbers. They are not written in thousands."""
    phrased = {"label": fact.get("label") or ""}
    for key in ("current", "base", "amount", "heads", "paid", "quota"):
        if key not in fact:
            continue
        number = _number(fact[key])
        phrased[key] = int(round(number)) if number is not None else fact[key]
    return phrased


def present_revenue_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """The copy the model reads. Statement dollars are already in thousands or millions."""
    shown = _display_evidence(evidence)
    for key in ("current", "comparison_amount", "variance"):
        if key in (shown.get("parent") or {}):
            shown["parent"][key] = _phrase_value(shown["parent"][key], per_unit=False)
    for line in shown.get("lines") or []:
        for key in ("current", "comparison_amount", "variance"):
            if key in line:
                line[key] = _phrase_value(line[key], per_unit=False)
        line["facts"] = [_phrase_fact(fact) for fact in line.get("facts") or []]
        for driver in line.get("drivers") or []:
            if "variance" in driver:
                driver["variance"] = _phrase_value(driver["variance"], per_unit=False)
    for item in shown.get("relationships") or []:
        if "variance" in item:
            item["variance"] = _phrase_value(item["variance"], per_unit=False)
        if "amount" in item:
            item["amount"] = _phrase_value(item["amount"], per_unit=False)
        if item.get("facts"):
            item["facts"] = [_phrase_fact(fact) for fact in item["facts"]]
    return shown


def analyze_revenue_rollup(section: RevenueSectionIn, client: Any | None) -> RevenueRollupResult:
    evidence = build_revenue_evidence(section)
    shown = present_revenue_evidence(evidence)
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
