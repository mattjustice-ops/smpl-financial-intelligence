"""Demo-data vendor subledger and stock comp schedule (scripts/demo_data/vendor_model.py, stock_comp.py)."""

from __future__ import annotations

import csv
import datetime as dt
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo_data"))

import stock_comp  # noqa: E402
import vendor_model as vm  # noqa: E402

EMPLOYEE_FIELDS = ["employee_id", "role", "level", "department", "cost_center", "hire_date", "termination_date",
                   "remote_flag", "base_salary", "equity_sbc_annual"]
ROSTER = [
    ("E1", "VP Engineering", "L8", "Engineering", "ENG-APP", "2022-03-01", "", "No", "260000", "120000"),
    ("E2", "Software Engineer", "L5", "Engineering", "ENG-PLAT", "2024-02-12", "", "Yes", "180000", "36000"),
    ("E3", "Account Executive", "L4", "Sales", "SALES-AE", "2023-06-01", "2025-05-15", "No", "130000", "24000"),
    ("E4", "Support Specialist", "L2", "Support", "SUP-TIER1", "2024-07-01", "", "Yes", "70000", "6000"),
    ("E5", "Controller", "L6", "Finance", "FIN-ACCT", "2025-09-02", "", "No", "190000", "48000"),
]


@pytest.fixture()
def src(tmp_path: Path) -> str:
    for version in ("Actual", "Budget", "Forecast"):
        with open(tmp_path / f"{version}_Employees.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(EMPLOYEE_FIELDS)
            w.writerows(ROSTER)
    return str(tmp_path)


def test_usage_shares_add_to_one() -> None:
    for account, shares in vm.USAGE_SHARES.items():
        assert sum(s for _, s in shares) == 1, account
        assert all(v in vm.VENDORS for v, _ in shares), account


def test_contract_amortizes_to_its_amount() -> None:
    c = vm.Contract("C1", "V1020", "6420", "Engineering", "ENG-DATA", "2025-01", Decimal("100000.00"), "test")
    months = vm.prange("2025-01", "2025-12")
    assert sum(c.amortization(p) for p in months) == c.amount
    assert c.amortization("2024-12") == 0 and c.amortization("2026-01") == 0
    assert c.remaining("2024-12") == 0
    assert c.remaining("2025-01") == c.amount - c.amortization("2025-01")
    assert c.remaining("2025-12") == 0


def test_payment_runs_are_thursdays() -> None:
    for d in (dt.date(2025, 3, 3), dt.date(2025, 3, 6), dt.date(2025, 3, 9)):
        before, after = vm.run_on_or_before(d), vm.run_on_or_after(d)
        assert before.weekday() == 3 and before <= d and (d - before).days < 7
        assert after.weekday() == 3 and after >= d and (after - d).days < 7


def test_aging_buckets() -> None:
    line = vm.Line("V1002", "5000", "Engineering", "ENG-PLAT", Decimal("10"), "x", dt.date(2025, 1, 1),
                   dt.date(2025, 1, 31))
    bill = vm.Bill("B1", "V1002", "1", dt.date(2025, 1, 31), dt.date(2025, 3, 2), [line])
    assert vm.aging_bucket(bill, dt.date(2025, 3, 2)) == "current"
    assert vm.aging_bucket(bill, dt.date(2025, 3, 3)) == "days_1_30"
    assert vm.aging_bucket(bill, dt.date(2025, 4, 2)) == "days_31_60"
    assert vm.aging_bucket(bill, dt.date(2025, 5, 31)) == "days_61_90"
    assert vm.aging_bucket(bill, dt.date(2025, 6, 1)) == "days_over_90"


def test_on_schedule_payment_is_never_before_the_bill_or_after_the_due_date() -> None:
    for vendor in ("V1002", "V1020", "V1051", "V1010"):
        v = vm.VENDORS[vendor]
        for day in range(1, 29):
            d = dt.date(2025, 5, day)
            bill = vm.Bill(f"B-{vendor}-{day}", vendor, "1", d, d + dt.timedelta(days=v.terms), [])
            paid = vm.VendorModel._pay_date(bill, late=False)
            assert paid >= bill.bill_date
            if v.terms >= 7:
                assert paid <= bill.due_date


def test_usage_split_keeps_the_amount(src: str) -> None:
    model = vm.VendorModel(src)
    model.add_usage("Actual", "2025-03", "5030", "Engineering", "ENG-PLAT", Decimal("12345.67"))
    lines = model.usage_lines("Actual", "2025-03")
    assert sum(ln.amount for ln in lines) == Decimal("12345.67")
    assert {ln.vendor for ln in lines} == {v for v, _ in vm.USAGE_SHARES["5030"]}
    with pytest.raises(ValueError):
        model.add_usage("Actual", "2025-03", "6400", "G&A", "GA-IT", Decimal("1"))


def test_lease_escalates_on_its_anniversary(src: str) -> None:
    model = vm.VendorModel(src)

    def rent(p: str) -> Decimal:
        return sum(ln.amount for ln in model.monthly_lines("Actual", p) if ln.vendor == "V1061")

    assert rent("2025-03") == 0
    assert rent("2025-04") == rent("2026-03") == Decimal("26000.00")
    assert rent("2026-04") == Decimal("26780.00")


@pytest.mark.parametrize("version", ["Actual", "Budget", "Forecast"])
def test_ap_and_prepaids_roll_forward(src: str, version: str) -> None:
    model = vm.VendorModel(src)
    actual = model.ledger("Actual")
    led = actual if version == "Actual" else model.ledger(version, actual)
    for b in led.bills:
        assert b.total > 0
        assert b.paid_date is None or b.paid_date >= b.bill_date
        assert b.payment_id == "" if b.paid_date is None else b.payment_id
    for p in vm.prange(*vm.WINDOW[version]):
        prev = vm.padd(p, -1)
        billed = sum((b.total for b in vm.bills_in(led, p)), Decimal(0))
        paid = sum((b.total for b in vm.payments_in(led, p)), Decimal(0))
        assert vm.ap_balance(led, prev) + billed - paid == vm.ap_balance(led, p), p
        added = sum((c.amount for c in led.contracts if c.start == p), Decimal(0))
        amort = sum((c.amortization(p) for c in led.contracts), Decimal(0))
        assert vm.prepaid_balance(led, prev) + added - amort == vm.prepaid_balance(led, p), p
    if version == "Actual":
        assert all(b.paid_date is None or b.paid_date <= vm.last_day(vm.CLOSE) for b in led.bills)
    else:
        assert vm.ap_balance(led, vm.WINDOW[version][1]) >= 0


def test_write_files_ties(src: str, tmp_path: Path) -> None:
    model = vm.VendorModel(src)
    actual = model.ledger("Actual")
    ledgers = {"Actual": actual, "Budget": model.ledger("Budget", actual), "Forecast": model.ledger("Forecast", actual)}
    out = tmp_path / "out"
    out.mkdir()
    vm.write_files(str(out), "org", model, ledgers)
    assert sorted(p.name for p in out.iterdir()) == sorted(vm.file_names())

    def read(name: str) -> list[dict[str, str]]:
        with open(out / name, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    close_open = sum(Decimal(r["amount"]) for r in read("Actual_vendor_bills.csv") if r["status"] == "Open")
    aging_close = sum(Decimal(r["total"]) for r in read("Actual_AP_Aging.csv") if r["period"] == vm.CLOSE)
    roll = {r["period"]: r for r in read("Actual_accounts_payable_rollforward.csv")}
    assert close_open == aging_close == Decimal(roll[vm.CLOSE]["ending_accounts_payable"])
    for name in vm.file_names():
        if name.endswith("rollforward.csv") or name.endswith("Rollforward.csv"):
            assert all(Decimal(r["rollforward_check"]) == 0 for r in read(name)), name
    master = {r["vendor_id"] for r in read("Actual_vendor_master.csv")}
    assert {r["vendor_id"] for r in read("Actual_vendor_bills.csv")} <= master


def test_sbc_prorates_days_employed(src: str) -> None:
    sbc = stock_comp.by_cost_center(src, "Actual", ["2024-02", "2025-05"])
    # E2 hired Feb 12 2024: 18 of 29 days.
    assert sbc["2024-02"][("Engineering", "ENG-PLAT")] == stock_comp.q(Decimal(36000) / 12 * 18 / 29)
    # E3 leaves May 15 2025: 15 of 31 days.
    assert sbc["2025-05"][("Sales", "SALES-AE")] == stock_comp.q(Decimal(24000) / 12 * 15 / 31)
    assert ("Finance", "FIN-ACCT") not in sbc["2025-05"]


def test_sbc_schedule_lines_add_to_total(src: str) -> None:
    rows = stock_comp.schedule_rows(src, "org", "Actual", vm.prange("2024-01", "2026-06"))
    for r in rows:
        assert r["total_sbc"] == r["cogs_sbc"] + r["sm_sbc"] + r["rd_sbc"] + r["ga_sbc"]
    july = next(r for r in rows if r["period"] == "2024-07")
    assert july["cogs_sbc"] == stock_comp.q(Decimal(6000) / 12)
    assert july["headcount"] == "4"
    assert stock_comp.line_of("Support", "SUP-TIER1") == "cogs"
    assert stock_comp.line_of("Support", "SUP-OPS") == "ga"
