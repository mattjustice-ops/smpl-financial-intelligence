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

Use only the JSON evidence. Name every line and its variance. When there is more than one line, write one sentence for each line and put a line break between those sentences. Begin each of those sentences with the line's label and a colon, then that line's dollar change, facts, and drivers. Do not join the lines into one sentence.
- with_total: state that line's own dollar change and its facts. Do not say it moved with revenue or with the total. Do not write the word with_total.
- offset: say that line was lower or higher against the section change, and cite its facts. When partly is true, say the offset is partial. Do not call that offset large, and do not call the section flat, unless largely is true. Do not write "offsetting the total" or treat the total increase as a cause.
- other_accounts: this is the remainder of the line's variance after the named drivers. Name that amount and say it is in other accounts. Do not call it unexplained. Do not invent a reason for it.
- unexplained: only when the evidence marks a true plug or unresolved gap (not a truncated driver list). Name that amount, say it is unexplained, and keep the resolve hint so the reader can investigate. Do not invent a reason.

If a line has no facts, state its dollar change only. Do not give it a reason, and do not call that change unexplained or other accounts. An account number at the start of a label is part of that label. You may write an account number only when it is already on a label in the evidence. It is not a dollar amount. Do not write an account number from these instructions. Budget and Forecast name the comparison. They are not a cause. Do not write because, due to, driven by, led by, or offset by unless the words that follow are a label or a fact already in the evidence.

Write every dollar amount with the phrase already on that field. A dollar amount has a dollar sign. From $1,000 it uses a lowercase k and two decimals, such as $94.65k or $4.25k. From $1,000,000 it uses a lowercase m and two decimals, such as $7.40m. Below $1,000 it is two decimals with a dollar sign, such as $868.00. Do not write the word thousand or million, and do not use an uppercase K. An average fee and average revenue are dollar amounts, so they use that form. A count, including customers and implementations, stays a whole number with no dollar sign and no k. Do not add a future period, or a cause whose name is not a label in the evidence. Do not mention hiring, pipeline, a customer, or anything absent from the evidence.

When events is empty, do not name a customer, a segment, a vendor, or a deal, and do not say a deal came in or did not come in. When events is present and an event has department, put that event only on the line whose label matches that department. When an event has account_label or account_number, put that event only on the matching account line's sentence (the line whose label contains that account number or account_label). Do not dump another department's payroll or vendors onto Sales, Marketing, or any other dept line. Do not dump vendor or payroll names after the last child line. When events is present without department/account_label and the section is revenue, put those ARR names only on the subscription line's sentence (the line whose label includes Subscription). After that line's dollar change and facts, add the event sentences on the same line block — still starting from the subscription label's sentence, before any recurring or implementation sentence. You may write the event's bucket and you must write its customer and amount. Event amount is the MoM change (or ARR for revenue names), not a period spend level — do not write absolute payroll or vendor stock beside the variance. If others is above zero, include that count and others_amount. If an event has tag, you may name that tag as a fact already on the event (service, driver, commit, or usage). Do not invent a usage method. On revenue these amounts are ARR beside recognized subscription revenue. If events already name a bucket (New Business, Expansion, Contraction, Churn, Reactivation), do not also restate that bucket's ARR fact totals. Never write empty ranges such as "from to". A fact with current and base must name both amounts or omit the fact. Do not say a customer or vendor caused the variance. Do not put New Business, Expansion, Contraction, Churn, or Reactivation names on implementation or recurring services. On a forecast comparison, the outcome says which expected customers came in and which did not. A budget comparison has no events. Do not write the word pipeline.

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
    account_number: str = ""
    current: float | None = None
    comparison_amount: float | None = None
    variance: float | None = None
    contribution: float | None = None
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
    account_number: str = ""
    account_label: str = ""
    department: str = ""
    event_kind: str = ""
    tag: str = ""
    prior_amount: float | None = None
    current_amount: float | None = None


FLUX_SECTION_IDS = frozenset({"sm", "rd", "ga", "cogs", "unmapped"})
FLUX_SECTION_BY_ID = {
    "sm": "opex",
    "rd": "opex",
    "ga": "opex",
    "unmapped": "opex",
    "cogs": "cogs",
}
# Mirror board dept → function map so sm/rd/ga do not share the full opex dump.
OPEX_DEPARTMENTS_BY_SECTION: dict[str, frozenset[str]] = {
    "sm": frozenset({"sales", "customer success", "marketing"}),
    "rd": frozenset({"r&d", "rd", "product", "engineering"}),
    "ga": frozenset({"g&a", "ga", "finance", "support"}),
}
FLUX_EVENT_CAP = 5


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
    r"customer|implementation|employee|hire|departure|head|people|person|hour|\bgb\b|"
    r"contract|deal|seat|logo|mau|sms|email|contact|commit|unit",
    re.IGNORECASE,
)
_EVENT_BUCKET_START = re.compile(
    r"^(?:New Business|Expansion|Contraction|Churn|Reactivation|expected)\b",
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
            # Sub-material account moves roll into other_accounts, not named drivers.
            if abs(driver_variance) < materiality:
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
        other_accounts = _other_accounts_remainder(variance, facts, drivers)
        _track_label_numbers(plain, line.label)
        for alias in _aliases(line.label):
            _track_label_numbers(plain, alias)
        contribution = _number(line.contribution)
        added = contribution if contribution is not None else variance
        if added is not None:
            child_sum += added
            counted += 1
        if other_accounts is not None:
            _track_statement_money(allowed, plain, other_accounts)
        prepared.append(
            {
                "label": line.label,
                "aliases": _aliases(line.label),
                "current": _number(line.current),
                "comparison_amount": _number(line.comparison_amount),
                "variance": variance,
                "contribution": contribution,
                "material": variance is not None and abs(variance) >= materiality,
                "facts": facts,
                "drivers": drivers,
                "other_accounts": other_accounts,
            }
        )

    story = [line for line in prepared if line["variance"] is not None and abs(line["variance"]) >= 1]
    primary = 0
    if story:
        primary = _sign(max(story, key=lambda line: abs(line["variance"]))["variance"])
    elif parent_variance:
        primary = _sign(parent_variance)

    uses_contribution = any(item.get("contribution") is not None for item in story)

    def _with_section(item: dict) -> bool:
        if uses_contribution and parent_variance is not None:
            effect = item["contribution"] if item.get("contribution") is not None else item["variance"]
            return _sign(effect) in (0, _sign(parent_variance))
        return _sign(item["variance"]) in (0, primary)

    offset_abs = sum(abs(line["variance"]) for line in story if not _with_section(line))
    largely = bool(offset_abs >= materiality and parent_variance is not None and abs(parent_variance) <= offset_abs * 0.25)
    partly = bool(offset_abs >= 1 and not largely)

    relationships: list[dict[str, Any]] = []
    for line in sorted(story, key=lambda item: abs(item["variance"]), reverse=True):
        kind = "with_total" if _with_section(line) else "offset"
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
        if line["other_accounts"] is not None and abs(line["other_accounts"]) >= materiality:
            relationships.append(
                {
                    "kind": "other_accounts",
                    "label": line["label"],
                    "amount": line["other_accounts"],
                    "must_name": True,
                }
            )

    if parent_variance is not None and counted:
        gap = parent_variance - child_sum
        _track_statement_money(allowed, plain, gap)
        if abs(gap) >= materiality:
            relationships.append(
                {
                    "kind": "other_accounts",
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
        lines_out.append(
            {
                key: value
                for key, value in line.items()
                if key != "contribution" and (key != "other_accounts" or value is not None)
            }
        )

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
        if not customer or amount is None or abs(amount) < 1:
            continue
        others = int(event.others or 0)
        others_amount = _number(event.others_amount) or 0.0
        if others > 0 and abs(others_amount) < 1:
            others = 0
            others_amount = 0.0
        _remember(allowed, abs(amount))
        for token in re.findall(r"\b\d+\b", customer):
            plain.add(float(token))
        if others > 0:
            _track_stated_fact(plain, others)
            _remember(allowed, abs(others_amount))
        event_kind = (event.event_kind or "").strip()
        # OpEx/CoR events carry signed MoM deltas; revenue ARR stays magnitude.
        reported_amount = (
            amount
            if event_kind in {"payroll_batch", "vendor_spend", "credit_reversal"}
            else abs(amount)
        )
        payload = {
            "bucket": event.bucket,
            "customer": customer,
            "amount": reported_amount,
            "others": others,
            "others_amount": abs(others_amount) if others else 0.0,
            "outcome": event.outcome,
        }
        account_number = (event.account_number or "").strip()
        account_label = (event.account_label or "").strip()
        department = (event.department or "").strip()
        tag = (event.tag or "").strip()
        prior_amount = _number(event.prior_amount)
        current_amount = _number(event.current_amount)
        if account_number:
            payload["account_number"] = account_number
        if account_label:
            payload["account_label"] = account_label
        if department:
            payload["department"] = department
        if event_kind:
            payload["event_kind"] = event_kind
        if tag:
            payload["tag"] = tag
        if prior_amount is not None:
            payload["prior_amount"] = abs(prior_amount)
        if current_amount is not None:
            payload["current_amount"] = abs(current_amount)
        events.append(payload)
    return events


def _is_subscription_label(label: str) -> bool:
    text = (label or "").lower()
    if "implementation" in text or "onboarding" in text or "professional" in text:
        return False
    if "recurring" in text and "service" in text:
        return False
    if "subscription" in text:
        return True
    return False


def _subscription_line_label(evidence_or_section: Any) -> str:
    lines = getattr(evidence_or_section, "lines", None)
    if lines is None and isinstance(evidence_or_section, dict):
        lines = evidence_or_section.get("lines") or []
    for line in lines or []:
        label = str(getattr(line, "label", None) or (line.get("label") if isinstance(line, dict) else "") or "")
        if _is_subscription_label(label):
            return label
    return ""


def _waterfall_arr_totals(db: Any, org: str, period: str) -> dict[str, float]:
    from sqlalchemy import text

    from app.services.dashboard.query_utils import table_exists

    table = "actual_mrr_waterfall"
    if not table_exists(db, table):
        table = "actual_arr_waterfall"
        if not table_exists(db, table):
            return {}
    cols = db.execute(
        text(
            """
            select column_name from information_schema.columns
            where table_schema = 'public' and table_name = :table
            """
        ),
        {"table": table},
    ).all()
    available = {str(name) for (name,) in cols}
    wanted = [
        name
        for name in (
            "new_business_arr",
            "expansion_arr",
            "contraction_arr",
            "churn_arr",
            "reactivation_arr",
        )
        if name in available
    ]
    if not wanted:
        return {}
    found = db.execute(
        text(
            f"""
            select {", ".join(wanted)}
            from "{table}"
            where organization_id = :org and left(cast(period as text), 7) = :period
            limit 1
            """
        ),
        {"org": org, "period": period},
    ).mappings().first()
    if not found:
        return {}
    out: dict[str, float] = {}
    for key in wanted:
        value = _number(found.get(key))
        if value is not None:
            out[key] = abs(value)
    return out


def _arr_mom_facts(db: Any, org: uuid.UUID, period: str) -> list[RevenueFactIn]:
    from app.services.reporting.period_utils import prior_period, to_period

    current = to_period(period)
    prior = prior_period(current)
    now = _waterfall_arr_totals(db, str(org), current)
    then = _waterfall_arr_totals(db, str(org), prior)
    if not now or not then:
        return []
    labels = {
        "new_business_arr": "new business ARR",
        "expansion_arr": "expansion ARR",
        "contraction_arr": "contraction ARR",
        "churn_arr": "churn ARR",
        "reactivation_arr": "reactivation ARR",
    }
    facts: list[RevenueFactIn] = []
    for key, label in labels.items():
        if key not in now or key not in then:
            continue
        current = _number(now.get(key))
        base = _number(then.get(key))
        # Both sides required — otherwise the model invents empty "from to" ranges.
        if current is None or base is None:
            continue
        facts.append(RevenueFactIn(label=label, current=current, base=base))
    return facts


_ARR_FACT_BY_BUCKET = {
    "new business": "new business arr",
    "expansion": "expansion arr",
    "contraction": "contraction arr",
    "churn": "churn arr",
    "reactivation": "reactivation arr",
}


def _omit_arr_facts_covered_by_events(
    facts: list[RevenueFactIn],
    events: list[CustomerEventIn],
) -> list[RevenueFactIn]:
    """When named ARR events cover a bucket, skip that bucket's ARR total fact."""
    covered = {
        _ARR_FACT_BY_BUCKET[str(event.bucket or "").strip().casefold()]
        for event in events
        if str(event.bucket or "").strip().casefold() in _ARR_FACT_BY_BUCKET
    }
    if not covered:
        return facts
    return [
        fact
        for fact in facts
        if str(fact.label or "").strip().casefold() not in covered
    ]


def _with_subscription_arr_facts(section: RevenueSectionIn, facts: list[RevenueFactIn]) -> RevenueSectionIn:
    facts = _omit_arr_facts_covered_by_events(facts, list(section.events or []))
    if not facts:
        return section
    lines: list[RevenueLineIn] = []
    placed = False
    for line in section.lines:
        if not placed and _is_subscription_label(line.label):
            existing = list(line.facts)
            known = {str(fact.label or "").casefold() for fact in existing}
            merged = existing + [fact for fact in facts if str(fact.label or "").casefold() not in known]
            lines.append(line.model_copy(update={"facts": merged}))
            placed = True
        else:
            lines.append(line)
    if not placed and lines:
        first = lines[0]
        lines[0] = first.model_copy(update={"facts": list(first.facts) + facts})
    return section.model_copy(update={"lines": lines})


def attach_stored_events(section: RevenueSectionIn, db: Any) -> RevenueSectionIn:
    """Load customers (revenue) or flux counterparties (OpEx/CoR) for MoM / forecast."""
    kind = (section.comparison_kind or "").strip().lower()
    section_id = (section.section_id or "revenue").strip().lower()
    if section_id == "revenue":
        if kind not in {"mom", "forecast"}:
            return section.model_copy(update={"events": []})
    elif section_id in FLUX_SECTION_IDS:
        if kind != "mom":
            return section.model_copy(update={"events": []})
    else:
        return section.model_copy(update={"events": []})
    if not section.organization_id or not section.period or db is None:
        return section.model_copy(update={"events": []})
    try:
        org = uuid.UUID(str(section.organization_id))
    except (ValueError, TypeError, AttributeError):
        return section.model_copy(update={"events": []})
    materiality = section.materiality if section.materiality and section.materiality > 0 else MATERIALITY_DEFAULT
    if section_id in FLUX_SECTION_IDS:
        return _attach_flux_events(section, db, org, materiality)
    try:
        from app.services.reporting.period_utils import to_period
        from app.services.reporting.source_trace import customer_movements, forecast_month_deals

        period = to_period(section.period)
        if kind == "mom":
            loaded = brief_movements(customer_movements(db, org, period), materiality)
        else:
            expected, closed = forecast_month_deals(db, org, period)
            loaded = pipeline_review(expected, closed, materiality)
        loaded = sorted(
            loaded,
            key=lambda item: (-abs(float(item.get("amount") or 0)), str(item.get("customer") or "")),
        )[:FLUX_EVENT_CAP]
    except Exception:
        loaded = []
    updated = section.model_copy(update={"events": [CustomerEventIn.model_validate(item) for item in loaded]})
    if kind == "mom":
        try:
            updated = _with_subscription_arr_facts(updated, _arr_mom_facts(db, org, section.period))
        except Exception:
            pass
    return updated


def _account_numbers_from_lines(lines: list[RevenueLineIn]) -> set[str]:
    found: set[str] = set()
    for line in lines:
        explicit = str(getattr(line, "account_number", "") or "").strip()
        if explicit:
            found.add(explicit)
        match = re.match(r"^(\d+)\b", str(line.label or "").strip())
        if match:
            found.add(match.group(1))
    return found


def _department_allowed(department: str, allow: frozenset[str]) -> bool:
    text = str(department or "").strip().lower()
    if not text:
        return False
    if text in allow:
        return True
    return any(token in text or text in token for token in allow)


def _filter_flux_rows_for_section(
    rows: list[dict[str, Any]],
    *,
    section_id: str,
    account_numbers: set[str],
) -> list[dict[str, Any]]:
    """Scope opex rows to the function card. Never fail-open to the full opex table."""
    filtered = list(rows)
    if account_numbers:
        wanted = {str(a).strip() for a in account_numbers if str(a).strip()}
        filtered = [
            row
            for row in filtered
            if str(row.get("account_number") or "").strip() in wanted
        ]
    if section_id == "cogs":
        # Warehouse load is already section=cogs; keep those rows (optionally account-narrowed).
        return filtered
    dept_allow = OPEX_DEPARTMENTS_BY_SECTION.get(section_id)
    if dept_allow is not None:
        return [
            row
            for row in filtered
            if _department_allowed(str(row.get("department") or ""), dept_allow)
        ]
    # unmapped / unknown without accounts → empty (do not dump all opex).
    if account_numbers:
        return filtered
    return []


def _attach_flux_events(
    section: RevenueSectionIn,
    db: Any,
    org: uuid.UUID,
    materiality: float,
) -> RevenueSectionIn:
    try:
        from app.services.reporting.period_utils import to_period
        from app.services.warehouse.compile_flux_events import brief_flux_for_rollup, load_flux_events

        section_id = (section.section_id or "").strip().lower()
        flux_section = FLUX_SECTION_BY_ID.get(section_id, "opex")
        account_numbers = _account_numbers_from_lines(section.lines)
        # Load the warehouse section, then narrow in-process (dept + accounts).
        # Passing account_numbers into load_flux_events also admits blank-account rows.
        rows = load_flux_events(
            db,
            org,
            to_period(section.period),
            section=flux_section,
            account_numbers=None,
        )
        rows = _filter_flux_rows_for_section(
            rows,
            section_id=section_id,
            account_numbers=account_numbers,
        )
        loaded = brief_flux_for_rollup(rows, materiality=materiality)[:FLUX_EVENT_CAP]
    except Exception:
        loaded = []
    return section.model_copy(update={"events": [CustomerEventIn.model_validate(item) for item in loaded]})


def _other_accounts_remainder(
    variance: float | None,
    facts: list[dict[str, Any]],
    drivers: list[dict[str, Any]],
) -> float | None:
    """Driver-list remainder — other accounts, not an unresolved plug."""
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


def unexplained_plug(
    *,
    amount: float | None,
    label: str,
    resolve_hint: str,
) -> dict[str, Any] | None:
    """True unresolved gap — call out the dollars and point the reader at follow-up work."""
    value = _number(amount)
    hint = str(resolve_hint or "").strip()
    if value is None or abs(value) < 1 or not hint:
        return None
    return {
        "kind": "unexplained",
        "label": str(label or "Unresolved").strip() or "Unresolved",
        "amount": value,
        "must_name": True,
        "resolve_hint": hint,
    }


_NUMBER_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
_LARGELY_RE = re.compile(r"\b(?:largely|nearly flat|almost flat)\b", re.IGNORECASE)
_RESTATE_RE = re.compile(r"moved with (?:the )?(?:total|revenue)|with total revenue", re.IGNORECASE)
_UNEXPLAINED_WORD = re.compile(r"\bunexplained\b", re.IGNORECASE)
_OTHER_ACCOUNTS_WORD = re.compile(r"\bother accounts?\b", re.IGNORECASE)
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


def _label_words(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _cause_is_supported(phrase: str, evidence: dict[str, Any]) -> bool:
    """Naming a loaded account, then the section change, is not a new cause."""
    labels: list[str] = []
    parent = str((evidence.get("parent") or {}).get("label") or "")
    if parent:
        labels.append(parent)
    for line in evidence.get("lines") or []:
        for label in [line.get("label"), *(line.get("aliases") or [])]:
            if label:
                labels.append(str(label))
        for fact in line.get("facts") or []:
            if fact.get("label"):
                labels.append(str(fact["label"]))
        for driver in line.get("drivers") or []:
            if driver.get("label"):
                labels.append(str(driver["label"]))
    normalized = _label_words(phrase)
    names = []
    for label in labels:
        text = _label_words(label)
        if len(text) < 3:
            continue
        names.append(text)
        without_number = re.sub(r"^\d{3,6}\s+", "", text)
        if without_number and without_number != text:
            names.append(without_number)
    names.sort(key=len, reverse=True)
    removed = False
    for name in names:
        if name and name in normalized:
            normalized = normalized.replace(name, " ")
            removed = True
    normalized = re.sub(
        r"\b(?:section|change|total|overall|parent|with|against|versus|increasing|decreasing|higher|lower|increase|decrease|offset|offsetting|partial|partially)\b",
        " ",
        normalized,
    )
    normalized = re.sub(r"\b\d+(?:\.\d+)?\b", " ", normalized)
    leftover = [word for word in normalized.split() if len(word) >= 3]
    return removed and not leftover


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


def _customer_aliases(customer: str) -> list[str]:
    """The stored name, and that name without a trailing id such as 166."""
    name = customer.strip()
    if not name:
        return []
    aliases = [name]
    trimmed = re.sub(r"\s+\d+$", "", name).strip()
    if trimmed and trimmed.casefold() != name.casefold():
        aliases.append(trimmed)
    return aliases


def _customer_named(text: str, customer: str) -> bool:
    haystack = text.casefold()
    return any(alias.casefold() in haystack for alias in _customer_aliases(customer))


def _matches_event(captured: str, events: list[dict[str, Any]]) -> bool:
    """The event bucket and the customer name are allowed, including a longer phrase that starts with either."""
    name = captured.strip().lower()
    if not name:
        return False
    for event in events:
        for raw in (event.get("customer"), event.get("bucket")):
            label = str(raw or "").strip().lower()
            if not label:
                continue
            if name == label or name.startswith(label + " ") or label.startswith(name + " "):
                return True
    return False


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
    relationships = evidence.get("relationships") or []
    has_unexplained = any(
        item.get("kind") == "unexplained" and item.get("must_name") for item in relationships
    )
    if _UNEXPLAINED_WORD.search(text) and not has_unexplained:
        return False, "The analysis calls a known change unexplained."
    if not evidence.get("largely") and _LARGELY_RE.search(text):
        return False, "The analysis calls the move largely offset, and the evidence does not."
    for relationship in relationships:
        kind = relationship.get("kind")
        if not relationship.get("must_name"):
            continue
        amount = _number(relationship.get("amount"))
        if amount is None or abs(amount) < 1:
            continue
        if kind == "other_accounts":
            if not _amount_named(text, amount):
                return False, f"The analysis leaves out the other-accounts {abs(round(amount)):,.0f}."
            if not _OTHER_ACCOUNTS_WORD.search(text):
                return False, "The analysis leaves out other accounts for the driver remainder."
            if _UNEXPLAINED_WORD.search(text):
                return False, "The analysis calls other accounts unexplained."
        elif kind == "unexplained":
            if not _amount_named(text, amount):
                return False, f"The analysis leaves out the unexplained {abs(round(amount)):,.0f}."
            if not _UNEXPLAINED_WORD.search(text):
                return False, "The analysis leaves out unexplained for an unresolved plug."
            hint = str(relationship.get("resolve_hint") or "").strip()
            if hint and hint.lower() not in text.lower():
                return False, "The analysis leaves out how to resolve the unexplained amount."
    events = evidence.get("events") or []
    known = {str(event.get("customer") or "").strip().lower() for event in events}
    known.discard("")
    labels, comparison = _evidence_labels(evidence)
    if not events and _DEAL_OUTCOME.search(text):
        return False, "The analysis names a customer the evidence does not list."
    for match in _CUSTOMER_CLAIM.finditer(text):
        captured = match.group(1).strip()
        if _is_listed_name(captured, labels, comparison) or _matches_event(captured, events):
            continue
        if captured.lower() not in known:
            return False, "The analysis names a customer the evidence does not list."
    for event in events:
        customer = str(event.get("customer") or "").strip()
        if customer and not _customer_named(text, customer):
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
            if phrase and (_names_only_the_total(phrase) or _cause_is_supported(phrase, evidence)):
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


def _phrase_fact(fact: dict[str, Any]) -> dict[str, Any] | None:
    """Counts stay whole numbers. Fees and average revenue use $ and k."""
    label = str(fact.get("label") or "")
    count = _is_count_fact(label)
    current = _number(fact.get("current")) if "current" in fact else None
    base = _number(fact.get("base")) if "base" in fact else None
    # Money from/to facts need both sides or the model writes empty "from to".
    if not count and ("current" in fact or "base" in fact):
        if current is None or base is None:
            if "amount" not in fact and "heads" not in fact and "paid" not in fact:
                return None
    phrased: dict[str, Any] = {"label": label}
    for key in ("current", "base", "amount", "heads", "paid", "quota"):
        if key not in fact:
            continue
        number = _number(fact[key])
        if number is None:
            continue
        if count or key == "heads":
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
        line["facts"] = [
            phrased
            for phrased in (_phrase_fact(fact) for fact in line.get("facts") or [])
            if phrased
        ]
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
            # Keep the sign on MoM deltas so the model can say up/down.
            amount = _number(event.get("amount"))
            if amount is not None:
                event["amount"] = _money_phrase(amount) if amount < 0 else _phrase_value(amount, per_unit=False)
        if event.get("others_amount"):
            event["others_amount"] = _phrase_value(event["others_amount"], per_unit=False)
        for key in ("prior_amount", "current_amount"):
            if key in event:
                event[key] = _phrase_value(event[key], per_unit=False)
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


def _drop_unknown_customers(text: str, evidence: dict[str, Any]) -> str:
    """Drop a name that is not a line and not an event. Keep the rest of the sentence."""
    events = evidence.get("events") or []
    known = {str(event.get("customer") or "").strip().lower() for event in events}
    known.discard("")
    labels, comparison = _evidence_labels(evidence)

    def replacer(match: re.Match[str]) -> str:
        captured = match.group(1).strip()
        if _is_listed_name(captured, labels, comparison) or _matches_event(captured, events) or captured.lower() in known:
            return match.group(0)
        return ""

    cleaned = _CUSTOMER_CLAIM.sub(replacer, text)
    if not events:
        cleaned = _DEAL_OUTCOME.sub("", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;])", r"\1", cleaned)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    return cleaned.strip()


def _without_unknown_customers(paragraph: str, evidence: dict[str, Any]) -> str:
    cleaned = _drop_unknown_customers(paragraph, evidence)
    if not cleaned or cleaned == paragraph.strip():
        return ""
    ok, _reason = check_revenue_paragraph(cleaned, evidence)
    return cleaned if ok else ""


def _other_accounts_clause(amount: float) -> str:
    return f"{_money_phrase(abs(amount)).lstrip('-')} is in other accounts"


def _rewrite_unexplained_as_other_accounts(paragraph: str, evidence: dict[str, Any]) -> str:
    """When evidence has other_accounts remainders, never leave the red-flag word in prose."""
    has_other = any(
        item.get("kind") == "other_accounts" and item.get("must_name")
        for item in evidence.get("relationships") or []
    )
    has_true_plug = any(
        item.get("kind") == "unexplained" and item.get("must_name")
        for item in evidence.get("relationships") or []
    )
    text = (paragraph or "").strip()
    if not text or not has_other or has_true_plug:
        return ""
    cleaned = text
    # Common model phrasings → other accounts.
    cleaned = re.sub(
        r"\ban?\s+unexplained\s+amount\s+of\s+(\$[\d,]+(?:\.\d+)?[km]?)\s+remains(?:\s+on\s+[^.]+)?",
        r"\1 is in other accounts",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bwhile\s+(\$[\d,]+(?:\.\d+)?[km]?)\s+(?:is|remained|remains)\s+unexplained\b",
        r"with \1 in other accounts",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bwith\s+(\$[\d,]+(?:\.\d+)?[km]?)\s+unexplained\b",
        r"with \1 in other accounts",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"(\$[\d,]+(?:\.\d+)?[km]?)\s+is\s+unexplained\b",
        r"\1 is in other accounts",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:is|was|remains|remained)\s+unexplained\b",
        "is in other accounts",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Drop any leftover unexplained token rather than inventing awkward grammar.
    cleaned = re.sub(r"\bunexplained\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = cleaned.strip(" ,;:")
    if not cleaned or cleaned == text:
        return ""
    # Return even when verify still fails — later repair fills missing other-accounts clauses.
    return cleaned


def _with_missing_other_accounts(paragraph: str, evidence: dict[str, Any]) -> str:
    """Append missing other-accounts remainders onto the matching line sentence."""
    text = (paragraph or "").strip()
    if not text:
        return ""
    needed = [
        item
        for item in evidence.get("relationships") or []
        if item.get("kind") == "other_accounts"
        and item.get("must_name")
        and _number(item.get("amount")) is not None
        and abs(_number(item.get("amount")) or 0) >= 1
    ]
    if not needed:
        return ""
    if _OTHER_ACCOUNTS_WORD.search(text) and all(
        _amount_named(text, _number(item.get("amount")) or 0) for item in needed
    ):
        return ""
    blocks = [block.strip() for block in text.split("\n") if block.strip()]
    if not blocks:
        return ""
    for item in needed:
        amount = _number(item.get("amount")) or 0.0
        if _amount_named(text, amount) and _OTHER_ACCOUNTS_WORD.search(text):
            continue
        clause = _other_accounts_clause(amount)
        label = str(item.get("label") or "").strip()
        placed = False
        for index, block in enumerate(blocks):
            if label and _line_starts_with_label(block, label):
                if _amount_named(block, amount) and _OTHER_ACCOUNTS_WORD.search(block):
                    placed = True
                    break
                blocks[index] = block.rstrip(".") + f", with {clause}."
                placed = True
                break
        if not placed:
            blocks[0] = blocks[0].rstrip(".") + f", with {clause}."
        text = "\n".join(blocks)
    ok, _reason = check_revenue_paragraph(text, evidence)
    return _finalize_paragraph(text, evidence) if ok else ""


def _event_sentence(event: dict[str, Any]) -> str:
    """One sentence that names the stored customer and MoM (or ARR) amount."""
    customer = _customer_aliases(str(event.get("customer") or ""))
    alias = customer[-1] if customer else ""
    amount = _number(event.get("amount"))
    if not alias or amount is None or abs(amount) < 1:
        return ""
    money = _money_phrase(abs(amount)).lstrip("-")
    outcome = str(event.get("outcome") or "")
    event_kind = str(event.get("event_kind") or "").strip()
    if outcome in {"came in", "did not come in"}:
        sentence = f"{alias} {outcome} at {money}"
    elif event_kind in {"payroll_batch", "vendor_spend", "credit_reversal"}:
        # OpEx/CoR event amount is MoM change, not period stock.
        direction = "up" if amount >= 0 else "down"
        bucket = str(event.get("bucket") or "Activity").strip() or "Activity"
        sentence = f"{bucket} {alias} {direction} {money}"
    else:
        bucket = str(event.get("bucket") or "The month").strip() or "The month"
        sentence = f"{bucket} included {alias} at {money}"
    others = int(event.get("others") or 0)
    others_amount = _number(event.get("others_amount"))
    if others > 0 and others_amount is not None and abs(others_amount) >= 1:
        sentence += f", and {others} others at {_money_phrase(abs(others_amount)).lstrip('-')}"
    return sentence + "."


def _line_starts_with_label(block: str, label: str) -> bool:
    text = block.lstrip()
    if not label:
        return False
    if text.startswith(label):
        return True
    for alias in _aliases(label):
        if text.lower().startswith(alias.lower()):
            return True
    return _is_subscription_label(label) and text.lower().find("subscription") == 0


def _event_target_label(event: dict[str, Any], evidence: dict[str, Any]) -> str:
    """Prefer department (OpEx), then account line; fall back to subscription for revenue ARR."""
    department = str(event.get("department") or "").strip()
    account_number = str(event.get("account_number") or "").strip()
    account_label = str(event.get("account_label") or "").strip()
    for line in evidence.get("lines") or []:
        label = str(line.get("label") or "").strip()
        if not label:
            continue
        if department and (
            department.casefold() == label.casefold()
            or department.casefold() in label.casefold()
            or label.casefold() in department.casefold()
        ):
            return label
    for line in evidence.get("lines") or []:
        label = str(line.get("label") or "").strip()
        if not label:
            continue
        if account_number and re.search(rf"\b{re.escape(account_number)}\b", label):
            return label
        if account_label and (
            account_label.casefold() in label.casefold() or label.casefold() in account_label.casefold()
        ):
            return label
    return _subscription_line_label(evidence)


def _insert_on_line(paragraph: str, evidence: dict[str, Any], additions: list[str], target_label: str) -> str:
    """Append event sentences onto the matching account (or subscription) block."""
    addition = " ".join(sentence for sentence in additions if sentence).strip()
    if not addition:
        return paragraph
    text = separate_lines(paragraph, evidence).rstrip()
    if not text:
        return addition
    blocks = text.split("\n")
    if target_label:
        for index, block in enumerate(blocks):
            if _line_starts_with_label(block, target_label):
                blocks[index] = block.rstrip() + " " + addition
                return "\n".join(blocks)
        if "subscription" in target_label.lower():
            for index, block in enumerate(blocks):
                if "subscription" in block[:120].lower():
                    blocks[index] = block.rstrip() + " " + addition
                    return "\n".join(blocks)
    # No matched dept/account — do not dump onto the first OpEx line (e.g. Sales).
    if len(blocks) == 1 and _subscription_line_label(evidence):
        return text + " " + addition
    if not target_label:
        return text + "\n" + addition
    if len(blocks) == 1:
        return text + " " + addition
    return text + "\n" + addition


def _insert_after_subscription(paragraph: str, evidence: dict[str, Any], additions: list[str]) -> str:
    """Put event sentences on the subscription block, not after the last account."""
    return _insert_on_line(paragraph, evidence, additions, _subscription_line_label(evidence))


def _relocate_orphan_events(paragraph: str, evidence: dict[str, Any]) -> str:
    """Move bucket-included trailers onto the matching account or subscription line."""
    text = separate_lines(paragraph, evidence)
    events = evidence.get("events") or []
    if not events:
        return text
    blocks = text.split("\n")
    if len(blocks) < 2:
        return text
    labels = [str(line.get("label") or "") for line in evidence.get("lines") or []]
    kept: list[str] = []
    orphans: list[str] = []
    for block in blocks:
        stripped = block.strip()
        if not stripped:
            continue
        on_account = any(_line_starts_with_label(stripped, label) for label in labels if label)
        if on_account:
            kept.append(stripped)
            continue
        if _EVENT_BUCKET_START.match(stripped) or " included " in stripped.lower():
            orphans.append(stripped)
        else:
            kept.append(stripped)
    if not orphans:
        return "\n".join(kept)
    # Prefer account-scoped placement when events carry account_label.
    account_events = [event for event in events if event.get("account_label") or event.get("account_number")]
    if account_events:
        joined = "\n".join(kept)
        # Match each orphan to a named counterparty when possible; else first account event.
        remaining = list(orphans)
        for event in account_events:
            customer = str(event.get("customer") or "").strip()
            matched = [item for item in remaining if customer and customer.casefold() in item.casefold()]
            if not matched and len(account_events) == 1 and remaining:
                matched = list(remaining)
            if not matched:
                continue
            for item in matched:
                remaining.remove(item)
            joined = _insert_on_line(joined, evidence, matched, _event_target_label(event, evidence))
        if remaining:
            joined = _insert_on_line(joined, evidence, remaining, _event_target_label(account_events[0], evidence))
        return joined
    return _insert_after_subscription("\n".join(kept), evidence, orphans)


def _with_missing_customers(paragraph: str, evidence: dict[str, Any]) -> str:
    """Drop a name that is not stored, then add any stored customer the paragraph still omits."""
    text = _drop_unknown_customers(paragraph, evidence)
    missing_events = [
        event
        for event in evidence.get("events") or []
        if str(event.get("customer") or "").strip() and not _customer_named(text, str(event.get("customer") or ""))
    ]
    if not missing_events:
        return "" if text == paragraph.strip() else text
    # Place each missing event on its account line when labeled; otherwise subscription.
    by_target: dict[str, list[str]] = {}
    order: list[str] = []
    for event in missing_events:
        sentence = _event_sentence(event)
        if not sentence:
            continue
        target = _event_target_label(event, evidence) or _subscription_line_label(evidence)
        if target not in by_target:
            by_target[target] = []
            order.append(target)
        by_target[target].append(sentence)
    updated = text
    for target in order:
        updated = _insert_on_line(updated, evidence, by_target[target], target)
    return updated


def _without_customer_gap(paragraph: str, evidence: dict[str, Any]) -> str:
    repaired = _with_missing_customers(paragraph, evidence)
    if not repaired or repaired == paragraph.strip():
        return ""
    ok, _reason = check_revenue_paragraph(repaired, evidence)
    return repaired if ok else ""


def _without_unknown_amounts(paragraph: str, evidence: dict[str, Any]) -> str:
    """Drop dollar/bare amounts the evidence does not allow so customer repair can succeed."""
    allowed = {float(item) for item in evidence.get("allowed_numbers") or []}
    plain = {float(item) for item in evidence.get("plain_numbers") or []}
    text = (paragraph or "").strip()
    if not text:
        return ""

    def replace_currency(match: re.Match[str]) -> str:
        raw = match.group(1).replace(",", "")
        suffix = match.group(2)
        stated = abs(float(raw))
        decimals = len(raw.split(".", 1)[1]) if "." in raw else 0
        kind = suffix.lower() if suffix else None
        if _currency_matches(stated, kind, allowed, decimals):
            return match.group(0)
        if not kind and _number_allowed(stated, plain):
            return match.group(0)
        return ""

    cleaned = _CURRENCY_RE.sub(replace_currency, text)
    # Drop invented percent callouts; evidence already carries the MoM rate in plain numbers.
    cleaned = re.sub(r"\s*\(\s*-?\d+(?:\.\d+)?\s*%\s*\)", "", cleaned)

    out_parts: list[str] = []
    last = 0
    for match in _NUMBER_RE.finditer(cleaned):
        out_parts.append(cleaned[last : match.start()])
        start = match.start()
        window = cleaned[max(0, start - 3) : start]
        if "$" in window:
            out_parts.append(match.group(0))
        else:
            raw = match.group(0).replace(",", "")
            try:
                stated = abs(float(raw))
            except ValueError:
                out_parts.append(match.group(0))
                last = match.end()
                continue
            if (
                _number_allowed(stated, plain)
                or _number_allowed(stated, allowed)
                or _scaled_amount(stated, allowed)
            ):
                out_parts.append(match.group(0))
        last = match.end()
    out_parts.append(cleaned[last:])
    cleaned = "".join(out_parts)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = cleaned.strip(" ,;:")
    if not cleaned or cleaned == paragraph.strip():
        return ""
    return cleaned


def _line_change_sentence(line: dict[str, Any]) -> str:
    label = str(line.get("label") or "").strip()
    variance = _number(line.get("variance"))
    current = _number(line.get("current"))
    if not label or variance is None:
        return ""
    direction = "increased" if variance >= 0 else "decreased"
    sentence = f"{label} {direction} {_money_phrase(abs(variance)).lstrip('-')}"
    if current is not None:
        sentence += f" to {_money_phrase(current).lstrip('-')}"
    facts = line.get("facts") or []
    for fact in facts[:2]:
        fact_label = str(fact.get("label") or "").strip()
        if not fact_label:
            continue
        current_value = _number(fact.get("current"))
        base_value = _number(fact.get("base"))
        if current_value is None:
            continue
        if _is_count_fact(fact_label):
            if base_value is not None and base_value != current_value:
                sentence += f"; {fact_label} {int(round(base_value))} to {int(round(current_value))}"
            else:
                sentence += f"; {fact_label} {int(round(current_value))}"
        else:
            sentence += f"; {fact_label} {_money_phrase(current_value).lstrip('-')}"
            if base_value is not None:
                sentence += f" from {_money_phrase(base_value).lstrip('-')}"
    other = _number(line.get("other_accounts"))
    if other is not None and abs(other) >= 1:
        sentence += f", with {_other_accounts_clause(other)}"
    return sentence + "."


def _deterministic_rollup_paragraph(evidence: dict[str, Any]) -> str:
    """Account-line commentary from evidence only — used when the model cannot be kept."""
    blocks: list[str] = []
    sub_label = _subscription_line_label(evidence)
    event_bits = [_event_sentence(event) for event in evidence.get("events") or []]
    event_bits = [bit for bit in event_bits if bit]
    for line in evidence.get("lines") or []:
        sentence = _line_change_sentence(line)
        if not sentence:
            continue
        label = str(line.get("label") or "")
        if event_bits and (
            (sub_label and _line_starts_with_label(sentence, sub_label))
            or (not sub_label and "subscription" in label.lower())
        ):
            sentence = sentence.rstrip(".") + " " + " ".join(event_bits)
            if not sentence.endswith("."):
                sentence += "."
            event_bits = []
        blocks.append(sentence)
    if event_bits and blocks:
        blocks[0] = blocks[0].rstrip(".") + " " + " ".join(event_bits)
        if not blocks[0].endswith("."):
            blocks[0] += "."
    text = "\n".join(blocks).strip()
    if not text:
        return ""
    ok, _reason = check_revenue_paragraph(text, evidence)
    return _finalize_paragraph(text, evidence) if ok else ""


def separate_lines(paragraph: str, evidence: dict[str, Any]) -> str:
    """A department starts a new line only when that name starts its own sentence."""
    text = paragraph.replace("\r\n", "\n")
    text = re.sub(r"([^.!?\n])[ \t]*\n+[ \t]*", r"\1 ", text)
    labels = [str(line.get("label") or "").strip() for line in evidence.get("lines") or []]
    labels = sorted((label for label in labels if label), key=len, reverse=True)
    for label in labels:
        pattern = re.compile(r"([.!?])[ \t]+(?=" + re.escape(label) + r"(?!\w))")
        text = pattern.sub(r"\1\n", text)
    return text


def _finalize_paragraph(paragraph: str, evidence: dict[str, Any]) -> str:
    return _relocate_orphan_events(separate_lines(paragraph, evidence), evidence)


def _without_empty_from_to(paragraph: str, evidence: dict[str, Any]) -> str:
    """Drop blank ARR ranges the model invents when a side is missing."""
    del evidence
    text = (paragraph or "").strip()
    if not text:
        return ""
    cleaned = re.sub(
        r"\b(?:improving|worsening|declining|increasing|decreasing)\s+from\s+to\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\bfrom\s+to\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = cleaned.strip(" ,;:")
    if not cleaned or cleaned == text:
        return ""
    return cleaned


def _repair_paragraph(paragraph: str, evidence: dict[str, Any]) -> str:
    """Strip unsupported wording/numbers, then place missing named events on the right line."""
    text = paragraph
    for step in (
        _without_unearned_largely,
        _without_unknown_customers,
        _without_unknown_amounts,
        _without_empty_from_to,
        _rewrite_unexplained_as_other_accounts,
    ):
        cleaned = step(text, evidence)
        if cleaned:
            text = cleaned
    filled = _with_missing_customers(text, evidence)
    if filled:
        text = filled
    remainder = _with_missing_other_accounts(text, evidence)
    if remainder:
        return remainder
    ok, _reason = check_revenue_paragraph(text, evidence)
    return _finalize_paragraph(text, evidence) if ok else ""


def _kept_paragraph(paragraph: str, evidence: dict[str, Any]) -> str:
    ok, _reason = check_revenue_paragraph(paragraph, evidence)
    if ok:
        return _finalize_paragraph(paragraph, evidence)
    repaired = _repair_paragraph(paragraph, evidence)
    if repaired:
        return repaired
    return _deterministic_rollup_paragraph(evidence)


def analyze_revenue_rollup(section: RevenueSectionIn, client: Any | None) -> RevenueRollupResult:
    evidence = build_revenue_evidence(section)
    shown = present_revenue_evidence(evidence)
    if client is None:
        salvaged = _deterministic_rollup_paragraph(evidence)
        if salvaged:
            return RevenueRollupResult(status="ai", paragraph=salvaged, evidence=shown)
        return RevenueRollupResult(
            status="fallback",
            reason="No analysis model is configured. Showing the calculated sentence.",
            evidence=shown,
        )
    try:
        raw = client.generate(system_prompt=ROLLUP_SYSTEM, user_prompt=json.dumps(shown, default=str))
    except (LLMError, Exception):
        salvaged = _deterministic_rollup_paragraph(evidence)
        if salvaged:
            return RevenueRollupResult(status="ai", paragraph=salvaged, evidence=shown)
        return RevenueRollupResult(
            status="fallback",
            reason="The analysis is unavailable. Showing the calculated sentence.",
            evidence=shown,
        )
    paragraph = str(raw.get("paragraph") or "").strip() if isinstance(raw, dict) else ""
    ok, reason = check_revenue_paragraph(paragraph, evidence)
    if not ok and paragraph:
        kept = _kept_paragraph(paragraph, evidence)
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
            if second_ok:
                return RevenueRollupResult(status="ai", paragraph=_finalize_paragraph(second, evidence), evidence=shown)
            kept = _kept_paragraph(second, evidence)
            if kept:
                return RevenueRollupResult(status="ai", paragraph=kept, evidence=shown)
            reason = second_reason or reason
    if not ok:
        salvaged = _deterministic_rollup_paragraph(evidence)
        if salvaged:
            return RevenueRollupResult(status="ai", paragraph=salvaged, evidence=shown)
        return RevenueRollupResult(status="fallback", reason=reason, evidence=shown)
    return RevenueRollupResult(status="ai", paragraph=_finalize_paragraph(paragraph, evidence), evidence=shown)
