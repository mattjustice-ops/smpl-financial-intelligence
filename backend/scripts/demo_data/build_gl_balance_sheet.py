"""Balance sheet GL activity for the demo, built from the dataset's own files.

Method (financial_dashboard_cf_re_logic.md): the GL holds an opening trial balance at the
    month end before the first Actual month (Dec 31, 2023) and every month's activity after it, the
    first month included. Balances are opening + cumulative activity. Retained earnings is never
    posted; it is computed from GL net income.

Where each balance sheet row comes from:
  * Opening balances (the first month's beginning balances, _opening_balances): each subledger line
    opens on its balance at the opening month end (AR and allowance rollforwards, the vendor ledger's
    open bills, unamortized contracts and unbilled services, the lease schedule, the deferred
    commissions rollforward with its current portion from the commission schedule, the deferred
    revenue waterfall). PP&E, debt and other liabilities (2600) open on the first month's balance
    sheet less the month's movement in its cash flow statement. Equity is one total in the dataset:
    the first month's equity less its net income and stock comp, on account 3000 with no split.
    Cash is the other side, so the opening trial balance nets to zero.
  * Accounts receivable: AR rollforward (billings, collections, write-offs). The allowance for doubtful
    accounts (1110, contra AR) from the allowance rollforward: the provision is credited (6560 is the debit),
    write-offs are debited. The balance sheet file's AR is net of it.
  * Accounts payable and prepaids (Oct 9 2026): the vendor ledger (vendor_model.py). Bills credit AP
    (Actual: one row per bill with the vendor; Budget and Forecast: one row a month), payments debit
    it (Actual: one row per payment run and vendor). Annual contracts paid up front debit 1200 when
    billed and amortize monthly to their expense account.
  * Accrued expenses (2050): services billed in arrears are accrued in the month of service and relieved when
    the bill posts to AP (Actual: one row per vendor accrual and per bill).
  * Operating leases (ASC 842, vendor_model.LEASES): the right-of-use asset (1600) and lease liability (2060)
    are recognized at commencement (non-cash, "Balance Sheet Activity"); rent bills reduce the liability,
    interest accretes on it, and the right-of-use asset amortizes by the rest of the straight-line cost
    (non-cash). A balance sheet file without other_assets holds the liability less the asset (deferred rent) in
    its other liabilities, so 2600 is measured net of it, with no cash move. The balance sheet file shows the
    asset as other_assets and both new liabilities in other_liabilities (STATEMENT_LINES).
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
from decimal import ROUND_HALF_UP, Decimal

from vendor_model import (LEASES, VENDORS, Ledger, accrual_moves, accrued_balance, ap_balance, bills_in,  # noqa: E402
                          last_day, lease_balances, open_bills, payments_in, prepaid_balance)

CENT = Decimal("0.01")
TIE = Decimal("1.00")
NON_CASH_DEPT = "Balance Sheet Activity"

ACCOUNTS = {
    "cash": ("1000", "Cash", "Assets", "Cash", "Cash"),
    "accounts_receivable": ("1100", "Accounts Receivable", "Assets", "AR", "Accounts Receivable"),
    "allowance_for_doubtful_accounts": ("1110", "Allowance for Doubtful Accounts", "Assets", "AR",
                                        "Accounts Receivable"),
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
                 "other_liabilities", "equity", "apic_sbc", "allowance_for_doubtful_accounts"}
# Credit-normal lines shown inside an asset column: they reduce it.
CONTRA = {"allowance_for_doubtful_accounts"}
BALANCE_LINES = ["cash", "accounts_receivable", "prepaids_and_other_current", "deferred_commissions_current", "ppe_net",
                 "deferred_commissions_noncurrent", "accounts_payable", "deferred_revenue", "debt", "other_liabilities",
                 "equity"]
# Balance sheet file columns that hold more than one GL line (the app's other assets / other liabilities).
STATEMENT_LINES = {**{k: (k,) for k in BALANCE_LINES if k != "equity"},
                   "accounts_receivable": ("accounts_receivable", "allowance_for_doubtful_accounts"),
                   "other_assets": ("operating_lease_rou",),
                   "other_liabilities": ("other_liabilities", "accrued_expenses", "operating_lease_liabilities")}
# sync_v5_statements.py writes other_assets; a balance sheet file with that column has the accrued expenses and
# lease liabilities in its other_liabilities. One without it predates them (ASC 840: deferred rent, not a lease
# liability).
SYNCED_COLUMN = "other_assets"
DEFERRED_COMMISSION_LINES = ("deferred_commissions_current", "deferred_commissions_noncurrent")

# source_system: the subledger or journal that posts the row.
AP_SOURCE = "AP"
AR_SOURCE = "AR"
REVENUE_SOURCE = "Revenue Recognition"
COMMISSION_SOURCE = "Commissions"
FIXED_ASSET_SOURCE = "Fixed Assets"
EQUITY_SOURCE = "Equity"
BANK_SOURCE = "Bank"
JOURNAL_SOURCE = "Journal Entry"
OPENING_SOURCE = "Opening Balance"

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


def _month_index(period: str) -> int:
    return int(period[:4]) * 12 + int(period[5:7]) - 1


def _add_months(period: str, n: int) -> str:
    i = _month_index(period) + n
    return f"{i // 12}-{i % 12 + 1:02d}"


def commission_current_portion(src: str, version: str, as_of: str, balance: Decimal) -> Decimal:
    """Deferred commissions current portion at ``as_of`` month end: the next 12 months' straight-line amortization of
    the capitalized cohorts in the commission schedule paid through ``as_of`` (cumulative amortization rounded to the
    cent, as the rollforward does). Raises unless those cohorts leave ``balance``."""
    path = os.path.join(src, f"{version}_commission_schedule.csv")
    if not os.path.exists(path):
        raise ValueError(f"{version} {as_of}: deferred commissions open at {balance:,.2f} but there is no "
                         f"{version}_commission_schedule.csv to split them into current and noncurrent")
    cohorts = [(r["period"][:7], num(r["capitalized_amount"]), int(r["amortization_months"]))
               for r in _read(path) if r["capitalize"] == "Y" and r["period"][:7] <= as_of]

    def amortized(through: str) -> Decimal:
        total = sum((amt * min(max(_month_index(through) - _month_index(p) + 1, 0), n) / n for p, amt, n in cohorts),
                    Decimal("0"))
        return total.quantize(CENT, ROUND_HALF_UP)

    left = sum((amt for _, amt, _ in cohorts), Decimal("0")).quantize(CENT, ROUND_HALF_UP) - amortized(as_of)
    if abs(left - balance) > TIE:
        raise ValueError(f"{version} {as_of}: {version}_commission_schedule.csv cohorts leave {left:,.2f} of deferred "
                         f"commissions, the rollforward begins the next month at {balance:,.2f}")
    return amortized(_add_months(as_of, 12)) - amortized(as_of)


def is_pl(row: dict[str, str]) -> bool:
    return row["statement"] != "Balance Sheet"


def is_da(row: dict[str, str]) -> bool:
    return row["statement_category"] == "D&A" or row["account_group"] == "D&A"


def is_interest(row: dict[str, str]) -> bool:
    return row.get("statement_category") == "Interest" or row.get("account_group") == "Interest"


class Writer:
    def __init__(self, org: str, version: str):
        self.org, self.version = org, version
        self.rows: list[dict[str, str]] = []

    def add(self, period: str, key: str, amount: Decimal, *, label: str, source_file: str,
            source_system: str, department: str = "", note: str = "", record: str = "",
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
    return sum((-line[k] if k in CONTRA else line[k] for k in STATEMENT_LINES[column]), Decimal("0"))


def _opening_balances(src: str, version: str, first: str, row: dict[str, str], cf_row: dict[str, str] | None,
                      ar_row: dict[str, str] | None, allow_row: dict[str, str] | None, dc_row: dict[str, str] | None,
                      led: Ledger, held_first: tuple[Decimal, Decimal] | None, *, da: Decimal, net_income: Decimal,
                      stock_comp: Decimal, other_liabilities_first: Decimal):
    """Balances at the month end before ``first``: {line: (natural balance, source file, note)}, and the balance sheet
    file columns at that month end that ``first``'s net changes are measured from."""
    cutoff = _prior(first)
    dr_file = f"{version}_deferred_revenue_waterfall.csv"
    dr_row = _by_period(os.path.join(src, dr_file)).get(first)
    for name, r in ((f"{version}_cash_flow_statement.csv", cf_row), (f"{version}_accounts_receivable_rollforward.csv",
                                                                       ar_row), (dr_file, dr_row)):
        if r is None:
            raise ValueError(f"{version} {first}: no {name} row; the {cutoff} opening balances need its {first} "
                             f"beginning balance or movement")
    bs_file, cf_file = f"{version}_balance_sheet.csv", f"{version}_cash_flow_statement.csv"
    lease_open, rou_open = lease_balances(cutoff)
    lease_first, rou_first = lease_balances(first)
    accrued_open, accrued_first = accrued_balance(led, cutoff), accrued_balance(led, first)
    new_lease = sum((m.new_liability for m in (lease.at(first) for lease in LEASES) if m is not None), Decimal("0"))
    synced = SYNCED_COLUMN in row
    # 2600 at the first month end: the file's other liabilities less the accrued expenses, lease liabilities and
    # right-of-use assets it holds once synced, else less the deferred rent (lease liability less right-of-use asset).
    if synced:
        if held_first is None:
            raise ValueError(f"{version} {first}: the balance sheet file has {SYNCED_COLUMN} but the dataset has no "
                             f"accrued expense or lease schedule row for the month")
        carved = held_first[0] + lease_first - rou_first + num(row.get(SYNCED_COLUMN))
    else:
        carved = lease_first - rou_first
    other_first = num(row.get("other_liabilities")) - carved
    # A synced cash flow statement's change in other liabilities holds the accrued expense and lease liability moves
    # (without new leases); 2600's own change is the rest.
    other_move = num(cf_row.get("change_in_other_liabilities"))
    if synced:
        other_move += new_lease - (accrued_first - accrued_open) - (lease_first - lease_open)
    ppe = num(row["ppe_net"]) + num(cf_row.get("capital_expenditures")) + da
    debt = num(row["debt"]) - num(cf_row.get("debt_issuance_repayment"))
    deferred_revenue = num(dr_row["beginning_deferred_revenue"])
    out = {
        "accounts_receivable": (num(ar_row["beginning_accounts_receivable"]),
                                f"{version}_accounts_receivable_rollforward.csv", "gross accounts receivable"),
        "prepaids_and_other_current": (prepaid_balance(led, cutoff), f"{version}_Prepaids_Rollforward.csv",
                                       "annual contracts not yet amortized"),
        "accounts_payable": (ap_balance(led, cutoff), "Actual_vendor_bills.csv",
                             f"{len(open_bills(led.bills, last_day(cutoff)))} vendor bills open"),
        "accrued_expenses": (accrued_open, f"{version}_accrued_expenses_rollforward.csv",
                             f"services through {cutoff} billed after it"),
        "operating_lease_liabilities": (lease_open, f"{version}_operating_lease_schedule.csv",
                                        "remaining lease payments discounted"),
        "operating_lease_rou": (rou_open, f"{version}_operating_lease_schedule.csv",
                                "lease liability less cumulative straight-line cost over payments"),
        "deferred_revenue": (deferred_revenue, dr_file, "billed, not yet recognized"),
        "ppe_net": (ppe, bs_file, f"{first} PP&E less its capital expenditures ({cf_file}) plus its D&A"),
        "debt": (debt, bs_file, f"{first} debt less its issuance and repayment ({cf_file})"),
        "other_liabilities": (other_first - other_move, bs_file,
                              f"{first} other liabilities less accrued expense and lease lines ({other_first:,.2f}) "
                              f"less its change in {cf_file} ({other_move:,.2f})"),
        "equity": (num(row["equity"]) - net_income - stock_comp, bs_file,
                   f"{first} equity less its net income ({net_income:,.2f}) and stock comp ({stock_comp:,.2f})"),
    }
    if allow_row is not None:
        out["allowance_for_doubtful_accounts"] = (num(allow_row["beginning_allowance"]),
                                                  f"{version}_allowance_for_doubtful_accounts.csv",
                                                  "allowance for doubtful accounts (contra AR)")
    if dc_row is not None:
        total = num(dc_row["beginning_deferred_commissions"])
        current = commission_current_portion(src, version, cutoff, total)
        dc_file = f"{version}_deferred_commissions_rollforward.csv"
        out["deferred_commissions_current"] = (current, dc_file, f"next 12 months' amortization of the cohorts in "
                                                                 f"{version}_commission_schedule.csv")
        out["deferred_commissions_noncurrent"] = (total - current, dc_file, "the rest of the capitalized commissions")
    cash = -sum((-b if k in CREDIT_NORMAL else b for k, (b, _, _) in out.items()), Decimal("0"))
    out["cash"] = (cash, f"{version}_gl_detail.csv", "the other side of the opening balances")
    prior_columns = {"ppe_net": ppe, "deferred_revenue": deferred_revenue, "debt": debt,
                     "other_liabilities": other_liabilities_first - other_move}
    return out, prior_columns


def build_balance_sheet_rows(src: str, gl_by_version: dict[str, list[dict[str, str]]], ledgers: dict[str, Ledger]):
    """Return {version: balance sheet rows} and a log of every choice made."""
    org = next(r["organization_id"] for r in gl_by_version["Actual"])
    actual_bs = _by_period(os.path.join(src, "Actual_balance_sheet.csv"))
    out: dict[str, list[dict[str, str]]] = {}
    log: list[dict[str, str]] = []
    actual_running: dict[str, dict[str, Decimal]] = {}
    # Balance sheet file columns at the opening month end, which the first month's changes are measured from.
    opening_prior: dict[str, dict[str, Decimal]] = {}
    held_actual = _held(src, "Actual")

    for version, gl_rows in gl_by_version.items():
        bs = _by_period(os.path.join(src, f"{version}_balance_sheet.csv"))
        cf = _by_period(os.path.join(src, f"{version}_cash_flow_statement.csv"))
        ar = _by_period(os.path.join(src, f"{version}_accounts_receivable_rollforward.csv"))
        allow_file = f"{version}_allowance_for_doubtful_accounts.csv"
        allow = _by_period(os.path.join(src, allow_file))
        sbc = _by_period(os.path.join(src, f"{version}_SBC_Schedule.csv"))
        dc_file = f"{version}_deferred_commissions_rollforward.csv"
        dc = _by_period(os.path.join(src, dc_file))
        led = ledgers[version]
        w = Writer(org, version)

        pl_total: dict[str, Decimal] = defaultdict(Decimal)
        da_total: dict[str, Decimal] = defaultdict(Decimal)
        interest_total: dict[str, Decimal] = defaultdict(Decimal)
        for r in gl_rows:
            if is_pl(r):
                pl_total[r["period"][:7]] += num(r["amount"])
                if is_da(r):
                    da_total[r["period"][:7]] += num(r["amount"])
                if is_interest(r):
                    interest_total[r["period"][:7]] += num(r["amount"])

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
            first = periods[0]
            cutoff = _prior(first)
            opening, opening_prior[cutoff] = _opening_balances(
                src, version, first, bs[first], cf.get(first), ar.get(first), allow.get(first), dc.get(first), led,
                held_actual.get(first), da=da_total[first], net_income=-pl_total[first],
                stock_comp=stock_comp(first)[0], other_liabilities_first=other_liabilities(bs[first], first))
            stated = num(cf[first].get("beginning_cash"))
            log.append({"version": version, "period": cutoff, "line": "cash", "action": "opening cash",
                        "detail": f"the other side of the opening balances; {version}_cash_flow_statement.csv begins "
                                  f"{first} at {stated:,.2f}", "amount": f"{opening['cash'][0] - stated:.2f}"})
            for key, (bal, source, note) in opening.items():
                w.add(cutoff, key, -bal if key in CREDIT_NORMAL else bal, label="opening", source_file=source,
                      source_system=OPENING_SOURCE,
                      note=f"Opening balance at {cutoff} month end ({first} beginning balance), from {source}: {note}")
            for r in w.rows:
                running[KEY_BY_NUMBER[r["account_number"]]] += _natural(KEY_BY_NUMBER[r["account_number"]], num(r["amount"]))
            actual_running[cutoff] = dict(running)
        else:
            running.update(actual_running.get(_prior(periods[0]), {}))

        for p in periods:
            before = len(w.rows)
            prior = bs.get(_prior(p)) or actual_bs.get(_prior(p)) or opening_prior.get(_prior(p))
            cur = bs[p]

            def change(key: str) -> Decimal:
                return num(cur.get(key)) - num(prior.get(key))

            def subledger(sched, key, begin_col, end_col, legs, file_label, system):
                row = sched.get(p)
                gl_begin = running[key]
                if row and not all(c in row for c in [begin_col, end_col, *(col for _, col, _ in legs)]):
                    reason = f"layout differs ({', '.join(k for k in row if k not in ('organization_id', 'version', 'period'))})"
                    amt = change(key)
                    w.add(p, key, -amt if key in CREDIT_NORMAL else amt, label="net_change",
                          source_file=f"{version}_balance_sheet.csv", source_system=JOURNAL_SOURCE,
                          note=f"change in {version}_balance_sheet.csv ({file_label} not used: {reason})")
                    log.append({"version": version, "period": p, "line": key, "action": "balance sheet change",
                                "detail": f"{file_label} not used: {reason}", "amount": f"{amt:.2f}"})
                    return
                if row and abs(num(row[begin_col]) - gl_begin) <= TIE:
                    for label, col, sign in legs:
                        w.add(p, key, sign * num(row[col]), label=label, source_file=file_label, source_system=system,
                              note=f"{label.replace('_', ' ')} from {file_label}")
                    rounding = _natural(key, num(row[end_col]) - gl_begin) - sum(
                        (sign * num(row[col]) for _, col, sign in legs), Decimal("0"))
                    if rounding:
                        w.add(p, key, rounding, label="rounding", source_file=file_label, source_system=system,
                              note=f"cents between the GL balance and {file_label}")
                    return
                if row:
                    amt = num(row[end_col]) - gl_begin
                    w.add(p, key, _natural(key, amt), label="net_change", source_file=file_label, source_system=system,
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
                      source_file=f"{version}_balance_sheet.csv", source_system=JOURNAL_SOURCE,
                      note=f"change in {version}_balance_sheet.csv ({file_label} not used: {reason})")
                log.append({"version": version, "period": p, "line": key, "action": "balance sheet change",
                            "detail": f"{file_label} not used: {reason}", "amount": f"{amt:.2f}"})

            ar_legs = [("billings", "new_billings", 1), ("collections", "cash_collections", -1)]
            if "write_offs" in ar.get(p, {}):
                ar_legs.append(("write_offs", "write_offs", -1))
            subledger(ar, "accounts_receivable", "beginning_accounts_receivable", "ending_accounts_receivable",
                      ar_legs, f"{version}_accounts_receivable_rollforward.csv", AR_SOURCE)
            if allow:
                subledger(allow, "allowance_for_doubtful_accounts", "beginning_allowance", "ending_allowance",
                          [("provision", "provision_for_credit_losses", -1), ("write_offs", "write_offs", 1)],
                          allow_file, AR_SOURCE)
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
                dc_kw = {"source_file": dc_file, "source_system": COMMISSION_SOURCE}
                w.add(p, "deferred_commissions_noncurrent", num(row["capitalized_commissions"]), label="capitalized",
                      note=f"commission payouts capitalized (ASC 340-40) from {dc_file}", **dc_kw)
                w.add(p, "deferred_commissions_current", -amort, label="amortization",
                      note=f"amortization to 6200 Sales Commissions from {dc_file}", **dc_kw)
                removed = (num(row.get("clawbacks")) - num(row.get("clawback_amortization_reversal"))
                           + num(row.get("commission_write_downs")))
                w.add(p, "deferred_commissions_noncurrent", -removed, label="no_start_removed",
                      note="no-start commission: unamortized balance clawed back or written down "
                           "(Actual_commission_clawbacks.csv)", **dc_kw)
                reclass = num(row["current_portion"]) - (running["deferred_commissions_current"] - amort)
                w.add(p, "deferred_commissions_current", reclass, label="reclass_current",
                      note=f"current portion = next 12 months' amortization ({dc_file})", **dc_kw)
                w.add(p, "deferred_commissions_noncurrent", -reclass, label="reclass_current",
                      note=f"current portion = next 12 months' amortization ({dc_file})", **dc_kw)

            da = da_total[p]
            w.add(p, "ppe_net", -da, label="depreciation", source_file=f"{version}_gl_detail.csv",
                  source_system=FIXED_ASSET_SOURCE, department=NON_CASH_DEPT,
                  note="depreciation journal: credit to property and equipment for this month's depreciation expense")
            additions = change("ppe_net") + da
            w.add(p, "ppe_net", additions, label="capex", source_file=f"{version}_gl_detail.csv",
                  source_system=FIXED_ASSET_SOURCE,
                  note="capex journal: debit to property and equipment")
            w.add(p, "cash", -additions, label="capex", source_file=f"{version}_gl_detail.csv",
                  source_system=FIXED_ASSET_SOURCE,
                  note="capex journal: credit to cash")
            if p in cf and abs(additions + num(cf[p]["capital_expenditures"])) > TIE:
                log.append({"version": version, "period": p, "line": "ppe_net", "action": "note",
                            "detail": f"cash flow statement capex {num(cf[p]['capital_expenditures']):,.2f}; "
                                      f"capex debit {additions:,.2f}", "amount": f"{additions:.2f}"})

            w.add(p, "deferred_revenue", -change("deferred_revenue"), label="net_change",
                  source_file=f"{version}_balance_sheet.csv", source_system=REVENUE_SOURCE,
                  note=f"change in {version}_balance_sheet.csv")
            debt_change = change("debt")
            w.add(p, "debt", -debt_change, label="issuance" if debt_change > 0 else "repayment",
                  source_file=f"{version}_gl_detail.csv", source_system=JOURNAL_SOURCE,
                  note="debt journal: draw" if debt_change > 0 else "debt journal: repayment")
            amt = other_liabilities(cur, p) - other_liabilities(prior, _prior(p))
            w.add(p, "other_liabilities", -amt, label="net_change", source_file=f"{version}_balance_sheet.csv",
                  source_system=JOURNAL_SOURCE,
                  note=f"change in other liabilities in {version}_balance_sheet.csv, less accrued expenses and lease "
                       f"liabilities")

            w.add(p, "apic_sbc", -sbc_amt, label="stock_comp", source_file=sbc_file, source_system=EQUITY_SOURCE,
                  department=NON_CASH_DEPT, note=f"stock comp (non-cash) from {sbc_file}; expense on 5040 / 6140")

            w.add(p, "cash", -interest_total[p], label="interest_paid", source_file=f"{version}_gl_detail.csv",
                  source_system=JOURNAL_SOURCE,
                  note="interest journal: cash paid for this month's interest expense")

            if p in cf:
                raised = num(cf[p]["debt_issuance_repayment"]) - change("debt")
                if raised:
                    w.add(p, "equity", -raised, label="equity_raise", source_file=f"{version}_cash_flow_statement.csv",
                          source_system=EQUITY_SOURCE,
                          note=f"equity raise: financing in {version}_cash_flow_statement.csv with no change in debt")
                    log.append({"version": version, "period": p, "line": "equity", "action": "equity raise",
                                "detail": "financing shown on the debt line of the cash flow statement; debt did not change",
                                "amount": f"{raised:.2f}"})

            other = sum((num(r["amount"]) for r in w.rows[before:]), Decimal("0")) + pl_total[p]
            w.add(p, "cash", -other, label="net_cash", source_file=f"{version}_gl_detail.csv",
                  source_system=BANK_SOURCE, note="cash: other side of this month's entries")
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
                  vendor_id=b.vendor, source_system=AP_SOURCE, note=f"bill {b.number} dated {b.bill_date.isoformat()}")
        runs: dict[str, list] = defaultdict(list)
        for b in paid:
            runs[b.payment_id].append(b)
        for pid, bills in sorted(runs.items()):
            w.add(p, "accounts_payable", sum((b.total for b in bills), Decimal("0")), label="vendor_payments",
                  source_file="Actual_vendor_payments.csv", record=pid, vendor_id=bills[0].vendor, source_system=AP_SOURCE,
                  note=f"payment {bills[0].paid_date.isoformat()}: {', '.join(b.number for b in bills)}")
        for c in led.contracts:
            if c.start == p:
                w.add(p, "prepaids_and_other_current", c.amount, label="additions", source_file=schedule, record=c.id,
                      vendor_id=c.vendor, source_system=AP_SOURCE, note=f"{c.description}: billed for {c.months} months")
            amort = c.amortization(p)
            if amort:
                w.add(p, "prepaids_and_other_current", -amort, label="amortization", source_file=schedule,
                      record=f"{c.id}-{p}", vendor_id=c.vendor, source_system=AP_SOURCE,
                      note=f"{c.description}: amortization to {c.account}")
        return
    w.add(p, "accounts_payable", -sum((b.total for b in billed), Decimal("0")), label="vendor_accruals",
          source_file=bills_file, source_system=AP_SOURCE, note=f"{len(billed)} planned vendor bills")
    w.add(p, "accounts_payable", sum((b.total for b in paid), Decimal("0")), label="vendor_payments",
          source_file=bills_file, source_system=AP_SOURCE, note=f"{len(paid)} planned vendor bills paid")
    w.add(p, "prepaids_and_other_current", sum((c.amount for c in led.contracts if c.start == p), Decimal("0")),
          label="additions", source_file=schedule, source_system=AP_SOURCE, note="annual contracts billed up front")
    w.add(p, "prepaids_and_other_current", -sum((c.amortization(p) for c in led.contracts), Decimal("0")),
          label="amortization", source_file=schedule, source_system=AP_SOURCE,
          note="amortization of prepaid contracts")


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
                  vendor_id=b.vendor, source_system=AP_SOURCE, note=f"services in {p} not billed by month end")
        by_bill = defaultdict(list)
        for b, _, ln in billed:
            by_bill[b.id].append((b, ln))
        for bid, items in by_bill.items():
            b = items[0][0]
            w.add(p, "accrued_expenses", sum((ln.amount for _, ln in items), Decimal("0")), label="billed",
                  source_file="Actual_vendor_bills.csv", record=bid, vendor_id=b.vendor, source_system=AP_SOURCE,
                  note=f"bill {b.number} dated {b.bill_date.isoformat()} for services accrued earlier")
    else:
        w.add(p, "accrued_expenses", -sum((ln.amount for _, _, ln in accrued), Decimal("0")), label="accrued",
              source_file=roll, source_system=AP_SOURCE, note="services in the month billed after it")
        w.add(p, "accrued_expenses", sum((ln.amount for _, _, ln in billed), Decimal("0")), label="billed",
              source_file=roll, source_system=AP_SOURCE, note="earlier months' accrued services billed")

    schedule = f"{w.version}_operating_lease_schedule.csv"
    for lease in LEASES:
        m = lease.at(p)
        if m is None:
            continue
        kw = {"source_file": schedule, "vendor_id": lease.vendor, "source_system": AP_SOURCE}
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


def journal_cash(rows: list[dict[str, str]]) -> dict[str, dict[str, Decimal]]:
    """Capex debit, interest paid, and financing (debt draws, repayments, equity raises) posted as journals."""
    out: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    ppe = ACCOUNTS["ppe_net"][0]
    for r in rows:
        label = r.get("source_record_id", "").rsplit("-", 1)[-1]
        period = r["period"][:7]
        amount = num(r["amount"])
        if label == "capex" and r["account_number"] == ppe:
            out[period]["capex"] += amount
        elif label == "interest_paid":
            out[period]["interest_paid"] += -amount
        elif label in ("issuance", "repayment", "equity_raise"):
            out[period]["financing"] += -amount
    return out


def balances(rows_by_version: dict[str, list[dict[str, str]]], gl_by_version: dict[str, list[dict[str, str]]]):
    """Month-end balance sheet lines per version from GL rows: opening + activity, equity incl. GL net income."""
    actual_rows = rows_by_version["Actual"]
    cutoff = min(r["period"] for r in actual_rows if r["source_system"] == OPENING_SOURCE)
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
