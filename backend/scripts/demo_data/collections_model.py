"""Customer payments, dunning, write-offs and the allowance for doubtful accounts for the demo company.

Rules (agreed with Matt, Oct 9 2026):
  * Non-payment comes first. An unpaid invoice goes through the dunning ladder from its due date (DUNNING_STEPS):
    reminders at 1 and 15 days past due, escalation to the customer's finance contact at 30, final notice at 45,
    service suspended at 60, written off at 120. A suspended customer leaves the ARR history the month after its
    service ends: inside its first year that is a No-start (churn that reverses new business; the AE's commission is
    clawed back when payment stopped inside the plan's clawback window), after it Non-payment churn.
  * About 1% of customers. NO_STARTS are placed by build_customer_history.py inside the existing ARR waterfall (the
    booking comes out of that month's new business, the exit out of a later month's churn). NONPAY_CHURN customers
    already leave the history in those months; their last invoices go unpaid. RECOVERED paid late after escalation;
    DISPUTE is in a billing dispute at the June 2026 close (service continues; the Forecast collects it).
  * Every other invoice is paid on the customer's habit (PAYMENT_HABITS): half by the due date, about a third up to
    15 days late, the rest 16-70 days late (about 7 days past due on average).
  * Allowance: open invoices at month end reserved by days past due (RESERVE_RATES); invoices of a suspended customer
    100%; invoices in dispute at least DISPUTE_RESERVE. Bad debt expense (G&A) = change in the allowance plus
    write-offs. Write-offs come out of the allowance and gross AR.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ZERO = Decimal("0")

# name, share of customers, days from due (first, last). The mix averages about 7 days past due, the agreed
# collection lag the Budget and Forecast keep.
PAYMENT_HABITS = (
    ("On time", Decimal("0.50"), -5, 0),
    ("Slightly late", Decimal("0.32"), 1, 15),
    ("Slow", Decimal("0.13"), 16, 40),
    ("Very slow", Decimal("0.05"), 41, 70),
)
EARLIEST_PAYMENT_DAYS = 3
DUNNING_STEPS = ((1, "Reminder"), (15, "Second reminder"), (30, "Escalated to customer finance contact"),
                 (45, "Final notice"))
SUSPEND_DAYS = 60
WRITE_OFF_DAYS = 120
BUCKETS = ("current", "days_1_30", "days_31_60", "days_61_90", "days_over_90")
RESERVE_RATES = {"current": Decimal("0.005"), "days_1_30": Decimal("0.02"), "days_31_60": Decimal("0.10"),
                 "days_61_90": Decimal("0.25"), "days_over_90": Decimal("0.50")}
DISPUTE_RESERVE = Decimal("0.50")
# Who works each dunning step: the first role with someone employed on the day (Actual_Employees.csv).
ROUTINE_OWNERS = ("Billing Specialist", "Revenue Accountant")
ESCALATION_OWNERS = ("Revenue Accounting Manager", "Controller")
WRITE_OFF_OWNERS = ("Controller",)
ROUTINE_STEPS = ("Reminder", "Second reminder", "Paid")

NO_START = "No-start"
NON_PAYMENT = "Non-payment"
CHURN_TYPES = (NO_START, NON_PAYMENT)
RECOVERED_CASE = "Recovered after escalation"
DISPUTE_CASE = "In dispute at close"


@dataclass(frozen=True)
class NoStart:
    booked: str
    unpaid_after: int  # months of invoices paid before payment stopped
    nb_share: Decimal  # share of the booking month's new business ARR
    reason: str


NO_START_TERMS_DAYS = 30
NO_STARTS = (
    NoStart("2024-06", 0, Decimal("0.12"),
            "Tax registration for the customer's new Brazil entity never completed; no invoice was paid"),
    NoStart("2024-11", 2, Decimal("0.10"),
            "Billing dispute over implementation scope; stopped paying after two invoices"),
    NoStart("2025-02", 7, Decimal("0.08"), "Customer became insolvent; stopped paying in its eighth month"),
)
NONPAY_CHURN = (
    ("2024-10", "Unresponsive after a change of ownership"),
    ("2025-08", "Customer went out of business"),
    ("2026-04", "Budget cut; stopped paying ahead of its renewal"),
)
RECOVERED = ("2025-03", 82, "Cash-flow problems; paid on a payment plan agreed after escalation")
DISPUTE = ("2026-04", dt.date(2026, 8, 12), "Disputed usage charges; service continues while the dispute is open")


# ----------------------------------------------------------------------------- dates


def unit(key: str) -> Decimal:
    h = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
    return Decimal(h % 10000) / Decimal(10000)


def pidx(p: str) -> int:
    return int(p[:4]) * 12 + int(p[5:7]) - 1


def padd(p: str, n: int) -> str:
    i = pidx(p) + n
    return f"{i // 12}-{i % 12 + 1:02d}"


def first_day(p: str) -> dt.date:
    return dt.date(int(p[:4]), int(p[5:7]), 1)


def last_day(p: str) -> dt.date:
    return first_day(padd(p, 1)) - dt.timedelta(days=1)


def month_of(d: dt.date) -> str:
    return f"{d.year}-{d.month:02d}"


def q(x: Decimal) -> Decimal:
    return x.quantize(CENT, ROUND_HALF_UP)


def no_start_exit(ns: NoStart) -> tuple[str, dt.date, dt.date, str]:
    """(first unpaid invoice month, its due date, suspension date, month the customer leaves the ARR history) for a
    no-start billed monthly on NO_START_TERMS_DAYS."""
    issue = padd(ns.booked, ns.unpaid_after)
    due = first_day(issue) + dt.timedelta(days=NO_START_TERMS_DAYS)
    suspended = due + dt.timedelta(days=SUSPEND_DAYS)
    return issue, due, suspended, padd(month_of(suspended), 1)


# ----------------------------------------------------------------------------- payment habits


def habit(customer_id: str) -> tuple[str, int, int]:
    x, acc = unit(f"habit|{customer_id}"), ZERO
    for name, share, lo, hi in PAYMENT_HABITS:
        acc += share
        if x < acc:
            return name, lo, hi
    name, _, lo, hi = PAYMENT_HABITS[-1]
    return name, lo, hi


def habit_payment_date(inv) -> dt.date:
    _, lo, hi = habit(inv.customer_id)
    days = lo + int(unit(f"pay|{inv.id}") * (hi - lo + 1))
    return max(inv.due_date + dt.timedelta(days=days), inv.invoice_date + dt.timedelta(days=EARLIEST_PAYMENT_DAYS))


# ----------------------------------------------------------------------------- cases


@dataclass
class Case:
    customer_id: str
    customer_name: str
    kind: str  # NO_START, NON_PAYMENT, RECOVERED_CASE, DISPUTE_CASE
    reason: str
    left: str = ""  # month the customer leaves the ARR history (no-start, non-payment)
    booked: str = ""  # no-start: month of the new business
    invoices: list = field(default_factory=list)  # the case's unpaid (or late) invoices, by due date
    suspended: dt.date | None = None
    written_off: dt.date | None = None
    paid: dt.date | None = None  # recovered / dispute: when the late invoices were paid

    @property
    def first_due(self) -> dt.date:
        return self.invoices[0].due_date


def plan_cases(history: list[dict[str, str]], invoices: list, cadence: dict[str, str],
               terms: dict[str, str]) -> list[Case]:
    """The collections cases from the Actual ARR history (rows marked churn_type) and the Actual invoices (every
    invoice issued from the first billed month to the close)."""
    by_customer: dict[str, list] = defaultdict(list)
    for inv in invoices:
        if inv.kind == "recurring":
            by_customer[inv.customer_id].append(inv)
    for rows in by_customer.values():
        rows.sort(key=lambda i: (i.due_date, i.id))
    booked = {}
    for r in sorted(history, key=lambda r: r["period"]):
        if r["movement_type"] == "New Business":
            booked[r["customer_id"]] = r["period"][:7]
    reasons = {ns.booked: ns.reason for ns in NO_STARTS}
    nonpay_reasons = dict(NONPAY_CHURN)
    cases: list[Case] = []
    for r in sorted(history, key=lambda r: (r["period"], r["customer_id"])):
        kind = r.get("churn_type", "")
        if kind not in CHURN_TYPES:
            continue
        cid, left = r["customer_id"], r["period"][:7]
        bills = [i for i in by_customer[cid] if i.issue < left]
        if not bills:
            raise ValueError(f"{cid}: {kind} in {left} but no invoices before it")
        target = last_day(padd(left, -1)) - dt.timedelta(days=SUSPEND_DAYS)
        first = max((i for i in bills if i.due_date <= target), key=lambda i: i.due_date, default=bills[0])
        unpaid = [i for i in bills if i.due_date >= first.due_date]
        suspended = first.due_date + dt.timedelta(days=SUSPEND_DAYS)
        if kind == NO_START:
            ns = next(ns for ns in NO_STARTS if ns.booked == booked[cid])
            if (first.issue, first.due_date, left) != tuple(no_start_exit(ns)[i] for i in (0, 1, 3)):
                raise ValueError(f"{cid}: first unpaid invoice {first.id} due {first.due_date} does not match the "
                                 f"no-start plan {no_start_exit(ns)}")
        reason = reasons[booked[cid]] if kind == NO_START else nonpay_reasons[left]
        cases.append(Case(cid, r["customer_name"], kind, reason, left=left,
                          booked=booked.get(cid, "") if kind == NO_START else "", invoices=unpaid,
                          suspended=suspended, written_off=first.due_date + dt.timedelta(days=WRITE_OFF_DAYS)))
    taken = {c.customer_id for c in cases}

    def candidates(months: list[str]) -> list[str]:
        out = []
        for cid, bills in by_customer.items():
            issued = {i.issue for i in bills}
            if cid in taken or cadence.get(cid) != "Monthly" or terms.get(cid) != "Net 30":
                continue
            if all(m in issued for m in months):
                out.append(cid)
        return sorted(out, key=lambda c: (-unit(f"case|{months[0]}|{c}"), c))

    month, days_late, reason = RECOVERED
    cid = candidates([padd(month, k) for k in range(-12, 4)])[0]
    late = next(i for i in by_customer[cid] if i.issue == month)
    paid = late.due_date + dt.timedelta(days=days_late)
    cases.append(Case(cid, late.customer_name, RECOVERED_CASE, reason, invoices=[late], paid=paid))
    taken.add(cid)

    month, resolved, reason = DISPUTE
    close = max(i.issue for i in invoices)
    cid = candidates([padd(month, k) for k in range(-12, pidx(close) - pidx(month) + 1)])[0]
    disputed = [i for i in by_customer[cid] if month <= i.issue <= close]
    cases.append(Case(cid, disputed[0].customer_name, DISPUTE_CASE, reason, invoices=disputed, paid=resolved))
    return cases


def settle(invoices: list, cases: list[Case]) -> None:
    """Set ``paid`` (date or None) and ``written_off`` (date or None) on every invoice."""
    special: dict[str, Case] = {}
    for c in cases:
        for inv in c.invoices:
            special[inv.id] = c
    for inv in invoices:
        c = special.get(inv.id)
        if c is None:
            inv.paid, inv.written_off = habit_payment_date(inv), None
        elif c.kind in CHURN_TYPES:
            inv.paid, inv.written_off = None, c.written_off
        else:
            inv.paid, inv.written_off = c.paid, None


def write_off_month(inv) -> str:
    return month_of(inv.written_off) if inv.written_off else ""


def is_open(inv, on: dt.date) -> bool:
    return inv.invoice_date <= on and not (inv.paid and inv.paid <= on) and not (inv.written_off and inv.written_off <= on)


def bucket(days_past_due: int) -> str:
    if days_past_due <= 0:
        return "current"
    if days_past_due <= 30:
        return "days_1_30"
    if days_past_due <= 60:
        return "days_31_60"
    if days_past_due <= 90:
        return "days_61_90"
    return "days_over_90"


def allowance_at(invoices: list, cases: list[Case], on: dt.date) -> dict[str, Decimal]:
    """Gross AR, the aging and the allowance (general by bucket, specific for cases) at ``on``."""
    case_of = {inv.id: c for c in cases for inv in c.invoices}
    out = defaultdict(lambda: ZERO)
    for inv in invoices:
        if not is_open(inv, on):
            continue
        b = bucket((on - inv.due_date).days)
        out["gross"] += inv.amount
        out[b] += inv.amount
        c = case_of.get(inv.id)
        if c is not None and c.kind in CHURN_TYPES and c.suspended <= on:
            out["specific"] += inv.amount
        elif c is not None and c.kind == DISPUTE_CASE:
            out["specific"] += inv.amount * max(DISPUTE_RESERVE, RESERVE_RATES[b])
        else:
            out[f"reserve_{b}"] += inv.amount * RESERVE_RATES[b]
    out = {k: q(v) for k, v in out.items()}
    out["general"] = sum((out.get(f"reserve_{b}", ZERO) for b in BUCKETS), ZERO)
    out["allowance"] = out["general"] + out.get("specific", ZERO)
    return defaultdict(lambda: ZERO, out)


def allowance_rollforward(invoices: list, cases: list[Case], months: list[str],
                          begin: Decimal | None = None) -> list[dict]:
    """One row per month: beginning, provision, write-offs, ending allowance, gross and net AR."""
    rows = []
    prev = allowance_at(invoices, cases, last_day(padd(months[0], -1)))["allowance"] if begin is None else begin
    for p in months:
        at = allowance_at(invoices, cases, last_day(p))
        written = sum((inv.amount for inv in invoices if write_off_month(inv) == p), ZERO)
        provision = at["allowance"] - prev + written
        rows.append({"period": p, "beginning_allowance": prev, "provision_for_credit_losses": provision,
                     "write_offs": written, "ending_allowance": at["allowance"],
                     "gross_accounts_receivable": at["gross"], "net_accounts_receivable": at["gross"] - at["allowance"],
                     **{f"reserve_{b}": at[f"reserve_{b}"] for b in BUCKETS}, "specific_reserve": at["specific"]})
        prev = at["allowance"]
    return rows


# ----------------------------------------------------------------------------- Actual files


def aging_rows(org: str, invoices: list, months: list[str], names: dict[str, str]) -> list[dict]:
    rows = []
    for p in months:
        on = last_day(p)
        by: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: ZERO))
        for inv in invoices:
            if is_open(inv, on):
                by[inv.customer_id][bucket((on - inv.due_date).days)] += inv.amount
        for cid in sorted(by):
            b = by[cid]
            rows.append({"organization_id": org, "version": "Actual", "period": p, "customer_id": cid,
                         "customer_name": names[cid], **{k: b[k] for k in BUCKETS},
                         "total": sum((b[k] for k in BUCKETS), ZERO)})
    return rows


def payment_method(segment: str, customer_id: str) -> str:
    if segment == "Enterprise":
        return "Wire"
    if segment == "SMB" and unit(f"card|{customer_id}") < Decimal("0.5"):
        return "Credit card"
    return "ACH"


def payment_rows(org: str, invoices: list, close: dt.date, segment: dict[str, str]) -> list[dict]:
    rows = []
    for inv in sorted((i for i in invoices if i.paid and i.paid <= close), key=lambda i: (i.paid, i.id)):
        rows.append({"organization_id": org, "version": "Actual", "customer_payment_id": f"RCPT-{inv.id}",
                     "period": month_of(inv.paid), "customer_id": inv.customer_id, "customer_name": inv.customer_name,
                     "invoice_id": inv.id, "invoice_date": inv.invoice_date.isoformat(),
                     "due_date": inv.due_date.isoformat(), "payment_date": inv.paid.isoformat(), "amount": inv.amount,
                     "payment_method": payment_method(segment.get(inv.customer_id, ""), inv.customer_id),
                     "days_past_due": max(0, (inv.paid - inv.due_date).days), "currency": "USD"})
    return rows


def owner_on(activity: str, day: dt.date, staff: list[dict[str, str]]) -> dict[str, str]:
    roles = (WRITE_OFF_OWNERS if activity == "Written off" else
             ROUTINE_OWNERS if activity in ROUTINE_STEPS else ESCALATION_OWNERS)
    for role in roles:
        for e in sorted(staff, key=lambda e: e["employee_id"]):
            hired = dt.date.fromisoformat(e["hire_date"])
            left = dt.date.fromisoformat(e["termination_date"]) if e.get("termination_date") else None
            if e["role"] == role and hired <= day and (left is None or day <= left):
                return e
    raise ValueError(f"nobody in {', '.join(roles)} employed on {day} for '{activity}'")


def activity_rows(org: str, invoices: list, cases: list[Case], close: dt.date,
                  staff: list[dict[str, str]]) -> list[dict]:
    """The dunning log through the close: every step each late invoice reached, and each case's suspension,
    payment plan, payment, dispute and write-off, with the employee who worked it."""
    case_of = {inv.id: c for c in cases for inv in c.invoices}
    events: list[tuple[dt.date, str, object, str, str, str]] = []  # date, customer, invoice, case, activity, note
    for inv in invoices:
        c = case_of.get(inv.id)
        settled = inv.paid or inv.written_off
        for days, step in DUNNING_STEPS:
            d = inv.due_date + dt.timedelta(days=days)
            if d > close or (settled and settled <= d) or (c is not None and c.kind == DISPUTE_CASE and days > 1):
                break
            events.append((d, inv.customer_id, inv, c.kind if c else "", step, ""))
    for c in cases:
        first = c.invoices[0]
        if c.kind in CHURN_TYPES:
            note = c.reason + (f"; booked {c.booked}" if c.booked else "")
            for d, act in ((c.suspended, "Service suspended"), (c.written_off, "Written off")):
                if d <= close:
                    total = sum((i.amount for i in c.invoices if i.due_date < d), ZERO)
                    events.append((d, c.customer_id, None, c.kind, act, f"{note}; {total:,.2f} unpaid"))
        elif c.kind == RECOVERED_CASE:
            plan = first.due_date + dt.timedelta(days=50)
            events.append((plan, c.customer_id, first, c.kind, "Payment plan agreed", c.reason))
            events.append((c.paid, c.customer_id, first, c.kind, "Paid", "paid in full under the payment plan"))
        else:
            opened = first.due_date + dt.timedelta(days=10)
            events.append((opened, c.customer_id, first, c.kind, "Dispute opened", c.reason))
            events.append((first.due_date + dt.timedelta(days=30), c.customer_id, first, c.kind,
                           "Escalated to customer finance contact", "dispute under review; suspension on hold"))
    rows = []
    for n, (d, cid, inv, kind, act, note) in enumerate(sorted(events, key=lambda e: (e[0], e[1], e[4])), 1):
        name = inv.customer_name if inv is not None else next(c.customer_name for c in cases if c.customer_id == cid)
        who = owner_on(act, d, staff)
        rows.append({"organization_id": org, "version": "Actual", "collection_activity_id": f"COLL-{n:06d}",
                     "period": month_of(d), "activity_date": d.isoformat(), "customer_id": cid, "customer_name": name,
                     "invoice_id": inv.id if inv is not None else "",
                     "amount": inv.amount if inv is not None else "",
                     "days_past_due": (d - inv.due_date).days if inv is not None else "",
                     "case_type": kind, "activity": act, "owner_id": who["employee_id"],
                     "owner": who["employee_name"], "note": note})
    return rows


def case_rows(org: str, cases: list[Case], close: dt.date) -> list[dict]:
    rows = []
    for c in sorted(cases, key=lambda c: (c.invoices[0].due_date, c.customer_id)):
        unpaid = sum((i.amount for i in c.invoices), ZERO)
        rows.append({"organization_id": org, "version": "Actual", "customer_id": c.customer_id,
                     "customer_name": c.customer_name, "case_type": c.kind, "reason": c.reason,
                     "booked_period": c.booked, "first_unpaid_invoice": c.invoices[0].id,
                     "first_unpaid_period": c.invoices[0].issue,
                     "first_unpaid_due_date": c.first_due.isoformat(), "invoices": len(c.invoices), "amount": unpaid,
                     "service_suspended": c.suspended.isoformat() if c.suspended else "",
                     "left_arr_history": c.left,
                     "written_off_date": c.written_off.isoformat() if c.written_off and c.written_off <= close else "",
                     "written_off_amount": unpaid if c.written_off and c.written_off <= close else ZERO,
                     "paid_date": c.paid.isoformat() if c.paid and c.paid <= close else "",
                     "status_at_close": status_at(c, close)})
    return rows


def status_at(c: Case, close: dt.date) -> str:
    if c.kind in CHURN_TYPES:
        if c.written_off <= close:
            return "Written off"
        return "Suspended, in collections" if c.suspended <= close else "In dunning"
    if c.paid <= close:
        return "Paid"
    return "Open, in dispute" if c.kind == DISPUTE_CASE else "Open"
