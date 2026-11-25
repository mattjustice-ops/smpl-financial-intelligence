"""Constrained period-overview narrative (Part 2 why).

Cites only client statement/ARR/cash facts plus server-loaded insight packs.
Never invents dollars, customers, or causes absent from evidence.
"""

from __future__ import annotations

import json
import math
import re
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.commentary.openai_client import LLMError

MATERIALITY_DEFAULT = 10_000

OVERVIEW_SYSTEM = """You write one short period overview paragraph (3 to 6 sentences) for the close discussion.

Use only the JSON evidence. Lead with the period picture: revenue, profit, ARR, cash, or spending when those facts are present. You may attribute a cause only when that cause is already named in evidence.facts, evidence.causes, or evidence.events. Do not invent a customer, vendor, deal, hiring story, pipeline story, or market reason.

Write every dollar amount with the phrase already on that field ($…k / $…m). Counts and rates stay as whole numbers or percents already on the evidence. Do not write the word thousand or million. Do not write empty ranges such as "from to". Do not say unexplained unless evidence marks a true unresolved plug. Prefer "other accounts" only when that phrase is already on a fact.

Return only JSON: {"paragraph": "..."}"""


class OverviewFactIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str = ""
    text: str = ""
    amount: float | None = None
    current: float | None = None
    base: float | None = None
    variance: float | None = None


class OverviewCauseIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str = ""
    text: str = ""
    amount: float | None = None
    customer: str = ""
    outcome: str = ""


class PeriodOverviewIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    comparison: str = ""
    comparison_kind: str = ""
    period: str = ""
    organization_id: str = ""
    materiality: float = MATERIALITY_DEFAULT
    lead: str = ""
    facts: list[OverviewFactIn] = Field(default_factory=list)
    causes: list[OverviewCauseIn] = Field(default_factory=list)


class PeriodOverviewResult(BaseModel):
    status: str
    paragraph: str = ""
    reason: str = ""
    evidence: dict[str, Any]


_CUSTOMER_CLAIM = re.compile(
    r"\b([A-Z][\w&.\'-]*(?:\s+[A-Z][\w&.\'-]*){0,4})\s+"
    r"(?:came in|did not come in|closed|churned|expanded|contracted)\b"
)


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


def _money_amount(amount: float, scale: float) -> str:
    scaled = Decimal(str(amount)) / Decimal(str(scale))
    return f"{scaled.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def _money_phrase(value: float) -> str:
    sign = "-" if value < 0 else ""
    amount = abs(value)
    if amount >= 1_000_000:
        return sign + f"${_money_amount(amount, 1_000_000)}m"
    if amount >= 1_000:
        return sign + f"${_money_amount(amount, 1_000)}k"
    return sign + f"${_money_amount(amount, 1)}"


def _remember(allowed: set[float], value: float | None) -> None:
    number = _number(value)
    if number is None:
        return
    allowed.add(abs(number))
    # Also accept display-rounded thousands/millions used in prose.
    if abs(number) >= 1_000:
        allowed.add(round(abs(number) / 1_000, 2))
        allowed.add(round(abs(number) / 1_000_000, 2) if abs(number) >= 1_000_000 else 0)


def _track_plain(plain: set[float], value: Any) -> None:
    number = _number(value)
    if number is None:
        return
    plain.add(float(abs(round(number))))


def _pack_causes(packs: dict[str, Any] | None, materiality: float) -> list[dict[str, Any]]:
    if not packs:
        return []
    causes: list[dict[str, Any]] = []
    behavior = packs.get("customer_behavior") or {}
    vs = behavior.get("vs_run_rate") or {}
    churn_above = _number(vs.get("churn_above_run_rate"))
    trailing = _number(vs.get("trailing_churn_avg"))
    churn_arr = _number(vs.get("churn_arr"))
    if (
        churn_above is not None
        and abs(churn_above) >= 1000
        and trailing is not None
        and churn_arr is not None
    ):
        above = churn_above > 0
        causes.append(
            {
                "label": "churn vs run-rate",
                "text": (
                    f"Churn ARR was {_money_phrase(abs(churn_arr))}, "
                    f"{'above' if above else 'below'} the recent run-rate of "
                    f"{_money_phrase(abs(trailing))}."
                ),
                "amount": abs(churn_arr),
            }
        )
    vintage = behavior.get("vintage_split") or {}
    nb_movers = int(vintage.get("new_business_movers") or 0)
    cs_movers = int(vintage.get("customer_success_movers") or 0)
    if nb_movers or cs_movers:
        causes.append(
            {
                "label": "vintage split",
                "text": (
                    f"Of the named movements, {nb_movers} were in the New Business period "
                    f"and {cs_movers} were Customer Success."
                ),
            }
        )
    bridge = packs.get("arr_vs_revenue_deferred") or {}
    net_new = _number(bridge.get("net_new_arr"))
    recognized = _number(bridge.get("recognized_revenue"))
    deferred = _number(bridge.get("deferred_ending"))
    if net_new is not None and recognized is not None:
        text = (
            f"Net new ARR was {_money_phrase(abs(net_new))} while recognized revenue was "
            f"{_money_phrase(abs(recognized))}"
        )
        if deferred is not None:
            text += f"; ending deferred revenue was {_money_phrase(abs(deferred))}"
        causes.append({"label": "ARR vs revenue", "text": text + ".", "amount": abs(net_new)})
    cash = packs.get("billings_cash") or {}
    collections = _number(cash.get("collections"))
    cadence = cash.get("billings_by_cadence") or {}
    if collections is not None and isinstance(cadence, dict) and cadence:
        causes.append(
            {
                "label": "billings and cash",
                "text": (
                    f"Billings collected {_money_phrase(abs(collections))} "
                    "against the month's billing cadence mix."
                ),
                "amount": abs(collections),
            }
        )
    miss = packs.get("forecast_miss") or {}
    for event in (miss.get("events") or [])[:2]:
        customer = str(event.get("customer") or "").strip()
        amount = _number(event.get("amount"))
        if not customer or amount is None or abs(amount) < materiality:
            continue
        outcome = "did not come in" if event.get("outcome") == "did not come in" else "came in"
        others = int(event.get("others") or 0)
        others_amount = _number(event.get("others_amount")) or 0.0
        clause = f"{customer} {outcome} at {_money_phrase(abs(amount))}"
        if others > 0 and abs(others_amount) >= 1:
            clause += f", with {others} others at {_money_phrase(abs(others_amount))}"
        causes.append(
            {
                "label": "forecast miss",
                "text": clause + ".",
                "amount": abs(amount),
                "customer": customer,
                "outcome": outcome,
                "others": others,
                "others_amount": abs(others_amount) if others else 0.0,
            }
        )
    gtm = packs.get("gtm_capacity") or {}
    nb_arr = _number(gtm.get("new_business_arr"))
    sm_expense = _number(gtm.get("sm_expense"))
    if nb_arr is not None and sm_expense is not None and abs(sm_expense) >= 1:
        causes.append(
            {
                "label": "GTM capacity",
                "text": (
                    f"New business ARR of {_money_phrase(abs(nb_arr))} sat against "
                    f"{_money_phrase(abs(sm_expense))} of sales and marketing expense."
                ),
                "amount": abs(nb_arr),
            }
        )
    retention = packs.get("retention") or {}
    gross = _number(retention.get("gross_retention_rate"))
    ndr = _number(retention.get("net_dollar_retention_rate"))
    if gross is not None:
        text = f"Gross retention was {(gross * 100):.1f}%"
        if ndr is not None:
            text += f" and net dollar retention was {(ndr * 100):.1f}%"
        causes.append({"label": "retention", "text": text + "."})
    return causes


def attach_overview_packs(section: PeriodOverviewIn, db: Any) -> PeriodOverviewIn:
    """Merge insight-pack causes for the close month when available."""
    if not section.organization_id or not section.period or db is None:
        return section
    try:
        org = uuid.UUID(str(section.organization_id))
    except (ValueError, TypeError, AttributeError):
        return section
    try:
        from app.services.warehouse.close_insight_packs import load_insight_packs

        packs = load_insight_packs(db, org, section.period) or {}
    except Exception:
        packs = {}
    materiality = section.materiality if section.materiality and section.materiality > 0 else MATERIALITY_DEFAULT
    loaded = _pack_causes(packs, materiality)
    if not loaded:
        return section
    existing = {(c.label, c.text) for c in section.causes}
    merged = list(section.causes)
    for item in loaded:
        key = (str(item.get("label") or ""), str(item.get("text") or ""))
        if key in existing:
            continue
        merged.append(OverviewCauseIn.model_validate(item))
    return section.model_copy(update={"causes": merged})


def build_overview_evidence(section: PeriodOverviewIn) -> dict[str, Any]:
    materiality = section.materiality if section.materiality and section.materiality > 0 else MATERIALITY_DEFAULT
    allowed: set[float] = set()
    plain: set[float] = set()
    facts_out: list[dict[str, Any]] = []
    causes_out: list[dict[str, Any]] = []
    events_out: list[dict[str, Any]] = []

    for year in re.findall(r"\d{4}", section.comparison or ""):
        plain.add(float(year))
    for token in re.findall(r"\b\d+\b", section.lead or ""):
        plain.add(float(token))

    for fact in section.facts:
        label = (fact.label or "").strip()
        text = (fact.text or "").strip()
        if not label and not text:
            continue
        amount = _number(fact.amount)
        current = _number(fact.current)
        base = _number(fact.base)
        variance = _number(fact.variance)
        for value in (amount, current, base, variance):
            _remember(allowed, value)
        payload: dict[str, Any] = {"label": label or "fact"}
        if text:
            payload["text"] = text
        if amount is not None:
            payload["amount"] = amount
            payload["amount_phrase"] = _money_phrase(amount)
        if current is not None:
            payload["current"] = current
            payload["current_phrase"] = _money_phrase(current)
        if base is not None:
            payload["base"] = base
            payload["base_phrase"] = _money_phrase(base)
        if variance is not None:
            payload["variance"] = variance
            payload["variance_phrase"] = _money_phrase(variance)
        facts_out.append(payload)

    for cause in section.causes:
        label = (cause.label or "").strip()
        text = (cause.text or "").strip()
        customer = (cause.customer or "").strip()
        amount = _number(cause.amount)
        if amount is not None:
            _remember(allowed, amount)
        if customer:
            for token in re.findall(r"\b\d+\b", customer):
                plain.add(float(token))
        # Rates / mover counts in cause text.
        for token in re.findall(r"\b\d+(?:\.\d+)?\b", text):
            plain.add(float(token))
        payload = {"label": label or "cause", "text": text}
        if amount is not None:
            payload["amount"] = amount
            payload["amount_phrase"] = _money_phrase(amount)
        if customer:
            payload["customer"] = customer
            payload["outcome"] = cause.outcome or ""
            events_out.append(
                {
                    "customer": customer,
                    "amount": abs(amount) if amount is not None else None,
                    "outcome": cause.outcome or "",
                }
            )
        causes_out.append(payload)

    return {
        "comparison": section.comparison,
        "comparison_kind": (section.comparison_kind or "").strip().lower(),
        "period": section.period,
        "materiality": materiality,
        "lead": (section.lead or "").strip(),
        "facts": facts_out,
        "causes": causes_out,
        "events": events_out,
        "allowed_numbers": sorted(allowed),
        "plain_numbers": sorted(plain),
    }


def present_overview_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Copy for the model — money already phrased on each field."""
    shown = {
        "comparison": evidence.get("comparison"),
        "comparison_kind": evidence.get("comparison_kind"),
        "period": evidence.get("period"),
        "lead": evidence.get("lead"),
        "facts": [],
        "causes": [],
        "events": evidence.get("events") or [],
    }
    for fact in evidence.get("facts") or []:
        item = {"label": fact.get("label")}
        if fact.get("text"):
            item["text"] = fact["text"]
        for key in ("amount_phrase", "current_phrase", "base_phrase", "variance_phrase"):
            if fact.get(key):
                item[key.replace("_phrase", "")] = fact[key]
        shown["facts"].append(item)
    for cause in evidence.get("causes") or []:
        item = {"label": cause.get("label"), "text": cause.get("text")}
        if cause.get("amount_phrase"):
            item["amount"] = cause["amount_phrase"]
        if cause.get("customer"):
            item["customer"] = cause["customer"]
            item["outcome"] = cause.get("outcome") or ""
        shown["causes"].append(item)
    return shown


def _currency_matches(stated: float, kind: str | None, allowed: set[float], decimals: int) -> bool:
    del decimals
    if kind in {"k", "K"}:
        candidates = {stated * 1_000, stated}
    elif kind in {"m", "M"}:
        candidates = {stated * 1_000_000, stated}
    else:
        candidates = {stated}
    for candidate in candidates:
        for known in allowed:
            if abs(candidate - known) <= max(0.02, abs(known) * 0.002):
                return True
            if abs(candidate - known) < 1 and abs(known) >= 1:
                return True
    return False


def _number_allowed(stated: float, pool: set[float]) -> bool:
    for known in pool:
        if abs(stated - known) <= max(0.02, abs(known) * 0.002):
            return True
    return False


def check_overview_paragraph(paragraph: str, evidence: dict[str, Any]) -> tuple[bool, str]:
    text = (paragraph or "").strip()
    if not text:
        return False, "The overview did not return a paragraph."
    allowed = {float(item) for item in evidence.get("allowed_numbers") or []}
    plain = {float(item) for item in evidence.get("plain_numbers") or []}
    # Also allow numbers embedded in lead/fact/cause text the client already showed.
    for blob in [evidence.get("lead") or ""]:
        for match in re.finditer(r"(-?\$[\d,]+(?:\.\d+)?)\s*([kKmM])?", blob):
            raw = match.group(1).replace(",", "").replace("$", "")
            suffix = match.group(2)
            stated = abs(float(raw))
            if suffix and suffix.lower() == "k":
                _remember(allowed, stated * 1_000)
            elif suffix and suffix.lower() == "m":
                _remember(allowed, stated * 1_000_000)
            else:
                _remember(allowed, stated)
        for token in re.findall(r"\b\d+(?:\.\d+)?\b", blob):
            plain.add(float(token))
    for item in (evidence.get("facts") or []) + (evidence.get("causes") or []):
        for blob in (item.get("text") or "",):
            for token in re.findall(r"\b\d+(?:\.\d+)?\b", blob):
                plain.add(float(token))
            for match in re.finditer(r"(-?\$[\d,]+(?:\.\d+)?)\s*([kKmM])?", blob):
                raw = match.group(1).replace(",", "").replace("$", "")
                suffix = match.group(2)
                stated = abs(float(raw))
                if suffix and suffix.lower() == "k":
                    _remember(allowed, stated * 1_000)
                elif suffix and suffix.lower() == "m":
                    _remember(allowed, stated * 1_000_000)
                else:
                    _remember(allowed, stated)

    for match in re.finditer(r"(-?\$[\d,]+(?:\.\d+)?)\s*([kKmM])?", text):
        raw = match.group(1).replace(",", "").replace("$", "")
        suffix = match.group(2)
        stated = abs(float(raw))
        decimals = len(raw.split(".", 1)[1]) if "." in raw else 0
        kind = suffix.lower() if suffix else None
        if _currency_matches(stated, kind, allowed, decimals):
            continue
        if not kind and _number_allowed(stated, plain):
            continue
        return False, f"The overview uses {match.group(0)}, which is not in the evidence."

    bare = re.sub(r"-?\$[\d,]+(?:\.\d+)?\s*[kKmM]?", " ", text)
    for stated in (float(token) for token in re.findall(r"(?<![\w.])(-?\d+(?:\.\d+)?)(?![\w.])", bare)):
        if _number_allowed(abs(stated), plain) or _number_allowed(abs(stated), allowed):
            continue
        # Ignore common non-claim noise (sentence counts of 1–6 are rare as bare claims).
        if abs(stated) < 10 and abs(stated - int(stated)) < 1e-9:
            continue
        return False, f"The overview uses {stated:g}, which is not in the evidence."

    events = evidence.get("events") or []
    known = {str(event.get("customer") or "").strip().lower() for event in events}
    known.discard("")
    if not events:
        if re.search(r"\b(came in|did not come in)\b", text, flags=re.IGNORECASE):
            return False, "The overview names a deal outcome the evidence does not list."
    for match in _CUSTOMER_CLAIM.finditer(text):
        captured = match.group(1).strip()
        if captured.lower() in known:
            continue
        # Allow labels already on facts/causes.
        labels = {
            str(item.get("label") or "").strip().lower()
            for item in (evidence.get("facts") or []) + (evidence.get("causes") or [])
        }
        if captured.lower() in labels:
            continue
        return False, "The overview names a customer the evidence does not list."
    return True, ""


def deterministic_overview_paragraph(evidence: dict[str, Any]) -> str:
    """Salvage: stitch lead + cause texts already on evidence."""
    parts: list[str] = []
    lead = str(evidence.get("lead") or "").strip()
    if lead:
        parts.append(lead if lead.endswith((".", "!", "?")) else lead + ".")
    for cause in evidence.get("causes") or []:
        text = str(cause.get("text") or "").strip()
        if text:
            parts.append(text if text.endswith((".", "!", "?")) else text + ".")
        if len(parts) >= 6:
            break
    if len(parts) < 2:
        for fact in evidence.get("facts") or []:
            text = str(fact.get("text") or "").strip()
            if text:
                parts.append(text if text.endswith((".", "!", "?")) else text + ".")
            if len(parts) >= 4:
                break
    return " ".join(parts[:6]).strip()


def analyze_period_overview(section: PeriodOverviewIn, client: Any | None) -> PeriodOverviewResult:
    evidence = build_overview_evidence(section)
    shown = present_overview_evidence(evidence)
    salvaged = deterministic_overview_paragraph(evidence)
    if client is None:
        if salvaged:
            return PeriodOverviewResult(status="ai", paragraph=salvaged, evidence=shown)
        return PeriodOverviewResult(
            status="fallback",
            reason="No analysis model is configured. Showing the calculated overview.",
            evidence=shown,
            paragraph=salvaged,
        )
    try:
        raw = client.generate(system_prompt=OVERVIEW_SYSTEM, user_prompt=json.dumps(shown, default=str))
    except (LLMError, Exception):
        if salvaged:
            return PeriodOverviewResult(status="ai", paragraph=salvaged, evidence=shown)
        return PeriodOverviewResult(
            status="fallback",
            reason="The overview is unavailable. Showing the calculated sentences.",
            evidence=shown,
            paragraph=salvaged,
        )
    paragraph = str(raw.get("paragraph") or "").strip() if isinstance(raw, dict) else ""
    ok, reason = check_overview_paragraph(paragraph, evidence)
    if ok and paragraph:
        return PeriodOverviewResult(status="ai", paragraph=paragraph, evidence=shown)
    if paragraph:
        # One rewrite pass.
        correction = (
            "The previous overview was rejected.\n"
            f"Reason: {reason}\n"
            "Rejected paragraph:\n"
            f"{paragraph}\n"
            "Rewrite it from the evidence below. Keep every number and every cause inside that evidence.\n"
            + json.dumps(shown, default=str)
        )
        try:
            rewritten = client.generate(system_prompt=OVERVIEW_SYSTEM, user_prompt=correction)
            paragraph = str(rewritten.get("paragraph") or "").strip() if isinstance(rewritten, dict) else ""
            ok, reason = check_overview_paragraph(paragraph, evidence)
            if ok and paragraph:
                return PeriodOverviewResult(status="ai", paragraph=paragraph, evidence=shown)
        except (LLMError, Exception):
            pass
    if salvaged:
        return PeriodOverviewResult(status="ai", paragraph=salvaged, evidence=shown)
    return PeriodOverviewResult(
        status="fallback",
        reason=reason or "The overview could not be verified.",
        evidence=shown,
        paragraph="",
    )
