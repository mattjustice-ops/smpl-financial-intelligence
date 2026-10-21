"""Dollar labor bridge for compensation commentary.

Hires and departures are priced from the roster's current salary, bonus, and benefits
load. Commissions are excluded. The roster keeps one pay rate, so a month-over-month
mix or raise cannot be separated and stays in the GL reconciling bar. That bar is the
amount that makes the bridge land on GL compensation. Versus budget, two rosters give
two rates, so a rate bar is saved for people who are on both.

The board reads these saved bars. It does not recompute them.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from app.services.reporting.period_utils import period_to_date, prior_period, to_period
from app.services.workforce.gl_payroll import GlPayroll, GlPayrollSet
from app.services.workforce.roster import RosterEmployee, on_roster

CENT = Decimal("0.01")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

COMPENSATION_INCLUDES = (
    "wages, severance, bonus, benefits, payroll taxes, retirement match, and unsplit labor"
)
PRICE_BASIS = (
    "Hires and departures are the current roster salary, bonus, and benefits load divided by 12. "
    "Commissions are excluded. One roster pay rate cannot separate mix or raises, so those stay "
    "in GL reconciling, which is what makes the bars land on GL compensation."
)


def person_month_cost(employee: RosterEmployee) -> Decimal:
    """Monthly compensation used to price a person. Commissions are not included."""
    salary = employee.salary_annual or Decimal(0)
    bonus = employee.bonus_annual or Decimal(0)
    pct = employee.benefits_load_pct or Decimal(0)
    return (salary + bonus) * (Decimal(1) + pct) / Decimal(12)


def compensation_of(payroll: GlPayroll) -> Decimal:
    return payroll.wages + payroll.bonus + payroll.benefits + payroll.labor


def _q(amount: Decimal) -> Decimal:
    return amount.quantize(CENT)


def _money(amount: Decimal) -> float:
    return float(_q(amount))


def _fmt(amount: Decimal) -> str:
    signed = _q(amount)
    sign = "-" if signed < 0 else ""
    return f"{sign}${abs(signed):,.2f}"


def _month_label(period: date) -> str:
    return f"{_MONTHS[period.month - 1]} {period.year}"


def _dept(employee: RosterEmployee) -> str:
    return employee.department.strip() or "Unassigned"


def _people(roster: list[RosterEmployee], period: date) -> dict[str, RosterEmployee]:
    out: dict[str, RosterEmployee] = {}
    for employee in roster:
        if employee.employee_id and on_roster(employee, period):
            out[employee.employee_id] = employee
    return out


def _gl_by_department(payroll: GlPayrollSet, period: date) -> dict[str, Decimal] | None:
    if period not in payroll.periods():
        return None
    out: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    for (when, department), value in payroll.by_department.items():
        if when == period:
            out[department.strip() or "Unassigned"] += compensation_of(value)
    return dict(out)


def _bar(key: str, label: str, amount: Decimal, heads: int | None) -> dict[str, Any]:
    row: dict[str, Any] = {"key": key, "label": label, "amount": _money(amount)}
    if heads is not None:
        row["heads"] = heads
    return row


def _bars(hires: Decimal, hire_heads: int, departures: Decimal, departure_heads: int, rate: Decimal, rate_heads: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if _q(hires) != 0:
        rows.append(_bar("hires", "Hires", hires, hire_heads))
    if _q(departures) != 0:
        rows.append(_bar("departures", "Departures", departures, departure_heads))
    if _q(rate) != 0:
        rows.append(_bar("rate", "Rate", rate, rate_heads))
    return rows


def _finish(
    *,
    bridge_id: str,
    title: str,
    from_label: str,
    to_label: str,
    beginning: Decimal,
    ending: Decimal,
    volume: list[dict[str, Any]],
    sentence: str,
    departments: list[dict[str, Any]],
) -> dict[str, Any]:
    begin = _q(beginning)
    end = _q(ending)
    priced = sum((_q(Decimal(str(bar["amount"]))) for bar in volume), Decimal(0))
    reconciling = end - begin - priced
    bars = list(volume)
    if reconciling != 0:
        bars.append(_bar("reconciling", "GL reconciling", reconciling, None))
    return {
        "id": bridge_id,
        "available": True,
        "title": title,
        "from_label": from_label,
        "to_label": to_label,
        "beginning": _money(begin),
        "ending": _money(end),
        "change": _money(end - begin),
        "bars": bars,
        "ties": begin + sum((_q(Decimal(str(bar["amount"]))) for bar in bars), Decimal(0)) == end,
        "commentary": sentence,
        "price_basis": PRICE_BASIS,
        "compensation_includes": COMPENSATION_INCLUDES,
        "departments": departments,
    }


def _unavailable(bridge_id: str, title: str, reason: str) -> dict[str, Any]:
    return {"id": bridge_id, "available": False, "title": title, "reason": reason}


def _sentence_change(change: Decimal, lead: str, bars: list[dict[str, Any]]) -> str:
    if _q(change) == 0 and not bars:
        return lead
    parts: list[str] = []
    for bar in bars:
        heads = bar.get("heads")
        who = ""
        if heads:
            who = f" ({heads} person)" if heads == 1 else f" ({heads} people)"
        parts.append(f"{bar['label']} {_fmt(Decimal(str(bar['amount'])))}{who}")
    if not parts:
        return lead
    return f"{lead} {'; '.join(parts)}."


def _department_rows(
    beginning: dict[str, Decimal],
    ending: dict[str, Decimal],
    hires: dict[str, Decimal],
    hire_heads: dict[str, int],
    departures: dict[str, Decimal],
    departure_heads: dict[str, int],
    rate: dict[str, Decimal],
    rate_heads: dict[str, int],
) -> list[dict[str, Any]]:
    names = sorted(set(beginning) | set(ending) | set(hires) | set(departures) | set(rate))
    rows: list[dict[str, Any]] = []
    for name in names:
        begin = beginning.get(name, Decimal(0))
        end = ending.get(name, Decimal(0))
        bars = _bars(
            hires.get(name, Decimal(0)),
            hire_heads.get(name, 0),
            departures.get(name, Decimal(0)),
            departure_heads.get(name, 0),
            rate.get(name, Decimal(0)),
            rate_heads.get(name, 0),
        )
        finished = _finish(
            bridge_id=name,
            title=name,
            from_label="",
            to_label="",
            beginning=begin,
            ending=end,
            volume=bars,
            sentence="",
            departments=[],
        )
        if finished["beginning"] == 0 and finished["ending"] == 0 and not finished["bars"]:
            continue
        rows.append(
            {
                "department": name,
                "beginning": finished["beginning"],
                "ending": finished["ending"],
                "change": finished["change"],
                "bars": finished["bars"],
                "ties": finished["ties"],
            }
        )
    return rows


def _mom_bridge(close: date, roster: list[RosterEmployee], payroll: GlPayrollSet) -> dict[str, Any]:
    prior = period_to_date(prior_period(to_period(close.isoformat()[:7])))
    title = f"Compensation bridge — {_month_label(prior)} to {_month_label(close)}"
    opening = _gl_by_department(payroll, prior)
    closing = _gl_by_department(payroll, close)
    if opening is None or closing is None:
        missing = _month_label(prior) if opening is None else _month_label(close)
        return _unavailable("mom", title, f"No GL compensation for {missing}.")
    before = _people(roster, prior)
    after = _people(roster, close)
    hires: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    hire_heads: dict[str, int] = defaultdict(int)
    departures: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    departure_heads: dict[str, int] = defaultdict(int)
    for emp_id, employee in after.items():
        if emp_id not in before:
            hires[_dept(employee)] += person_month_cost(employee)
            hire_heads[_dept(employee)] += 1
    for emp_id, employee in before.items():
        if emp_id not in after:
            departures[_dept(employee)] -= person_month_cost(employee)
            departure_heads[_dept(employee)] += 1
    empty: dict[str, Decimal] = {}
    empty_heads: dict[str, int] = {}
    departments = _department_rows(opening, closing, hires, hire_heads, departures, departure_heads, empty, empty_heads)
    company_bars = _bars(
        sum(hires.values(), Decimal(0)),
        sum(hire_heads.values()),
        sum(departures.values(), Decimal(0)),
        sum(departure_heads.values()),
        Decimal(0),
        0,
    )
    begin = sum(opening.values(), Decimal(0))
    end = sum(closing.values(), Decimal(0))
    change = _q(end) - _q(begin)
    if change > 0:
        lead = f"Compensation rose {_fmt(change)} from {_month_label(prior)} to {_month_label(close)}."
    elif change < 0:
        lead = f"Compensation fell {_fmt(abs(change))} from {_month_label(prior)} to {_month_label(close)}."
    else:
        lead = f"Compensation was unchanged from {_month_label(prior)} to {_month_label(close)}."
    preview = _finish(
        bridge_id="mom",
        title=title,
        from_label=_month_label(prior),
        to_label=_month_label(close),
        beginning=begin,
        ending=end,
        volume=company_bars,
        sentence="",
        departments=departments,
    )
    preview["commentary"] = _sentence_change(change, lead, preview["bars"])
    return preview


def _budget_bridge(
    close: date,
    roster: list[RosterEmployee],
    budget_roster: list[RosterEmployee],
    actual_payroll: GlPayrollSet,
    budget_payroll: GlPayrollSet,
) -> dict[str, Any] | None:
    title = f"Compensation bridge — {_month_label(close)} vs budget"
    actual_gl = _gl_by_department(actual_payroll, close)
    budget_gl = _gl_by_department(budget_payroll, close)
    if actual_gl is None or budget_gl is None:
        return None
    actual = _people(roster, close)
    budget = _people(budget_roster, close)
    hires: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    hire_heads: dict[str, int] = defaultdict(int)
    departures: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    departure_heads: dict[str, int] = defaultdict(int)
    rate: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    rate_heads: dict[str, int] = defaultdict(int)
    for emp_id, employee in actual.items():
        planned = budget.get(emp_id)
        if planned is None:
            hires[_dept(employee)] += person_month_cost(employee)
            hire_heads[_dept(employee)] += 1
        elif _dept(planned) != _dept(employee):
            departures[_dept(planned)] -= person_month_cost(planned)
            departure_heads[_dept(planned)] += 1
            hires[_dept(employee)] += person_month_cost(employee)
            hire_heads[_dept(employee)] += 1
        else:
            delta = person_month_cost(employee) - person_month_cost(planned)
            if _q(delta) != 0:
                rate[_dept(employee)] += delta
                rate_heads[_dept(employee)] += 1
    for emp_id, employee in budget.items():
        if emp_id not in actual:
            departures[_dept(employee)] -= person_month_cost(employee)
            departure_heads[_dept(employee)] += 1
    departments = _department_rows(
        budget_gl, actual_gl, hires, hire_heads, departures, departure_heads, rate, rate_heads
    )
    company_bars = _bars(
        sum(hires.values(), Decimal(0)),
        sum(hire_heads.values()),
        sum(departures.values(), Decimal(0)),
        sum(departure_heads.values()),
        sum(rate.values(), Decimal(0)),
        sum(rate_heads.values()),
    )
    begin = sum(budget_gl.values(), Decimal(0))
    end = sum(actual_gl.values(), Decimal(0))
    change = _q(end) - _q(begin)
    if change > 0:
        lead = f"{_month_label(close)} compensation was {_fmt(change)} above budget."
    elif change < 0:
        lead = f"{_month_label(close)} compensation was {_fmt(abs(change))} below budget."
    else:
        lead = f"{_month_label(close)} compensation matched budget."
    finished = _finish(
        bridge_id="budget",
        title=title,
        from_label=f"{_month_label(close)} budget",
        to_label=_month_label(close),
        beginning=begin,
        ending=end,
        volume=company_bars,
        sentence="",
        departments=departments,
    )
    finished["commentary"] = _sentence_change(change, lead, finished["bars"])
    return finished


def build_labor_bridges(
    *,
    close: date,
    roster: list[RosterEmployee],
    budget_roster: list[RosterEmployee],
    actual_payroll: GlPayrollSet,
    budget_payroll: GlPayrollSet | None,
) -> list[dict[str, Any]]:
    """Saved compensation bridges for the close month. Versus budget is omitted when that GL is absent."""
    bridges = [_mom_bridge(close, roster, actual_payroll)]
    if budget_payroll is not None:
        versus_budget = _budget_bridge(close, roster, budget_roster, actual_payroll, budget_payroll)
        if versus_budget is not None:
            bridges.append(versus_budget)
    return bridges
