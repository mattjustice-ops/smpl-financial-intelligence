"""Vendors, bills, payments and prepaids for the demo company, driven by its own roster and P&L.

Spend (what each vendor charges in a month):
  * Seat-priced software: heads on the roster in the teams that use the tool x the list price for the year.
  * Fixed contracts: contractors, outside counsel, HubSpot, Bill.com.
  * Office leases (ASC 842 operating leases, LEASES): rent escalates on the anniversary and is paid monthly in
    advance. Rent bills reduce the lease liability (2060); the P&L cost is the straight-line cost on 6510; the
    right-of-use asset (1600) is the liability less cumulative straight-line cost over payments.
  * Per-hire: recruiting agency fees (VP-level and senior engineering hires) and laptops; laptops are also refreshed
    every 36 months.
  * American Express: one statement a month with T&E by cost center (sales kickoff in January, company offsite in
    September).
  * Annual contracts (Salesforce, Snowflake, NetSuite, insurance, the AWS Savings Plan, ...): billed at renewal for
    12 months, seat contracts sized on the heads at renewal, booked to 1200 Prepaids and amortized monthly to the
    expense account. The Savings Plan's amortization is part of production hosting (5000), so the usage bills are
    the rest of the account.
  * Usage: the rest of a P&L line whose total is fixed (cloud hosting and third-party fees in cost of revenue,
    marketing programs in S&M) and development cloud (its share of R&D) are split across the account's vendors
    by share (USAGE_SHARES).

Bills: one bill per vendor per month (per hire for recruiting fees; per renewal for annual contracts), dated on
the vendor's billing day. Usage and services vendors (cloud, ads, events, content, partners, legal, audit,
contractors, facilities) bill in arrears, in the month after the services; until then the services are accrued
expenses (2050). Due date = bill date + terms. Payments go out in the Thursday payment run on or before the due date; autopay vendors are paid on
the bill date. Actual payments: 1 in 10 bills misses its run, and 4 in 10 from vendors whose invoices need a
budget owner's approval (legal, audit, contractors, events, partners, recruiting, facilities); of the late ones
70% miss one run, 21% slip 2-4 weeks and 9% are disputed for 6-10 weeks. Payments after the June 2026 close are
not in the Actual files: those bills are open. Bills dated after the close are not in the Actual files either;
the services they bill are the accrued expenses at the close.
Budget and Forecast pay every bill on schedule, including the Actual bills open (or not yet billed) when they start.

The Actual months before January 2024 (the GL's opening month) are billed from the January 2024 roster and P&L
so the opening AP, prepaid and accrued expense balances are the bills, contracts and unbilled services open at
January 31, 2024.
"""

from __future__ import annotations

import calendar
import csv
import datetime as dt
import functools
import hashlib
import os
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ZERO = Decimal("0")
FIRST, CLOSE = "2024-01", "2026-06"
HISTORY_FROM = "2023-02"
CHAIN_FROM = {"Actual": None, "Budget": "2026-01", "Forecast": "2026-07"}
WINDOW = {"Actual": (FIRST, CLOSE), "Budget": ("2026-01", "2026-12"), "Forecast": ("2026-07", "2026-12")}
PRICE_GROWTH = Decimal("0.05")
PREPAID_ACCOUNT = "1200"
AP_ACCOUNT = "2000"
ACCRUED_ACCOUNT = "2050"
LEASE_LIABILITY_ACCOUNT = "2060"
ROU_ACCOUNT = "1600"
RENT_ACCOUNT = "6510"
# Bill lines coded to the balance sheet, not the P&L: annual contracts paid up front and lease payments.
BALANCE_SHEET_LINE_ACCOUNTS = frozenset({PREPAID_ACCOUNT, LEASE_LIABILITY_ACCOUNT})

# account number -> (name, statement category, account group, expense type, description); added to the COA.
VENDOR_ACCOUNTS = {
    "6430": ("Computer Equipment and Supplies", "Operating Expense", "Technology Expense", "Software",
             "Laptops and peripherals for new hires and the 36-month refresh, below the capitalization threshold"),
    "6535": ("Recruiting", "Operating Expense", "G&A Expense", "Recruiting",
             "Recruiting agency fees and recruiting software"),
    "6550": ("Travel and Entertainment", "Operating Expense", "G&A Expense", "Travel & Entertainment",
             "Travel, meals and events outside Sales, from the corporate card statement"),
}
CONTRACTOR_ACCOUNT = ("6130", "Contractor Labor", "Operating Expense", "Outside Services", "Contractors",
                      "Contract engineering, billed monthly by the agency")


@dataclass(frozen=True)
class Vendor:
    id: str
    name: str
    category: str
    terms: int
    method: str
    bill_day: int
    is_1099: bool = False
    # Invoices routed to a budget owner for approval (services billed for work done): paid late more often.
    approval: bool = False
    # Billed in arrears: a month's services are billed on bill_day of the next month (accrued at month end).
    arrears: bool = False


V = Vendor
VENDORS: dict[str, Vendor] = {v.id: v for v in (
    V("V1001", "Amazon Web Services", "Cloud Infrastructure", 30, "ACH", 3, arrears=True),
    V("V1002", "Datadog", "Cloud Infrastructure", 30, "ACH", 2, arrears=True),
    V("V1003", "Cloudflare", "Cloud Infrastructure", 30, "ACH", 1, arrears=True),
    V("V1004", "OpenAI", "Third-Party Product Services", 0, "Autopay", 1, arrears=True),
    V("V1005", "Twilio", "Third-Party Product Services", 0, "Autopay", 1, arrears=True),
    V("V1006", "Plaid", "Third-Party Product Services", 30, "ACH", 5, arrears=True),
    V("V1007", "Merge API", "Third-Party Product Services", 30, "ACH", 1, arrears=True),
    V("V1010", "Google Workspace", "Software", 0, "Autopay", 1),
    V("V1011", "Zoom Video Communications", "Software", 30, "ACH", 5),
    V("V1012", "1Password", "Software", 0, "Autopay", 8),
    V("V1013", "Notion Labs", "Software", 30, "ACH", 12),
    V("V1014", "Rippling", "Software", 0, "Autopay", 3),
    V("V1015", "Slack Technologies", "Software", 30, "ACH", 1),
    V("V1016", "Okta", "Software", 30, "ACH", 1),
    V("V1017", "GitHub", "Software", 30, "ACH", 1),
    V("V1018", "Atlassian", "Software", 30, "ACH", 1),
    V("V1019", "Figma", "Software", 30, "ACH", 1),
    V("V1020", "Snowflake", "Software", 45, "Wire", 1),
    V("V1021", "Zendesk", "Software", 30, "ACH", 1),
    V("V1022", "ChurnZero", "Software", 30, "ACH", 1),
    V("V1023", "Oracle NetSuite", "Software", 30, "ACH", 1),
    V("V1024", "Carta", "Software", 30, "ACH", 1),
    V("V1025", "Ironclad", "Software", 30, "ACH", 1),
    V("V1026", "Bill.com", "Software", 0, "Autopay", 2),
    V("V1027", "Anysphere (Cursor)", "Software", 0, "Autopay", 6),
    V("V1028", "HubSpot", "Software", 30, "ACH", 4),
    V("V1030", "Salesforce", "Sales Software", 30, "ACH", 1),
    V("V1031", "Gong", "Sales Software", 30, "ACH", 1),
    V("V1032", "Outreach", "Sales Software", 30, "ACH", 1),
    V("V1033", "ZoomInfo", "Sales Software", 30, "ACH", 1),
    V("V1034", "LinkedIn", "Advertising and Sales Software", 30, "ACH", 1, arrears=True),
    V("V1040", "Google Ads", "Advertising", 30, "ACH", 1, arrears=True),
    V("V1041", "Microsoft Advertising", "Advertising", 30, "ACH", 5, arrears=True),
    V("V1042", "Meta Platforms", "Advertising", 30, "ACH", 1, arrears=True),
    V("V1043", "ON24", "Events and Webinars", 30, "ACH", 5, arrears=True),
    V("V1044", "Cvent", "Events and Webinars", 30, "ACH", 5, arrears=True),
    V("V1045", "Summit Events Group", "Events and Webinars", 45, "ACH", 10, approval=True, arrears=True),
    V("V1046", "CFO Leadership Forum", "Events and Webinars", 15, "ACH", 10, approval=True, arrears=True),
    V("V1047", "G2", "Content and Syndication", 30, "ACH", 5, arrears=True),
    V("V1048", "TechTarget", "Content and Syndication", 45, "ACH", 10, arrears=True),
    V("V1049", "Integrate", "Content and Syndication", 30, "ACH", 5, arrears=True),
    V("V1050", "Brightline Content Studio", "Content and Syndication", 15, "ACH", 5, is_1099=True, approval=True,
      arrears=True),
    V("V1051", "Ledgerwise Partners", "Partner Marketing", 60, "ACH", 15, approval=True, arrears=True),
    V("V1052", "Northstar CPA Alliance", "Partner Marketing", 60, "ACH", 15, approval=True, arrears=True),
    V("V1060", "Harborview Properties", "Rent", 0, "ACH", 1),
    V("V1061", "Eastgate Office Partners", "Rent", 0, "ACH", 1),
    V("V1062", "Metro Facility Services", "Facilities", 15, "ACH", 5, approval=True, arrears=True),
    V("V1063", "City Utilities", "Facilities", 15, "ACH", 12, arrears=True),
    V("V1064", "Amazon Business", "Office Supplies", 30, "ACH", 25),
    V("V1065", "CDW", "Computer Equipment", 30, "ACH", 20),
    V("V1066", "American Express", "Corporate Card", 25, "ACH", 22),
    V("V1067", "Summit Risk Advisors", "Insurance", 30, "ACH", 1),
    V("V1070", "Brennan Cole LLP", "Legal", 30, "Check", 10, is_1099=True, approval=True, arrears=True),
    V("V1071", "Hartwell & Pierce LLP", "Audit and Tax", 30, "ACH", 10, approval=True, arrears=True),
    V("V1072", "Talentbridge Search", "Recruiting", 30, "ACH", 15, approval=True),
    V("V1073", "Northwind Software Partners", "Contract Engineering", 45, "ACH", 5, is_1099=True, approval=True,
      arrears=True),
)}

# Usage vendors: the account's monthly amount is split by these shares (they add to 1).
USAGE_SHARES: dict[str, tuple[tuple[str, Decimal], ...]] = {
    "5000": (("V1001", Decimal("0.80")), ("V1002", Decimal("0.13")), ("V1003", Decimal("0.07"))),
    "5030": (("V1004", Decimal("0.35")), ("V1005", Decimal("0.25")), ("V1006", Decimal("0.25")),
             ("V1007", Decimal("0.15"))),
    "6410": (("V1001", Decimal("0.90")), ("V1002", Decimal("0.10"))),
    "6300": (("V1040", Decimal("0.85")), ("V1041", Decimal("0.15"))),
    "6310": (("V1034", Decimal("0.70")), ("V1042", Decimal("0.30"))),
    "6320": (("V1043", Decimal("0.20")), ("V1044", Decimal("0.15")), ("V1045", Decimal("0.40")),
             ("V1046", Decimal("0.25"))),
    "6330": (("V1047", Decimal("0.25")), ("V1048", Decimal("0.30")), ("V1049", Decimal("0.15")),
             ("V1050", Decimal("0.30"))),
    "6340": (("V1051", Decimal("0.50")), ("V1052", Decimal("0.50"))),
}
USAGE_ACCOUNTS = frozenset(USAGE_SHARES)

ALL = None  # every team
SALES_CLOSERS = {"SALES-AE", "SALES-MGMT"}
# (vendor, account, department, cost center, teams that hold a seat, 2024 price per seat per month, first month)
MONTHLY_SEATS = (
    ("V1010", "6400", "G&A", "GA-IT", ALL, Decimal("16.80"), None),
    ("V1011", "6400", "G&A", "GA-IT", ALL, Decimal("13.33"), None),
    ("V1012", "6400", "G&A", "GA-IT", ALL, Decimal("7.99"), None),
    ("V1013", "6400", "G&A", "GA-IT", ALL, Decimal("10.00"), None),
    ("V1014", "6400", "G&A", "GA-PEOPLE", ALL, Decimal("35.00"), None),
    ("V1027", "6400", "Engineering", "ENG-MGMT", {"Engineering"}, Decimal("40.00"), "2025-01"),
    ("V1034", "6220", "Sales", "SALES-OPS", {"SALES-AE", "SALES-SDR", "SALES-MGMT"}, Decimal("99.99"), None),
)
# (vendor, account, department, cost center, teams, 2024 price per seat per month, renewal month)
ANNUAL_SEATS = (
    ("V1030", "6220", "Sales", "SALES-OPS", {"Sales", "Customer Success"}, Decimal("165"), 2),
    ("V1031", "6220", "Sales", "SALES-OPS", {"SALES-AE", "SALES-MGMT", "CS-CSM", "CS-MGMT"}, Decimal("110"), 6),
    ("V1032", "6220", "Sales", "SALES-OPS", {"SALES-AE", "SALES-SDR", "SALES-MGMT"}, Decimal("95"), 4),
    ("V1015", "6400", "G&A", "GA-IT", ALL, Decimal("12.50"), 3),
    ("V1016", "6400", "G&A", "GA-IT", ALL, Decimal("8"), 9),
    ("V1017", "6400", "Engineering", "ENG-MGMT", {"Engineering"}, Decimal("21"), 11),
    ("V1018", "6400", "Engineering", "ENG-MGMT", {"Engineering", "Product"}, Decimal("15.25"), 8),
    ("V1019", "6400", "Product", "PROD-DESIGN", {"Product", "MKT-PROD"}, Decimal("45"), 5),
    ("V1021", "6400", "Support", "SUP-OPS", {"Support"}, Decimal("115"), 7),
)
# (vendor, account, department, cost center, renewal month, {renewal year: annual amount}, description)
ANNUAL_FIXED = (
    ("V1001", "5000", "Engineering", "ENG-DEVOPS", 10, {2023: 2400000, 2024: 2900000, 2025: 3400000, 2026: 3900000},
     "AWS Compute Savings Plan, 1-year term paid all upfront (about a third of production compute)"),
    ("V1020", "6420", "Engineering", "ENG-DATA", 1, {2023: 180000, 2024: 240000, 2025: 300000, 2026: 360000},
     "Snowflake capacity commitment"),
    ("V1023", "6400", "Finance", "FIN-ACCT", 1, {2023: 84000, 2024: 96000, 2025: 110000, 2026: 125000},
     "NetSuite ERP subscription"),
    ("V1034", "6535", "G&A", "GA-PEOPLE", 1, {2023: 60000, 2024: 72000, 2025: 96000, 2026: 104000},
     "LinkedIn Recruiter seats"),
    ("V1024", "6400", "Finance", "FIN-ACCT", 4, {2023: 24000, 2024: 28000, 2025: 32000, 2026: 36000},
     "Carta equity management"),
    ("V1025", "6400", "G&A", "GA-LEGAL", 9, {2023: 36000, 2024: 42000, 2025: 48000, 2026: 54000},
     "Ironclad contract management"),
    ("V1033", "6220", "Sales", "SALES-OPS", 10, {2023: 48000, 2024: 54000, 2025: 60000, 2026: 66000},
     "ZoomInfo data subscription"),
    ("V1022", "6400", "Customer Success", "CS-REVOPS", 12, {2023: 42000, 2024: 48000, 2025: 54000, 2026: 60000},
     "ChurnZero customer success platform"),
    ("V1067", "6520", "G&A", "GA-OPS", 1, {2023: 48000, 2024: 55000, 2025: 64000, 2026: 72000},
     "General liability, property and workers' compensation policy"),
    ("V1067", "6520", "G&A", "GA-OPS", 3, {2023: 150000, 2024: 165000, 2025: 185000, 2026: 205000},
     "Directors and officers policy"),
    ("V1067", "6520", "G&A", "GA-OPS", 7, {2023: 95000, 2024: 110000, 2025: 130000, 2026: 150000},
     "Cyber and technology errors and omissions policy"),
)
# (vendor, account, department, cost center, {year: monthly amount}, first month, description, monthly noise)
MONTHLY_FIXED = (
    ("V1028", "6400", "Marketing", "MKT-OPS", {2023: 4300, 2024: 4300, 2025: 5000, 2026: 5800}, None,
     "HubSpot Marketing Hub", False),
    ("V1026", "6400", "Finance", "FIN-ACCT", {2023: 1100, 2024: 1200, 2025: 1350, 2026: 1500}, None,
     "Bill.com AP automation", False),
    ("V1073", "6130", "Engineering", "ENG-APP", {2023: 42000, 2024: 42000, 2025: 36000, 2026: 28000}, None,
     "Contract engineering", False),
    ("V1070", "6500", "G&A", "GA-LEGAL", {2023: 24000, 2024: 24000, 2025: 28000, 2026: 32000}, None,
     "Outside counsel: commercial contracts, employment and corporate matters", True),
)
LEASE_ESCALATION = Decimal("0.03")
LEASE_DEPARTMENT, LEASE_COST_CENTER = "G&A", "GA-OPS"
# Incremental borrowing rate used to discount the lease payments (ASC 842).
LEASE_DISCOUNT_RATE = Decimal("0.07")
# Audit and tax: {fiscal year audited: fee}, billed in progress bills the next year.
AUDIT_FEES = {2022: 190000, 2023: 210000, 2024: 240000, 2025: 275000}
AUDIT_BILLING = ((2, Decimal("0.30")), (3, Decimal("0.45")), (4, Decimal("0.25")))
TAX_FEES = {2022: 48000, 2023: 52000, 2024: 58000, 2025: 64000}
TAX_BILLING = ((3, Decimal("0.60")), (10, Decimal("0.40")))
# Actual bills paid in their scheduled run; the late ones miss one run, slip 2-4 weeks, or are disputed for 6-10.
ON_TIME, ON_TIME_APPROVAL = 0.90, 0.60
LATE_ONE_RUN, LATE_WEEKS = 0.70, 0.21
RECRUITING_FEE = Decimal("0.20")
LAPTOP = Decimal("2300")
LAPTOP_LIFE_MONTHS = 36
FACILITIES_PER_OFFICE_HEAD = Decimal("95")
UTILITIES_BASE, UTILITIES_PER_OFFICE_HEAD = Decimal("4000"), Decimal("15")
SUPPLIES_PER_HEAD = Decimal("22")
# Monthly T&E per head by cost center (6230 Sales Travel for Sales and Customer Success, else 6550).
TNE_PER_HEAD = {"SALES-AE": Decimal("900"), "SALES-MGMT": Decimal("1100"), "SALES-SDR": Decimal("120"),
                "SALES-OPS": Decimal("150"), "CS-CSM": Decimal("350"), "CS-MGMT": Decimal("500"),
                "CS-IMPL": Decimal("450"), "GA-EXEC": Decimal("1500")}
TNE_DEFAULT = Decimal("110")
SALES_KICKOFF_PER_HEAD, OFFSITE_PER_HEAD = Decimal("1800"), Decimal("600")


def q(x: Decimal) -> Decimal:
    return x.quantize(CENT, ROUND_HALF_UP)


def unit(key: str) -> float:
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) / 0x100000000


def pidx(p: str) -> int:
    return int(p[:4]) * 12 + int(p[5:7]) - 1


def padd(p: str, n: int) -> str:
    i = pidx(p) + n
    return f"{i // 12}-{i % 12 + 1:02d}"


def prange(a: str, b: str) -> list[str]:
    return [padd(a, i) for i in range(pidx(b) - pidx(a) + 1)]


def last_day(p: str) -> dt.date:
    y, m = int(p[:4]), int(p[5:7])
    return dt.date(y, m, calendar.monthrange(y, m)[1])


def on_day(p: str, day: int) -> dt.date:
    return dt.date(int(p[:4]), int(p[5:7]), min(day, last_day(p).day))


def month(d: dt.date) -> str:
    return f"{d.year}-{d.month:02d}"


def run_on_or_before(d: dt.date) -> dt.date:
    """The Thursday payment run on or before ``d``."""
    return d - dt.timedelta(days=(d.weekday() - 3) % 7)


def run_on_or_after(d: dt.date) -> dt.date:
    return d + dt.timedelta(days=(3 - d.weekday()) % 7)


def price(base: Decimal, year: int) -> Decimal:
    return q(base * (1 + PRICE_GROWTH) ** (year - 2024))


@dataclass
class Line:
    vendor: str
    account: str
    department: str
    cost_center: str
    amount: Decimal
    description: str
    service_start: dt.date
    service_end: dt.date


@dataclass
class Bill:
    id: str
    vendor: str
    number: str
    bill_date: dt.date
    due_date: dt.date
    lines: list[Line]
    paid_date: dt.date | None = None
    payment_id: str = ""
    period: str = ""  # month the bill's services (or the contract) start

    @property
    def total(self) -> Decimal:
        return sum((ln.amount for ln in self.lines), ZERO)


@dataclass
class Contract:
    id: str
    vendor: str
    account: str
    department: str
    cost_center: str
    start: str
    amount: Decimal
    description: str
    months: int = 12

    def amortization(self, p: str) -> Decimal:
        k = pidx(p) - pidx(self.start)
        if not 0 <= k < self.months:
            return ZERO
        each = q(self.amount / self.months)
        return self.amount - each * (self.months - 1) if k == self.months - 1 else each

    def remaining(self, p: str) -> Decimal:
        """Unamortized at the end of ``p``."""
        k = pidx(p) - pidx(self.start)
        if k < 0:
            return ZERO
        return self.amount - sum((self.amortization(padd(self.start, i)) for i in range(min(k + 1, self.months))), ZERO)


@dataclass(frozen=True)
class LeaseMonth:
    period: str
    payment: Decimal
    straight_line_cost: Decimal
    accretion: Decimal
    rou_amortization: Decimal
    new_liability: Decimal
    liability: Decimal
    rou_asset: Decimal


@dataclass(frozen=True)
class Lease:
    """Operating lease (ASC 842): rent paid at the start of each month, escalating every lease year.

    Liability = remaining payments discounted at LEASE_DISCOUNT_RATE; cost = total payments straight-line over the
    term; right-of-use asset = liability less (cumulative cost - cumulative payments)."""
    id: str
    vendor: str
    commencement: str
    months: int
    rent: Decimal
    rent_from: str  # first month of the lease year whose monthly rent is ``rent``
    description: str

    @property
    def end(self) -> str:
        return padd(self.commencement, self.months - 1)

    def payment(self, p: str) -> Decimal:
        if not self.commencement <= p <= self.end:
            return ZERO
        return q(self.rent * (1 + LEASE_ESCALATION) ** ((pidx(p) - pidx(self.rent_from)) // 12))

    @functools.cache
    def schedule(self) -> dict[str, LeaseMonth]:
        months = prange(self.commencement, self.end)
        pays = [self.payment(p) for p in months]
        rate = 1 + LEASE_DISCOUNT_RATE / 12

        def pv(k: int) -> Decimal:
            """Payments k.. at the start of month k."""
            return q(sum((pays[j] / rate ** (j - k) for j in range(k, len(pays))), ZERO))

        total = sum(pays, ZERO)
        each = q(total / self.months)
        out: dict[str, LeaseMonth] = {}
        liability = rou = cum_cost = cum_paid = ZERO
        for k, p in enumerate(months):
            new = pv(0) if k == 0 else ZERO
            cost = total - each * (self.months - 1) if k == self.months - 1 else each
            end = pv(k + 1) if k + 1 < len(pays) else ZERO
            cum_cost += cost
            cum_paid += pays[k]
            end_rou = end - (cum_cost - cum_paid)
            out[p] = LeaseMonth(p, pays[k], cost, end - (liability + new - pays[k]), rou + new - end_rou, new, end,
                                end_rou)
            liability, rou = end, end_rou
        return out

    def at(self, p: str) -> LeaseMonth | None:
        return self.schedule().get(p)

    def balances(self, p: str) -> tuple[Decimal, Decimal]:
        """(lease liability, right-of-use asset) at the end of ``p``."""
        if p < self.commencement or p > self.end:
            return ZERO, ZERO
        m = self.schedule()[p]
        return m.liability, m.rou_asset


LEASES = (
    Lease("LEASE-V1060", "V1060", "2021-03", 84, Decimal("52000"), "2022-03",
          "Harborview Properties headquarters lease, 7 years from March 2021"),
    Lease("LEASE-V1061", "V1061", "2025-04", 60, Decimal("26000"), "2025-04",
          "Eastgate Office Partners second office lease, 5 years from April 2025"),
)


class Roster:
    """Heads and hires by month from {V}_Employees.csv (the Actual roster before the version's first month; months
    before January 2024 use January 2024)."""

    def __init__(self, src: str, version: str):
        self.version = version
        self.files: dict[str, list[dict[str, str]]] = {}
        for v in {"Actual", version}:
            with open(os.path.join(src, f"{v}_Employees.csv"), newline="", encoding="utf-8-sig") as f:
                self.files[v] = list(csv.DictReader(f))
        self._heads: dict[str, dict[tuple[str, str], list[dict[str, str]]]] = {}

    def _source(self, p: str) -> str:
        start = WINDOW[self.version][0] if self.version != "Actual" else FIRST
        return self.version if p >= start else "Actual"

    def staff(self, p: str) -> dict[tuple[str, str], list[dict[str, str]]]:
        p = max(p, FIRST)
        if p not in self._heads:
            end = last_day(p).isoformat()
            out: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
            for e in self.files[self._source(p)]:
                if e["hire_date"] <= end and (not e["termination_date"] or e["termination_date"] > end):
                    out[(e["department"], e["cost_center"])].append(e)
            self._heads[p] = out
        return self._heads[p]

    def heads(self, p: str, teams=ALL) -> int:
        return sum(len(people) for (d, cc), people in self.staff(p).items()
                   if teams is None or d in teams or cc in teams)

    def office_heads(self, p: str) -> int:
        return sum(1 for people in self.staff(p).values() for e in people if e["remote_flag"] != "Yes")

    def hires(self, p: str) -> list[dict[str, str]]:
        if p < FIRST:
            return []
        return [e for e in self.files[self._source(p)] if e["hire_date"][:7] == p]


@dataclass
class Ledger:
    version: str
    bills: list[Bill] = field(default_factory=list)
    contracts: list[Contract] = field(default_factory=list)


class VendorModel:
    def __init__(self, src: str):
        self.src = src
        self.rosters = {v: Roster(src, v) for v in WINDOW}
        self.usage: dict[str, dict[str, list[tuple[str, str, str, Decimal]]]] = {v: defaultdict(list) for v in WINDOW}

    # ------------------------------------------------------------------ spend

    def months(self, version: str) -> list[str]:
        """Months the version bills: Actual from HISTORY_FROM; Budget and Forecast from their first month."""
        a, b = WINDOW[version]
        return prange(HISTORY_FROM if version == "Actual" else a, b)

    def monthly_lines(self, version: str, p: str) -> list[Line]:
        r = self.rosters[version]
        y = max(int(p[:4]), 2023)
        start, end = on_day(p, 1), last_day(p)
        out: list[Line] = []

        def add(vendor, account, dept, cc, amount, desc):
            if q(amount):
                out.append(Line(vendor, account, dept, cc, q(amount), desc, start, end))

        for vendor, account, dept, cc, teams, base, first in MONTHLY_SEATS:
            if first and p < first:
                continue
            n = r.heads(p, teams)
            add(vendor, account, dept, cc, n * price(base, y), f"{n} seats x {price(base, y)}")
        for vendor, account, dept, cc, amounts, first, desc, noisy in MONTHLY_FIXED:
            amt = Decimal(amounts[y])
            if noisy:
                amt *= Decimal(str(round(0.7 + 0.7 * unit(f"{vendor}-{p}"), 4)))
            add(vendor, account, dept, cc, amt, desc)
        for lease in LEASES:
            add(lease.vendor, LEASE_LIABILITY_ACCOUNT, LEASE_DEPARTMENT, LEASE_COST_CENTER, lease.payment(p),
                f"Office rent (operating lease payment; cost is straight-line on {RENT_ACCOUNT})")
        office = r.office_heads(p)
        add("V1062", "6510", "G&A", "GA-OPS", office * FACILITIES_PER_OFFICE_HEAD, f"Cleaning and maintenance, {office} office staff")
        add("V1063", "6510", "G&A", "GA-OPS", UTILITIES_BASE + office * UTILITIES_PER_OFFICE_HEAD, "Utilities")
        add("V1064", "6530", "G&A", "GA-OPS", r.heads(p) * SUPPLIES_PER_HEAD, "Office supplies")
        hires = r.hires(p)
        refresh = Decimal(r.heads(p)) / LAPTOP_LIFE_MONTHS
        add("V1065", "6430", "G&A", "GA-IT", (len(hires) + refresh) * LAPTOP,
            f"Laptops: {len(hires)} new hires and the {LAPTOP_LIFE_MONTHS}-month refresh")
        for (dept, cc), people in sorted(r.staff(p).items()):
            per_head = TNE_PER_HEAD.get(cc, TNE_DEFAULT)
            account = "6230" if dept in ("Sales", "Customer Success") else "6550"
            amt = len(people) * per_head
            note = "Travel and meals"
            if p[5:7] == "01" and dept in ("Sales", "Customer Success"):
                amt += len(people) * SALES_KICKOFF_PER_HEAD
                note += "; sales kickoff"
            if p[5:7] == "09":
                amt += len(people) * OFFSITE_PER_HEAD
                note += "; company offsite"
            amt *= Decimal(str(round(0.85 + 0.3 * unit(f"tne-{cc}-{p}"), 4)))
            add("V1066", account, dept, cc, amt, note)
        audit_year, tax_year = y - 1, y - 1
        for m, share in AUDIT_BILLING:
            if int(p[5:7]) == m and audit_year in AUDIT_FEES:
                add("V1071", "6500", "Finance", "FIN-ACCT", AUDIT_FEES[audit_year] * share, f"FY{audit_year} audit")
        for m, share in TAX_BILLING:
            if int(p[5:7]) == m and tax_year in TAX_FEES:
                add("V1071", "6500", "Finance", "FIN-ACCT", TAX_FEES[tax_year] * share, f"FY{tax_year} tax returns")
        return out

    def hire_bills(self, version: str, p: str) -> list[tuple[dt.date, Line]]:
        out = []
        for e in self.rosters[version].hires(p):
            senior = e["level"] in ("L6", "L7", "L8", "L9", "L10") or (e["department"] == "Engineering" and e["level"] == "L5")
            if not senior:
                continue
            start = dt.date.fromisoformat(e["hire_date"])
            fee = q(Decimal(e["base_salary"]) * RECRUITING_FEE)
            out.append((start, Line("V1072", "6535", e["department"], e["cost_center"], fee,
                                    f"Placement fee: {e['role']} ({e['employee_id']})", start, start)))
        return out

    def contracts(self, version: str) -> list[Contract]:
        """Annual contracts that renew in the version's months (Actual's before them)."""
        out: list[Contract] = []
        for v in ({"Actual", version} if version != "Actual" else {"Actual"}):
            r = self.rosters[v]
            for p in self.months(v):
                if v == "Actual" and version != "Actual" and p >= WINDOW[version][0]:
                    continue
                y, m = max(int(p[:4]), 2023), int(p[5:7])
                for vendor, account, dept, cc, teams, base, renew in ANNUAL_SEATS:
                    if m == renew and (n := r.heads(p, teams)):
                        out.append(Contract(f"{v[0]}C-{vendor}-{p}", vendor, account, dept, cc, p,
                                            q(n * price(base, y) * 12), f"{n} seats x {price(base, y)} x 12 months"))
                for vendor, account, dept, cc, renew, amounts, desc in ANNUAL_FIXED:
                    if m == renew and y in amounts:
                        out.append(Contract(f"{v[0]}C-{vendor}-{account}-{p}", vendor, account, dept, cc, p,
                                            Decimal(amounts[y]), desc))
        return sorted(out, key=lambda c: (c.start, c.vendor, c.id))

    def add_usage(self, version: str, period: str, account: str, department: str, cost_center: str, amount: Decimal):
        if account not in USAGE_SHARES:
            raise ValueError(f"{account} has no usage vendors")
        self.usage[version][period].append((account, department, cost_center, amount))

    def usage_lines(self, version: str, p: str) -> list[Line]:
        rows = self.usage[version].get(p)
        if rows is None and version == "Actual" and p < FIRST:
            rows = self.usage[version].get(FIRST, [])
        out = []
        for account, dept, cc, amount in rows or []:
            shares = USAGE_SHARES[account]
            parts = [q(amount * s) for _, s in shares]
            parts[0] += amount - sum(parts, ZERO)
            for (vendor, _), part in zip(shares, parts):
                if part:
                    out.append(Line(vendor, account, dept, cc, part, "Usage", on_day(p, 1), last_day(p)))
        return out

    # ------------------------------------------------------------------ bills and payments

    def ledger(self, version: str, actual: Ledger | None = None) -> Ledger:
        led = Ledger(version)
        months = self.months(version)
        drafts: list[tuple[dt.date, str, list[Line], str]] = []
        for p in months:
            by_vendor: dict[str, list[Line]] = defaultdict(list)
            for ln in self.monthly_lines(version, p) + self.usage_lines(version, p):
                by_vendor[ln.vendor].append(ln)
            for vendor, lines in by_vendor.items():
                v = VENDORS[vendor]
                drafts.append((on_day(padd(p, 1) if v.arrears else p, v.bill_day), vendor, lines, p))
            for d, ln in self.hire_bills(version, p):
                drafts.append((d, ln.vendor, [ln], p))
        led.contracts = self.contracts(version)
        for c in led.contracts:
            if c.start in months:
                end = last_day(padd(c.start, c.months - 1))
                drafts.append((on_day(c.start, VENDORS[c.vendor].bill_day), c.vendor,
                               [Line(c.vendor, PREPAID_ACCOUNT, c.department, c.cost_center, c.amount,
                                     f"{c.description} (prepaid; expensed to {c.account} over {c.months} months)",
                                     on_day(c.start, 1), end)], c.start))
        drafts.sort(key=lambda t: (t[0], t[1]))
        prefix = {"Actual": "BILL", "Budget": "BBILL", "Forecast": "FBILL"}[version]
        counter: dict[str, int] = defaultdict(int)
        for n, (d, vendor, lines, p) in enumerate(drafts, 1):
            v = VENDORS[vendor]
            counter[vendor] += 1
            bill = Bill(f"{prefix}-{p.replace('-', '')}-{n:05d}", vendor,
                        f"{vendor[1:]}-{d.strftime('%y%m')}{counter[vendor]:03d}", d, d + dt.timedelta(days=v.terms),
                        lines, period=p)
            bill.paid_date = self._pay_date(bill, late=version == "Actual")
            led.bills.append(bill)
        if version == "Actual":
            # Bills dated after the close (services through the close billed in arrears) stay in the ledger,
            # unpaid: they are the accrued expenses at the close. The Actual files leave them out.
            close = last_day(CLOSE)
            for b in led.bills:
                if b.paid_date and b.paid_date > close:
                    b.paid_date = None
        else:
            start_month = WINDOW[version][0]
            start = dt.date.fromisoformat(f"{start_month}-01")
            carried = [b for b in (actual.bills if actual else [])
                       if b.period < start_month and (b.paid_date is None or b.paid_date >= start)]
            for b in carried:
                nb = Bill(b.id, b.vendor, b.number, b.bill_date, b.due_date, b.lines, period=b.period)
                nb.paid_date = max(self._pay_date(nb, late=False), run_on_or_after(start))
                led.bills.append(nb)
        payments: dict[tuple[str, dt.date], str] = {}
        for b in led.bills:
            if b.paid_date:
                key = (b.vendor, b.paid_date)
                payments.setdefault(key, f"{prefix.replace('BILL', 'PAY')}-{b.paid_date.strftime('%Y%m%d')}-{b.vendor}")
                b.payment_id = payments[key]
        return led

    @staticmethod
    def _pay_date(bill: Bill, late: bool) -> dt.date:
        v = VENDORS[bill.vendor]
        if v.terms == 0 or v.method == "Autopay":
            return bill.bill_date
        scheduled = max(run_on_or_before(bill.due_date), run_on_or_after(bill.bill_date))
        if not late:
            return scheduled
        on_time = ON_TIME_APPROVAL if v.approval else ON_TIME
        u = unit(f"pay-{bill.id}")
        if u < on_time:
            return scheduled
        r = (u - on_time) / (1 - on_time)
        if r < LATE_ONE_RUN:
            return scheduled + dt.timedelta(days=7)
        if r < LATE_ONE_RUN + LATE_WEEKS:
            return scheduled + dt.timedelta(days=7 * (2 + int(unit(f"wk-{bill.id}") * 3)))
        return scheduled + dt.timedelta(days=7 * (6 + int(unit(f"wk-{bill.id}") * 5)))


def open_bills(bills: list[Bill], as_of: dt.date) -> list[Bill]:
    return [b for b in bills if b.bill_date <= as_of and (b.paid_date is None or b.paid_date > as_of)]


AGING_BUCKETS = (("current", None), ("days_1_30", 30), ("days_31_60", 60), ("days_61_90", 90), ("days_over_90", None))


def aging_bucket(bill: Bill, as_of: dt.date) -> str:
    late = (as_of - bill.due_date).days
    if late <= 0:
        return "current"
    if late <= 30:
        return "days_1_30"
    if late <= 60:
        return "days_31_60"
    if late <= 90:
        return "days_61_90"
    return "days_over_90"


# ---------------------------------------------------------------------- files

def bills_in(ledger: Ledger, p: str) -> list[Bill]:
    return [b for b in ledger.bills if month(b.bill_date) == p]


def payments_in(ledger: Ledger, p: str) -> list[Bill]:
    return [b for b in ledger.bills if b.paid_date and month(b.paid_date) == p]


def ap_balance(ledger: Ledger, p: str) -> Decimal:
    return sum((b.total for b in open_bills(ledger.bills, last_day(p))), ZERO)


def prepaid_balance(ledger: Ledger, p: str) -> Decimal:
    return sum((c.remaining(p) for c in ledger.contracts), ZERO)


def accrued_lines(ledger: Ledger, p: str) -> list[tuple[Bill, int, Line]]:
    """Expense lines for services through the end of ``p`` that are billed after it: (bill, line number, line)."""
    as_of = last_day(p)
    return [(b, i, ln) for b in ledger.bills if b.bill_date > as_of
            for i, ln in enumerate(b.lines, 1)
            if ln.account not in BALANCE_SHEET_LINE_ACCOUNTS and month(ln.service_start) <= p]


def accrued_balance(ledger: Ledger, p: str) -> Decimal:
    return sum((ln.amount for _, _, ln in accrued_lines(ledger, p)), ZERO)


def accrual_moves(ledger: Ledger, p: str) -> tuple[list[tuple[Bill, int, Line]], list[tuple[Bill, int, Line]]]:
    """(services in ``p`` not billed by its end, earlier months' accrued services billed in ``p``)."""
    as_of = last_day(p)
    accrued = [(b, i, ln) for b, i, ln in accrued_lines(ledger, p) if month(ln.service_start) == p]
    billed = [(b, i, ln) for b, i, ln in accrued_lines(ledger, padd(p, -1)) if b.bill_date <= as_of]
    return accrued, billed


def lease_balances(p: str) -> tuple[Decimal, Decimal]:
    """(lease liabilities, right-of-use assets) at the end of ``p``."""
    out = [lease.balances(p) for lease in LEASES]
    return sum((x for x, _ in out), ZERO), sum((y for _, y in out), ZERO)


def terms_label(v: Vendor) -> str:
    return "Due on receipt" if v.terms == 0 else f"Net {v.terms}"


def file_names() -> list[str]:
    """Every file write_files writes (sync_v5_statements.py copies them into the dataset)."""
    names = ["Actual_vendor_master.csv", "Actual_vendor_bills.csv", "Actual_vendor_payments.csv", "Actual_AP_Aging.csv",
             "Actual_accrued_expenses_detail.csv"]
    for v in WINDOW:
        names += [f"{v}_Prepaid_Amortization_Schedule.csv", f"{v}_Prepaids_Rollforward.csv",
                  f"{v}_accounts_payable_rollforward.csv", f"{v}_accrued_expenses_rollforward.csv",
                  f"{v}_operating_lease_schedule.csv"]
    return names + ["Budget_vendor_spend_plan.csv", "Forecast_vendor_spend_plan.csv"]


def _write(path: str, fields: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{r[k]:.2f}" if isinstance(r.get(k), Decimal) else r.get(k, "")) for k in fields})


def write_files(dst: str, org: str, model: VendorModel, ledgers: dict[str, Ledger]) -> list[str]:
    notes: list[str] = []
    actual = ledgers["Actual"]
    close = last_day(CLOSE)
    first = dt.date.fromisoformat(f"{FIRST}-01")

    on_books = [b for b in actual.bills if b.bill_date <= close]
    spend: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for b in on_books:
        for ln in b.lines:
            spend[b.vendor][RENT_ACCOUNT if ln.account == LEASE_LIABILITY_ACCOUNT else ln.account] += ln.amount
    _write(os.path.join(dst, "Actual_vendor_master.csv"),
           ["organization_id", "vendor_id", "vendor_name", "vendor_category", "payment_terms", "payment_terms_days",
            "payment_method", "billing_day", "bills_in_arrears", "is_1099", "invoice_approval", "default_account",
            "status"],
           [{"organization_id": org, "vendor_id": v.id, "vendor_name": v.name, "vendor_category": v.category,
             "payment_terms": terms_label(v), "payment_terms_days": str(v.terms), "payment_method": v.method,
             "billing_day": "last" if v.bill_day >= 28 else str(v.bill_day),
             "bills_in_arrears": "Yes" if v.arrears else "No", "is_1099": "Yes" if v.is_1099 else "No",
             "invoice_approval": "Budget owner" if v.approval else "AP", "default_account": max(spend[v.id], key=spend[v.id].get) if spend[v.id] else "",
             "status": "Active" if spend[v.id] else "Inactive"} for v in VENDORS.values()])

    # Bills dated from the GL's first month through the close, plus older bills still open when it starts.
    listed = [b for b in on_books if b.bill_date >= first or b.paid_date is None or b.paid_date >= first]
    rows = []
    for b in listed:
        v = VENDORS[b.vendor]
        for i, ln in enumerate(b.lines, 1):
            rows.append({"organization_id": org, "version": "Actual", "bill_id": b.id, "bill_number": b.number,
                         "vendor_id": v.id, "vendor_name": v.name, "bill_date": b.bill_date.isoformat(),
                         "due_date": b.due_date.isoformat(), "payment_terms": terms_label(v), "line_number": str(i),
                         "account_number": ln.account, "department": ln.department, "cost_center": ln.cost_center,
                         "description": ln.description, "service_start": ln.service_start.isoformat(),
                         "service_end": ln.service_end.isoformat(), "period": month(ln.service_start),
                         "amount": ln.amount, "bill_total": b.total,
                         "status": "Paid" if b.paid_date else "Open",
                         "paid_date": b.paid_date.isoformat() if b.paid_date else "", "payment_id": b.payment_id})
    _write(os.path.join(dst, "Actual_vendor_bills.csv"),
           ["organization_id", "version", "bill_id", "bill_number", "vendor_id", "vendor_name", "bill_date", "due_date",
            "payment_terms", "line_number", "account_number", "department", "cost_center", "description",
            "service_start", "service_end", "period", "amount", "bill_total", "status", "paid_date", "payment_id"], rows)
    open_at_close = [b for b in listed if b.paid_date is None]
    notes.append(f"Actual_vendor_bills.csv: {len(listed)} bills, {len(rows)} lines; {len(open_at_close)} open at the "
                 f"close ({sum((b.total for b in open_at_close), ZERO):,.2f})")

    paid = sorted((b for b in actual.bills if b.paid_date and b.paid_date >= first), key=lambda b: (b.paid_date, b.id))
    _write(os.path.join(dst, "Actual_vendor_payments.csv"),
           ["organization_id", "version", "vendor_payment_id", "period", "vendor_id", "vendor_name", "expense_category",
            "invoice_date", "payment_date", "amount", "payment_terms", "currency", "bill_id", "due_date",
            "payment_method", "days_past_due"],
           [{"organization_id": org, "version": "Actual", "vendor_payment_id": b.payment_id,
             "period": month(b.paid_date), "vendor_id": b.vendor, "vendor_name": VENDORS[b.vendor].name,
             "expense_category": VENDORS[b.vendor].category, "invoice_date": b.bill_date.isoformat(),
             "payment_date": b.paid_date.isoformat(), "amount": b.total, "payment_terms": terms_label(VENDORS[b.vendor]),
             "currency": "USD", "bill_id": b.id, "due_date": b.due_date.isoformat(),
             "payment_method": VENDORS[b.vendor].method,
             "days_past_due": str(max(0, (b.paid_date - b.due_date).days))} for b in paid])
    late = [b for b in paid if b.paid_date > b.due_date]
    notes.append(f"Actual_vendor_payments.csv: {len(paid)} bills paid, {len(late)} after the due date")

    buckets = [k for k, _ in AGING_BUCKETS]
    rows = []
    for p in prange(FIRST, CLOSE):
        as_of = last_day(p)
        by_vendor: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
        for b in open_bills(actual.bills, as_of):
            by_vendor[b.vendor][aging_bucket(b, as_of)] += b.total
        for vid in sorted(by_vendor):
            amounts = by_vendor[vid]
            rows.append({"organization_id": org, "version": "Actual", "period": p, "vendor_id": vid,
                         "vendor_name": VENDORS[vid].name, **{k: amounts[k] for k in buckets},
                         "total": sum(amounts.values(), ZERO)})
    _write(os.path.join(dst, "Actual_AP_Aging.csv"),
           ["organization_id", "version", "period", "vendor_id", "vendor_name", *buckets, "total"], rows)

    rows = []
    for p in prange(FIRST, CLOSE):
        for b, i, ln in accrued_lines(actual, p):
            billed = b.bill_date <= close
            rows.append({"organization_id": org, "version": "Actual", "period": p, "vendor_id": b.vendor,
                         "vendor_name": VENDORS[b.vendor].name, "account_number": ln.account,
                         "department": ln.department, "cost_center": ln.cost_center, "description": ln.description,
                         "service_period": month(ln.service_start), "amount": ln.amount,
                         "bill_id": b.id if billed else "", "bill_date": b.bill_date.isoformat() if billed else "",
                         "line_number": str(i) if billed else "",
                         "status": "Billed" if billed else "Not billed at the close"})
    _write(os.path.join(dst, "Actual_accrued_expenses_detail.csv"),
           ["organization_id", "version", "period", "vendor_id", "vendor_name", "account_number", "department",
            "cost_center", "description", "service_period", "amount", "bill_id", "bill_date", "line_number", "status"],
           rows)
    unbilled = accrued_balance(actual, CLOSE)
    notes.append(f"Actual_accrued_expenses_detail.csv: {len(rows)} accrued lines; {unbilled:,.2f} of services "
                 f"through the close not billed by it")

    for version, led in ledgers.items():
        months = prange(*WINDOW[version])
        rows, roll = [], []
        for p in months:
            for c in led.contracts:
                begin, end = c.remaining(padd(p, -1)), c.remaining(p)
                added = c.amount if c.start == p else ZERO
                amort = c.amortization(p)
                if not (begin or added or amort):
                    continue
                rows.append({"organization_id": org, "version": version, "period": p, "contract_id": c.id,
                             "vendor_id": c.vendor, "vendor_name": VENDORS[c.vendor].name, "account_number": c.account,
                             "department": c.department, "cost_center": c.cost_center, "description": c.description,
                             "service_start": c.start, "service_months": str(c.months), "contract_amount": c.amount,
                             "beginning_balance": begin, "additions": added, "amortization": amort,
                             "ending_balance": end})
            begin, end = prepaid_balance(led, padd(p, -1)), prepaid_balance(led, p)
            added = sum((c.amount for c in led.contracts if c.start == p), ZERO)
            amort = sum((c.amortization(p) for c in led.contracts), ZERO)
            roll.append({"organization_id": org, "version": version, "period": p, "beginning_prepaid_balance": begin,
                         "prepaid_additions": added, "prepaid_amortization": amort, "ending_prepaid_balance": end,
                         "rollforward_check": begin + added - amort - end})
        _write(os.path.join(dst, f"{version}_Prepaid_Amortization_Schedule.csv"),
               ["organization_id", "version", "period", "contract_id", "vendor_id", "vendor_name", "account_number",
                "department", "cost_center", "description", "service_start", "service_months", "contract_amount",
                "beginning_balance", "additions", "amortization", "ending_balance"], rows)
        _write(os.path.join(dst, f"{version}_Prepaids_Rollforward.csv"),
               ["organization_id", "version", "period", "beginning_prepaid_balance", "prepaid_additions",
                "prepaid_amortization", "ending_prepaid_balance", "rollforward_check"], roll)

        ap = []
        for p in months:
            begin, end = ap_balance(led, padd(p, -1)), ap_balance(led, p)
            billed = sum((b.total for b in bills_in(led, p)), ZERO)
            paid_out = sum((b.total for b in payments_in(led, p)), ZERO)
            ap.append({"organization_id": org, "version": version, "period": p, "beginning_accounts_payable": begin,
                       "vendor_expense_accruals": billed, "vendor_cash_payments_n30": paid_out,
                       "ending_accounts_payable": end, "rollforward_check": begin + billed - paid_out - end})
        _write(os.path.join(dst, f"{version}_accounts_payable_rollforward.csv"),
               ["organization_id", "version", "period", "beginning_accounts_payable", "vendor_expense_accruals",
                "vendor_cash_payments_n30", "ending_accounts_payable", "rollforward_check"], ap)

        acc = []
        for p in months:
            begin, end = accrued_balance(led, padd(p, -1)), accrued_balance(led, p)
            accrued, billed = accrual_moves(led, p)
            added = sum((ln.amount for _, _, ln in accrued), ZERO)
            relieved = sum((ln.amount for _, _, ln in billed), ZERO)
            acc.append({"organization_id": org, "version": version, "period": p, "beginning_accrued_expenses": begin,
                        "services_accrued": added, "accruals_billed": relieved, "ending_accrued_expenses": end,
                        "rollforward_check": begin + added - relieved - end})
        _write(os.path.join(dst, f"{version}_accrued_expenses_rollforward.csv"),
               ["organization_id", "version", "period", "beginning_accrued_expenses", "services_accrued",
                "accruals_billed", "ending_accrued_expenses", "rollforward_check"], acc)

        rows = []
        for lease in LEASES:
            for p in months:
                m = lease.at(p)
                if m is None:
                    continue
                liab, rou = lease.balances(padd(p, -1))
                rows.append({"organization_id": org, "version": version, "period": p, "lease_id": lease.id,
                             "vendor_id": lease.vendor, "vendor_name": VENDORS[lease.vendor].name,
                             "description": lease.description, "commencement": lease.commencement,
                             "term_months": str(lease.months), "discount_rate": f"{LEASE_DISCOUNT_RATE:.4f}",
                             "beginning_lease_liability": liab, "new_lease_liability": m.new_liability,
                             "lease_payment": m.payment, "interest_accretion": m.accretion,
                             "ending_lease_liability": m.liability, "beginning_rou_asset": rou,
                             "new_rou_asset": m.new_liability, "rou_amortization": m.rou_amortization,
                             "ending_rou_asset": m.rou_asset, "straight_line_cost": m.straight_line_cost})
        _write(os.path.join(dst, f"{version}_operating_lease_schedule.csv"),
               ["organization_id", "version", "period", "lease_id", "vendor_id", "vendor_name", "description",
                "commencement", "term_months", "discount_rate", "beginning_lease_liability", "new_lease_liability",
                "lease_payment", "interest_accretion", "ending_lease_liability", "beginning_rou_asset", "new_rou_asset",
                "rou_amortization", "ending_rou_asset", "straight_line_cost"], rows)

        if version != "Actual":
            plan: dict[tuple, Decimal] = defaultdict(Decimal)
            basis: dict[tuple, str] = {}
            for b in led.bills:
                for ln in b.lines:
                    p = month(ln.service_start)
                    if ln.account in BALANCE_SHEET_LINE_ACCOUNTS or p not in months:
                        continue
                    key = (p, ln.vendor, ln.account, ln.department, ln.cost_center)
                    plan[key] += ln.amount
                    basis.setdefault(key, ln.description)
            for lease in LEASES:
                for p in months:
                    m = lease.at(p)
                    if m is not None:
                        key = (p, lease.vendor, RENT_ACCOUNT, LEASE_DEPARTMENT, LEASE_COST_CENTER)
                        plan[key] += m.straight_line_cost
                        basis.setdefault(key, f"{lease.description}: straight-line lease cost")
            for c in led.contracts:
                for p in months:
                    if c.amortization(p):
                        key = (p, c.vendor, c.account, c.department, c.cost_center)
                        plan[key] += c.amortization(p)
                        basis.setdefault(key, f"{c.description} (amortization of the {c.start} prepaid)")
            _write(os.path.join(dst, f"{version}_vendor_spend_plan.csv"),
                   ["organization_id", "version", "period", "vendor_id", "vendor_name", "account_number", "department",
                    "cost_center", "amount", "basis"],
                   [{"organization_id": org, "version": version, "period": k[0], "vendor_id": k[1],
                     "vendor_name": VENDORS[k[1]].name, "account_number": k[2], "department": k[3],
                     "cost_center": k[4], "amount": amt, "basis": basis[k]} for k, amt in sorted(plan.items())])
    return notes
