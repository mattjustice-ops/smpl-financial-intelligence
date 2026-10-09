"""Demo-data customer payments, dunning, write-offs and the allowance (scripts/demo_data/collections_model.py)."""

from __future__ import annotations

import datetime as dt
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo_data"))

import collections_model as cm  # noqa: E402


class Inv:
    def __init__(self, cid: str, issue: str, amount: str, terms_days: int = 30):
        self.id = f"INV-{issue}-{cid}"
        self.customer_id, self.customer_name, self.issue = cid, f"Customer {cid}", issue
        self.invoice_date = cm.first_day(issue)
        self.due_date = self.invoice_date + dt.timedelta(days=terms_days)
        self.amount, self.kind = Decimal(amount), "recurring"
        self.paid = self.written_off = None


def months(a: str, b: str) -> list[str]:
    return [cm.padd(a, i) for i in range(cm.pidx(b) - cm.pidx(a) + 1)]


def test_habit_shares_add_to_one_and_average_about_a_week_late() -> None:
    assert sum(s for _, s, _, _ in cm.PAYMENT_HABITS) == 1
    mean = sum(s * Decimal(lo + hi) / 2 for _, s, lo, hi in cm.PAYMENT_HABITS)
    assert Decimal(6) <= mean <= Decimal(9)


@pytest.mark.parametrize("ns", cm.NO_STARTS)
def test_no_starts_leave_inside_their_first_year(ns: cm.NoStart) -> None:
    issue, due, suspended, left = cm.no_start_exit(ns)
    assert issue == cm.padd(ns.booked, ns.unpaid_after)
    assert suspended - due == dt.timedelta(days=cm.SUSPEND_DAYS)
    assert cm.pidx(left) - cm.pidx(ns.booked) < 12


def test_cases_settle_and_allowance_rolls() -> None:
    history = [
        {"period": "2024-02", "customer_id": "C1", "customer_name": "Customer C1", "movement_type": "New Business",
         "churn_type": ""},
        {"period": "2024-10", "customer_id": "C1", "customer_name": "Customer C1", "movement_type": "Churn",
         "churn_type": cm.NON_PAYMENT},
    ]
    invoices = [Inv("C1", p, "1000") for p in months("2024-02", "2024-09")]
    for c in ("C2", "C3"):
        invoices += [Inv(c, p, "500") for p in months("2024-01", "2026-06")]
    cadence = {c: "Monthly" for c in ("C1", "C2", "C3")}
    terms = {c: "Net 30" for c in cadence}
    cases = cm.plan_cases(history, invoices, cadence, terms)
    kinds = {c.kind: c for c in cases}
    assert set(kinds) == {cm.NON_PAYMENT, cm.RECOVERED_CASE, cm.DISPUTE_CASE}

    nonpay = kinds[cm.NON_PAYMENT]
    target = cm.last_day("2024-09") - dt.timedelta(days=cm.SUSPEND_DAYS)
    assert nonpay.first_due <= target
    assert all(i.issue < "2024-10" for i in nonpay.invoices)

    cm.settle(invoices, cases)
    for inv in invoices:
        assert (inv.paid is None) != (inv.written_off is None)
        if inv.paid:
            assert inv.paid >= inv.invoice_date + dt.timedelta(days=cm.EARLIEST_PAYMENT_DAYS)
    assert all(i.written_off == nonpay.written_off for i in nonpay.invoices)

    roll = cm.allowance_rollforward(invoices, cases, months("2024-01", "2026-06"))
    prev = roll[0]["beginning_allowance"]
    for r in roll:
        assert r["beginning_allowance"] == prev
        assert r["beginning_allowance"] + r["provision_for_credit_losses"] - r["write_offs"] == r["ending_allowance"]
        assert r["net_accounts_receivable"] == r["gross_accounts_receivable"] - r["ending_allowance"]
        prev = r["ending_allowance"]
    assert sum(r["write_offs"] for r in roll) == sum(i.amount for i in nonpay.invoices)

    at = {r["period"]: r for r in roll}
    on = cm.last_day(cm.month_of(nonpay.suspended))
    if on < nonpay.written_off:
        open_case = sum(i.amount for i in nonpay.invoices if cm.is_open(i, on))
        assert at[cm.month_of(on)]["specific_reserve"] >= open_case


def test_owner_is_whoever_holds_the_role_that_day() -> None:
    staff = [
        {"employee_id": "E1", "employee_name": "Controller One", "role": "Controller", "hire_date": "2016-01-01",
         "termination_date": ""},
        {"employee_id": "E2", "employee_name": "Billing One", "role": "Billing Specialist", "hire_date": "2025-04-01",
         "termination_date": ""},
        {"employee_id": "E3", "employee_name": "Rev One", "role": "Revenue Accountant", "hire_date": "2021-01-01",
         "termination_date": ""},
    ]
    assert cm.owner_on("Reminder", dt.date(2024, 5, 1), staff)["employee_id"] == "E3"
    assert cm.owner_on("Reminder", dt.date(2025, 5, 1), staff)["employee_id"] == "E2"
    assert cm.owner_on("Final notice", dt.date(2025, 5, 1), staff)["employee_id"] == "E1"
    assert cm.owner_on("Written off", dt.date(2025, 5, 1), staff)["employee_id"] == "E1"
    with pytest.raises(ValueError):
        cm.owner_on("Reminder", dt.date(2020, 1, 1), staff)
