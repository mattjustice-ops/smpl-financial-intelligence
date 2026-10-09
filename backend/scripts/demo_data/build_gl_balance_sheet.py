"""Balance sheet GL activity for the demo, built from the dataset's own files.

Method (financial_dashboard_cf_re_logic.md): the GL holds an opening trial balance at the
    cutoff (Jan 31, 2024) and monthly activity after it. Balances are opening + cumulative
    activity. Retained earnings is never posted; it is computed from GL net income.

Where each balance sheet row comes from:
  * Opening balances: the cutoff month of Actual_balance_sheet.csv. Equity is one total
    in the dataset, so it opens on account 3000 with no split.
  * Accounts receivable: AR rollforward (billings, collections).
  * Accounts payable and prepaids (Oct 9 2026): the vendor ledger (vendor_model.py). Bills credit AP
    (Actual: one row per bill with the vendor; Budget and Forecast: one row a month), payments debit
    it (Actual: one row per payment run and vendor). Annual contracts paid up front debit 1200 when
    billed and amortize monthly to their expense account. The opening AP and prepaids are restated
    to the bills open and the contracts unamortized at the cutoff, with opening cash moved by the
    same amounts.
  * Accrued expenses (2050): services billed in arrears are accrued in the month of service and relieved when
    the bill posts to AP (Actual: one row per vendor accrual and per bill). The file's opening AP is restated
    to the open bills plus the opening accrued expenses (services through the cutoff billed after it).
  * Operating leases (ASC 842, vendor_model.LEASES): the right-of-use asset (1600) and lease liability (2060)
    are recognized at commencement (non-cash, "Balance Sheet Activity"); rent bills reduce the liability,
    interest accretes on it, and the right-of-use asset amortizes by the rest of the straight-line cost
    (non-cash). At the cutoff the liability less the asset (deferred rent) comes out of the file's other
    liabilities, with no cash move. The balance sheet file shows the asset as other_assets and both new liabilities in
    other_liabilities (STATEMENT_LINES).
  * Deferred commissions: deferred commissions rollforward. Capitalized payouts post to
    1550 (noncurrent), amortization comes out of 1250 (current), and a monthly reclass
    keeps 1250 at the next 12 months' amortization.
  * PP&E: depreciation = the month's GL D&A; additions = the balance sheet change plus D&A.
  * Deferred revenue, debt, other liabilities (2600): change in the version's balance sheet file (other
    liabilities less the accrued expense and lease lines it holds).
  * Stock comp: SBC schedule total, credited to APIC - Stock Compensation as non-cash
    ("Balance Sheet Activity"). The expense is on 5040 / 6140.
  * Equity raises: financing in the cash flow statement that is not a change in debt.
  * Cash: the other side of the month's entries, so every month's journal balances.
A sub-ledger is the source for its line. Its billings/payments are posted when it starts
on the GL's own balance for that line; when it starts elsewhere (Budget and Forecast
schedules that do not continue from the Actual balance), the move to its ending balance
is posted as one net change and logged. The balance sheet file is used for the line only
when there is no schedule row or the schedule's layout differs.

Amounts are debit-positive (assets +, liabilities and equity -).
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from decimal import Decimal

from vendor_model import (LEASES, VENDORS, Ledger, accrual_moves, accrued_balance, ap_balance, bills_in,  # noqa: E402
                          last_day, lease_balances, open_bills, payments_in, prepaid_balance)

CENT = Decimal("0.01")
TIE = Decimal("1.00")
NON_CASH_DEPT = "Balance Sheet Activity"

ACCOUNTS = {
    "cash": ("1000", "Cash", "Assets", "Cash", "Cash"),
    "accounts_receivable": ("1100", "Accounts Receivable", "Assets", "AR", "Accounts Receivable"),
    "prepaids_and_other_current": ("1200", "Prepaids and Other Current Assets", "Assets", "Current Assets", "Prepaids"),
    "deferred_commissions_current": ("1250", "Deferred Commissions - Current", "Assets", "Deferred Commissions",
                                     "Deferred Commissions"),
    "ppe_net": ("1500", "Property and Equipment Net", "Assets", "PP&E", "Fixed Assets"),
    "deferred_commissions_noncurrent": ("1550", "Deferred Commissions - Noncurrent", "Assets", "Deferred Commissions",
                                        "Deferred Commissions Noncurrent"),
    "operating_lease_rou": ("1600", "Operating Lease Right-of-Use Assets", "Assets", "Other Assets", "Other Assets"),
    "accounts_payable": ("2000", "Accounts Payable", "Liabilities", "AP", "Accounts Payable"),
    "accrued_expenses": ("2050", "Accrued Expenses", "Liabilities", "Other Liabilities", "Other Liabilities"),
    "operating_lease_liabilities": ("2060", "Operating Lease Liabilities", "Liabilities", "Other Liabilities",
                                    "Other Liabilities"),
    "deferred_revenue": ("2100", "Deferred Revenue", "Liabilities", "Deferred Revenue", "Deferred Revenue"),
    "debt": ("2500", "Debt", "Liabilities", "Debt", "Debt"),
    "other_liabilities": ("2600", "Other Liabilities", "Liabilities", "Other Liabilities", "Other Liabilities"),
    "equity": ("3000", "Equity", "Equity", "Equity", "Equity"),
    "apic_sbc": ("3311", "APIC - Stock Compensation", "Equity", "Equity", "Equity"),
}
CREDIT_NORMAL = {"accounts_payable", "accrued_expenses", "operating_lease_liabilities", "deferred_revenue", "debt",
                 "other_liabilities", "equity", "apic_sbc"}
BALANCE_LINES = ["cash", "accounts_receivable", "prepaids_and_other_current", "deferred_commissions_current", "ppe_net",
                 "deferred_commissions_noncurrent", "accounts_payable", "deferred_revenue", "debt", "other_liabilities",
                 "equity"]
# Balance sheet file columns that hold more than one GL line (the app's other assets / other liabilities).
STATEMENT_LINES = {**{k: (k,) for k in BALANCE_LINES if k != "equity"},
                   "other_assets": ("operating_lease_rou",),
                   "other_liabilities": ("other_liabilities", "accrued_expenses", "operating_lease_liabilities")}
# sync_v5_statements.py writes other_assets; a balance sheet file with that column has the accrued expenses and
# lease liabilities in its other_liabilities. One without it predates them (ASC 840: deferred rent, not a lease
# liability).
SYNCED_COLUMN = "other_assets"
DEFERRED_COMMISSION_LINES = ("deferred_commissions_current", "deferred_commissions_noncurrent")

OPENING_VERSION = "Actual"
CHAIN_FROM_ACTUAL = {"Budget": "2026-01", "Forecast": "2026-07"}


def num(value) -> Decimal:
    text = str(value or "0").replace(",", "").strip()
    return Decimal(text or "0")


def _read(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _by_period(path: str) -> dict[str, dict[str, str]]:
    if not os.path.exists(path):
        return {}
    return {r["period"][:7]: r for r in _read(path)}


def _prior(period: str) -> str:
    y, m = int(period[:4]), int(period[5:])
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def is_pl(row: dict[str, str]) -> bool:
    return row["statement"] != "Balance Sheet"


def is_da(row: dict[str, str]) -> bool:
    return row["statement_category"] == "D&A" or row["account_group"] == "D&A"


class Writer:
    def __init__(self, org: str, version: str):
        self.org, self.version = org, version
        self.rows: list[dict[str, str]] = []

    def add(self, period: str, key: str, amount: Decimal, *, label: str, source_file: str,
            source_system: str = "Demo Model", department: str = "", note: str = "", record: str = "",
            vendor_id: str = "") -> None:
        """``record``: the subledger document (bill, payment, contract) the row posts; the record id ends in ``label``."""
        if amount == 0:
            return
        number, name, category, group, expense_type = ACCOUNTS[key]
        self.rows.append({
            "organization_id": self.org, "version": self.version, "period": period,
            "account_number": number, "account_name": name, "statement": "Balance Sheet",
            "statement_category": category, "account_group": group, "expense_type": expense_type,
            "department": department, "cost_center": "", "sub_department": "", "vendor_id": vendor_id,
            "vendor_name": VENDORS[vendor_id].name if vendor_id else "", "source_file": source_file,
            "source_record_id": f"{record}-{label}" if record else f"{self.version}-{period}-{number}-{label}",
            "amount": f"{amount.quantize(CENT):.2f}", "currency": "USD", "subsidiary": "US Parent",
            "source_system": source_system, "notes": note,
        })


KEY_BY_NUMBER = {v[0]: k for k, v in ACCOUNTS.items()}


def _natural(key: str, amount: Decimal) -> Decimal:
    return -amount if key in CREDIT_NORMAL else amount


def statement_value(line: dict[str, Decimal], column: str) -> Decimal:
    """A balance sheet file column from GL balances (natural sign)."""
    return sum((line[k] for k in STATEMENT_LINES[column]), Decimal("0"))


def build_balance_sheet_rows(src: str, gl_by_version: dict[str, list[dict[str, str]]], ledgers: dict[str, Ledger]):
    """Return {version: balance sheet rows} and a log of every choice made."""
    org = next(r["organization_id"] for r in gl_by_version["Actual"])
    actual_bs = _by_period(os.path.join(src, "Actual_balance_sheet.csv"))
    out: dict[str, list[dict[str, str]]] = {}
    log: list[dict[str, str]] = []
    actual_running: dict[str, dict[str, Decimal]] = {}
    actual_cutoff = min(actual_bs)
    accrued0 = accrued_balance(ledgers["Actual"], actual_cutoff)
    lease0, rou0 = lease_balances(actual_cutoff)
    held_actual = _held(src, "Actual")

    for version, gl_rows in gl_by_version.items():
        bs = _by_period(os.path.join(src, f"{version}_balance_sheet.csv"))
        cf = _by_period(os.path.join(src, f"{version}_cash_flow_statement.csv"))
        ar = _by_period(os.path.join(src, f"{version}_accounts_receivable_rollforward.csv"))
        sbc = _by_period(os.path.join(src, f"{version}_SBC_Schedule.csv"))
        dc_file = f"{version}_deferred_commissions_rollforward.csv"
        dc = _by_period(os.path.join(src, dc_file))
        led = ledgers[version]
        w = Writer(org, version)

        pl_total: dict[str, Decimal] = defaultdict(Decimal)
        da_total: dict[str, Decimal] = defaultdict(Decimal)
        for r in gl_rows:
            if is_pl(r):
                pl_total[r["period"][:7]] += num(r["amount"])
                if is_da(r):
                    da_total[r["period"][:7]] += num(r["amount"])

        def stock_comp(p: str) -> tuple[Decimal, str]:
            sched = sbc.get(p, {})
            if sched.get("total_sbc") not in (None, ""):
                return num(sched["total_sbc"]), f"{version}_SBC_Schedule.csv"
            return num(cf.get(p, {}).get("stock_based_compensation")), f"{version}_cash_flow_statement.csv"

        held_version = _held(src, version)

        def other_liabilities(row: dict[str, str], p: str) -> Decimal:
            """The file's other liabilities less the accrued expense and lease lines it holds (per the dataset's
            own rollforward and lease files when the file has them)."""
            if SYNCED_COLUMN not in row:
                return num(row.get("other_liabilities"))
            held = held_version.get(p, held_actual.get(p))
            if held is None:
                raise ValueError(f"{version} {p}: the balance sheet file has {SYNCED_COLUMN} but the dataset has no "
                                 f"accrued expense or lease schedule row for the month")
            return num(row.get("other_liabilities")) - sum(held)

        periods = sorted(bs)
        running: dict[str, Decimal] = defaultdict(Decimal)
        if version == OPENING_VERSION:
            cutoff = periods[0]
            opening = {key: num(bs[cutoff][key]) for key in BALANCE_LINES if key in bs[cutoff]}
            synced = SYNCED_COLUMN in bs[cutoff]
            # Vendor liabilities in the file: AP, plus the accrued expenses its other liabilities hold once synced.
            file_accrued = held_actual[cutoff][0] if synced else Decimal("0")
            open_ap = ap_balance(led, cutoff)
            restated = {"accounts_payable": (opening["accounts_payable"] + file_accrued, open_ap + accrued0,
                                             f"{len(open_bills(led.bills, last_day(cutoff)))} vendor bills open "
                                             f"({open_ap:,.2f}) and services through {cutoff} billed after it "
                                             f"({accrued0:,.2f}, accrued expenses)"),
                        "prepaids_and_other_current": (opening["prepaids_and_other_current"],
                                                       prepaid_balance(led, cutoff), "unamortized annual contracts")}
            notes: dict[str, str] = {}
            for key, (file_balance, subledger_balance, what) in restated.items():
                moved = file_balance - subledger_balance
                opening[key] = subledger_balance
                # Restating a liability down (or an asset up) uses cash; the other way frees it.
                opening["cash"] += moved if key not in CREDIT_NORMAL else -moved
                notes[key] = (f"restated from {file_balance:,.2f} in {version}_balance_sheet.csv to the "
                              f"{what} at {cutoff} month end; opening cash moves by {moved:,.2f}")
                log.append({"version": version, "period": cutoff, "line": key, "action": "opening restated",
                            "detail": notes[key], "amount": f"{-moved:.2f}"})
            opening["accounts_payable"] -= accrued0
            # The lease lines replace the file's deferred rent (or, once synced, the lease lines it holds) without
            # moving cash or equity.
            file_other_assets = num(bs[cutoff].get(SYNCED_COLUMN))
            carved = file_accrued + lease0 - rou0 + file_other_assets
            opening["other_liabilities"] -= carved
            opening.update({"accrued_expenses": accrued0, "operating_lease_liabilities": lease0,
                            "operating_lease_rou": rou0})
            notes["other_liabilities"] = (f"less {carved:,.2f}: lease liabilities {lease0:,.2f} less right-of-use "
                                          f"assets {rou0:,.2f}"
                                          + (f", plus the file's other assets {file_other_assets:,.2f} and accrued "
                                             f"expenses {file_accrued:,.2f}" if synced else " (deferred rent)"))
            notes["accrued_expenses"] = f"services through {cutoff} billed after it"
            notes["operating_lease_liabilities"] = "remaining lease payments discounted"
            notes["operating_lease_rou"] = "lease liability less cumulative straight-line cost over payments"
            sources = {"accrued_expenses": f"{version}_accrued_expenses_rollforward.csv",
                       "operating_lease_liabilities": f"{version}_operating_lease_schedule.csv",
                       "operating_lease_rou": f"{version}_operating_lease_schedule.csv"}
            log.append({"version": version, "period": cutoff, "line": "other_liabilities", "action": "opening split",
                        "detail": notes["other_liabilities"], "amount": f"{carved:.2f}"})
            for key, bal in opening.items():
                source = sources.get(key, f"{version}_balance_sheet.csv")
                note = f"Opening balance at {cutoff} month end, from {source}"
                if key in notes:
                    note += f"; {notes[key]}"
                elif key == "cash":
                    note += "; moved by the AP and prepaid restatements"
                w.add(cutoff, key, -bal if key in CREDIT_NORMAL else bal, label="opening",
                      source_file=source, source_system="Opening Balance", note=note)
            for r in w.rows:
                running[KEY_BY_NUMBER[r["account_number"]]] += _natural(KEY_BY_NUMBER[r["account_number"]], num(r["amount"]))
            actual_running[cutoff] = dict(running)
            periods = periods[1:]
        else:
            running.update(actual_running.get(_prior(periods[0]), {}))

        for p in periods:
            before = len(w.rows)
            prior = bs.get(_prior(p)) or actual_bs.get(_prior(p))
            cur = bs[p]

            def change(key: str) -> Decimal:
                return num(cur.get(key)) - num(prior.get(key))

            def subledger(sched, key, begin_col, end_col, legs, file_label):
                row = sched.get(p)
                gl_begin = running[key]
                if row and not all(c in row for c in [begin_col, end_col, *(col for _, col, _ in legs)]):
                    reason = f"layout differs ({', '.join(k for k in row if k not in ('organization_id', 'version', 'period'))})"
                    amt = change(key)
                    w.add(p, key, -amt if key in CREDIT_NORMAL else amt, label="net_change",
                          source_file=f"{version}_balance_sheet.csv",
                          note=f"change in {version}_balance_sheet.csv ({file_label} not used: {reason})")
                    log.append({"version": version, "period": p, "line": key, "action": "balance sheet change",
                                "detail": f"{file_label} not used: {reason}", "amount": f"{amt:.2f}"})
                    return
                if row and abs(num(row[begin_col]) - gl_begin) <= TIE:
                    for label, col, sign in legs:
                        w.add(p, key, sign * num(row[col]), label=label, source_file=file_label,
                              note=f"{label.replace('_', ' ')} from {file_label}")
                    rounding = _natural(key, num(row[end_col]) - gl_begin) - sum(
                        (sign * num(row[col]) for _, col, sign in legs), Decimal("0"))
                    if rounding:
                        w.add(p, key, rounding, label="rounding", source_file=file_label,
                              note=f"cents between the GL balance and {file_label}")
                    return
                if row:
                    amt = num(row[end_col]) - gl_begin
                    w.add(p, key, _natural(key, amt), label="net_change", source_file=file_label,
                          note=f"move to the ending balance in {file_label}; it starts at "
                               f"{num(row[begin_col]):,.2f}, not the GL balance {gl_begin:,.2f}")
                    log.append({"version": version, "period": p, "line": key, "action": "schedule ending",
                                "detail": f"{file_label} starts {num(row[begin_col]):,.2f}, GL balance {gl_begin:,.2f}; "
                                          f"posted the move to its ending {num(row[end_col]):,.2f}",
                                "amount": f"{amt:.2f}"})
                    return
                reason = "no schedule row"
                amt = change(key)
                w.add(p, key, -amt if key in CREDIT_NORMAL else amt, label="net_change",
                      source_file=f"{version}_balance_sheet.csv",
                      note=f"change in {version}_balance_sheet.csv ({file_label} not used: {reason})")
                log.append({"version": version, "period": p, "line": key, "action": "balance sheet change",
                            "detail": f"{file_label} not used: {reason}", "amount": f"{amt:.2f}"})

            subledger(ar, "accounts_receivable", "beginning_accounts_receivable", "ending_accounts_receivable",
                      [("billings", "new_billings", 1), ("collections", "cash_collections", -1)],
                      f"{version}_accounts_receivable_rollforward.csv")
            sbc_amt, sbc_file = stock_comp(p)
            if sbc_file.endswith("_cash_flow_statement.csv"):
                log.append({"version": version, "period": p, "line": "apic_sbc", "action": "source",
                            "detail": f"{version}_SBC_Schedule.csv has no total_sbc in the 1%-of-revenue layout; "
                                      f"stock comp from {sbc_file}", "amount": f"{sbc_amt:.2f}"})

            post_vendor_ledger(w, led, p)
            post_accruals_and_leases(w, led, p)

            if p in dc:
                row = dc[p]
                gl_begin = sum((running[k] for k in DEFERRED_COMMISSION_LINES), Decimal("0"))
                if abs(num(row["beginning_deferred_commissions"]) - gl_begin) > TIE:
                    raise ValueError(f"{version} {p}: {dc_file} starts {num(row['beginning_deferred_commissions']):,.2f}, "
                                     f"GL deferred commissions {gl_begin:,.2f}")
                amort = num(row["commission_amortization"])
                w.add(p, "deferred_commissions_noncurrent", num(row["capitalized_commissions"]), label="capitalized",
                      source_file=dc_file, note=f"commission payouts capitalized (ASC 340-40) from {dc_file}")
                w.add(p, "deferred_commissions_current", -amort, label="amortization", source_file=dc_file,
                      note=f"amortization to 6200 Sales Commissions from {dc_file}")
                reclass = num(row["current_portion"]) - (running["deferred_commissions_current"] - amort)
                w.add(p, "deferred_commissions_current", reclass, label="reclass_current", source_file=dc_file,
                      note=f"current portion = next 12 months' amortization ({dc_file})")
                w.add(p, "deferred_commissions_noncurrent", -reclass, label="reclass_current", source_file=dc_file,
                      note=f"current portion = next 12 months' amortization ({dc_file})")

            da = da_total[p]
            w.add(p, "ppe_net", -da, label="depreciation", source_file=f"{version}_gl_detail.csv",
                  department=NON_CASH_DEPT, note="depreciation and amortization from this month's GL D&A")
            additions = change("ppe_net") + da
            w.add(p, "ppe_net", additions, label="additions", source_file=f"{version}_balance_sheet.csv",
                  note=f"additions = change in PP&E in {version}_balance_sheet.csv plus D&A")
            if p in cf and abs(additions + num(cf[p]["capital_expenditures"])) > TIE:
                log.append({"version": version, "period": p, "line": "ppe_net", "action": "note",
                            "detail": f"cash flow statement capex {num(cf[p]['capital_expenditures']):,.2f}; "
                                      f"balance sheet additions {additions:,.2f}", "amount": f"{additions:.2f}"})

            for key in ("deferred_revenue", "debt"):
                amt = change(key)
                w.add(p, key, -amt if key in CREDIT_NORMAL else amt, label="net_change",
                      source_file=f"{version}_balance_sheet.csv", note=f"change in {version}_balance_sheet.csv")
            amt = other_liabilities(cur, p) - other_liabilities(prior, _prior(p))
            w.add(p, "other_liabilities", -amt, label="net_change", source_file=f"{version}_balance_sheet.csv",
                  note=f"change in other liabilities in {version}_balance_sheet.csv, less accrued expenses and lease "
                       f"liabilities")

            w.add(p, "apic_sbc", -sbc_amt, label="stock_comp", source_file=sbc_file, department=NON_CASH_DEPT,
                  note=f"stock comp (non-cash) from {sbc_file}; expense on 5040 / 6140")

            if p in cf:
                raised = num(cf[p]["debt_issuance_repayment"]) - change("debt")
                if raised:
                    w.add(p, "equity", -raised, label="equity_raise", source_file=f"{version}_cash_flow_statement.csv",
                          note=f"equity raise: financing in {version}_cash_flow_statement.csv with no change in debt")
                    log.append({"version": version, "period": p, "line": "equity", "action": "equity raise",
                                "detail": "financing shown on the debt line of the cash flow statement; debt did not change",
                                "amount": f"{raised:.2f}"})

            other = sum((num(r["amount"]) for r in w.rows[before:]), Decimal("0")) + pl_total[p]
            w.add(p, "cash", -other, label="net_cash", source_file=f"{version}_gl_detail.csv",
                  note="cash: other side of this month's entries")
            for r in w.rows[before:]:
                key = KEY_BY_NUMBER[r["account_number"]]
                running[key] += _natural(key, num(r["amount"]))
            if version == OPENING_VERSION:
                actual_running[p] = dict(running)

        out[version] = w.rows
    return out, log


def _held(src: str, version: str) -> dict[str, tuple[Decimal, Decimal]]:
    """{month: (accrued expenses, lease liabilities)} from the dataset's own files (empty when it has none)."""
    acc = os.path.join(src, f"{version}_accrued_expenses_rollforward.csv")
    if not os.path.exists(acc):
        return {}
    accrued = {r["period"][:7]: num(r["ending_accrued_expenses"]) for r in _read(acc)}
    lease: dict[str, Decimal] = defaultdict(Decimal)
    for r in _read(os.path.join(src, f"{version}_operating_lease_schedule.csv")):
        lease[r["period"][:7]] += num(r["ending_lease_liability"])
    return {p: (a, lease.get(p, Decimal("0"))) for p, a in accrued.items()}


def post_vendor_ledger(w: Writer, led: Ledger, p: str) -> None:
    """AP and prepaid activity for month ``p``. Record ids end in vendor_accruals / vendor_payments (AP) and
    additions / amortization (prepaids)."""
    actual = w.version == "Actual"
    bills_file = "Actual_vendor_bills.csv" if actual else f"{w.version}_vendor_spend_plan.csv"
    schedule = f"{w.version}_Prepaid_Amortization_Schedule.csv"
    billed = bills_in(led, p)
    paid = payments_in(led, p)
    if actual:
        for b in billed:
            w.add(p, "accounts_payable", -b.total, label="vendor_accruals", source_file=bills_file, record=b.id,
                  vendor_id=b.vendor, source_system="AP", note=f"bill {b.number} dated {b.bill_date.isoformat()}")
        runs: dict[str, list] = defaultdict(list)
        for b in paid:
            runs[b.payment_id].append(b)
        for pid, bills in sorted(runs.items()):
            w.add(p, "accounts_payable", sum((b.total for b in bills), Decimal("0")), label="vendor_payments",
                  source_file="Actual_vendor_payments.csv", record=pid, vendor_id=bills[0].vendor, source_system="AP",
                  note=f"payment {bills[0].paid_date.isoformat()}: {', '.join(b.number for b in bills)}")
        for c in led.contracts:
            if c.start == p:
                w.add(p, "prepaids_and_other_current", c.amount, label="additions", source_file=schedule, record=c.id,
                      vendor_id=c.vendor, source_system="AP", note=f"{c.description}: billed for {c.months} months")
            amort = c.amortization(p)
            if amort:
                w.add(p, "prepaids_and_other_current", -amort, label="amortization", source_file=schedule,
                      record=f"{c.id}-{p}", vendor_id=c.vendor, source_system="AP",
                      note=f"{c.description}: amortization to {c.account}")
        return
    w.add(p, "accounts_payable", -sum((b.total for b in billed), Decimal("0")), label="vendor_accruals",
          source_file=bills_file, note=f"{len(billed)} planned vendor bills")
    w.add(p, "accounts_payable", sum((b.total for b in paid), Decimal("0")), label="vendor_payments",
          source_file=bills_file, note=f"{len(paid)} planned vendor bills paid")
    w.add(p, "prepaids_and_other_current", sum((c.amount for c in led.contracts if c.start == p), Decimal("0")),
          label="additions", source_file=schedule, note="annual contracts billed up front")
    w.add(p, "prepaids_and_other_current", -sum((c.amortization(p) for c in led.contracts), Decimal("0")),
          label="amortization", source_file=schedule, note="amortization of prepaid contracts")


def post_accruals_and_leases(w: Writer, led: Ledger, p: str) -> None:
    """Accrued expenses (2050) and operating leases (1600 / 2060) for month ``p``. Accrued record ids end in
    accrued / billed; lease ids in new_lease (non-cash), lease_payments, accretion and amortization (non-cash)."""
    actual = w.version == "Actual"
    roll = f"{w.version}_accrued_expenses_rollforward.csv"
    accrued, billed = accrual_moves(led, p)
    if actual:
        by_bill: dict[str, list] = defaultdict(list)
        for b, _, ln in accrued:
            by_bill[b.id].append((b, ln))
        for items in by_bill.values():
            b = items[0][0]
            w.add(p, "accrued_expenses", -sum((ln.amount for _, ln in items), Decimal("0")), label="accrued",
                  source_file="Actual_accrued_expenses_detail.csv", record=f"ACCR-{p.replace('-', '')}-{b.vendor}",
                  vendor_id=b.vendor, source_system="AP", note=f"services in {p} not billed by month end")
        by_bill = defaultdict(list)
        for b, _, ln in billed:
            by_bill[b.id].append((b, ln))
        for bid, items in by_bill.items():
            b = items[0][0]
            w.add(p, "accrued_expenses", sum((ln.amount for _, ln in items), Decimal("0")), label="billed",
                  source_file="Actual_vendor_bills.csv", record=bid, vendor_id=b.vendor, source_system="AP",
                  note=f"bill {b.number} dated {b.bill_date.isoformat()} for services accrued earlier")
    else:
        w.add(p, "accrued_expenses", -sum((ln.amount for _, _, ln in accrued), Decimal("0")), label="accrued",
              source_file=roll, note="services in the month billed after it")
        w.add(p, "accrued_expenses", sum((ln.amount for _, _, ln in billed), Decimal("0")), label="billed",
              source_file=roll, note="earlier months' accrued services billed")

    schedule = f"{w.version}_operating_lease_schedule.csv"
    for lease in LEASES:
        m = lease.at(p)
        if m is None:
            continue
        kw = {"source_file": schedule, "vendor_id": lease.vendor, "source_system": "AP"}
        rec = f"{lease.id}-{p}"
        w.add(p, "operating_lease_rou", m.new_liability, label="new_lease", record=rec, department=NON_CASH_DEPT,
              note=f"{lease.description}: right-of-use asset at commencement (non-cash)", **kw)
        w.add(p, "operating_lease_liabilities", -m.new_liability, label="new_lease", record=rec,
              department=NON_CASH_DEPT, note=f"{lease.description}: lease liability at commencement (non-cash)", **kw)
        w.add(p, "operating_lease_liabilities", m.payment, label="lease_payments", record=rec,
              note=f"{lease.description}: rent billed for {p}", **kw)
        w.add(p, "operating_lease_liabilities", -m.accretion, label="accretion", record=rec,
              note=f"{lease.description}: interest on the lease liability, part of the straight-line cost", **kw)
        w.add(p, "operating_lease_rou", -m.rou_amortization, label="amortization", record=rec,
              department=NON_CASH_DEPT,
              note=f"{lease.description}: right-of-use amortization, the rest of the straight-line cost (non-cash)",
              **kw)


def balances(rows_by_version: dict[str, list[dict[str, str]]], gl_by_version: dict[str, list[dict[str, str]]]):
    """Month-end balance sheet lines per version from GL rows: opening + activity, equity incl. GL net income."""
    actual_rows = rows_by_version["Actual"]
    cutoff = min(r["period"] for r in actual_rows if r["source_system"] == "Opening Balance")
    result: dict[str, dict[str, dict[str, Decimal]]] = {}
    for version in rows_by_version:
        chain_start = CHAIN_FROM_ACTUAL.get(version)
        bs_rows = [r for r in actual_rows if not chain_start or r["period"] < chain_start]
        pl_rows = [r for r in gl_by_version["Actual"] if is_pl(r) and (not chain_start or r["period"][:7] < chain_start)]
        if version != "Actual":
            bs_rows += rows_by_version[version]
            pl_rows += [r for r in gl_by_version[version] if is_pl(r)]
        act: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
        key_by_number = {v[0]: k for k, v in ACCOUNTS.items()}
        for r in bs_rows:
            act[r["period"][:7]][key_by_number[r["account_number"]]] += num(r["amount"])
        for r in pl_rows:
            if r["period"][:7] > cutoff:
                act[r["period"][:7]]["net_income"] -= num(r["amount"])
        running: dict[str, Decimal] = defaultdict(Decimal)
        months = {}
        for p in sorted(act):
            for k, v in act[p].items():
                running[k] += v
            line = {k: (-running[k] if k in CREDIT_NORMAL else running[k]) for k in ACCOUNTS}
            line["retained_earnings"] = running["net_income"] - act[p]["net_income"]
            line["net_income"] = act[p]["net_income"]
            line["total_equity"] = line["equity"] + line["apic_sbc"] + running["net_income"]
            months[p] = line
        result[version] = months
    return result


def check_against_statements(src: str, bal: dict[str, dict[str, dict[str, Decimal]]]) -> list[dict[str, str]]:
    rows = []
    for version, months in bal.items():
        bs = _by_period(os.path.join(src, f"{version}_balance_sheet.csv"))
        for p, line in sorted(months.items()):
            if p not in bs:
                continue
            for key in [*STATEMENT_LINES, "equity"]:
                gl_value = line["total_equity"] if key == "equity" else statement_value(line, key)
                diff = gl_value - num(bs[p].get(key))
                rows.append({"version": version, "period": p, "line": key,
                             "gl": f"{gl_value:.2f}", "statement": f"{num(bs[p].get(key)):.2f}", "difference": f"{diff:.2f}"})
    return rows
