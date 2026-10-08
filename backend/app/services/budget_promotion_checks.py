"""Checks a budget version must pass before its tables replace the Budget warehouse rows."""

from __future__ import annotations

from typing import Any, Optional

from app.services.reporting.period_utils import to_period

TOLERANCE = 0.01

CORE_TABLES: tuple[str, ...] = (
    "budget_mrr_waterfall",
    "budget_income_statement",
    "budget_cash_flow_statement",
    "budget_balance_sheet",
    "budget_bookings_summary",
)
MONTHLY_TABLES: tuple[str, ...] = (*CORE_TABLES, "budget_deferred_commissions_rollforward")
SCHEDULE = "budget_commission_schedule"
ROLLFORWARD = "budget_deferred_commissions_rollforward"


def _period(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        p = to_period(value)
    except (TypeError, ValueError):
        return None
    year, _, month = p.partition("-")
    if not (year.isdigit() and month.isdigit() and 1 <= int(month) <= 12):
        return None
    return p


def _num(row: dict[str, Any], key: str) -> Optional[float]:
    value = row.get(key)
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def _money(v: float) -> str:
    return f"{v:,.2f}"


def _required(
    failures: list[str], table: str, period: str, row: dict[str, Any], keys: tuple[str, ...]
) -> Optional[dict[str, float]]:
    values: dict[str, float] = {}
    missing = []
    for key in keys:
        v = _num(row, key)
        if v is None:
            missing.append(key)
        else:
            values[key] = v
    if missing:
        failures.append(f"{table} {period}: missing or non-numeric {', '.join(missing)}.")
        return None
    return values


def budget_promotion_failures(
    tables: dict[str, list[dict[str, Any]]], budget_year: Optional[int]
) -> list[str]:
    """Return every reason the tables can't be promoted; empty when they can."""
    failures: list[str] = []
    if budget_year is None:
        failures.append("The version has no budget year, so its periods can't be confirmed.")
    expected = [f"{budget_year:04d}-{m:02d}" for m in range(1, 13)] if budget_year else []
    for table in CORE_TABLES:
        if table not in tables:
            failures.append(f"{table} is not in the version.")

    by_period: dict[str, dict[str, dict[str, Any]]] = {}
    for table, rows in tables.items():
        seen: dict[str, dict[str, Any]] = {}
        bad = 0
        outside: set[str] = set()
        for row in rows:
            p = _period(row.get("period"))
            if p is None:
                bad += 1
                continue
            if budget_year and not p.startswith(f"{budget_year:04d}-"):
                outside.add(p)
            if table in MONTHLY_TABLES:
                if p in seen:
                    failures.append(f"{table}: more than one row for {p}.")
                seen[p] = row
        if bad:
            failures.append(f"{table}: {bad} row(s) without a valid period.")
        if outside:
            failures.append(f"{table}: periods outside FY{budget_year}: {', '.join(sorted(outside))}.")
        if table in MONTHLY_TABLES and expected:
            missing = [p for p in expected if p not in seen]
            if missing:
                failures.append(f"{table}: no row for {', '.join(missing)}.")
        by_period[table] = seen

    has_schedule = SCHEDULE in tables
    has_rollforward = ROLLFORWARD in tables
    if has_schedule != has_rollforward:
        present, absent = (SCHEDULE, ROLLFORWARD) if has_schedule else (ROLLFORWARD, SCHEDULE)
        failures.append(f"{present} is in the version but {absent} is not; they are promoted together.")
    if not (has_schedule and has_rollforward):
        return failures

    schedule_cap: dict[str, float] = {}
    schedule_exp: dict[str, float] = {}
    for row in tables[SCHEDULE]:
        p = _period(row.get("period"))
        if p is None:
            continue
        label = f"{p} {row.get('plan_id') or '(no plan_id)'}"
        v = _required(
            failures, SCHEDULE, label, row, ("commission_payout", "capitalized_amount", "expensed_amount")
        )
        if v is None:
            continue
        diff = v["capitalized_amount"] + v["expensed_amount"] - v["commission_payout"]
        if abs(diff) > TOLERANCE:
            failures.append(
                f"{SCHEDULE} {label}: capitalized {_money(v['capitalized_amount'])} + expensed "
                f"{_money(v['expensed_amount'])} ≠ payout {_money(v['commission_payout'])}."
            )
        cap_flag = str(row.get("capitalize") or "").strip().upper()
        if cap_flag not in {"Y", "N"}:
            failures.append(f"{SCHEDULE} {label}: capitalize must be Y or N.")
        elif cap_flag == "N" and abs(v["capitalized_amount"]) > TOLERANCE:
            failures.append(f"{SCHEDULE} {label}: capitalize is N but {_money(v['capitalized_amount'])} is capitalized.")
        elif cap_flag == "Y" and abs(v["expensed_amount"]) > TOLERANCE:
            failures.append(f"{SCHEDULE} {label}: capitalize is Y but {_money(v['expensed_amount'])} is expensed.")
        schedule_cap[p] = schedule_cap.get(p, 0.0) + v["capitalized_amount"]
        schedule_exp[p] = schedule_exp.get(p, 0.0) + v["expensed_amount"]

    rf_rows = by_period.get(ROLLFORWARD, {})
    bs_rows = by_period.get("budget_balance_sheet", {})
    cfs_rows = by_period.get("budget_cash_flow_statement", {})
    prior_end: Optional[float] = None
    prior_period: Optional[str] = None
    for p in sorted(rf_rows):
        row = rf_rows[p]
        v = _required(
            failures,
            ROLLFORWARD,
            p,
            row,
            (
                "beginning_deferred_commissions",
                "capitalized_commissions",
                "commission_amortization",
                "ending_deferred_commissions",
                "current_portion",
                "noncurrent_portion",
                "expensed_commissions",
                "payroll_tax_on_commissions",
            ),
        )
        if v is None:
            prior_end, prior_period = None, None
            continue
        beg, end = v["beginning_deferred_commissions"], v["ending_deferred_commissions"]
        foot = beg + v["capitalized_commissions"] - v["commission_amortization"] - end
        if abs(foot) > TOLERANCE:
            failures.append(
                f"{ROLLFORWARD} {p}: beginning + capitalized − amortization ≠ ending (off by {_money(foot)})."
            )
        split = v["current_portion"] + v["noncurrent_portion"] - end
        if abs(split) > TOLERANCE:
            failures.append(f"{ROLLFORWARD} {p}: current + noncurrent ≠ ending (off by {_money(split)}).")
        if prior_end is not None and abs(beg - prior_end) > TOLERANCE:
            failures.append(
                f"{ROLLFORWARD} {p}: beginning {_money(beg)} ≠ {prior_period} ending {_money(prior_end)}."
            )
        prior_end, prior_period = end, p

        exp_diff = v["expensed_commissions"] - schedule_exp.get(p, 0.0)
        if abs(exp_diff) > TOLERANCE:
            failures.append(
                f"{ROLLFORWARD} {p}: expensed {_money(v['expensed_commissions'])} ≠ commission schedule "
                f"expensed {_money(schedule_exp.get(p, 0.0))}."
            )
        # The roll-forward also capitalizes payroll tax on capitalized commissions when policy says so.
        cap_extra = v["capitalized_commissions"] - schedule_cap.get(p, 0.0)
        if cap_extra < -TOLERANCE or cap_extra > v["payroll_tax_on_commissions"] + TOLERANCE:
            failures.append(
                f"{ROLLFORWARD} {p}: capitalized {_money(v['capitalized_commissions'])} doesn't tie to the "
                f"commission schedule's {_money(schedule_cap.get(p, 0.0))} (plus at most "
                f"{_money(v['payroll_tax_on_commissions'])} capitalized payroll tax)."
            )

        bs = bs_rows.get(p)
        if bs is not None:
            for bs_key, rf_key in (
                ("deferred_commissions_current", "current_portion"),
                ("deferred_commissions_noncurrent", "noncurrent_portion"),
            ):
                bs_val = _num(bs, bs_key)
                if bs_val is None:
                    failures.append(f"budget_balance_sheet {p}: missing {bs_key}.")
                elif abs(bs_val - v[rf_key]) > TOLERANCE:
                    failures.append(
                        f"budget_balance_sheet {p}: {bs_key} {_money(bs_val)} ≠ roll-forward {rf_key} {_money(v[rf_key])}."
                    )
        cfs = cfs_rows.get(p)
        if cfs is not None:
            chg = _num(cfs, "change_in_deferred_commissions")
            if chg is None:
                failures.append(f"budget_cash_flow_statement {p}: missing change_in_deferred_commissions.")
            elif abs(chg - (beg - end)) > TOLERANCE:
                failures.append(
                    f"budget_cash_flow_statement {p}: change_in_deferred_commissions {_money(chg)} ≠ "
                    f"roll-forward beginning − ending {_money(beg - end)}."
                )
    return failures
