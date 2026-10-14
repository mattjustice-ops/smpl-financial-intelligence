"""The sales and customer success team: one population, the employee files (HRIS).

Every file that names a rep or a CSM uses the employee's ID and name: quotas, sales_reps, opportunity and
movement owners, commission payouts, renewal pipelines and renewal commissions.

  * Sales and customer success employees work a CRM territory (the opportunity regions Central, East, South,
    West). HRIS region EMEA becomes South; Remote takes the territory with the most Actual opportunities per
    head in the employee's role group (AEs and Senior AEs together, CSMs and Senior CSMs together). Plan-only
    hires get theirs the same way, on top of the Actual team.
  * Employees carry names (the HRIS export had placeholders), the same name for an ID in every version.
  * New business goes to a closing team by deal size: Enterprise Sales closes deals at or above a floor measured so
    that the year's new business splits between the teams as their ramped quota does (enterprise_floor);
    Mid-Market Sales closes the rest.
  * A customer's CSM is an active CSM in the customer's territory, picked when the customer first comes up for
    renewal (the CSM with the fewest accounts) or first expands (the CSM left lowest against year-to-date
    expansion quota); the customer keeps that CSM.
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from decimal import Decimal

VERSIONS = ("Actual", "Budget", "Forecast")
TEAM_DEPARTMENTS = ("Sales", "Customer Success")
TERRITORIES = ("Central", "East", "South", "West")
REGION_TO_TERRITORY = {"EMEA": "South"}
BOOKINGS_ROLES = frozenset({"Account Executive", "Senior Account Executive"})
PIPELINE_ROLES = frozenset({"Sales Development Rep"})
CSM_ROLES = frozenset({"Customer Success Manager", "Senior Customer Success Manager"})
REP_SEGMENT = {"Enterprise Sales": "Enterprise", "Mid-Market Sales": "Mid-Market"}
# Largest deals first; there is no SMB team.
CLOSING_TEAMS = ("Enterprise Sales", "Mid-Market Sales")
FIRST_NAMES = ("Alex", "Avery", "Blake", "Cameron", "Casey", "Charlie", "Dakota", "Drew", "Elliot", "Emerson",
               "Finley", "Harper", "Hayden", "Jamie", "Jordan", "Kendall", "Logan", "Morgan", "Parker", "Quinn",
               "Reese", "Riley", "Rowan", "Sage", "Skyler", "Taylor")
LAST_NAMES = ("Adams", "Bennett", "Brooks", "Carter", "Clark", "Davis", "Ellis", "Foster", "Garcia", "Hayes",
              "Hughes", "Johnson", "Kim", "Lee", "Martinez", "Miller", "Nguyen", "Patel", "Price", "Reed",
              "Rivera", "Shaw", "Turner", "Walker", "Wilson", "Young")


def _unit(key: str) -> float:
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) / 0x100000000


def role_group(role: str) -> str:
    """Roles that cover the same accounts: closers together, CSMs together."""
    if role in BOOKINGS_ROLES:
        return "closers"
    return "csms" if role in CSM_ROLES else role


def quota_type(role: str) -> str:
    """Closers on new business booked, SDRs on outbound pipeline created, CSMs on expansion closed in their accounts."""
    if role in BOOKINGS_ROLES:
        return "Bookings ARR"
    if role in CSM_ROLES:
        return "Expansion ARR"
    return "Pipeline ARR" if role in PIPELINE_ROLES else "Non-Quota"


def enterprise_floor(won: list[Decimal], capacity: dict[str, Decimal]) -> Decimal:
    """Smallest new-business ARR Enterprise Sales closes. Each closing team sells the deals that make up its share of
    the closing teams' ramped quota, so the year's new business, largest deal first, is Enterprise Sales' until it
    reaches that share. ``won``: the year's new-business deal sizes; ``capacity``: ramped quota by team that year."""
    missing = [t for t in CLOSING_TEAMS if not capacity.get(t)]
    if missing or not won:
        raise ValueError(f"cannot split new business between the closing teams: no ramped quota for {missing} "
                         f"or no deals ({len(won)})")
    target = sum(won, Decimal(0)) * capacity[CLOSING_TEAMS[0]] / sum(capacity[t] for t in CLOSING_TEAMS)
    booked = Decimal(0)
    for a in sorted(won, reverse=True):
        booked += a
        if booked >= target:
            break
    return a


def closing_team(arr: Decimal, floor: Decimal) -> str:
    return CLOSING_TEAMS[0] if arr >= floor else CLOSING_TEAMS[1]


def active(e: dict[str, str], p: str) -> bool:
    """Employed in month ``p`` (YYYY-MM): hired on or before it, not terminated before or in it."""
    return e["hire_date"][:7] <= p and (not e["termination_date"] or e["termination_date"][:7] > p)


def employee_names(ids: set[str]) -> dict[str, str]:
    n = len(FIRST_NAMES) * len(LAST_NAMES)
    if len(ids) > n:
        raise ValueError(f"{len(ids)} employees, only {n} names")
    out, used = {}, set()
    for i in sorted(ids):
        k = int(_unit(f"name|{i}") * n)
        while f"{FIRST_NAMES[k % len(FIRST_NAMES)]} {LAST_NAMES[k // len(FIRST_NAMES)]}" in used:
            k = (k + 1) % n
        out[i] = f"{FIRST_NAMES[k % len(FIRST_NAMES)]} {LAST_NAMES[k // len(FIRST_NAMES)]}"
        used.add(out[i])
    return out


def territories(emps: dict[str, list[dict[str, str]]], demand: dict[str, int]) -> dict[str, str]:
    """Employee ID -> territory for Sales and Customer Success employees, Actual first, then plan-only hires."""
    missing = [t for t in TERRITORIES if not demand.get(t)]
    if missing:
        raise ValueError(f"no Actual opportunities in territories {missing}")
    out: dict[str, str] = {}
    for v in VERSIONS:
        team = [e for e in emps[v] if e["department"] in TEAM_DEPARTMENTS]
        for e in team:
            t = REGION_TO_TERRITORY.get(e["region"], e["region"])
            if e["employee_id"] not in out and t in TERRITORIES:
                out[e["employee_id"]] = t
        heads = Counter((role_group(e["role"]), out[e["employee_id"]]) for e in team if e["employee_id"] in out)
        for e in sorted((e for e in team if e["employee_id"] not in out), key=lambda e: e["employee_id"]):
            g = role_group(e["role"])
            t = max(TERRITORIES, key=lambda t: (demand[t] / (heads[(g, t)] + 1), -TERRITORIES.index(t)))
            out[e["employee_id"]] = t
            heads[(g, t)] += 1
    return out


def team_employees(emps: dict[str, list[dict[str, str]]], demand: dict[str, int]) -> dict[str, list[dict[str, str]]]:
    """The employee files with names and, for Sales and Customer Success, CRM territories."""
    shared: dict[str, dict[str, str]] = {}
    for v in VERSIONS:
        for e in emps[v]:
            prev = shared.setdefault(e["employee_id"], e)
            diff = [k for k in ("department", "role", "region", "hire_date") if prev[k] != e[k]]
            if diff:
                raise ValueError(f"{e['employee_id']} differs across versions in {diff}")
    names = employee_names(set(shared))
    terr = territories(emps, demand)
    out = {}
    for v in VERSIONS:
        rows = []
        for e in emps[v]:
            ne = dict(e)
            ne["employee_name"] = names[e["employee_id"]]
            t = terr.get(e["employee_id"])
            if t and t != e["region"]:
                ne["region"] = t
                ne["source"] = f"{e['source']}; territory {t} (HRIS region {e['region']})"
            rows.append(ne)
        out[v] = rows
    return out


def ytd_quota(e: dict[str, str], p: str) -> Decimal:
    """Annual quota pro rata for the months of ``p``'s year through ``p`` the employee is on staff."""
    months = sum(1 for m in range(1, int(p[5:7]) + 1) if active(e, f"{p[:4]}-{m:02d}"))
    return Decimal(e["annual_quota_arr"]) * months / 12


def assign_csms(due: list[dict], team: list[dict[str, str]], territory_of, assigned: dict[str, str]) -> dict[str, str]:
    """Customer -> CSM employee ID for accounts ``due`` (customer_id, period YYYY-MM, expansion_arr on an expansion);
    ``assigned`` carries earlier picks. A customer first seen at a renewal goes to the in-territory CSM with the
    fewest accounts; one first seen expanding goes to the in-territory CSM left lowest against year-to-date quota
    once the expansion is counted."""
    load = Counter(assigned.values())
    credited: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for r in sorted(due, key=lambda r: (r["period"], r["customer_id"])):
        c, p, a = r["customer_id"], r["period"], r.get("expansion_arr")
        if c not in assigned:
            csms = [e for e in team if e["role"] in CSM_ROLES and active(e, p)]
            if not csms:
                raise ValueError(f"no active CSM in {p}")
            pool = [e for e in csms if e["region"] == territory_of(c)] or csms
            if a is None:
                pick = min(pool, key=lambda e: (load[e["employee_id"]], e["employee_id"]))
            else:
                pick = min(pool, key=lambda e: ((credited[(p[:4], e["employee_id"])] + a) / ytd_quota(e, p),
                                                load[e["employee_id"]], e["employee_id"]))
            assigned[c] = pick["employee_id"]
            load[pick["employee_id"]] += 1
        if a is not None:
            credited[(p[:4], assigned[c])] += a
    return assigned
