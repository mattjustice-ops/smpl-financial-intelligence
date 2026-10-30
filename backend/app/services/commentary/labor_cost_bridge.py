"""Mapping function: labor_cost_bridge.

Reads the company labor bridge for the page's two periods and emits the fields
the Workforce section is allowed to print. It never sums department bars.

Amounts arrive in USD thousands, the bridge's unit, and are converted once
to dollars at display. A bar driven by fewer than 3 people prints by category.
"""

from decimal import Decimal, ROUND_HALF_UP

MATERIAL = 10_000
FOLD_SHARE = 0.10
PRIVACY_FLOOR = 3
TIE_TOLERANCE = 1.0

BAR_ORDER = (
    "hires",
    "departures",
    "mix",
    "rate",
    "timing",
    "benefits",
    "variable",
    "capitalized",
    "one_time",
    "reconciling",
)

CATEGORY = {
    "hires": "hires",
    "departures": "departures",
    "mix": "a shift toward higher-cost groups",
    "rate": "pay adjustments",
    "timing": "partial-month pay for mid-month departures",
    "benefits": "benefits and payroll taxes",
    "variable": "variable comp",
    "capitalized": "capitalized labor",
    "one_time": "one-time pay",
    "reconciling": "GL vs payroll reconciling",
}

VOLUME = ("hires", "departures")


def money(value):
    """Page display: $52.70k, $1.04M, rounded once from the exact dollar value."""
    amount = float(value)
    absolute = abs(amount)
    if absolute >= 1_000_000:
        body = f"${absolute / 1_000_000:.2f}M"
    elif absolute >= 1000:
        body = f"${absolute / 1000:.2f}k"
    else:
        body = f"${absolute:.2f}"
    return ("−" if amount < 0 else "") + body


def _dollars(thousands):
    return float((Decimal(str(thousands)) * Decimal(1000)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _cap(text):
    return text[:1].upper() + text[1:] if text else text


def labor_cost_bridge(inp):
    """Emit Workforce fields. Bridge facts ship only when every gate passes."""
    out = {
        "function": "labor_cost_bridge",
        "ships": False,
        "status": "withheld",
        "checks": [],
        "printed_bars": [],
        "folded": [],
    }
    heads = inp.get("heads") or {}
    labor = inp.get("labor_thousands") or {}
    bars = inp.get("bars_thousands") or None
    missing = []
    if inp.get("status") not in ("FINAL", "PROVISIONAL"):
        missing.append("status")
    if inp.get("page_headcount") is None:
        missing.append("page_headcount")
    for key in ("opening", "hires", "departures", "ending"):
        if heads.get(key) is None:
            missing.append(f"heads.{key}")
    for key in ("prior", "current"):
        if labor.get(key) is None:
            missing.append(f"labor_thousands.{key}")
    if not isinstance(bars, dict):
        missing.append("bars_thousands")
    if missing:
        out["reason"] = "missing inputs: " + ", ".join(missing)
        return out

    opening = int(heads["opening"])
    hires = int(heads["hires"])
    departures = int(heads["departures"])
    ending = int(heads["ending"])
    rolls = opening + hires - departures == ending
    out["checks"].append({
        "check": "heads roll forward",
        "opening": opening,
        "hires": hires,
        "departures": departures,
        "ending": ending,
        "ok": rolls,
    })

    company = {key: _dollars(bars.get(key) or 0) for key in BAR_ORDER}
    # Department rows are a different bridge. They are never added to company bars.
    out["checks"].append({"check": "department bars are not summed", "ok": True})
    change = _dollars(labor["current"]) - _dollars(labor["prior"])
    footed = abs(sum(company.values()) - change) <= TIE_TOLERANCE
    out["checks"].append({
        "check": "bars foot to the labor change",
        "bars": sum(company.values()),
        "change": change,
        "ok": footed,
    })

    final = inp["status"] == "FINAL"
    out["checks"].append({"check": "FINAL bridge", "status": inp["status"], "ok": final})
    page_heads = int(inp["page_headcount"])
    heads_match = ending == page_heads
    out["checks"].append({
        "check": "bridge heads equal the page headcount",
        "bridge_heads": ending,
        "page_headcount": page_heads,
        "ok": heads_match,
    })

    if not rolls:
        out["reason"] = f"heads do not roll forward: {opening} + {hires} − {departures} against {ending}"
        return out
    if not footed:
        out["reason"] = "bars do not foot to the labor change"
        return out
    if not final:
        out["reason"] = "bridge is PROVISIONAL"
        return out
    if not heads_match:
        out["reason"] = f"bridge heads {ending} differ from the page headcount {page_heads}"
        return out

    people = inp.get("people") or {}
    phrases = inp.get("phrases") or {}
    volume_dollars = company["hires"] + company["departures"]
    nets = abs(volume_dollars) < MATERIAL
    threshold = FOLD_SHARE * abs(change)
    printed = []
    folded = []
    for key in BAR_ORDER:
        amount = company[key]
        if key in VOLUME and nets:
            continue
        if abs(amount) < 0.5:
            continue
        count = people.get(key)
        private = count is not None and int(count) < PRIVACY_FLOOR
        label = CATEGORY[key] if private or not phrases.get(key) else phrases[key]
        row = {"key": key, "amount": amount, "display": money(amount), "privacy": private, "label": label}
        if abs(amount) >= MATERIAL or abs(amount) >= threshold:
            printed.append(row)
        else:
            folded.append({"key": key, "amount": amount, "display": money(amount)})
    printed.sort(key=lambda row: abs(row["amount"]), reverse=True)
    other = sum(row["amount"] for row in folded)
    out["checks"].append({
        "check": "privacy floor",
        "floor": PRIVACY_FLOOR,
        "private_bars": [row["key"] for row in printed if row["privacy"]],
        "ok": all("people" not in row for row in printed),
    })

    settings = inp.get("settings") or {}
    prior_settings = inp.get("prior_settings") or settings
    compare_mix_rate = (
        settings.get("group_key_version") == prior_settings.get("group_key_version")
        and settings.get("bar_order_version") == prior_settings.get("bar_order_version")
    )
    plan = inp.get("plan_thousands") or {}
    plan_facts = None
    if plan.get("variance") is not None and plan.get("planned_heads") is not None:
        variance = _dollars(plan["variance"])
        plan_facts = {
            "variance": variance,
            "planned_heads": int(plan["planned_heads"]),
            "direction": "under" if variance < 0 else "over" if variance > 0 else "in line",
        }

    out.update(
        ships=True,
        status="pass",
        facts={
            "heads": {"opening": opening, "hires": hires, "departures": departures, "ending": ending},
            "labor_cost": {
                "prior": _dollars(labor["prior"]),
                "current": _dollars(labor["current"]),
                "change": change,
            },
            "plan": plan_facts,
            "compare_mix_rate": compare_mix_rate,
        },
        printed_bars=printed,
        folded=folded,
        other_items={"amount": other, "display": money(other)} if folded else None,
        volume_counts={"hires": hires, "departures": departures, "nets": nets},
        display={
            "labor_change": money(change),
            "labor_current": money(_dollars(labor["current"])),
            "labor_prior": money(_dollars(labor["prior"])),
            "plan_gap": money(plan_facts["variance"]) if plan_facts else None,
        },
    )
    return out


def render_workforce(ev, month, prior):
    """The Workforce labor sentences. Empty unless the bridge ships."""
    if not ev.get("ships"):
        return ""
    heads = ev["facts"]["heads"]
    labor = ev["facts"]["labor_cost"]
    if heads["ending"] == heads["opening"]:
        lead = f"Headcount was flat at {heads['ending']} in {month}"
    elif heads["ending"] > heads["opening"]:
        lead = f"Headcount grew by {heads['ending'] - heads['opening']} from {prior} to {heads['ending']}"
    else:
        lead = f"Headcount was down by {heads['opening'] - heads['ending']} from {prior} to {heads['ending']}"
    counts = ev["volume_counts"]
    if counts["nets"] and counts["hires"] and counts["departures"]:
        if counts["hires"] == counts["departures"]:
            lead += f", with {counts['hires']} hires replacing {counts['departures']} departures"
        else:
            lead += f", with {counts['hires']} hires and {counts['departures']} departures"
    change = labor["change"]
    verb = "increased" if change > 0 else "decreased"
    joiner = ", but " if heads["ending"] == heads["opening"] and change else ", and "
    lead += f"{joiner}labor cost {verb} {money(abs(change))} from {prior} to {money(labor['current'])}."

    bars = list(ev["printed_bars"])
    lead_bars, rest = bars[:2], bars[2:]
    sentences = [lead]
    if lead_bars:
        bits = []
        for index, bar in enumerate(lead_bars):
            if bar["key"] == "mix":
                bit = f"{bar['label']} added {bar['display']} of mix"
            else:
                bit = f"{bar['label']} accounted for {bar['display']}"
            bits.append(_cap(bit) if index == 0 else bit)
        sentences.append(", and ".join(bits) + ".")
    rest_bits = [f"{bar['label']} ({bar['display']})" for bar in rest]
    if ev.get("other_items"):
        rest_bits.append(f"other items ({ev['other_items']['display']})")
    if rest_bits:
        if len(rest_bits) == 1:
            tail = rest_bits[0]
        else:
            tail = ", ".join(rest_bits[:-1]) + " and " + rest_bits[-1]
        sentences.append("The rest came from " + tail + ".")
    plan = ev["facts"].get("plan")
    if plan and plan["direction"] != "in line":
        sentences.append(
            f"Labor came in {money(abs(plan['variance']))} {plan['direction']} plan, "
            f"with {heads['ending']} heads against {plan['planned_heads']} planned."
        )
    return " ".join(sentences)
