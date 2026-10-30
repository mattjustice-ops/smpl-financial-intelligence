"""Reference implementation: net_new_arr_bridge, version 1.

The function emits evidence (facts, a net-change frame and a relationship). It never writes a sentence.
render_fallback() shows the sentence the fallback pattern builds from that evidence, for review and tests only.

Amounts are in dollars, as exact source values. Thresholds follow the spec:
  materiality and the flat band: $10K; "largely" test: the parent's move is at most 25% of the offsetting side.
"""

MATERIAL = 10_000
LARGELY_SHARE = 0.25
TIE_TOLERANCE = 1.0
FOLD = 1_000

ADDS = ["new_business", "reactivation", "expansion"]
LOSSES = ["churn", "contraction"]
LABELS = {
    "new_business": "new business",
    "reactivation": "reactivation",
    "expansion": "expansion",
    "contraction": "contraction",
    "churn": "churn",
}


def money(x):
    """Two decimals. Lowercase k under $1M, uppercase M from $1M."""
    amount = abs(x)
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:,.2f}M"
    if amount >= 1000:
        return f"${amount / 1000:,.2f}k"
    return f"${amount:,.2f}"


def signed_money(x):
    if x < 0:
        return "negative " + money(x)
    return money(x)


def join_labels(names):
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def net_new_arr_bridge(inp):
    """Losses are positive amounts. Reactivation may be missing; it then counts as zero."""
    out = {
        "function": "net_new_arr_bridge",
        "version": 2,
        "comparison": inp["comparison"],
        "checks": [],
        "status": "pass",
    }
    cur, pri = inp.get("current"), inp.get("prior")
    need = ["new_business", "expansion", "contraction", "churn"]
    missing = [
        f"{p}.{k}"
        for p, d in (("current", cur), ("prior", pri))
        for k in need
        if d is None or d.get(k) is None
    ]
    if missing or inp.get("ending_arr") is None or inp.get("opening_arr_prior") is None:
        out.update(status="fail", reason="missing inputs: " + ", ".join(missing or ["ARR balances"]))
        return out

    def total(d, keys):
        return sum(d.get(k) or 0 for k in keys)

    A, Ap = total(cur, ADDS), total(pri, ADDS)
    L, Lp = total(cur, LOSSES), total(pri, LOSSES)
    N, Np = A - L, Ap - Lp
    end = inp["ending_arr"]["current"]
    end_p = inp["ending_arr"]["prior"]
    open_p = inp["opening_arr_prior"]
    # Adjacent windows share one balance: the prior ending is this period's opening.
    # A year-ago window does not, so its own ending is passed separately.
    prior_end = end_p if inp.get("prior_ending") is None else inp["prior_ending"]

    for name, got, want in (
        ("waterfall foots to ARR, current", N, end - end_p),
        ("waterfall foots to ARR, prior", Np, prior_end - open_p),
    ):
        ok = abs(got - want) <= TIE_TOLERANCE
        out["checks"].append({"check": name, "net_new_arr": got, "arr_change": want, "ok": ok})
        if not ok:
            out.update(status="fail", reason=f"{name}: net new ARR {got:,.2f} against ARR change {want:,.2f}")
            return out

    def members(keys):
        return [k for k in keys if max(abs(cur.get(k) or 0), abs(pri.get(k) or 0)) >= FOLD]

    def group(key, keys, level, prior):
        m = members(keys)
        return {
            "group": key,
            "members": m,
            "label": join_labels([LABELS[k] for k in m]) if m else None,
            "plural": len(m) > 1,
            "current": level,
            "prior": prior,
            "change": level - prior,
            "member_changes": {k: (cur.get(k) or 0) - (pri.get(k) or 0) for k in m},
        }

    gA = group("gross_additions", ADDS, A, Ap)
    gL = group("gross_losses", LOSSES, L, Lp)
    D = N - Np
    out["facts"] = {
        "net_new_arr": {"current": N, "prior": Np, "change": D},
        "ending_arr": {"current": end, "prior": end_p},
        "gross_additions": gA,
        "gross_losses": gL,
    }
    out["net_change_frame"] = net_change_frame(N, Np)
    out["relationship"] = relationship(gA, gL, D)
    out["display"] = {
        "net_new_arr": money(N),
        "net_new_arr_prior": money(Np),
        "ending_arr": money(end),
        "gross_additions": money(A),
        "gross_additions_prior": money(Ap),
        "gross_losses": money(L),
        "gross_losses_prior": money(Lp),
        "net_new_arr_change": signed_money(D),
    }
    return out


def net_change_frame(N, Np):
    """Compare this period's Net ARR with the prior period's Net ARR. Ending ARR stays out of it."""
    change = N - Np
    if abs(Np) < FOLD and abs(change) >= MATERIAL:
        key, words = "after_flat", "after little change in {prior}"
    elif abs(change) < MATERIAL and N >= 0 and Np >= 0:
        key, words = "in_line", "in line with {prior}'s {prior_amount}"
    elif N >= 0 and Np >= 0 and change > 0:
        key, words = "improvement", "a {change} improvement over {prior}'s {prior_amount}"
    else:
        key, words = "decline", "down {change} from {prior}'s {prior_amount}"
    return {"key": key, "words": words, "prior_amount": Np, "change": change}


def relationship(gA, gL, D):
    eA, eL = gA["change"], -gL["change"]
    mA, mL = abs(eA) >= MATERIAL, abs(eL) >= MATERIAL

    def move(g):
        return "decline" if g["change"] < 0 else "increase"

    if not mA and not mL:
        return {"kind": "none", "reason": "neither group moved $10K or more"}
    if mA != mL:
        big, flat = (gA, gL) if mA else (gL, gA)
        return {
            "kind": "single_cause",
            "order": [big["group"], flat["group"]],
            "connector": "while",
            "flat_group": flat["group"] if flat["label"] else None,
            "words": ["while", "was little changed at" if not flat["plural"] else "were little changed at"],
        }
    if (eA > 0) == (eL > 0):
        return {
            "kind": "driven_by",
            "subtype": "both",
            "order": ["gross_additions", "gross_losses"],
            "connector": "and",
            "words": ["and"],
        }
    fav, unf = (gA, gL) if eA > 0 else (gL, gA)
    if D > 0:
        if D <= LARGELY_SHARE * abs(min(eA, eL)):
            sub, order = "largely", [fav, unf]
        else:
            sub, order = "more_than", [unf, fav]
    elif D < 0:
        sub = "largely" if -D <= LARGELY_SHARE * max(eA, eL) else "partly"
        order = [unf, fav]
    else:
        sub, order = "largely", [gA, gL]
    connector = "but" if sub == "more_than" else "and"
    frame = {"more_than": "more than offsetting", "partly": "partly offsetting", "largely": "largely offsetting"}[sub]
    return {
        "kind": "offset",
        "subtype": sub,
        "order": [g["group"] for g in order],
        "connector": connector,
        "words": [connector, f"{frame} the {move(order[0])}"],
        "offset_side": order[1]["group"],
        "offset_amount": abs(order[1]["change"]),
        "parent_change": D,
    }


def clause(g, prior_name, flat=False):
    lab = g["label"]
    if flat:
        return f"{lab} {'were' if g['plural'] else 'was'} little changed at {money(g['current'])}"
    if g["group"] == "gross_additions":
        direction = "down" if g["change"] < 0 else "up"
        return f"{lab} added {money(g['current'])}, {direction} from {money(g['prior'])} in {prior_name}"
    verb = "fell" if g["change"] < 0 else "rose"
    return f"{lab} {verb} to {money(g['current'])} from {money(g['prior'])}"


def cap(s):
    return s[0].upper() + s[1:]


def render_fallback(ev):
    if ev["status"] != "pass":
        return None
    facts, comparison = ev["facts"], ev["comparison"]
    frame = ev["net_change_frame"]
    net_new = facts["net_new_arr"]["current"]
    end = facts["ending_arr"]["current"]
    lead = f"Net ARR in {comparison['current']} was {signed_money(net_new)}"
    if frame["words"]:
        lead += ", " + frame["words"].format(
            prior=comparison["prior"],
            prior_amount=signed_money(frame["prior_amount"]),
            change=money(abs(frame["change"])),
        )
    lead += f", and ARR finished the month at {money(end)}."
    rel = ev["relationship"]
    groups = {"gross_additions": facts["gross_additions"], "gross_losses": facts["gross_losses"]}
    prior_name = comparison["prior"]
    if rel["kind"] == "none":
        return lead
    if rel["kind"] == "single_cause":
        sentence = clause(groups[rel["order"][0]], prior_name)
        if rel["flat_group"]:
            sentence += ", while " + clause(groups[rel["order"][1]], prior_name, flat=True)
    elif rel["kind"] == "driven_by":
        sentence = clause(groups[rel["order"][0]], prior_name) + ", and " + clause(groups[rel["order"][1]], prior_name)
    else:
        sentence = f"{clause(groups[rel['order'][0]], prior_name)}, {rel['connector']} {clause(groups[rel['order'][1]], prior_name)}, {rel['words'][1]}"
    return lead + " " + cap(sentence) + "."
