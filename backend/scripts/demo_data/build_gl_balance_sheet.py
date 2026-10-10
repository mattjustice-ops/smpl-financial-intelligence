"""Balance sheet GL activity for the demo, built from the dataset's own files.

Method (financial_dashboard_cf_re_logic.md): the GL holds an opening trial balance at the
    cutoff (Jan 31, 2024) and monthly activity after it. Balances are opening + cumulative
    activity. Retained earnings is never posted; it is computed from GL net income.

Where each balance sheet row comes from:
  * Opening balances: the cutoff month of Actual_balance_sheet.csv. Equity is one total
    in the dataset, so it opens on account 3000 with no split.
  * Accounts receivable: AR rollforward (billings, collections).
  * Accounts payable (Oct 8 2026): vendor invoices are the month's GL expense other than payroll,
    commissions, D&A, interest and tax, less the month's stock comp and prepaid amortization
    (non-cash / paid when prepaid); they are paid the next month (net 30), so each month pays the
    opening balance. The opening AP is restated to the cutoff month's invoices by the same rule,
    with opening cash moved by the same amount. The AP rollforward file is rewritten from the GL
    (sync_v5_statements.py).
  * Prepaids: prepaids rollforward (additions, amortization).
  * Deferred commissions: deferred commissions rollforward. Capitalized payouts post to
    1550 (noncurrent), amortization comes out of 1250 (current), and a monthly reclass
    keeps 1250 at the next 12 months' amortization.
  * PP&E: depreciation = the month's GL D&A; additions = the balance sheet change plus D&A.
  * Deferred revenue, debt, other liabilities: change in the version's balance sheet file.
  * Stock comp: SBC schedule total, credited to APIC - Stock Compensation as non-cash
    ("Balance Sheet Activity"). The P&L rows already include the expense.
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
    "accounts_payable": ("2000", "Accounts Payable", "Liabilities", "AP", "Accounts Payable"),
    "deferred_revenue": ("2100", "Deferred Revenue", "Liabilities", "Deferred Revenue", "Deferred Revenue"),
    "debt": ("2500", "Debt", "Liabilities", "Debt", "Debt"),
    "other_liabilities": ("2600", "Other Liabilities", "Liabilities", "Other Liabilities", "Other Liabilities"),
    "equity": ("3000", "Equity", "Equity", "Equity", "Equity"),
    "apic_sbc": ("3311", "APIC - Stock Compensation", "Equity", "Equity", "Equity"),
}
CREDIT_NORMAL = {"accounts_payable", "deferred_revenue", "debt", "other_liabilities", "equity", "apic_sbc"}
BALANCE_LINES = ["cash", "accounts_receivable", "prepaids_and_other_current", "deferred_commissions_current", "ppe_net",
                 "deferred_commissions_noncurrent", "accounts_payable", "deferred_revenue", "debt", "other_liabilities",
                 "equity"]
DEFERRED_COMMISSION_LINES = ("deferred_commissions_current", "deferred_commissions_noncurrent")

OPENING_VERSION = "Actual"
CHAIN_FROM_ACTUAL = {"Budget": "2026-01", "Forecast": "2026-07"}

NON_VENDOR_CATEGORIES = frozenset({"revenue", "d&a", "interest", "taxes", "tax"})
NON_VENDOR_EXPENSE_TYPES = frozenset({"salaries and wages", "bonus", "payroll taxes", "retirement match", "benefits",
                                      "severance", "labor", "commissions"})


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


def vendor_spend(gl_rows: list[dict[str, str]]) -> dict[str, Decimal]:
    """Monthly P&L expense billed by vendors: all expense but payroll, commissions, D&A, interest and tax."""
    out: dict[str, Decimal] = defaultdict(Decimal)
    for r in gl_rows:
        if not is_pl(r) or is_da(r) or r["statement_category"].strip().lower() in NON_VENDOR_CATEGORIES:
            continue
        if (r["expense_type"] or "").strip().lower() in NON_VENDOR_EXPENSE_TYPES:
            continue
        out[r["period"][:7]] += num(r["amount"])
    return out


class Writer:
    def __init__(self, org: str, version: str):
        self.org, self.version = org, version
        self.rows: list[dict[str, str]] = []

    def add(self, period: str, key: str, amount: Decimal, *, label: str, source_file: str,
            source_system: str = "Demo Model", department: str = "", note: str = "") -> None:
        if amount == 0:
            return
        number, name, category, group, expense_type = ACCOUNTS[key]
        self.rows.append({
            "organization_id": self.org, "version": self.version, "period": period,
            "account_number": number, "account_name": name, "statement": "Balance Sheet",
            "statement_category": category, "account_group": group, "expense_type": expense_type,
            "department": department, "cost_center": "", "sub_department": "", "vendor_id": "",
            "vendor_name": "", "source_file": source_file,
            "source_record_id": f"{self.version}-{period}-{number}-{label}",
            "amount": f"{amount.quantize(CENT):.2f}", "currency": "USD", "subsidiary": "US Parent",
            "source_system": source_system, "notes": note,
        })


KEY_BY_NUMBER = {v[0]: k for k, v in ACCOUNTS.items()}


def _natural(key: str, amount: Decimal) -> Decimal:
    return -amount if key in CREDIT_NORMAL else amount


def build_balance_sheet_rows(src: str, gl_by_version: dict[str, list[dict[str, str]]]):
    """Return {version: balance sheet rows} and a log of every choice made."""
    org = next(r["organization_id"] for r in gl_by_version["Actual"])
    actual_bs = _by_period(os.path.join(src, "Actual_balance_sheet.csv"))
    out: dict[str, list[dict[str, str]]] = {}
    log: list[dict[str, str]] = []
    actual_running: dict[str, dict[str, Decimal]] = {}

    for version, gl_rows in gl_by_version.items():
        bs = _by_period(os.path.join(src, f"{version}_balance_sheet.csv"))
        cf = _by_period(os.path.join(src, f"{version}_cash_flow_statement.csv"))
        ar = _by_period(os.path.join(src, f"{version}_accounts_receivable_rollforward.csv"))
        ap = _by_period(os.path.join(src, f"{version}_accounts_payable_rollforward.csv"))
        pp = _by_period(os.path.join(src, f"{version}_Prepaids_Rollforward.csv"))
        sbc = _by_period(os.path.join(src, f"{version}_SBC_Schedule.csv"))
        dc_file = f"{version}_deferred_commissions_rollforward.csv"
        dc = _by_period(os.path.join(src, dc_file))
        w = Writer(org, version)

        vendor = vendor_spend(gl_rows)
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

        def invoices(p: str) -> tuple[Decimal, str]:
            sbc_amt, amortized = stock_comp(p)[0], num(pp.get(p, {}).get("prepaid_amortization"))
            amount = vendor[p] - sbc_amt - amortized
            if amount < 0:
                raise ValueError(f"{version} {p}: vendor expense {vendor[p]:,.2f} is less than stock comp {sbc_amt:,.2f} "
                                 f"plus prepaid amortization {amortized:,.2f}")
            return amount, (f"vendor invoices: non-payroll expense {vendor[p]:,.2f} less stock comp {sbc_amt:,.2f} "
                            f"and prepaid amortization {amortized:,.2f}")

        periods = sorted(bs)
        running: dict[str, Decimal] = defaultdict(Decimal)
        if version == OPENING_VERSION:
            cutoff = periods[0]
            opening = {key: num(bs[cutoff][key]) for key in BALANCE_LINES if key in bs[cutoff]}
            restated, invoice_note = invoices(cutoff)
            moved = opening["accounts_payable"] - restated
            opening["accounts_payable"], opening["cash"] = restated, opening["cash"] - moved
            log.append({"version": version, "period": cutoff, "line": "accounts_payable", "action": "opening restated",
                        "detail": f"opening AP {restated + moved:,.2f} in {version}_balance_sheet.csv restated to the "
                                  f"month's {invoice_note} (net 30); opening cash moves by the same amount",
                        "amount": f"{-moved:.2f}"})
            for key, bal in opening.items():
                note = f"Opening balance at {cutoff} month end, from {version}_balance_sheet.csv"
                if key in ("accounts_payable", "cash") and moved:
                    note += f"; AP restated to one month of vendor invoices (net 30), {-moved:,.2f} on both lines"
                w.add(cutoff, key, -bal if key in CREDIT_NORMAL else bal, label="opening",
                      source_file=f"{version}_balance_sheet.csv", source_system="Opening Balance", note=note)
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

            invoiced, note = invoices(p)
            w.add(p, "accounts_payable", running["accounts_payable"], label="vendor_payments",
                  source_file=f"{version}_gl_detail.csv", note="last month's vendor invoices paid (net 30)")
            w.add(p, "accounts_payable", -invoiced, label="vendor_accruals", source_file=f"{version}_gl_detail.csv",
                  note=note)
            subledger(pp, "prepaids_and_other_current", "beginning_prepaid_balance", "ending_prepaid_balance",
                      [("additions", "prepaid_additions", 1), ("amortization", "prepaid_amortization", -1)],
                      f"{version}_Prepaids_Rollforward.csv")

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

            for key in ("deferred_revenue", "debt", "other_liabilities"):
                amt = change(key)
                w.add(p, key, -amt if key in CREDIT_NORMAL else amt, label="net_change",
                      source_file=f"{version}_balance_sheet.csv", note=f"change in {version}_balance_sheet.csv")

            w.add(p, "apic_sbc", -sbc_amt, label="stock_comp", source_file=sbc_file, department=NON_CASH_DEPT,
                  note=f"stock comp (non-cash) from {sbc_file}; expense is inside the P&L lines")

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

        if ap:
            log.append({"version": version, "period": "", "line": "accounts_payable", "action": "from GL",
                        "detail": f"{version}_accounts_payable_rollforward.csv not used: invoices = non-payroll expense "
                                  f"less stock comp and prepaid amortization, paid net 30", "amount": ""})
        out[version] = w.rows
    return out, log


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
            for key in BALANCE_LINES:
                gl_value = line["total_equity"] if key == "equity" else line[key]
                diff = gl_value - num(bs[p].get(key))
                rows.append({"version": version, "period": p, "line": key,
                             "gl": f"{gl_value:.2f}", "statement": f"{num(bs[p].get(key)):.2f}", "difference": f"{diff:.2f}"})
    return rows
