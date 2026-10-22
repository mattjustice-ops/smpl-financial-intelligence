"""Confirmed funding rounds and where each dollar lands.

The forecast engine is what the customer fills in. These functions are the same
split the cash walk, the cash flow statement, and the balance sheet have to follow:
net proceeds are cash, equity proceeds are paid-in capital, debt proceeds are the
debt balance, and interest is interest expense from the month it starts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_MONTH = re.compile(r"^\d{4}-\d{2}$")


def cents(value: float) -> float:
    return round(float(value) + 1e-9, 2)


@dataclass(frozen=True)
class FinancingRound:
    month: str
    instrument: str
    gross: float
    fees: float
    net: float
    debt_proceeds: float
    equity_proceeds: float
    rate: float
    interest_start: str
    principal: float
    principal_month: str


@dataclass(frozen=True)
class MonthEffect:
    financing: float = 0.0
    interest: float = 0.0
    debt_delta: float = 0.0
    equity_delta: float = 0.0
    debt_balance: float = 0.0


def normalize_round(raw: dict[str, Any], close_month: str) -> FinancingRound:
    """Reject a round that is not a confirmed open-month term sheet."""
    month = str(raw.get("month") or "")
    if not _MONTH.match(month):
        raise ValueError("Choose the month the cash is wired.")
    if month <= close_month:
        raise ValueError("The wire month has to be after the close.")
    instrument = raw.get("instrument")
    if instrument not in ("equity", "debt"):
        raise ValueError("Choose equity or debt.")
    gross = float(raw.get("gross") or 0)
    fees = float(raw.get("fees") or 0)
    if gross <= 0:
        raise ValueError("Enter the gross amount.")
    if fees < 0 or fees >= gross:
        raise ValueError("Fees have to be less than the gross amount.")
    net = cents(gross - fees)
    warrant = float(raw.get("warrantPct") or 0) if instrument == "debt" else 0.0
    if warrant < 0 or warrant > 100:
        raise ValueError("Warrant coverage is a percent from 0 to 100.")
    rate_pct = float(raw.get("ratePct") or 0) if instrument == "debt" else 0.0
    if rate_pct < 0:
        raise ValueError("The interest rate cannot be negative.")
    interest_start = str(raw.get("interestStart") or month)
    if not _MONTH.match(interest_start) or interest_start < month:
        raise ValueError("Interest starts in the wire month or later.")
    principal = float(raw.get("principalDue") or 0) if instrument == "debt" else 0.0
    principal_month = str(raw.get("principalMonth") or "") if principal else ""
    debt_proceeds = cents(net * (1 - warrant / 100)) if instrument == "debt" else 0.0
    equity_proceeds = cents(net - debt_proceeds)
    if principal < 0 or principal > debt_proceeds + 0.01:
        raise ValueError("Principal repaid this year cannot exceed the debt.")
    if principal and (not _MONTH.match(principal_month) or principal_month < month):
        raise ValueError("Choose the month principal is repaid.")
    return FinancingRound(
        month=month,
        instrument=instrument,
        gross=cents(gross),
        fees=cents(fees),
        net=net,
        debt_proceeds=debt_proceeds,
        equity_proceeds=equity_proceeds,
        rate=rate_pct / 100,
        interest_start=interest_start,
        principal=cents(principal),
        principal_month=principal_month,
    )


def effects(
    rounds: list[dict[str, Any]],
    periods: list[str],
    close_month: str,
) -> dict[str, MonthEffect]:
    """Cash financing, interest, and the debt or equity movement for each month."""
    open_rounds: list[dict[str, Any]] = []
    for raw in rounds:
        try:
            parsed = normalize_round(raw, close_month)
        except ValueError:
            continue
        open_rounds.append(
            {
                "month": parsed.month,
                "instrument": parsed.instrument,
                "net": parsed.net,
                "debt": parsed.debt_proceeds,
                "equity": parsed.equity_proceeds,
                "rate": parsed.rate,
                "interest_start": parsed.interest_start,
                "principal": parsed.principal,
                "principal_month": parsed.principal_month,
                "outstanding": 0.0,
            }
        )
    out: dict[str, MonthEffect] = {}
    balance = 0.0
    for period in periods:
        if period <= close_month:
            out[period] = MonthEffect()
            continue
        financing = debt_delta = equity_delta = 0.0
        for row in open_rounds:
            if row["month"] != period:
                continue
            financing += row["net"]
            debt_delta += row["debt"]
            equity_delta += row["equity"]
            row["outstanding"] = cents(row["outstanding"] + row["debt"])
            balance = cents(balance + row["debt"])
        interest = 0.0
        for row in open_rounds:
            if row["instrument"] != "debt" or row["interest_start"] > period or row["outstanding"] <= 0:
                continue
            interest += row["outstanding"] * row["rate"] / 12
        interest = cents(interest)
        for row in open_rounds:
            if not row["principal"] or row["principal_month"] != period:
                continue
            pay = min(row["principal"], row["outstanding"])
            row["outstanding"] = cents(row["outstanding"] - pay)
            balance = cents(balance - pay)
            financing -= pay
            debt_delta -= pay
        out[period] = MonthEffect(
            financing=cents(financing),
            interest=interest,
            debt_delta=cents(debt_delta),
            equity_delta=cents(equity_delta),
            debt_balance=balance,
        )
    return out
