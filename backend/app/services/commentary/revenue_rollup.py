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
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.commentary.attribution_verify import verify_text_attribution
from app.services.commentary.customer_events import brief_movements, pipeline_review
from app.services.commentary.openai_client import LLMError

MATERIALITY_DEFAULT = 10_000

ROLLUP_SYSTEM = """You write one paragraph of analysis for the section named by parent.label.

Use only the JSON evidence. Name every relationship and its variance, including a smaller line. Those lines are how the total was reached.
- with_total: state that line's own dollar change and its facts. Do not say it moved with revenue or with the total. Do not write the word with_total.
- offset: say that line was lower or higher against the section change, and cite its facts. When partly is true, say the offset is partial. Do not call that offset large, and do not call the section flat, unless largely is true. Do not write "offsetting the total" or treat the total increase as a cause.
- unexplained: this is a remainder that does not add up, not the line's own variance. Name that amount and say it is unexplained. Do not invent a reason for it.

If a line has no facts, state its dollar change only. Do not give it a reason, and do not call that change unexplained. An account number at the start of a label is part of that label. You may write an account number only when it is already on a label in the evidence. It is not a dollar amount. Do not write an account number from these instructions. Budget and Forecast name the comparison. They are not a cause. Do not write because, due to, driven by, led by, or offset by unless the words that follow are a label or a fact already in the evidence.

Write every dollar amount with the phrase already on that field. A dollar amount has a dollar sign. From $1,000 it uses a lowercase k and two decimals, such as $94.65k or $4.25k. From $1,000,000 it uses a lowercase m and two decimals, such as $7.40m. Below $1,000 it is two decimals with a dollar sign, such as $868.00. Do not write the word thousand or million, and do not use an uppercase K. An average fee and average revenue are dollar amounts, so they use that form. A count, including customers and implementations, stays a whole number with no dollar sign and no k. Do not add a future period, or a cause whose name is not a label in the evidence. Do not mention hiring, pipeline, a customer, or anything absent from the evidence.

When events is empty, do not name a customer or a deal, and do not say a deal came in or did not come in. When events is present, add one sentence. Use each event's bucket, customer, and amount. If others is above zero, include that count and others_amount. These amounts are ARR beside the section. Do not say a customer caused the variance. On a forecast comparison, the outcome says which expected customers came in and which did not. A budget comparison has no events. Do not write the word pipeline.

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


class CustomerEventIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    bucket: str = ""
    customer: str = ""
    amount: float | None = None
    others: int = 0
    others_amount: float = 0
    outcome: str = ""


class RevenueParentIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str = "Revenue"
    current: float | None = None
    comparison_amount: float | None = None
    variance: float | None = None


class RevenueSectionIn(BaseModel):
    comparison: str = ""
    comparison_kind: str = ""
    section_id: str = "revenue"
    period: str = ""
    organization_id: str = ""
    materiality: float = MATERIALITY_DEFAULT
    parent: RevenueParentIn
    lines: list[RevenueLineIn] = Field(default_factory=list)
    events: list[CustomerEventIn] = Field(default_factory=list)


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


_MONEY_FACT = re.compile(r"average|fee|salary|cost|wage|price|\bsize\b", re.IGNORECASE)
_COUNT_FACT = re.compile(
    r"customer|implementation|employee|hire|departure|head|people|person|hour|\bgb\b|contract|deal|seat|logo",
    re.IGNORECASE,
)


def _is_count_fact(label: str) -> bool:
    if _MONEY_FACT.search(label or ""):
        return False
    return _COUNT_FACT.search(label or "") is not None


def _track_statement_money(allowed: set[float], plain: set[float], value: Any) -> None:
    """Dollar amounts are checked as $ amounts. Counts stay in plain."""
    del plain
    number = _number(value)
    if number is None:
        return
    _remember(allowed, number)


def _money_amount(value: float, scale: int) -> Decimal:
    return (Decimal(str(abs(value))) / Decimal(scale)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _track_stated_fact(plain: set[float], value: Any) -> None:
    number = _number(value)
    if number is None:
        return
    plain.add(float(abs(round(number))))


def _track_label_numbers(plain: set[float], label: str) -> None:
    """An account number on a label is the line's name, not a dollar amount."""
    for token in re.findall(r"\b\d{3,6}\b", label or ""):
        plain.add(float(token))


def _money_phrase(value: float) -> str:
    sign = "-" if value < 0 else ""
    amount = abs(value)
    if amount >= 1_000_000:
        return sign + f"${_money_amount(amount, 1_000_000)}m"
    if amount >= 1_000:
        return sign + f"${_money_amount(amount, 1_000)}k"
    return sign + f"${_money_amount(amount, 1)}"


def build_revenue_evidence(section: RevenueSectionIn) -> dict[str, Any]:
    materiality = section.materiality if section.materiality and section.materiality > 0 else MATERIALITY_DEFAULT
    parent_variance = _number(section.parent.variance)
    lines_out: list[dict[str, Any]] = []
    allowed: set[float] = set()
    plain: set[float] = set()
    _track_statement_money(allowed, plain, section.parent.current)
    _track_statement_money(allowed, plain, section.parent.comparison_amount)
    _track_statement_money(allowed, plain, parent_variance)
    _track_label_numbers(plain, section.parent.label or "Revenue")
    for year in re.findall(r"\d{4}", section.comparison or ""):
        plain.add(float(year))
    for quarter in re.findall(r"\b[QqHh]([1-4])\b", section.comparison or ""):
        plain.add(float(quarter))

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
            _track_label_numbers(plain, driver.label)
        for fact in facts:
            _track_label_numbers(plain, str(fact.get("label") or ""))
            count = _is_count_fact(str(fact.get("label") or ""))
            current_value = _number(fact.get("current"))
            base_value = _number(fact.get("base"))
            for key in ("current", "base", "amount", "heads", "paid", "quota"):
                if key not in fact:
                    continue
                if count or key == "heads":
                    _track_stated_fact(plain, fact[key])
                else:
                    _remember(allowed, fact[key])
            if current_value is not None and base_value is not None:
                change = current_value - base_value
                if count:
                    _track_stated_fact(plain, change)
                else:
                    _remember(allowed, change)
        _track_statement_money(allowed, plain, line.current)
        _track_statement_money(allowed, plain, line.comparison_amount)
        _track_statement_money(allowed, plain, variance)
        base_amount = _number(line.comparison_amount)
        if variance is not None and base_amount:
            plain.add(float(round(abs(variance / base_amount) * 100, 1)))
        unexplained = _unexplained(variance, facts, drivers)
        _track_label_numbers(plain, line.label)
        for alias in _aliases(line.label):
            _track_label_numbers(plain, alias)
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
                    "label": "Other revenue" if (section.section_id or "revenue") == "revenue" else "Remainder",
                    "amount": gap,
                    "must_name": True,
                }
            )

    events_out = _events(section, allowed, plain)

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
        "comparison_kind": (section.comparison_kind or "").strip().lower(),
        "relationships": relationships,
        "events": events_out,
        "largely": largely,
        "allowed_numbers": sorted(allowed),
        "plain_numbers": sorted(plain),
    }


def _events(section: RevenueSectionIn, allowed: set[float], plain: set[float]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for event in section.events:
        amount = _number(event.amount)
        customer = (event.customer or "").strip()
        if not customer or amount is None:
            continue
        others = int(event.others or 0)
        others_amount = _number(event.others_amount) or 0.0
        _remember(allowed, abs(amount))
        if others > 0:
            _track_stated_fact(plain, others)
            _remember(allowed, abs(others_amount))
        events.append(
            {
                "bucket": event.bucket,
                "customer": customer,
                "amount": abs(amount),
                "others": others,
                "others_amount": abs(others_amount),
                "outcome": event.outcome,
            }
        )
    return events


def attach_stored_events(section: RevenueSectionIn, db: Any) -> RevenueSectionIn:
    """Load the customers for a month or a forecast. Every other comparison stays a number."""
    kind = (section.comparison_kind or "").strip().lower()
    if (section.section_id or "revenue") != "revenue" or kind not in {"mom", "forecast"}:
        return section.model_copy(update={"events": []})
    if not section.organization_id or not section.period or db is None:
        return section.model_copy(update={"events": []})
    try:
        org = uuid.UUID(str(section.organization_id))
    except (ValueError, TypeError, AttributeError):
        return section.model_copy(update={"events": []})
    materiality = section.materiality if section.materiality and section.materiality > 0 else MATERIALITY_DEFAULT
    try:
        from app.services.reporting.period_utils import to_period
        from app.services.reporting.source_trace import customer_movements, forecast_month_deals

        period = to_period(section.period)
        if kind == "mom":
            loaded = brief_movements(customer_movements(db, org, period), materiality)
        else:
            expected, closed = forecast_month_deals(db, org, period)
            loaded = pipeline_review(expected, closed, materiality)
    except Exception:
        loaded = []
    return section.model_copy(update={"events": [CustomerEventIn.model_validate(item) for item in loaded]})


def _unexplained(
    variance: float | None,
    facts: list[dict[str, Any]],
    drivers: list[dict[str, Any]],
) -> float | None:
    if variance is None:
        return None
    if facts:
        return None
    if not drivers:
        # The dollar change is known. A missing quarterly or budget driver is not a plug.
        return None
    cited = sum(driver["variance"] for driver in drivers)
    rest = variance - cited
    if abs(rest) >= 1:
        return rest
    return None


_NUMBER_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
_LARGELY_RE = re.compile(r"\b(?:largely|nearly flat|almost flat)\b", re.IGNORECASE)
_RESTATE_RE = re.compile(r"moved with (?:the )?(?:total|revenue)|with total revenue", re.IGNORECASE)
_UNEXPLAINED_WORD = re.compile(r"\bunexplained\b", re.IGNORECASE)
_EFFECT_PHRASE = re.compile(
    r"^(?:the |a |an )?(?:overall |total |revenue |parent )?"
    r"(?:increase|decrease|decline|growth|change|variance|gain|drop)$",
    re.IGNORECASE,
)
_EFFECT_HEAD = re.compile(
    r"^(?:the |a |an )?(?:overall |total |revenue |parent )?"
    r"(?:increase|decrease|decline|growth|change|variance|gain|drop)\b",
    re.IGNORECASE,
)
_FACT_CONTINUATION = re.compile(
    r"^(?:,?\s*)?(?:as|while|with)\s+\S.+\b(?:rose|fell|declined|increased|decreased|dropped|grew|unchanged)\b",
    re.IGNORECASE,
)


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
    """94.65, 94.6, and 95 can all be the same evidence amount in thousands."""
    if stated <= 0 or stated >= 10000:
        return False
    for scale, floor in ((1_000, 1_000), (1_000_000, 100_000)):
        for item in allowed:
            if item < floor:
                continue
            for digits in (0, 1, 2):
                if abs(round(item / scale, digits) - stated) <= 0.05:
                    return True
    return False


def _number_allowed(stated: float, allowed: set[float]) -> bool:
    for item in allowed:
        gap = 0.51 if stated >= 100 or item >= 100 else 0.05
        if abs(stated - item) <= gap:
            return True
    return False


_CURRENCY_RE = re.compile(r"\$(\d[\d,]*(?:\.\d+)?)(?:\s*([kmKM]))?")


def _amount_named(paragraph: str, amount: float) -> bool:
    text = paragraph.replace("−", "-").replace("–", "-")
    if _money_phrase(amount).lstrip("-") in text:
        return True
    compact = text.replace(",", "")
    whole = int(abs(round(amount)))
    return re.search(rf"(?<!\d){whole}(?!\d)", compact) is not None


def _names_only_the_total(phrase: str) -> bool:
    """The total's own movement is not a cause, even when a loaded fact follows it."""
    text = (phrase or "").strip()
    if _EFFECT_PHRASE.match(text):
        return True
    head = _EFFECT_HEAD.match(text)
    if not head:
        return False
    rest = text[head.end() :].strip()
    return bool(rest) and _FACT_CONTINUATION.match(rest) is not None


def _currency_matches(stated: float, suffix: str | None, allowed: set[float], decimals: int) -> bool:
    if suffix == "k":
        scale, floor = 1_000, 0.0
    elif suffix == "m":
        scale, floor = 1_000_000, 1_000_000.0
    else:
        scale, floor = 1, 0.0
    tolerance = 0.051 if suffix else 0.51
    for item in allowed:
        if item < floor:
            continue
        shown = float(_money_amount(item, scale))
        if abs(shown - stated) <= tolerance:
            return True
        # $16.6k is $16.59k with the second decimal left off, or rounded to one decimal.
        if suffix and decimals == 1:
            rounded = float(Decimal(str(shown)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
            truncated = math.floor(shown * 10 + 1e-6) / 10
            if abs(rounded - stated) <= 0.001 or abs(truncated - stated) <= 0.001:
                return True
    return False


_CUSTOMER_CLAIM = re.compile(
    r"\b(?:included|customer|logo)\s+([A-Z][\w&.'’-]*(?:\s+[A-Z][\w&.'’-]*)*)"
)
_DEAL_OUTCOME = re.compile(r"\b(?:did not come in|came in)\b", re.IGNORECASE)


def _evidence_labels(evidence: dict[str, Any]) -> tuple[set[str], str]:
    labels: set[str] = set()
    parent = str((evidence.get("parent") or {}).get("label") or "").strip().lower()
    if parent:
        labels.add(parent)
    for line in evidence.get("lines") or []:
        for label in [line.get("label"), *(line.get("aliases") or [])]:
            text = str(label or "").strip().lower()
            if text:
                labels.add(text)
        for fact in line.get("facts") or []:
            text = str(fact.get("label") or "").strip().lower()
            if text:
                labels.add(text)
        for driver in line.get("drivers") or []:
            text = str(driver.get("label") or "").strip().lower()
            if text:
                labels.add(text)
    return labels, str(evidence.get("comparison") or "").strip().lower()


def _is_listed_name(captured: str, labels: set[str], comparison: str) -> bool:
    """A line, a fact, or the comparison period is not a customer name."""
    name = captured.strip().lower()
    if not name:
        return True
    if name in labels or name in comparison:
        return True
    return any(label.startswith(name + " ") or name.startswith(label) for label in labels)


def check_revenue_paragraph(paragraph: str, evidence: dict[str, Any]) -> tuple[bool, str]:
    text = (paragraph or "").strip()
    if not text:
        return False, "The analysis did not return a paragraph."
    allowed = {float(item) for item in evidence.get("allowed_numbers") or []}
    plain = {float(item) for item in evidence.get("plain_numbers") or []}
    for match in _CURRENCY_RE.finditer(text):
        raw = match.group(1).replace(",", "")
        suffix = match.group(2)
        stated = abs(float(raw))
        decimals = len(raw.split(".", 1)[1]) if "." in raw else 0
        kind = suffix.lower() if suffix else None
        if _currency_matches(stated, kind, allowed, decimals):
            continue
        # $6,100 can be the account on the label, not a dollar amount.
        if not kind and _number_allowed(stated, plain):
            continue
        return False, f"The analysis uses {match.group(0)}, which is not in the revenue evidence."
    bare = _CURRENCY_RE.sub(" ", text)
    for stated in _stated_numbers(bare):
        if _number_allowed(stated, plain) or _number_allowed(stated, allowed) or _scaled_amount(stated, allowed):
            continue
        return False, f"The analysis uses {stated:g}, which is not in the revenue evidence."
    if _RESTATE_RE.search(text):
        return False, "The analysis restates the total instead of the line's own change."
    if re.search(r"\bwith_total\b", text):
        return False, "The analysis quotes a field name. State the line's own change."
    has_unexplained = any(
        item.get("kind") == "unexplained" and item.get("must_name")
        for item in evidence.get("relationships") or []
    )
    if _UNEXPLAINED_WORD.search(text) and not has_unexplained:
        return False, "The analysis calls a known revenue change unexplained."
    if not evidence.get("largely") and _LARGELY_RE.search(text):
        return False, "The analysis calls the move largely offset, and the evidence does not."
    for relationship in evidence.get("relationships") or []:
        if relationship.get("kind") != "unexplained" or not relationship.get("must_name"):
            continue
        amount = _number(relationship.get("amount"))
        if amount is not None and abs(amount) >= 1 and not _amount_named(text, amount):
            return False, f"The analysis leaves out the unexplained {abs(round(amount)):,.0f}."
    events = evidence.get("events") or []
    known = {str(event.get("customer") or "").strip().lower() for event in events}
    known.discard("")
    labels, comparison = _evidence_labels(evidence)
    if not events and _DEAL_OUTCOME.search(text):
        return False, "The analysis names a customer the evidence does not list."
    for match in _CUSTOMER_CLAIM.finditer(text):
        captured = match.group(1).strip()
        if _is_listed_name(captured, labels, comparison):
            continue
        if captured.lower() not in known:
            return False, "The analysis names a customer the evidence does not list."
    for event in events:
        customer = str(event.get("customer") or "").strip()
        if customer and customer.lower() not in text.lower():
            return False, f"The analysis leaves out {customer}."
        others = int(event.get("others") or 0)
        others_amount = _number(event.get("others_amount"))
        if others > 0 and others_amount is not None and abs(others_amount) >= 1 and not _amount_named(text, others_amount):
            return False, f"The analysis leaves out the other {event.get('bucket') or 'customers'}."
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
        blocking = []
        for check in attribution.failures:
            phrase = (check.claim.phrase or "").strip() if check.claim else ""
            if phrase and _names_only_the_total(phrase):
                continue
            blocking.append(phrase or "an unnamed cause")
        if blocking:
            named = ", ".join(blocking[:3])
            return False, f"The analysis names a cause the revenue evidence does not support: {named}."
    return True, ""


def _display_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    shown = copy.deepcopy(evidence)
    shown.pop("allowed_numbers", None)
    shown.pop("plain_numbers", None)
    for line in shown.get("lines") or []:
        line.pop("aliases", None)
    return shown


def _phrase_value(value: Any, *, per_unit: bool) -> Any:
    del per_unit
    number = _number(value)
    if number is None:
        return value
    return _money_phrase(number)


def _phrase_fact(fact: dict[str, Any]) -> dict[str, Any]:
    """Counts stay whole numbers. Fees and average revenue use $ and k."""
    label = str(fact.get("label") or "")
    count = _is_count_fact(label)
    phrased: dict[str, Any] = {"label": label}
    for key in ("current", "base", "amount", "heads", "paid", "quota"):
        if key not in fact:
            continue
        number = _number(fact[key])
        if number is None:
            phrased[key] = fact[key]
        elif count or key == "heads":
            phrased[key] = int(round(number))
        else:
            phrased[key] = _money_phrase(number)
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
    for event in shown.get("events") or []:
        if "amount" in event:
            event["amount"] = _phrase_value(event["amount"], per_unit=False)
        if event.get("others_amount"):
            event["others_amount"] = _phrase_value(event["others_amount"], per_unit=False)
    return shown


def _drop_unearned_largely(text: str) -> str:
    """A partial offset is still an offset. Drop the word that overstates it."""
    cleaned = re.sub(
        r",?\s*leaving\b[^.]*?\b(?:nearly|almost) flat\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\b(?:largely|nearly flat|almost flat)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;])", r"\1", cleaned)
    return cleaned.strip()


def _without_unearned_largely(paragraph: str, evidence: dict[str, Any]) -> str:
    if evidence.get("largely"):
        return ""
    cleaned = _drop_unearned_largely(paragraph)
    if not cleaned or cleaned == paragraph.strip():
        return ""
    ok, _reason = check_revenue_paragraph(cleaned, evidence)
    return cleaned if ok else ""


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
    if not ok and paragraph:
        kept = _without_unearned_largely(paragraph, evidence)
        if kept:
            return RevenueRollupResult(status="ai", paragraph=kept, evidence=shown)
    if not ok and paragraph:
        correction = (
            "The previous paragraph was rejected.\n"
            f"Reason: {reason}\n"
            "Rejected paragraph:\n"
            f"{paragraph}\n"
            "Rewrite it from the evidence below. Keep every number and every cause inside that evidence.\n"
            + json.dumps(shown, default=str)
        )
        try:
            rewritten = client.generate(system_prompt=ROLLUP_SYSTEM, user_prompt=correction)
        except (LLMError, Exception):
            rewritten = None
        if isinstance(rewritten, dict):
            second = str(rewritten.get("paragraph") or "").strip()
            second_ok, second_reason = check_revenue_paragraph(second, evidence)
            if not second_ok:
                kept = _without_unearned_largely(second, evidence)
                if kept:
                    return RevenueRollupResult(status="ai", paragraph=kept, evidence=shown)
            if second_ok:
                return RevenueRollupResult(status="ai", paragraph=second, evidence=shown)
            reason = second_reason or reason
    if not ok:
        return RevenueRollupResult(status="fallback", reason=reason, evidence=shown)
    return RevenueRollupResult(status="ai", paragraph=paragraph, evidence=shown)
