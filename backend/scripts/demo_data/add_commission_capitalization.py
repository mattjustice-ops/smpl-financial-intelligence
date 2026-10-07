"""v6 demo data: sales commissions capitalized under ASC 340-40.

Writes a new folder only (never touches the database):
  python add_commission_capitalization.py <v5_folder> <v5_gl_folder> <v6_folder>

Then rebuild the GL (rebuild_gl_to_summary.py <v6_folder> <gl_folder>) and sync the statement
files to it (sync_v5_statements.py <v6_folder> <gl_folder>).

Rules (agreed with Matt, Oct 7 2026; docs/COMMISSION_CAPITALIZATION_DESIGN.md):
  * Policy lives on the commission plan: capitalize, amortization_months, payout_basis,
    payout_lag_months, capitalize_payroll_taxes. New business and expansion are capitalized
    and amortized straight-line over 60 months from the payout month (renewal commissions
    are not commensurate). Renewal commissions (12-month terms) are expensed when paid
    (practical expedient). Employer payroll taxes on commissions are expensed when paid.
  * Payouts are paid in the booking month (payout_date is the month end; no accrual).
  * Actual Jan-Jun 2026 new business and expansion payouts are the payout detail; renewal
    payouts are the renewal detail.
  * Months without payout detail: new business = (ARR waterfall new + reactivation) x the
    plan's effective rate in the 2026 payout detail; expansion = waterfall expansion x
    its effective rate; renewal = beginning ARR x the share of beginning ARR renewed in the
    renewal detail x the renewal plan rate. Budget and Forecast use their own ARR waterfalls.
    When a version has a customer ARR history ({version}_customer_arr_history.csv), new
    business and expansion use the commission base of each movement in it (the return
    policy; Forecast bases are probability-weighted), and Forecast renewals are the renewals
    expected in Forecast_renewal_pipeline.csv (renewal ARR x renewal probability) x the
    renewal plan rate.
  * Opening asset (Jan 2024 month end): the 60 monthly cohorts paid through Jan 2024. Pre-2024
    payouts are Jan 2024's payout discounted by the ARR growth rate from Jan 2024 to Dec 2025.
  * Employer payroll tax rate = GL payroll taxes / base salaries (Actual).
  * Income statement: S&M = v5 S&M - the v5 GL's 6200 (commissions expensed as paid, replaced)
    + amortization + expensed commissions + payroll tax on payouts; totals recomputed.
  * Opening balance sheet: deferred commissions current/noncurrent added; equity rises by the
    asset; cash and equity rise by the commission cash paid Feb 2024-Jun 2026 so June 2026
    cash is unchanged (~$30M).
"""

from __future__ import annotations

import csv
import os
import shutil
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_v5_dataset import HISTORY_FILE, commission_bases  # noqa: E402

CENT = Decimal("0.01")
ZERO = Decimal("0")
CUTOFF = "2024-01"
CLOSE = "2026-06"
VERSION_MONTHS = {
    "Actual": (CUTOFF, CLOSE),
    "Budget": ("2026-01", "2026-12"),
    "Forecast": ("2026-07", "2026-12"),
}
NEW, EXP, REN = "PLAN-AE-NEW", "PLAN-AM-EXP", "PLAN-RENEWAL"
CAPITALIZED_PLANS = (NEW, EXP)
AMORTIZATION_MONTHS = 60
POLICY = {
    NEW: {"capitalize": "Y", "amortization_months": str(AMORTIZATION_MONTHS), "payout_basis": "booking",
          "payout_lag_months": "0", "capitalize_payroll_taxes": "N"},
    EXP: {"capitalize": "Y", "amortization_months": str(AMORTIZATION_MONTHS), "payout_basis": "booking",
          "payout_lag_months": "0", "capitalize_payroll_taxes": "N"},
    REN: {"capitalize": "N", "amortization_months": "0", "payout_basis": "booking",
          "payout_lag_months": "0", "capitalize_payroll_taxes": "N"},
}
RENEWAL_PLAN_ROW = {"plan_id": REN, "role": "CSM", "eligible_opportunity_type": "Renewal",
                    "base_commission_rate": "0.02", "accelerator_multiplier": "1.0",
                    "accelerator_threshold": "1.0", "accelerated_rate": "0.02", "clawback_window_months": "0"}
POLICY_COLUMNS = ["capitalize", "amortization_months", "payout_basis", "payout_lag_months", "capitalize_payroll_taxes"]
BS_NEW = ["deferred_commissions_current", "deferred_commissions_noncurrent"]
CF_NEW = "change_in_deferred_commissions"
ROLLFORWARD_FIELDS = ["organization_id", "version", "period", "beginning_deferred_commissions", "capitalized_commissions",
                      "commission_amortization", "ending_deferred_commissions", "current_portion", "noncurrent_portion",
                      "expensed_commissions", "total_commission_payouts", "payroll_tax_on_commissions",
                      "amortization_months", "notes"]
SCHEDULE_FIELDS = ["organization_id", "version", "period", "plan_id", "commission_base_arr", "commission_rate",
                   "commission_payout", "capitalize", "capitalized_amount", "expensed_amount", "amortization_months",
                   "source"]


def num(value) -> Decimal:
    text = str(value if value is not None else "").replace(",", "").strip()
    return Decimal(text or "0")


def q(x: Decimal) -> Decimal:
    return x.quantize(CENT, ROUND_HALF_UP)


def read(path: str) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames or []), list(r)


def write(path: str, fields: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{r[k]:.2f}" if isinstance(r.get(k), Decimal) else r.get(k, "")) for k in fields})


def pidx(p: str) -> int:
    return int(p[:4]) * 12 + int(p[5:7]) - 1


def padd(p: str, n: int) -> str:
    i = pidx(p) + n
    return f"{i // 12}-{i % 12 + 1:02d}"


def prange(a: str, b: str) -> list[str]:
    return [padd(a, i) for i in range(pidx(b) - pidx(a) + 1)]


def by_period(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {r["period"][:7]: r for r in rows}


def insert_after(fields: list[str], anchor: str, new: list[str]) -> list[str]:
    out = [f for f in fields if f not in new]
    i = out.index(anchor) + 1
    return out[:i] + new + out[i:]


class Cohorts:
    """Straight-line amortization of monthly payout cohorts, exact to the cent on cumulative totals."""

    def __init__(self, months: int):
        self.n = months
        self.paid: dict[str, Decimal] = defaultdict(Decimal)

    def add(self, period: str, amount: Decimal) -> None:
        self.paid[period] += amount

    def cumulative_amortization(self, through: str, *, paid_through: str | None = None) -> Decimal:
        total = ZERO
        for p, amt in self.paid.items():
            if paid_through and p > paid_through:
                continue
            age = pidx(through) - pidx(p) + 1
            if age <= 0:
                continue
            total += amt * min(age, self.n) / self.n
        return q(total)

    def cumulative_paid(self, through: str) -> Decimal:
        return sum((a for p, a in self.paid.items() if p <= through), ZERO)

    def balance(self, through: str) -> Decimal:
        return q(self.cumulative_paid(through)) - self.cumulative_amortization(through)

    def current_portion(self, at: str) -> Decimal:
        """Amortization in the next 12 months of cohorts paid through ``at``."""
        return self.cumulative_amortization(padd(at, 12), paid_through=at) - self.cumulative_amortization(at)


def build(src: str, gl_dir: str, dst: str) -> list[str]:
    if os.path.exists(dst):
        raise SystemExit(f"{dst} exists; refusing to overwrite")
    shutil.copytree(src, dst)
    notes: list[str] = []
    org = read(os.path.join(src, "Actual_commission_plans.csv"))[1][0]["organization_id"]

    for v in VERSION_MONTHS:
        path = os.path.join(dst, f"{v}_commission_plans.csv")
        fields, rows = read(path)
        rows = [r for r in rows if r["plan_id"] != REN]
        rows.append({"organization_id": org, **RENEWAL_PLAN_ROW})
        for r in rows:
            r.update(POLICY[r["plan_id"]])
        write(path, fields + [c for c in POLICY_COLUMNS if c not in fields], rows)
    notes.append(f"commission plans: added {', '.join(POLICY_COLUMNS)}; added {REN} "
                 f"(used by Actual_renewal_commissions.csv, missing from the plan files)")

    detail_base: dict[str, Decimal] = defaultdict(Decimal)
    detail_paid: dict[str, Decimal] = defaultdict(Decimal)
    detail: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    detail_arr: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for r in read(os.path.join(src, "Actual_commission_payouts.csv"))[1]:
        base = num(r.get("commission_base_arr") or r["booked_arr"])
        detail[(r["period"][:7], r["plan_id"])] += num(r["commission_amount"])
        detail_arr[(r["period"][:7], r["plan_id"])] += base
        detail_base[r["plan_id"]] += base
        detail_paid[r["plan_id"]] += num(r["commission_amount"])
    renewal_months = set()
    renewal_booked = ZERO
    for r in read(os.path.join(src, "Actual_renewal_commissions.csv"))[1]:
        detail[(r["period"][:7], REN)] += num(r["commission_amount"])
        detail_arr[(r["period"][:7], REN)] += num(r["booked_arr"])
        renewal_months.add(r["period"][:7])
        renewal_booked += num(r["booked_arr"])
    detail_months = {p for p, _ in detail}
    eff = {plan: detail_paid[plan] / detail_base[plan] for plan in CAPITALIZED_PLANS}
    ren_rate = num(RENEWAL_PLAN_ROW["base_commission_rate"])

    wf = {v: by_period(read(os.path.join(src, f"{v}_MRR_Waterfall.csv"))[1]) for v in VERSION_MONTHS}
    renew_share = renewal_booked / sum((num(wf["Actual"][p]["beginning_arr"]) for p in renewal_months), ZERO)
    ren_span = f"{min(renewal_months)}..{max(renewal_months)}"
    notes.append(f"effective rates from the 2026 payout detail: new business {eff[NEW]:.5f}, expansion {eff[EXP]:.5f}; "
                 f"renewals: {renew_share:.4%} of beginning ARR renews a month ({ren_span} renewal detail) x {ren_rate}")

    _, gl_rows = read(os.path.join(gl_dir, "Actual_gl_detail.csv"))
    wages = sum((num(r["amount"]) for r in gl_rows if r["account_number"] == "6100"), ZERO)
    ptax = sum((num(r["amount"]) for r in gl_rows if r["account_number"] == "6110"), ZERO)
    tax_rate = ptax / wages
    notes.append(f"employer payroll tax on commissions: {tax_rate:.4%} (Actual GL 6110 / 6100)")

    actual_hist = read(os.path.join(src, HISTORY_FILE))[1] if os.path.exists(os.path.join(src, HISTORY_FILE)) else None
    hist: dict[str, dict[str, dict[str, Decimal]]] = {}
    for v, (a, b) in VERSION_MONTHS.items():
        path = os.path.join(src, f"{v}_customer_arr_history.csv")
        if not os.path.exists(path):
            continue
        rows = read(path)[1]
        if v != "Actual":
            if actual_hist is None:
                raise ValueError(f"{v}_customer_arr_history.csv needs {HISTORY_FILE} (the customers' Actual history)")
            rows = [r for r in actual_hist if r["period"] < a] + rows
        new, exp = defaultdict(Decimal), defaultdict(Decimal)
        for x in commission_bases(rows):
            if a <= x["period"] <= b:
                (exp if x["movement_type"] == "Expansion" else new)[x["period"]] += x["base"]
        hist[v] = {"new": new, "exp": exp}
        notes.append(f"{v} commission bases from {v}_customer_arr_history.csv: new + reactivation "
                     f"{sum(new.values(), ZERO):,.2f}, expansion {sum(exp.values(), ZERO):,.2f}")
    expected_renewals: dict[str, Decimal] = defaultdict(Decimal)
    ren_path = os.path.join(src, "Forecast_renewal_pipeline.csv")
    if "Forecast" in hist and os.path.exists(ren_path):
        for r in read(ren_path)[1]:
            expected_renewals[r["renewal_period"][:7]] += num(r["renewal_arr"]) * num(r["renewal_probability"])

    def estimate(v: str, p: str) -> dict[str, tuple[Decimal, Decimal, str]]:
        w = wf[v][p]
        if v == "Forecast" and expected_renewals:
            ren = (expected_renewals[p], ren_rate, "Forecast_renewal_pipeline.csv renewal ARR x renewal probability x renewal rate")
        else:
            ren = (num(w["beginning_arr"]) * renew_share, ren_rate, f"beginning ARR x {ren_span} renewal share x renewal rate")
        if v in hist:
            src_file = f"{v}_customer_arr_history.csv"
            return {NEW: (hist[v]["new"][p], eff[NEW], f"{src_file}: new + reactivation above prior ARR x 2026 effective rate"),
                    EXP: (hist[v]["exp"][p], eff[EXP], f"{src_file}: expansion above prior level x 2026 effective rate"),
                    REN: ren}
        new_arr = num(w["new_business_arr"]) + num(w["reactivation_arr"])
        exp_arr = num(w["expansion_arr"])
        return {NEW: (new_arr, eff[NEW], "ARR waterfall new + reactivation x 2026 effective rate"),
                EXP: (exp_arr, eff[EXP], "ARR waterfall expansion x 2026 effective rate"), REN: ren}

    schedule: dict[str, list[dict]] = defaultdict(list)
    payouts: dict[str, dict[str, dict[str, Decimal]]] = {v: defaultdict(lambda: defaultdict(Decimal)) for v in VERSION_MONTHS}
    for v, (a, b) in VERSION_MONTHS.items():
        for p in prange(a, b):
            est = estimate(v, p)
            for plan in (NEW, EXP, REN):
                if v == "Actual" and (p, plan) in detail:
                    base, amt = detail_arr[(p, plan)], q(detail[(p, plan)])
                    rate, source = (amt / base if base else ZERO), (
                        "Actual_renewal_commissions.csv" if plan == REN else "Actual_commission_payouts.csv")
                else:
                    if v == "Actual" and p in detail_months and plan != REN:
                        raise ValueError(f"{p} {plan}: payout detail month without this plan")
                    base, rate, source = est[plan]
                    amt = q(base * rate)
                cap = plan in CAPITALIZED_PLANS
                payouts[v][p][plan] = amt
                schedule[v].append({"organization_id": org, "version": v, "period": p, "plan_id": plan,
                                    "commission_base_arr": q(base), "commission_rate": f"{rate:.5f}",
                                    "commission_payout": amt, "capitalize": "Y" if cap else "N",
                                    "capitalized_amount": amt if cap else ZERO, "expensed_amount": ZERO if cap else amt,
                                    "amortization_months": str(AMORTIZATION_MONTHS) if cap else "0", "source": source})

    end_arr = num(wf["Actual"]["2025-12"]["ending_arr"])
    start_arr = num(wf["Actual"][CUTOFF]["beginning_arr"])
    growth = (end_arr / start_arr) ** (Decimal(12) / Decimal(pidx("2025-12") - pidx(CUTOFF) + 1))
    ladder: dict[str, dict[str, Decimal]] = defaultdict(dict)
    for k in range(1, AMORTIZATION_MONTHS):
        p = padd(CUTOFF, -k)
        for plan in CAPITALIZED_PLANS:
            amt = q(payouts["Actual"][CUTOFF][plan] / growth ** (Decimal(k) / 12))
            ladder[p][plan] = amt
            schedule["Actual"].append({"organization_id": org, "version": "Actual", "period": p, "plan_id": plan,
                                       "commission_base_arr": "", "commission_rate": "", "commission_payout": amt,
                                       "capitalize": "Y", "capitalized_amount": amt, "expensed_amount": ZERO,
                                       "amortization_months": str(AMORTIZATION_MONTHS),
                                       "source": f"opening ladder: Jan 2024 payout / {growth:.4f} annual ARR growth"})
    notes.append(f"opening ladder: {AMORTIZATION_MONTHS - 1} pre-2024 months, Jan 2024 payout discounted at "
                 f"{growth:.4f} a year (ARR {start_arr:,.0f} Jan 2024 -> {end_arr:,.0f} Dec 2025)")
    for v in VERSION_MONTHS:
        schedule[v].sort(key=lambda r: (r["period"], r["plan_id"]))
        write(os.path.join(dst, f"{v}_commission_schedule.csv"), SCHEDULE_FIELDS, schedule[v])

    chain_start = {"Actual": None, "Budget": "2026-01", "Forecast": "2026-07"}
    rollforward: dict[str, dict[str, dict]] = {}
    for v, (a, b) in VERSION_MONTHS.items():
        c = Cohorts(AMORTIZATION_MONTHS)
        for p, plans in ladder.items():
            for amt in plans.values():
                c.add(p, amt)
        for p, plans in payouts["Actual"].items():
            if chain_start[v] is None or p < chain_start[v]:
                for plan in CAPITALIZED_PLANS:
                    c.add(p, plans[plan])
        if v != "Actual":
            for p, plans in payouts[v].items():
                for plan in CAPITALIZED_PLANS:
                    c.add(p, plans[plan])
        rows = {}
        for p in prange(a, b):
            begin = c.balance(padd(p, -1))
            cap = sum((payouts[v][p][plan] for plan in CAPITALIZED_PLANS), ZERO)
            amort = c.cumulative_amortization(p) - c.cumulative_amortization(padd(p, -1))
            end = c.balance(p)
            current = c.current_portion(p)
            expensed = payouts[v][p][REN]
            total = cap + expensed
            rows[p] = {"organization_id": org, "version": v, "period": p, "beginning_deferred_commissions": begin,
                       "capitalized_commissions": cap, "commission_amortization": amort,
                       "ending_deferred_commissions": end, "current_portion": current, "noncurrent_portion": end - current,
                       "expensed_commissions": expensed, "total_commission_payouts": total,
                       "payroll_tax_on_commissions": q(total * tax_rate),
                       "amortization_months": str(AMORTIZATION_MONTHS),
                       "notes": "straight-line from the payout month; renewal commissions expensed (12-month term)"}
        rollforward[v] = rows
        write(os.path.join(dst, f"{v}_deferred_commissions_rollforward.csv"), ROLLFORWARD_FIELDS, list(rows.values()))

    replaced_6200: dict[str, dict[str, Decimal]] = {}
    for v in VERSION_MONTHS:
        old_6200: dict[str, Decimal] = defaultdict(Decimal)
        for r in read(os.path.join(gl_dir, f"{v}_gl_detail.csv"))[1]:
            if r["account_number"] == "6200":
                old_6200[r["period"][:7]] += num(r["amount"])
        replaced_6200[v] = old_6200
        path = os.path.join(dst, f"{v}_income_statement.csv")
        fields, rows = read(path)
        for r in rows:
            p = r["period"][:7]
            rf = rollforward[v][p]
            add = rf["commission_amortization"] + rf["expensed_commissions"] + rf["payroll_tax_on_commissions"]
            r["sales_and_marketing"] = q(num(r["sales_and_marketing"]) - old_6200[p] + add)
            gp = num(r["gross_profit"])
            ebitda = gp - num(r["sales_and_marketing"]) - num(r["research_and_development"]) - num(r["general_and_administrative"])
            r["ebitda"] = q(ebitda)
            r["net_income"] = q(ebitda - num(r["depreciation_and_amortization"]) - num(r["interest_expense"]) - num(r["tax_expense"]))
        write(path, fields, rows)
        yr = defaultdict(Decimal)
        for p, rf in rollforward[v].items():
            yr[p[:4]] += rf["commission_amortization"] + rf["expensed_commissions"] + rf["payroll_tax_on_commissions"]
        notes.append(f"{v} S&M up by commission expense: " + ", ".join(f"{y} {a:,.2f}" for y, a in sorted(yr.items()))
                     + f"; v5 GL 6200 removed: {sum(old_6200.values(), ZERO):,.2f}")

    cash_paid = sum((rf["total_commission_payouts"] + rf["payroll_tax_on_commissions"] - replaced_6200["Actual"][p]
                     for p, rf in rollforward["Actual"].items() if p > CUTOFF), ZERO)
    for v in VERSION_MONTHS:
        path = os.path.join(dst, f"{v}_balance_sheet.csv")
        fields, rows = read(path)
        fields = insert_after(fields, "prepaids_and_other_current", BS_NEW)
        for r in rows:
            p = r["period"][:7]
            rf = rollforward[v][p]
            r["deferred_commissions_current"] = rf["current_portion"]
            r["deferred_commissions_noncurrent"] = rf["noncurrent_portion"]
            if v == "Actual" and p == CUTOFF:
                asset = rf["ending_deferred_commissions"]
                r["cash"] = q(num(r["cash"]) + cash_paid)
                r["equity"] = q(num(r["equity"]) + asset + cash_paid)
                r["total_assets"] = q(num(r["total_assets"]) + asset + cash_paid)
                r["total_liabilities_and_equity"] = q(num(r["total_liabilities_and_equity"]) + asset + cash_paid)
                notes.append(f"opening balance sheet {CUTOFF}: deferred commissions {asset:,.2f} "
                             f"(current {rf['current_portion']:,.2f}); cash +{cash_paid:,.2f} (commission cash paid "
                             f"Feb 2024-Jun 2026 less the replaced v5 6200, so June 2026 cash is unchanged); "
                             f"equity +{asset + cash_paid:,.2f}")
        write(path, fields, rows)

        path = os.path.join(dst, f"{v}_cash_flow_statement.csv")
        fields, rows = read(path)
        write(path, insert_after(fields, "change_in_prepaids", [CF_NEW]), rows)

    for v in VERSION_MONTHS:
        tot = defaultdict(lambda: defaultdict(Decimal))
        for p, rf in rollforward[v].items():
            for k in ("capitalized_commissions", "commission_amortization", "expensed_commissions", "payroll_tax_on_commissions"):
                tot[p[:4]][k] += rf[k]
        last = rollforward[v][VERSION_MONTHS[v][1]]
        notes.append(f"{v}: " + "; ".join(
            f"{y} capitalized {t['capitalized_commissions']:,.0f}, amortized {t['commission_amortization']:,.0f}, "
            f"renewal expensed {t['expensed_commissions']:,.0f}, payroll tax {t['payroll_tax_on_commissions']:,.0f}"
            for y, t in sorted(tot.items()))
            + f"; deferred commissions at {VERSION_MONTHS[v][1]} {last['ending_deferred_commissions']:,.2f}")

    with open(os.path.join(dst, "v6_build_notes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(notes) + "\n")
    return notes


if __name__ == "__main__":
    for n in build(sys.argv[1], sys.argv[2], sys.argv[3]):
        print(n)
