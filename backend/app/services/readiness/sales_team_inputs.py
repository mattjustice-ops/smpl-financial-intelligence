"""Sales team the Budget Engine opens from: the Forecast HRIS at the fiscal-year end, read from loaded data only.

- Team: Sales and Customer Success employees on staff at ``fy_end`` in ``forecast_employees`` (hired in or
  before that month and not terminated by it), with territory (HRIS region), role, annual quota, ramp
  months, hire month, base salary and commission target, and heads by department, role and territory.
- Quota type of each role from the loaded quota files (``actual_sales_quotas``, ``budget_sales_quotas``).
- Ramp: curves by ramp length from ``workforce_hiring_ramp_assumptions`` (department and role ``*``,
  level = ramp months, month_offset = month after start − 1, as ``Hiring_Ramp_Assumptions.csv`` loads),
  Budget rows if loaded, else Forecast. Each curve is checked against the ramp the Actual quota file applied.
- Attainment: expected from onboarding 7.25; measured (closers' attainment of ramped quota) from the sales
  plan checks.

Nothing is filled in: a missing table, field or curve is reported in ``missing``.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.services.readiness.commission_plan_inputs import _flag, _months, _num, _rows

TEAM_DEPARTMENTS = ("Sales", "Customer Success")
RAMP_VERSIONS = ("Budget", "Forecast")
NON_QUOTA = "non-quota"
RAMP_TOLERANCE = Decimal("0.0001")


def _tenure(hire: str, period: str) -> int:
    """Month of tenure ``period`` falls in; the hire month is month 1."""
    return (int(period[:4]) - int(hire[:4])) * 12 + int(period[5:7]) - int(hire[5:7]) + 1


def ramp_pct(curve: list[float], tenure: int) -> float:
    """Share of full quota in a month of tenure; past the end of the curve the rep is fully ramped."""
    if tenure < 1:
        return 0.0
    return curve[tenure - 1] if tenure <= len(curve) else 1.0


def _ramp_curves(rows: list[dict[str, Any]], missing: list[str]) -> tuple[str | None, dict[int, list[float]]]:
    by_version: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_version[str(r.get("version") or "")].append(r)
    version = next((v for v in RAMP_VERSIONS if by_version.get(v)), None)
    if version is None:
        missing.append("workforce_hiring_ramp_assumptions has no Budget or Forecast rows: new-hire ramp can't be planned")
        return None, {}
    points: dict[int, dict[int, Decimal]] = defaultdict(dict)
    ignored: set[str] = set()
    for r in by_version[version]:
        n, offset, pct = _months(r.get("level")), _months(r.get("month_offset")), _num(r.get("productivity_pct"))
        if str(r.get("department")) != "*" or str(r.get("role")) != "*" or n is None or offset is None or pct is None:
            ignored.add(f"{r.get('department')} / {r.get('role')} / {r.get('level')}")
            continue
        points[n][offset + 1] = pct
    if ignored:
        missing.append(f"workforce_hiring_ramp_assumptions ({version}) has curves not keyed by ramp length, not used: "
                       + "; ".join(sorted(ignored)))
    curves: dict[int, list[float]] = {}
    for n, by_month in sorted(points.items()):
        if sorted(by_month) != list(range(1, len(by_month) + 1)):
            missing.append(f"workforce_hiring_ramp_assumptions ({version}): the {n}-month ramp curve skips a month")
            continue
        if by_month[len(by_month)] != 1:
            missing.append(f"workforce_hiring_ramp_assumptions ({version}): the {n}-month ramp curve ends below 100%")
            continue
        curves[n] = [float(by_month[m]) for m in sorted(by_month)]
    return version, curves


def _quota_types(db: Session, org_id: uuid.UUID, missing: list[str]) -> dict[str, str]:
    seen: dict[str, set[str]] = defaultdict(set)
    loaded = False
    for table in ("actual_sales_quotas", "budget_sales_quotas"):
        rows = _rows(db, table, org_id)
        loaded = loaded or bool(rows)
        for r in rows or []:
            if r.get("role") and r.get("quota_type"):
                seen[str(r["role"])].add(str(r["quota_type"]))
    if not loaded:
        missing.append("actual_sales_quotas and budget_sales_quotas are not loaded: quota type by role is unknown")
    for role, kinds in sorted(seen.items()):
        if len(kinds) > 1:
            missing.append(f"Quota files give {role} more than one quota type ({', '.join(sorted(kinds))})")
    return {role: next(iter(kinds)) for role, kinds in seen.items() if len(kinds) == 1}


def _ramp_check(db: Session, org_id: uuid.UUID, curves: dict[int, list[float]], version: str | None) -> dict[str, Any] | None:
    """Does the loaded ramp table reproduce the ramp the Actual quota file applied?"""
    tested = off = 0
    no_curve: set[int] = set()
    example = None
    for r in _rows(db, "actual_sales_quotas", org_id) or []:
        if str(r.get("quota_type") or "").strip().lower() in ("", NON_QUOTA):
            continue
        n, applied, hire = _months(r.get("productivity_ramp_months")), _num(r.get("ramp_pct")), str(r.get("hire_period") or "")[:7]
        if n is None or applied is None or len(hire) != 7 or not r.get("period"):
            continue
        if n not in curves:
            no_curve.add(n)
            continue
        tested += 1
        expected = Decimal(str(ramp_pct(curves[n], _tenure(hire, str(r["period"])[:7]))))
        if abs(expected - applied) > RAMP_TOLERANCE:
            off += 1
            example = example or (f"{r.get('rep_name') or r.get('employee_id')} {r['period']} ({n}-month ramp, "
                                  f"month {_tenure(hire, str(r['period'])[:7])}): quota file {applied:.0%}, curve {expected:.0%}")
    if not tested and not no_curve:
        return None
    lengths = ", ".join(str(n) for n in sorted(no_curve))
    finding = (f"{tested - off} of {tested} Actual quota rows apply the {version} ramp curve"
               + (f"; e.g. {example}" if example else "")
               + (f"; no curve for {lengths}-month ramps" if no_curve else ""))
    return {"id": "ramp_vs_quotas", "status": "pass" if tested and not off and not no_curve else "conflict",
            "finding": finding}


def sales_team(db: Session, org_id: uuid.UUID, answers: dict[str, str], fy_end: str,
               measured: dict[str, Any] | None = None) -> dict[str, Any]:
    missing: list[str] = []
    checks: list[dict[str, Any]] = []

    employees = _rows(db, "forecast_employees", org_id)
    if not employees:
        missing.append("forecast_employees is not loaded: the sales team at the forecast year end is unknown")
    quota_types = _quota_types(db, org_id, missing)
    ramp_rows = _rows(db, "workforce_hiring_ramp_assumptions", org_id)
    if not ramp_rows:
        missing.append("workforce_hiring_ramp_assumptions is not loaded: new-hire ramp can't be planned")
        version, curves = None, {}
    else:
        version, curves = _ramp_curves(ramp_rows, missing)

    team: list[dict[str, Any]] = []
    gaps: dict[str, list[str]] = defaultdict(list)
    for e in employees or []:
        if str(e.get("department")) not in TEAM_DEPARTMENTS:
            continue
        hire, term = str(e.get("hire_date") or "")[:7], str(e.get("termination_date") or "")[:7]
        if len(hire) != 7:
            gaps["no hire date"].append(str(e.get("employee_id")))
            continue
        if hire > fy_end or (term and term <= fy_end):
            continue
        role, carrying = str(e.get("role") or ""), _flag(e.get("quota_carrying"))
        quota, ramp_months = _num(e.get("annual_quota_arr")), _months(e.get("productivity_ramp_months"))
        target, base = _num(e.get("commission_target")), _num(e.get("base_salary"))
        row = {
            "employee_id": e.get("employee_id"),
            "employee_name": e.get("employee_name"),
            "department": e.get("department"),
            "sub_department": e.get("sub_department"),
            "role": role,
            "level": e.get("level"),
            "territory": e.get("region"),
            "hire_period": hire,
            "tenure_months": _tenure(hire, fy_end),
            "quota_carrying": carrying,
            "quota_type": quota_types.get(role),
            "annual_quota_arr": float(quota) if quota is not None else None,
            "ramp_months": ramp_months,
            "base_salary": float(base) if base is not None else None,
            "commission_target": float(target) if target is not None else None,
        }
        team.append(row)
        who = f"{e.get('employee_id')} ({role})"
        if base is None:
            gaps["no base salary"].append(who)
        if not carrying:
            continue
        if role not in quota_types:
            gaps["quota-carrying role not in the quota files"].append(who)
        if not quota:
            gaps["no annual quota"].append(who)
        if target is None:
            gaps["no commission target"].append(who)
        if ramp_months is None:
            gaps["no ramp months"].append(who)
        elif ramp_rows and ramp_months not in curves:
            gaps[f"no {ramp_months}-month ramp curve"].append(who)
    if employees and not team:
        missing.append(f"forecast_employees has no Sales or Customer Success employees on staff at {fy_end}")
    for gap, who in sorted(gaps.items()):
        missing.append(f"forecast_employees at {fy_end}: {gap}: " + ", ".join(who[:5]) + (f" and {len(who) - 5} more" if len(who) > 5 else ""))

    heads: dict[tuple[str, str, str], dict[str, Any]] = {}
    for r in team:
        key = (str(r["department"]), r["role"], str(r["territory"]))
        h = heads.setdefault(key, {"department": key[0], "role": key[1], "territory": key[2], "quota_type": r["quota_type"],
                                   "heads": 0, "ramping": 0, "annual_quota_arr": 0.0})
        h["heads"] += 1
        h["annual_quota_arr"] += r["annual_quota_arr"] or 0.0
        if r["quota_carrying"] and r["ramp_months"] in curves and ramp_pct(curves[r["ramp_months"]], r["tenure_months"]) < 1:
            h["ramping"] += 1

    if curves:
        check = _ramp_check(db, org_id, curves, version)
        if check:
            checks.append(check)

    expected = answers.get("7.25")
    if not expected:
        missing.append("Expected quota attainment (7.25) is not answered: closer hiring can't be sized")
    measured = measured or {}

    return {
        "as_of": fy_end,
        "source": "forecast_employees",
        "employees": team,
        "heads": [heads[k] for k in sorted(heads)],
        "quota_types": dict(sorted(quota_types.items())),
        "ramp": {"version": version, "curves": {str(n): c for n, c in curves.items()}},
        "attainment": {
            "expected": int(expected) / 100 if expected else None,
            "measured": measured.get("closer_attainment"),
            "measured_months": measured.get("months"),
        },
        "checks": checks,
        "missing": missing,
    }
