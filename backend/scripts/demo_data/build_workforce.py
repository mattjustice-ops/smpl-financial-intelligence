"""Workforce: one employee roster, sized to the headcount plan; the GL books its payroll.

Writes a new folder only (never touches the database):
  python build_workforce.py <source_folder> <output_folder>

The output is a copy of the source with these files replaced or added:
  {V}_Employees.csv           the HRIS roster. Actual: everyone employed Jan 2024-Jun 2026, exits included.
                              Budget: the Dec 2025 roster plus the budget's planned hires. Forecast: the Actual
                              roster plus planned hires Jul-Dec 2026.
  {V}_payroll_register.csv    employee x month: wages, bonus, severance, employer payroll tax, health benefits and
                              401(k) match (Actual Jan 2024-Jun 2026, Budget 2026, Forecast Jul-Dec 2026)
  {V}_payroll_policies.csv    the pay policies the register applies (the company's onboarding answers)
  {V}_Headcount_Plan.csv      by GL department and month, counted from the roster; payroll from the register
  {V}_SBC_Schedule.csv        stock comp by P&L line and month from the roster's equity grants (stock_comp.py)
  {V}_Open_Requisitions.csv   one requisition per hire: filled through the June close, open after
  Compensation_Bands.csv      every role on the roster (2026 midpoints)
  Department_Allocation_Rules.csv  GL departments and the P&L line each cost center posts to
  {V}_chart_of_accounts.csv   every account the GL posts: the payroll accounts the register posts to, 6200/6210
                              commissions (Sales Travel moves from 6210 to 6230; no GL rows used it), 5040/6140 stock
                              comp, the vendor accounts of vendor_model.py and the balance sheet accounts of
                              build_gl_balance_sheet.py; the removed Accounting True-Up plug is gone
  Workforce_Planning_Validation_Summary.csv is removed (a v4 check of the old roster).

Rules (agreed with Matt, Oct 8 2026):
  * Headcount is the plan (HEADCOUNT_PLAN): month-end heads by team in Jan 2024, Dec 2025, at the June 2026 close
    and in Dec 2026 (Budget, Forecast), straight-line between them; exits are backfilled the next month. About 250
    at the close and 270-275 at Dec 2026 for an ~$88M-ARR company. rebuild_gl_to_summary books payroll from the
    register and stock comp from the grants; S&M and cost of revenue keep their P&L totals (marketing programs and
    hosting take the rest), R&D and G&A are payroll, stock comp and vendor spend (Oct 9 2026). A team's payroll may
    not exceed PAYROLL_SHARE_CAP of its P&L line.
  * Stock comp: each employee's equity_sbc_annual (the role's grant value per year), expensed for the days employed.
  * Teams are the GL departments and cost centers (department_cost_centers.csv). Every role has a cost center, an
    HRIS team (sub_department), a pay plan and a 2026 band. Leaders are on staff from before 2024; other hires keep
    each team's role mix.
  * Pay: salaries are the 2026 band midpoint x a personal factor (0.92-1.08), less the merit increases since hire.
    Merit increases are 3.5% every April 1 for employees hired before January 1 of that year. Bonus plans pay their
    target % of salary and the SDR incentive its target amount, monthly with payroll. Commission plans (AEs and
    CSMs) are paid from the commission files, not the register.
  * Exits (Actual only): each employee with 6+ months of tenure leaves in a month with probability 0.70%
    (voluntary) or 0.25% (involuntary); leaders stay. Exits are on the 15th or the last day of the month.
    Involuntary exits get 2 weeks of base salary per completed year of service (4 to 26 weeks), paid in the exit
    month. Budget and Forecast plan no exits.
  * Hires start on the 1st or the 16th; wages are paid for the days employed. Health benefits are paid for every
    month the employee is on staff on the 1st. Employer payroll tax is 8% of wages, bonus and severance. The 401(k)
    match is 100% of the employee's deferral up to 4% of wages and bonus.
  * Sales and Customer Success hires work the CRM territory with the most Actual opportunities per head in their
    role group (sales_team.py), so coverage follows demand.
"""

from __future__ import annotations

import calendar
import copy
import csv
import datetime as dt
import hashlib
import os
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_gl_balance_sheet import ACCOUNTS as BS_ACCOUNTS  # noqa: E402
from rebuild_gl_to_summary import COGS_PAYROLL, PAYROLL_COLUMNS  # noqa: E402
from sales_team import BOOKINGS_ROLES, TEAM_DEPARTMENTS, TERRITORIES, employee_names, role_group  # noqa: E402
from stock_comp import SBC_ACCOUNTS, SBC_EXPENSE_TYPE, SCHEDULE_FIELDS, schedule_rows  # noqa: E402
from vendor_model import CONTRACTOR_ACCOUNT, VENDOR_ACCOUNTS  # noqa: E402

CENT = Decimal("0.01")
ZERO = Decimal("0")
VERSIONS = ("Actual", "Budget", "Forecast")
FIRST, CLOSE = "2024-01", "2026-06"
WINDOW = {"Actual": (FIRST, CLOSE), "Budget": ("2026-01", "2026-12"), "Forecast": ("2026-07", "2026-12")}
BUDGET_FROM = "2025-12"
ID_PREFIX = {"Actual": "EMP-", "Budget": "BEMP-", "Forecast": "FEMP-"}
ID_START = {"Actual": 1001, "Budget": 5001, "Forecast": 7001}
REQ_PREFIX = {"Actual": "AREQ-", "Budget": "BREQ-", "Forecast": "FREQ-"}
PLAN_POINTS = ("2024-01", "2025-12", CLOSE)
HEADCOUNT_PLAN = {
    #                         Jan 2024  Dec 2025  Jun 2026  Budget Dec 2026  Forecast Dec 2026
    "Engineering":           (33, 47, 59, 69, 67),
    "Product":               (9, 11, 13, 16, 16),
    "Sales":                 (36, 48, 52, 56, 55),
    "Marketing":             (17, 22, 25, 26, 26),
    "Customer Success":      (14, 20, 21, 22, 22),
    "Customer Success COGS": (8, 12, 13, 14, 13),
    "Support":               (4, 6, 7, 8, 8),
    "Support COGS":          (12, 16, 18, 19, 18),
    "Finance":               (7, 11, 14, 16, 15),
    "G&A":                   (12, 19, 26, 29, 28),
}
PAYROLL_SHARE_CAP = Decimal("0.92")
PNL_LINE = {"Sales": "sales_and_marketing", "Marketing": "sales_and_marketing", "Customer Success": "sales_and_marketing",
            "Engineering": "research_and_development", "Product": "research_and_development",
            "Finance": "general_and_administrative", "G&A": "general_and_administrative",
            "Support": "general_and_administrative"}

TAX_RATE = Decimal("0.08")
HEALTH_MONTHLY = {"2024": Decimal("1050"), "2025": Decimal("1120"), "2026": Decimal("1200")}
MATCH_RATE, MATCH_CAP = Decimal("1.00"), Decimal("0.04")
MERIT = Decimal("0.035")
MERIT_MONTH = 4
SEVERANCE_WEEKS_PER_YEAR, SEVERANCE_MIN_WEEKS, SEVERANCE_MAX_WEEKS = 2, 4, 26
VOLUNTARY_MONTHLY, INVOLUNTARY_MONTHLY = 0.0070, 0.0025
MIN_TENURE_MONTHS = 6
DEFERRALS = ((0.15, Decimal("0")), (0.25, Decimal("0.03")), (0.45, Decimal("0.04")), (0.65, Decimal("0.05")),
             (0.85, Decimal("0.06")), (0.95, Decimal("0.08")), (1.0, Decimal("0.10")))
OFFICE_REGIONS = ((0.30, "East"), (0.60, "West"), (0.80, "Central"), (0.90, "South"), (1.0, "Remote"))

COGS_ACCOUNT = {cc: number for cc, (number, _) in COGS_PAYROLL.items()}
PAYROLL_DESCRIPTIONS = {
    "6100": "Base salaries and wages, from the payroll register",
    "6105": "Bonus plans and the SDR incentive, paid monthly with payroll",
    "6110": "Employer payroll tax on wages, bonus, severance and commissions",
    "6115": "Employer 401(k) match: 100% of deferrals up to 4% of wages and bonus",
    "6120": "Employer medical, dental and vision premiums",
    "6125": "Severance for involuntary exits under the severance policy",
}
COMPONENTS = ("regular_wages", "bonus", "severance", "employer_payroll_tax", "health_benefits", "retirement_match")
REGISTER_FIELDS = ["organization_id", "version", "period", "employee_id", "employee_name", "department", "cost_center",
                   "gl_account", "days_employed", "regular_wages", "bonus", "severance", "employer_payroll_tax",
                   "health_benefits", "retirement_match", "total_payroll_cost"]
EMPLOYEE_FIELDS = ["employee_id", "employee_name", "scenario", "department", "sub_department", "cost_center", "role",
                   "level", "region", "manager", "employment_status", "hire_date", "termination_date",
                   "termination_type", "base_salary", "pay_plan", "bonus_target_pct", "variable_comp",
                   "commission_target", "equity_sbc_annual", "benefits_load_pct", "retirement_deferral_pct",
                   "fully_loaded_cash_cost", "fully_loaded_gaap_cost", "quota_carrying", "annual_quota_arr",
                   "productivity_ramp_months", "remote_flag", "source"]
REQ_FIELDS = ["req_id", "scenario", "department", "sub_department", "role", "level", "status", "approved_flag",
              "priority", "replacement_vs_new", "hiring_manager", "recruiter", "target_hire_date",
              "planned_start_date", "scenario_start_date", "scenario_delay_months", "source"]
REMOVED_FILES = ("Workforce_Planning_Validation_Summary.csv",)
REMOVED_ACCOUNTS = {"6540"}
COMMISSION_ACCOUNTS = (
    ("6200", "Sales Commissions", "Amortization of deferred commissions (ASC 340-40, straight-line from the payout month)"),
    ("6210", "Sales Commissions - Expensed", "Renewal commissions expensed when paid (12-month term)"),
)
SALES_TRAVEL_ACCOUNT = "6230"


@dataclass(frozen=True)
class Role:
    unit: str
    cost_center: str
    team: str
    role: str
    level: str
    salary: int
    plan: str  # Bonus | Commission | Incentive
    variable: Decimal  # bonus % of salary, or the commission/incentive target amount
    equity: int
    weight: float
    seed: bool = False
    quota: int = 0
    ramp: int = 2
    cap: int = 0


def R(unit, cc, team, role, level, salary, plan, variable, equity, weight, **kw) -> Role:
    return Role(unit, cc, team, role, level, salary, plan, Decimal(str(variable)), equity, weight, **kw)


B, C, I = "Bonus", "Commission", "Incentive"
ROLES: tuple[Role, ...] = (
    R("Sales", "SALES-MGMT", "Sales Leadership", "Chief Revenue Officer", "L9", 290000, B, 0.50, 120000, 0, seed=True),
    R("Sales", "SALES-MGMT", "Sales Leadership", "VP Sales", "L8", 235000, B, 0.40, 70000, 0, seed=True),
    R("Sales", "SALES-MGMT", "Enterprise Sales", "Regional Sales Director", "L7", 195000, B, 0.35, 40000, 1.5),
    R("Sales", "SALES-MGMT", "Mid-Market Sales", "Sales Manager", "L6", 160000, B, 0.30, 25000, 3),
    R("Sales", "SALES-MGMT", "Sales Development", "SDR Manager", "L5", 125000, B, 0.20, 15000, 2),
    R("Sales", "SALES-AE", "Enterprise Sales", "Senior Account Executive", "L5", 150000, C, 75000, 18000, 8,
      quota=1100000, ramp=4),
    R("Sales", "SALES-AE", "Mid-Market Sales", "Account Executive", "L4", 125000, C, 55000, 12000, 11,
      quota=800000, ramp=4),
    R("Sales", "SALES-AE", "Solutions Engineering", "Solutions Engineer", "L5", 150000, B, 0.20, 20000, 6),
    R("Sales", "SALES-SDR", "Sales Development", "Sales Development Rep", "L2", 70000, I, 25000, 6000, 14,
      quota=300000, ramp=3),
    R("Sales", "SALES-OPS", "Sales Operations", "Sales Operations Analyst", "L3", 95000, B, 0.10, 8000, 3),
    R("Sales", "SALES-OPS", "Sales Operations", "Sales Operations Manager", "L5", 140000, B, 0.15, 18000, 1),
    R("Sales", "SALES-OPS", "Sales Operations", "Sales Enablement Manager", "L5", 135000, B, 0.15, 15000, 1),
    R("Sales", "SALES-OPS", "Sales Operations", "Deal Desk Analyst", "L3", 90000, B, 0.10, 7000, 1),

    R("Marketing", "MKT-OPS", "Marketing Leadership", "Chief Marketing Officer", "L9", 270000, B, 0.35, 100000, 0,
      seed=True),
    R("Marketing", "MKT-DG", "Demand Generation", "Director of Demand Generation", "L7", 185000, B, 0.20, 30000, 1,
      cap=1),
    R("Marketing", "MKT-DG", "Demand Generation", "Demand Generation Manager", "L4", 120000, B, 0.12, 12000, 4),
    R("Marketing", "MKT-DG", "Demand Generation", "Growth Marketing Manager", "L4", 115000, B, 0.12, 10000, 2),
    R("Marketing", "MKT-CONTENT", "Content", "Content Marketing Manager", "L3", 95000, B, 0.10, 7000, 3),
    R("Marketing", "MKT-CONTENT", "Content", "Senior Content Marketing Manager", "L4", 115000, B, 0.12, 10000, 1),
    R("Marketing", "MKT-PROD", "Product Marketing", "Product Marketing Manager", "L4", 125000, B, 0.12, 13000, 3),
    R("Marketing", "MKT-PROD", "Product Marketing", "Senior Product Marketing Manager", "L5", 150000, B, 0.15, 20000, 1),
    R("Marketing", "MKT-EVENTS", "Field and Events", "Events Manager", "L3", 100000, B, 0.10, 8000, 2),
    R("Marketing", "MKT-EVENTS", "Field and Events", "Field Marketing Manager", "L4", 115000, B, 0.12, 10000, 2),
    R("Marketing", "MKT-OPS", "Marketing Operations", "Marketing Operations Manager", "L4", 115000, B, 0.12, 9000, 2),
    R("Marketing", "MKT-OPS", "Marketing Operations", "Marketing Operations Analyst", "L3", 90000, B, 0.10, 7000, 2),

    R("Customer Success", "CS-MGMT", "CS Leadership", "VP Customer Success", "L8", 215000, B, 0.30, 60000, 0, seed=True),
    R("Customer Success", "CS-MGMT", "CS Leadership", "Customer Success Director", "L7", 175000, B, 0.20, 30000, 1),
    R("Customer Success", "CS-MGMT", "CS Leadership", "Customer Success Team Lead", "L5", 140000, B, 0.15, 15000, 2),
    R("Customer Success", "CS-CSM", "Enterprise CS", "Senior Customer Success Manager", "L4", 125000, C, 18000, 12000, 6,
      quota=800000, ramp=3),
    R("Customer Success", "CS-CSM", "Mid-Market CS", "Customer Success Manager", "L3", 105000, C, 15000, 9000, 8,
      quota=550000, ramp=3),
    R("Customer Success", "CS-REVOPS", "Revenue Operations", "Revenue Operations Analyst", "L3", 95000, B, 0.10, 8000, 2),
    R("Customer Success", "CS-REVOPS", "Revenue Operations", "Revenue Operations Manager", "L5", 135000, B, 0.15, 15000, 1),
    R("Customer Success", "CS-REVOPS", "CS Operations", "CS Operations Analyst", "L3", 90000, B, 0.10, 7000, 1),

    R("Customer Success COGS", "CS-IMPL", "Implementation", "Director of Implementation", "L7", 170000, B, 0.20, 30000, 0,
      seed=True),
    R("Customer Success COGS", "CS-IMPL", "Implementation", "Implementation Manager", "L5", 140000, B, 0.15, 15000, 3),
    R("Customer Success COGS", "CS-IMPL", "Implementation", "Implementation Consultant", "L3", 100000, B, 0.10, 8000, 10),
    R("Customer Success COGS", "CS-IMPL", "Implementation", "Senior Implementation Consultant", "L4", 120000, B, 0.12,
      11000, 6),
    R("Customer Success COGS", "CS-IMPL", "Technical Account Management", "Technical Account Manager", "L4", 125000, B,
      0.12, 12000, 6),
    R("Customer Success COGS", "CS-IMPL", "Implementation", "Solutions Architect", "L5", 155000, B, 0.15, 20000, 3),

    R("Engineering", "ENG-MGMT", "Engineering Leadership", "Chief Technology Officer", "L9", 300000, B, 0.30, 150000, 0,
      seed=True),
    R("Engineering", "ENG-MGMT", "Engineering Leadership", "VP Engineering", "L8", 250000, B, 0.25, 90000, 0, seed=True),
    R("Engineering", "ENG-MGMT", "Engineering Leadership", "Director of Engineering", "L7", 225000, B, 0.20, 70000, 1),
    R("Engineering", "ENG-MGMT", "Engineering Leadership", "Engineering Manager", "L6", 200000, B, 0.15, 50000, 4),
    R("Engineering", "ENG-APP", "Application Engineering", "Software Engineer", "L3", 130000, B, 0.10, 20000, 4),
    R("Engineering", "ENG-APP", "Application Engineering", "Software Engineer II", "L4", 150000, B, 0.10, 25000, 6),
    R("Engineering", "ENG-APP", "Application Engineering", "Senior Software Engineer", "L5", 175000, B, 0.12, 35000, 6),
    R("Engineering", "ENG-APP", "Application Engineering", "Staff Software Engineer", "L6", 205000, B, 0.15, 50000, 1.5),
    R("Engineering", "ENG-PLAT", "Platform Engineering", "Platform Engineer", "L4", 155000, B, 0.10, 25000, 4),
    R("Engineering", "ENG-PLAT", "Platform Engineering", "Senior Platform Engineer", "L5", 180000, B, 0.12, 35000, 3),
    R("Engineering", "ENG-DATA", "Data", "Data Engineer", "L4", 155000, B, 0.10, 25000, 3),
    R("Engineering", "ENG-DATA", "Data", "Senior Data Engineer", "L5", 180000, B, 0.12, 35000, 2),
    R("Engineering", "ENG-DATA", "Data", "Data Scientist", "L5", 175000, B, 0.12, 35000, 1.5),
    R("Engineering", "ENG-DEVOPS", "DevOps and Security", "DevOps Engineer", "L4", 155000, B, 0.10, 25000, 2),
    R("Engineering", "ENG-DEVOPS", "DevOps and Security", "Site Reliability Engineer", "L5", 175000, B, 0.12, 35000, 2),
    R("Engineering", "ENG-DEVOPS", "DevOps and Security", "Security Engineer", "L5", 175000, B, 0.12, 28000, 2),
    R("Engineering", "ENG-QA", "Quality Assurance", "QA Engineer", "L3", 115000, B, 0.08, 12000, 3),
    R("Engineering", "ENG-QA", "Quality Assurance", "Senior QA Engineer", "L4", 135000, B, 0.10, 18000, 1.5),

    R("Product", "PROD-PM", "Product Management", "Chief Product Officer", "L9", 275000, B, 0.30, 120000, 0, seed=True),
    R("Product", "PROD-PM", "Product Management", "Director of Product", "L7", 205000, B, 0.20, 50000, 1, cap=2),
    R("Product", "PROD-PM", "Product Management", "Senior Product Manager", "L5", 170000, B, 0.15, 35000, 3),
    R("Product", "PROD-PM", "Product Management", "Product Manager", "L4", 145000, B, 0.12, 25000, 4),
    R("Product", "PROD-DESIGN", "Product Design", "Product Designer", "L4", 135000, B, 0.10, 22000, 3),
    R("Product", "PROD-DESIGN", "Product Design", "Senior Product Designer", "L5", 155000, B, 0.12, 28000, 1.5),
    R("Product", "PROD-DESIGN", "Product Design", "Design Manager", "L6", 175000, B, 0.15, 35000, 0.6, cap=1),
    R("Product", "PROD-OPS", "Product Operations", "Product Operations Manager", "L4", 125000, B, 0.10, 18000, 1.5),
    R("Product", "PROD-OPS", "Product Operations", "Technical Writer", "L3", 100000, B, 0.08, 9000, 1),

    R("Finance", "FIN-BIZOPS", "Finance Leadership", "Chief Financial Officer", "L9", 290000, B, 0.35, 120000, 0,
      seed=True),
    R("Finance", "FIN-ACCT", "Accounting", "Controller", "L7", 210000, B, 0.20, 35000, 0, seed=True),
    R("Finance", "FIN-ACCT", "Accounting", "Accounting Manager", "L5", 145000, B, 0.15, 15000, 1, cap=2),
    R("Finance", "FIN-ACCT", "Accounting", "Senior Accountant", "L4", 110000, B, 0.10, 9000, 2),
    R("Finance", "FIN-ACCT", "Accounting", "Staff Accountant", "L3", 85000, B, 0.08, 6000, 2),
    R("Finance", "FIN-ACCT", "Accounting", "Accounts Payable Specialist", "L2", 65000, B, 0.05, 3000, 1),
    R("Finance", "FIN-ACCT", "Accounting", "Payroll Specialist", "L3", 80000, B, 0.08, 5000, 0.7, cap=2),
    R("Finance", "FIN-REV", "Revenue Accounting", "Revenue Accounting Manager", "L5", 150000, B, 0.15, 15000, 1, cap=1),
    R("Finance", "FIN-REV", "Revenue Accounting", "Revenue Accountant", "L4", 110000, B, 0.10, 9000, 1.5),
    R("Finance", "FIN-REV", "Revenue Accounting", "Billing Specialist", "L2", 65000, B, 0.05, 3000, 1),
    R("Finance", "FIN-REV", "Revenue Accounting", "Collections Specialist", "L2", 62000, B, 0.05, 3000, 0.7),
    R("Finance", "FIN-FPA", "FP&A", "FP&A Manager", "L5", 150000, B, 0.15, 15000, 1, cap=1),
    R("Finance", "FIN-FPA", "FP&A", "Senior FP&A Analyst", "L4", 120000, B, 0.12, 10000, 1),
    R("Finance", "FIN-FPA", "FP&A", "FP&A Analyst", "L3", 95000, B, 0.10, 7000, 1.5),
    R("Finance", "FIN-BIZOPS", "Business Operations Finance", "Finance Business Partner", "L4", 125000, B, 0.12, 10000,
      0.8),
    R("Finance", "FIN-BIZOPS", "Business Operations Finance", "Business Operations Finance Manager", "L5", 140000, B,
      0.15, 14000, 0.6, cap=1),

    R("G&A", "GA-EXEC", "Executive", "Chief Executive Officer", "L10", 340000, B, 0.50, 250000, 0, seed=True),
    R("G&A", "GA-EXEC", "Executive", "Executive Assistant", "L3", 85000, B, 0.08, 5000, 1, cap=3),
    R("G&A", "GA-EXEC", "Executive", "Chief of Staff", "L6", 180000, B, 0.15, 30000, 0.6, cap=1),
    R("G&A", "GA-LEGAL", "Legal", "General Counsel", "L9", 270000, B, 0.30, 90000, 0.8, cap=1),
    R("G&A", "GA-LEGAL", "Legal", "Corporate Counsel", "L6", 195000, B, 0.15, 30000, 1),
    R("G&A", "GA-LEGAL", "Legal", "Paralegal", "L3", 85000, B, 0.08, 5000, 1),
    R("G&A", "GA-LEGAL", "Legal", "Contracts Manager", "L4", 115000, B, 0.10, 9000, 1),
    R("G&A", "GA-PEOPLE", "People", "VP People", "L8", 210000, B, 0.25, 50000, 0.8, cap=1),
    R("G&A", "GA-PEOPLE", "People", "HR Business Partner", "L5", 130000, B, 0.12, 12000, 1.5),
    R("G&A", "GA-PEOPLE", "People", "Recruiter", "L4", 105000, B, 0.10, 8000, 2.5),
    R("G&A", "GA-PEOPLE", "People", "Senior Recruiter", "L5", 125000, B, 0.12, 10000, 1),
    R("G&A", "GA-PEOPLE", "People", "People Operations Specialist", "L3", 80000, B, 0.08, 5000, 1.5),
    R("G&A", "GA-IT", "IT", "IT Manager", "L5", 140000, B, 0.12, 12000, 0.8, cap=1),
    R("G&A", "GA-IT", "IT", "Systems Administrator", "L4", 110000, B, 0.10, 8000, 1),
    R("G&A", "GA-IT", "IT", "IT Support Specialist", "L3", 80000, B, 0.08, 5000, 1.5),
    R("G&A", "GA-OPS", "Business Operations", "Business Operations Manager", "L5", 140000, B, 0.15, 14000, 1),
    R("G&A", "GA-OPS", "Business Operations", "Business Operations Analyst", "L3", 95000, B, 0.10, 7000, 1.5),
    R("G&A", "GA-OPS", "Business Operations", "Office Manager", "L3", 75000, B, 0.08, 4000, 0.8, cap=2),

    R("Support", "SUP-OPS", "Support Leadership", "Director of Support", "L7", 175000, B, 0.20, 30000, 0, seed=True),
    R("Support", "SUP-OPS", "Support Operations", "Support Operations Analyst", "L3", 85000, B, 0.08, 6000, 1.5),
    R("Support", "SUP-OPS", "Support Operations", "Support Manager", "L5", 125000, B, 0.12, 12000, 1),
    R("Support", "SUP-TIER2", "Technical Support", "Technical Support Engineer", "L3", 95000, B, 0.08, 7000, 5),
    R("Support", "SUP-TIER2", "Technical Support", "Senior Technical Support Engineer", "L4", 115000, B, 0.10, 10000, 2),

    R("Support COGS", "SUP-TIER1", "Customer Support", "Customer Support Specialist", "L2", 62000, B, 0.05, 3000, 8),
    R("Support COGS", "SUP-TIER1", "Customer Support", "Senior Customer Support Specialist", "L3", 72000, B, 0.06, 4000, 4),
    R("Support COGS", "SUP-TIER1", "Customer Support", "Customer Support Engineer", "L3", 88000, B, 0.08, 6000, 6),
    R("Support COGS", "SUP-TIER1", "Customer Support", "Support Team Lead", "L4", 98000, B, 0.10, 8000, 2.5),
)
UNIT_DEPARTMENT = {"Customer Success COGS": "Customer Success", "Support COGS": "Support"}


def department_of(unit: str) -> str:
    return UNIT_DEPARTMENT.get(unit, unit)


# ----------------------------------------------------------------------------- helpers


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


def unit(key: str) -> float:
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) / 0x100000000


def pick(table, key: str):
    u = unit(key)
    return next(v for edge, v in table if u < edge)


def pidx(p: str) -> int:
    return int(p[:4]) * 12 + int(p[5:7]) - 1


def padd(p: str, n: int) -> str:
    i = pidx(p) + n
    return f"{i // 12}-{i % 12 + 1:02d}"


def prange(a: str, b: str) -> list[str]:
    return [padd(a, i) for i in range(pidx(b) - pidx(a) + 1)]


def first_day(p: str) -> dt.date:
    return dt.date(int(p[:4]), int(p[5:7]), 1)


def last_day(p: str) -> dt.date:
    return dt.date(int(p[:4]), int(p[5:7]), calendar.monthrange(int(p[:4]), int(p[5:7]))[1])


def month(d: dt.date) -> str:
    return f"{d.year}-{d.month:02d}"


# ----------------------------------------------------------------------------- people


@dataclass
class Person:
    id: str
    role: Role
    hire: dt.date
    factor: Decimal
    region: str
    deferral: Decimal
    remote: bool
    exit: dt.date | None = None
    exit_type: str = ""
    planned: bool = False
    req: str = ""
    replacement: bool = False
    salary_at_hire: Decimal = ZERO
    manager: str = ""
    name: str = ""
    versions: set[str] = field(default_factory=set)

    def raises_through(self, d: dt.date) -> int:
        """Merit increases received by date ``d``: every April 1 after the hire date's calendar year."""
        n = 0
        for y in range(self.hire.year + 1, d.year + 1):
            if dt.date(y, MERIT_MONTH, 1) <= d:
                n += 1
        return n

    def salary(self, d: dt.date) -> Decimal:
        return q(self.salary_at_hire * (1 + MERIT) ** self.raises_through(d))

    def bonus_annual(self, salary: Decimal) -> Decimal:
        if self.role.plan == B:
            return q(salary * self.role.variable)
        return self.role.variable if self.role.plan == I else ZERO

    def on_staff(self, d: dt.date) -> bool:
        return self.hire <= d and (self.exit is None or self.exit >= d)

    def at_month_end(self, p: str) -> bool:
        """In month-end headcount: hired by the last day and not leaving on or before it."""
        return self.hire <= last_day(p) and (self.exit is None or self.exit > last_day(p))

    def days(self, p: str) -> int:
        start, end = max(self.hire, first_day(p)), min(self.exit or last_day(p), last_day(p))
        return max(0, (end - start).days + 1)


def salary_at_hire(role: Role, factor: Decimal, hire: dt.date) -> Decimal:
    """Personal 2026 salary (midpoint x factor, to $500) less the merit increases an employee hired then has had by
    the June 2026 close, so a continuing employee is at their 2026 salary."""
    current = (Decimal(role.salary) * factor / 500).quantize(Decimal(1), ROUND_HALF_UP) * 500
    raises = sum(1 for y in range(hire.year + 1, 2027) if dt.date(y, MERIT_MONTH, 1) <= dt.date(2026, 6, 30))
    return q(current / (1 + MERIT) ** raises)


def cost(person: Person, p: str) -> dict[str, Decimal]:
    """The person's payroll register line for month ``p`` (all zero when not on staff)."""
    days = person.days(p)
    out = {k: ZERO for k in COMPONENTS}
    if not days:
        return out
    full = calendar.monthrange(int(p[:4]), int(p[5:7]))[1]
    end = min(person.exit or last_day(p), last_day(p))
    salary = person.salary(end)
    share = Decimal(days) / Decimal(full)
    out["regular_wages"] = q(salary / 12 * share)
    out["bonus"] = q(person.bonus_annual(salary) / 12 * share)
    if person.exit and month(person.exit) == p and person.exit_type == "Involuntary":
        years = (person.exit - person.hire).days // 365
        weeks = min(max(SEVERANCE_WEEKS_PER_YEAR * years, SEVERANCE_MIN_WEEKS), SEVERANCE_MAX_WEEKS)
        out["severance"] = q(salary / 52 * weeks)
    out["employer_payroll_tax"] = q((out["regular_wages"] + out["bonus"] + out["severance"]) * TAX_RATE)
    out["health_benefits"] = HEALTH_MONTHLY[p[:4]] if person.on_staff(first_day(p)) else ZERO
    out["retirement_match"] = q((out["regular_wages"] + out["bonus"]) * min(person.deferral, MATCH_CAP) * MATCH_RATE)
    return out


# ----------------------------------------------------------------------------- targets


def straight_line(points: list[tuple[str, int]]) -> dict[str, int]:
    """Month-end heads between plan points, rounded half up."""
    out: dict[str, int] = {}
    for (a, ha), (b, hb) in zip(points, points[1:]):
        n = pidx(b) - pidx(a)
        for i in range(n + 1):
            out[padd(a, i)] = int(Decimal(ha) + Decimal(hb - ha) * i / n + Decimal("0.5"))
    return out


def head_targets(unit_name: str) -> dict[str, dict[str, int]]:
    """{version: {period: month-end heads}} from HEADCOUNT_PLAN."""
    jan24, dec25, close, budget, forecast = HEADCOUNT_PLAN[unit_name]
    actual = straight_line([(PLAN_POINTS[0], jan24), (PLAN_POINTS[1], dec25), (CLOSE, close)])
    return {"Actual": actual,
            "Budget": {p: h for p, h in straight_line([(BUDGET_FROM, dec25), ("2026-12", budget)]).items()
                       if p >= "2026-01"},
            "Forecast": {p: h for p, h in straight_line([(CLOSE, close), ("2026-12", forecast)]).items() if p > CLOSE}}


# ----------------------------------------------------------------------------- hiring


class Staffing:
    def __init__(self, version: str, demand: Counter, seq_start: int):
        self.version = version
        self.demand = demand
        self.people: list[Person] = []
        self.seq = seq_start

    def team_heads(self, d: dt.date) -> Counter:
        return Counter((role_group(x.role.role), x.region) for x in self.people
                       if department_of(x.role.unit) in TEAM_DEPARTMENTS and x.on_staff(d))

    def region_for(self, role: Role, pid: str, d: dt.date) -> str:
        if department_of(role.unit) not in TEAM_DEPARTMENTS:
            return pick(OFFICE_REGIONS, f"region|{pid}")
        heads, g = self.team_heads(d), role_group(role.role)
        return max(TERRITORIES, key=lambda t: (self.demand[t] / (heads[(g, t)] + 1), -TERRITORIES.index(t)))

    def hire(self, role: Role, hire: dt.date, *, planned: bool, replacement: bool = False) -> Person:
        pid = f"{ID_PREFIX[self.version]}{self.seq}"
        self.seq += 1
        factor = Decimal(str(round(0.92 + 0.16 * unit(f"factor|{pid}"), 3)))
        person = Person(pid, role, hire, factor, self.region_for(role, pid, hire), pick(DEFERRALS, f"401k|{pid}"),
                        unit(f"remote|{pid}") < 0.35, planned=planned, replacement=replacement)
        person.salary_at_hire = salary_at_hire(role, factor, hire)
        self.people.append(person)
        return person


def next_role(unit_roles: list[Role], staff: list[Person]) -> Role:
    """The role furthest below its share of the team (largest weight x (heads + 1) - role heads)."""
    counts = Counter(x.role for x in staff)
    total = len([x for x in staff if not x.role.seed]) + 1
    wsum = sum(r.weight for r in unit_roles if r.weight)
    open_roles = [r for r in unit_roles if r.weight and (not r.cap or counts[r] < r.cap)]
    return max(open_roles, key=lambda r: (r.weight / wsum * total - counts[r], r.weight, r.role))


def staff_unit(st: Staffing, unit_name: str, target: dict[str, int], months: list[str], *, planned: bool,
               opening: bool, exits: bool) -> None:
    """Hire to the month's planned heads. People leaving in a month still count that month, so exits are backfilled
    the next month."""
    roles = [r for r in ROLES if r.unit == unit_name]

    def present(p: str) -> list[Person]:
        return [x for x in st.people if x.role.unit == unit_name and x.hire <= last_day(p)
                and (x.exit is None or month(x.exit) >= p)]

    open_backfills = 0
    for i, p in enumerate(months):
        if opening and i == 0:
            for r in (r for r in roles if r.seed):
                hire = dt.date(2016 + int(unit(f"seedy|{r.role}") * 4), 1 + int(unit(f"seedm|{r.role}") * 12), 1)
                st.hire(r, hire, planned=False)
            mine = present(p)
            while len(mine) < target[p]:
                r = next_role(roles, mine)
                back = 1 + int(unit(f"tenure|{unit_name}|{len(mine)}") ** 1.6 * 84)
                hp = padd(p, -back)
                mine.append(st.hire(r, dt.date(int(hp[:4]), int(hp[5:7]),
                                               1 if unit(f"day|{unit_name}|{len(mine)}") < 0.6 else 16), planned=False))
            if exits:
                schedule_exits(st, unit_name, months)
            continue
        mine = present(p)
        open_backfills += sum(1 for x in st.people if x.role.unit == unit_name and x.exit
                              and month(x.exit) == padd(p, -1))
        while len(mine) < target[p]:
            r = next_role(roles, mine)
            day = 1 if unit(f"hireday|{unit_name}|{p}|{len(mine)}") < 0.6 else 16
            person = st.hire(r, dt.date(int(p[:4]), int(p[5:7]), day), planned=planned, replacement=open_backfills > 0)
            open_backfills = max(0, open_backfills - 1)
            if exits:
                schedule_exits(st, unit_name, months, only=person)
            mine.append(person)


def schedule_exits(st: Staffing, unit_name: str, months: list[str], only: Person | None = None) -> None:
    """Voluntary and involuntary exits through the close for non-leaders with enough tenure."""
    people = [only] if only else [x for x in st.people if x.role.unit == unit_name]
    for x in people:
        if x.role.seed or x.exit:
            continue
        for p in months:
            if p > CLOSE or pidx(p) - pidx(month(x.hire)) < MIN_TENURE_MONTHS:
                continue
            u = unit(f"exit|{x.id}|{p}")
            if u < VOLUNTARY_MONTHLY + INVOLUNTARY_MONTHLY:
                x.exit = dt.date(int(p[:4]), int(p[5:7]), 15) if unit(f"exitday|{x.id}") < 0.5 else last_day(p)
                x.exit_type = "Voluntary" if u < VOLUNTARY_MONTHLY else "Involuntary"
                break


def renumber(people: list[Person], version: str) -> None:
    """Employee IDs in hire order."""
    for n, x in enumerate(sorted(people, key=lambda x: (x.hire, x.role.unit, x.role.role, x.id))):
        x.id = f"{ID_PREFIX[version]}{ID_START[version] + n}"


def assign_managers(people: list[Person], as_of: dt.date) -> None:
    """Manager = the most senior colleague in the cost center, else the department's most senior; department heads
    report to the CEO. Planned hires get their manager on their start date, others at the file's as-of date (or
    their exit)."""
    level = {x.id: int(x.role.level[1:]) for x in people}
    for x in people:
        d = x.hire if x.planned else min(x.exit or as_of, as_of)
        staff = [y for y in people if y.id != x.id and y.on_staff(d)]
        ceo = next((y for y in staff if y.role.role == "Chief Executive Officer"), None)
        same_cc = [y for y in staff if y.role.cost_center == x.role.cost_center and level[y.id] > level[x.id]]
        same_dept = [y for y in staff if department_of(y.role.unit) == department_of(x.role.unit) and level[y.id] > level[x.id]]
        boss = max(same_cc or same_dept or ([ceo] if ceo else []), key=lambda y: (level[y.id], y.hire, y.id), default=None)
        x.manager = boss.id if boss else ""


# ----------------------------------------------------------------------------- build


def build(src: str, dst: str) -> list[str]:
    if os.path.exists(dst):
        raise SystemExit(f"{dst} exists; pick a new folder")
    notes: list[str] = []
    org = read(os.path.join(src, "Actual_customers.csv"))[1][0]["organization_id"]
    demand = Counter(o["region"] for o in read(os.path.join(src, "Actual_opportunities.csv"))[1])
    units = sorted({r.unit for r in ROLES})
    if set(HEADCOUNT_PLAN) != set(units):
        raise ValueError(f"HEADCOUNT_PLAN teams {sorted(HEADCOUNT_PLAN)} differ from the role teams {units}")
    targets = {u: head_targets(u) for u in units}
    role_ccs = {(department_of(r.unit), r.cost_center) for r in ROLES}
    for v in VERSIONS:
        ccs = {(r["department"], r["cost_center"]) for r in read(os.path.join(src, f"{v}_department_cost_centers.csv"))[1]}
        if role_ccs - ccs:
            raise ValueError(f"{v}_department_cost_centers.csv lacks {sorted(role_ccs - ccs)}")
        unstaffed = sorted(cc for d, cc in ccs - role_ccs if d in {department_of(r.unit) for r in ROLES})
        if unstaffed:
            notes.append(f"{v}: cost centers with no roles (no payroll): {', '.join(unstaffed)}")

    actual = Staffing("Actual", demand, ID_START["Actual"])
    a_months = prange(*WINDOW["Actual"])
    for u in units:
        staff_unit(actual, u, targets[u]["Actual"], a_months, planned=False, opening=True, exits=True)
    renumber(actual.people, "Actual")

    def plan_view(x: Person) -> Person:
        """Budget does not know the 2026 exits."""
        y = copy.copy(x)
        if y.exit and y.exit > last_day(BUDGET_FROM):
            y.exit, y.exit_type = None, ""
        return y

    budget = Staffing("Budget", demand, ID_START["Budget"])
    budget.people = [plan_view(x) for x in actual.people if x.at_month_end(BUDGET_FROM)]
    forecast = Staffing("Forecast", demand, ID_START["Forecast"])
    forecast.people = [copy.copy(x) for x in actual.people]
    for u in units:
        staff_unit(budget, u, targets[u]["Budget"], prange(*WINDOW["Budget"]), planned=True, opening=False,
                   exits=False)
        staff_unit(forecast, u, targets[u]["Forecast"], prange(*WINDOW["Forecast"]), planned=True, opening=False,
                   exits=False)
    renumber([x for x in budget.people if x.planned], "Budget")
    renumber([x for x in forecast.people if x.planned], "Forecast")

    names = employee_names({x.id for s in (actual, budget, forecast) for x in s.people})
    for s in (actual, budget, forecast):
        for x in s.people:
            x.name = names[x.id]
    assign_managers(actual.people, last_day(CLOSE))
    assign_managers(budget.people, last_day("2026-12"))
    assign_managers(forecast.people, last_day("2026-12"))

    shutil.copytree(src, dst)
    for name in REMOVED_FILES:
        if os.path.exists(os.path.join(dst, name)):
            os.remove(os.path.join(dst, name))
            notes.append(f"removed {name} (a v4 check of the old roster)")

    staffs = {"Actual": actual, "Budget": budget, "Forecast": forecast}
    registers = {v: write_register(dst, org, v, s, notes) for v, s in staffs.items()}
    for v, s in staffs.items():
        reqs = write_requisitions(dst, v, s, staffs)
        write_employees(dst, v, s, notes)
        write_policies(dst, org, v)
        payroll = registers["Actual"] + registers["Forecast"] if v == "Forecast" else registers[v]
        write_headcount_plan(dst, v, s, payroll, reqs, src)
        write_sbc_schedule(dst, org, v, notes)
        write_chart_of_accounts(dst, v)
    write_bands(dst)
    write_allocation_rules(dst, registers["Actual"])
    check_payroll_share(src, registers, notes)
    with open(os.path.join(dst, "workforce_build_notes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(notes) + "\n")
    return notes


def register_rows(org: str, v: str, s: Staffing) -> list[dict]:
    out = []
    for p in prange(*WINDOW[v]):
        for x in s.people:
            c = cost(x, p)
            if not x.days(p) and not any(c.values()):
                continue
            out.append({"organization_id": org, "version": v, "period": p, "employee_id": x.id, "employee_name": x.name,
                        "department": department_of(x.role.unit), "cost_center": x.role.cost_center,
                        "gl_account": COGS_ACCOUNT.get(x.role.cost_center, "61xx"), "days_employed": str(x.days(p)),
                        **c, "total_payroll_cost": sum(c.values(), ZERO)})
    return out


def write_register(dst, org, v, s, notes) -> list[dict]:
    rows = register_rows(org, v, s)
    write(os.path.join(dst, f"{v}_payroll_register.csv"), REGISTER_FIELDS, rows)
    tot = {k: sum((r[k] for r in rows), ZERO) for k in COMPONENTS}
    notes.append(f"{v} payroll register: {len(rows)} employee-months, {WINDOW[v][0]}..{WINDOW[v][1]}; "
                 + ", ".join(f"{k} {tot[k]:,.0f}" for k in COMPONENTS))
    return rows


def employee_row(v: str, x: Person, as_of: dt.date) -> dict:
    d = min(x.exit or as_of, as_of) if not x.planned else x.hire
    salary = x.salary(d)
    bonus = x.bonus_annual(salary)
    commission = x.role.variable if x.role.plan == C else ZERO
    variable = bonus + commission
    health = HEALTH_MONTHLY["2026"] * 12
    tax = (salary + variable) * TAX_RATE
    match = (salary + bonus) * min(x.deferral, MATCH_CAP) * MATCH_RATE
    cash = salary + variable + tax + health + match
    if x.planned:
        status = "Planned"
    elif x.exit and x.exit <= as_of:
        status = "Terminated"
    else:
        status = "Active"
    src = {"Actual": "HRIS export at the June 2026 close",
           "Budget": "Budget planned hire" if x.planned else "HRIS roster at Dec 2025 (budget build)",
           "Forecast": "Forecast planned hire" if x.planned else "HRIS export at the June 2026 close"}[v]
    if x.planned and x.req:
        src += f" ({x.req})"
    return {
        "employee_id": x.id, "employee_name": x.name, "scenario": v, "department": department_of(x.role.unit),
        "sub_department": x.role.team, "cost_center": x.role.cost_center, "role": x.role.role, "level": x.role.level,
        "region": x.region, "manager": x.manager, "employment_status": status, "hire_date": x.hire.isoformat(),
        "termination_date": x.exit.isoformat() if x.exit and x.exit <= as_of else "",
        "termination_type": x.exit_type if x.exit and x.exit <= as_of else "",
        "base_salary": f"{salary:.2f}", "pay_plan": x.role.plan,
        "bonus_target_pct": f"{x.role.variable:.2f}" if x.role.plan == B else "",
        "variable_comp": f"{variable:.2f}", "commission_target": f"{commission:.2f}",
        "equity_sbc_annual": str(x.role.equity),
        "benefits_load_pct": f"{(tax + health + match) / (salary + variable):.4f}",
        "retirement_deferral_pct": f"{x.deferral:.2f}",
        "fully_loaded_cash_cost": f"{cash:.2f}", "fully_loaded_gaap_cost": f"{cash + x.role.equity:.2f}",
        "quota_carrying": "Yes" if x.role.quota and x.role.plan != C or x.role.role in BOOKINGS_ROLES else "No",
        "annual_quota_arr": str(x.role.quota), "productivity_ramp_months": str(x.role.ramp),
        "remote_flag": "Yes" if x.remote or x.region == "Remote" else "No", "source": src,
    }


def write_employees(dst, v, s, notes) -> None:
    as_of = last_day(CLOSE if v == "Actual" else "2026-12")
    rows = [employee_row(v, x, as_of) for x in sorted(s.people, key=lambda x: x.id)]
    write(os.path.join(dst, f"{v}_Employees.csv"), EMPLOYEE_FIELDS, rows)
    c = Counter(r["employment_status"] for r in rows)
    notes.append(f"{v}_Employees.csv: {len(rows)} employees ({', '.join(f'{k} {n}' for k, n in sorted(c.items()))}); "
                 + ", ".join(f"{d} {n}" for d, n in sorted(Counter(r['department'] for r in rows
                                                                   if r['employment_status'] != 'Terminated').items())))


def write_policies(dst, org, v) -> None:
    rows = [
        ("employer_payroll_tax_rate", f"{TAX_RATE}", "2016-01", "", "All wages, bonus, severance and commissions",
         "Employer FICA, Medicare and unemployment, blended"),
        *[("health_benefits_monthly", f"{amt}", f"{y}-01", f"{y}-12", "Employees on staff on the 1st of the month",
           "Employer medical, dental and vision premium per employee per month") for y, amt in HEALTH_MONTHLY.items()],
        ("retirement_match_rate", f"{MATCH_RATE}", "2016-01", "", "All employees",
         "401(k) match: share of the employee's deferral the company matches"),
        ("retirement_match_cap_pct", f"{MATCH_CAP}", "2016-01", "", "All employees",
         "401(k) match: deferrals matched up to this share of wages and bonus"),
        ("merit_increase_pct", f"{MERIT}", "2016-04", "", f"Employees hired before January 1; effective April 1",
         "Annual merit increase to base salary"),
        ("severance_weeks_per_year", str(SEVERANCE_WEEKS_PER_YEAR), "2016-01", "", "Involuntary exits",
         "Weeks of base salary per completed year of service, paid in the exit month"),
        ("severance_min_weeks", str(SEVERANCE_MIN_WEEKS), "2016-01", "", "Involuntary exits", "Minimum severance"),
        ("severance_max_weeks", str(SEVERANCE_MAX_WEEKS), "2016-01", "", "Involuntary exits", "Maximum severance"),
        ("bonus_payout", "monthly", "2016-01", "", "Bonus pay plan (bonus_target_pct of base salary)",
         "Paid monthly with payroll at target"),
        ("incentive_payout", "monthly", "2016-01", "", "Incentive pay plan (SDRs; variable_comp)",
         "Paid monthly with payroll at target"),
        ("commission_payout", "commission plans", "2016-01", "", "Commission pay plan (AEs, CSMs)",
         "Paid from the commission payout files under the commission plans; not in the payroll register"),
    ]
    write(os.path.join(dst, f"{v}_payroll_policies.csv"),
          ["organization_id", "version", "policy", "value", "effective_from", "effective_to", "applies_to", "description"],
          [{"organization_id": org, "version": v, "policy": a, "value": b, "effective_from": c, "effective_to": d,
            "applies_to": e, "description": f} for a, b, c, d, e, f in rows])


def write_requisitions(dst, v, s, staffs) -> list[dict]:
    """Actual: a filled requisition for every hire since Jan 2024 and the open requisitions for the Forecast's planned
    hires. Budget and Forecast: one open requisition per planned hire."""
    if v == "Actual":
        people = [(x, "Filled") for x in s.people if x.hire >= first_day(FIRST)]
        people += [(x, "Open") for x in staffs["Forecast"].people if x.planned]
    else:
        people = [(x, "Open") for x in s.people if x.planned]
    rows = []
    for n, (x, status) in enumerate(sorted(people, key=lambda t: (t[0].hire, t[0].id)), 1):
        req = f"{REQ_PREFIX[v]}{n:04d}"
        if v != "Actual":
            x.req = req
        target = x.hire - dt.timedelta(days=20)
        rows.append({"req_id": req, "scenario": v, "department": department_of(x.role.unit), "sub_department": x.role.team,
                     "role": x.role.role, "level": x.role.level, "status": status, "approved_flag": "Yes",
                     "priority": "High" if x.role.plan == C or x.role.quota else "Medium",
                     "replacement_vs_new": "Replacement" if x.replacement else "New",
                     "hiring_manager": x.manager, "recruiter": "Recruiting Team", "target_hire_date": target.isoformat(),
                     "planned_start_date": x.hire.isoformat(), "scenario_start_date": x.hire.isoformat(),
                     "scenario_delay_months": "0",
                     "source": f"{x.id} {'hired' if status == 'Filled' else 'planned start'} {x.hire.isoformat()}"})
    write(os.path.join(dst, f"{v}_Open_Requisitions.csv"), REQ_FIELDS, rows)
    return rows


def ramp_curve(src: str) -> dict[int, dict[int, Decimal]]:
    curve: dict[int, dict[int, Decimal]] = defaultdict(dict)
    for r in read(os.path.join(src, "Hiring_Ramp_Assumptions.csv"))[1]:
        curve[int(r["ramp_months"])][int(r["month_after_start"])] = num(r["productivity_pct"])
    return curve


def write_headcount_plan(dst, v, s, payroll, reqs, src) -> None:
    """Heads by GL department at month end from the roster; cash payroll from the register (Forecast: Actual through
    the close); open requisitions = requisitions starting in the next two months."""
    fields = read(os.path.join(src, f"{v}_Headcount_Plan.csv"))[0]
    curve = ramp_curve(src)
    months = prange(FIRST, CLOSE) if v == "Actual" else prange("2026-01", "2026-12")
    reg: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for r in payroll:
        reg[(r["period"], r["department"])] += r["total_payroll_cost"]
    depts = sorted({department_of(r.unit) for r in ROLES})
    rows = []
    for p in months:
        for d in depts:
            team = [x for x in s.people if department_of(x.role.unit) == d]
            end = [x for x in team if x.at_month_end(p)]
            begin = [x for x in team if x.at_month_end(padd(p, -1))]
            quota = [x for x in end if x.role.quota and x.role.plan != C or x.role.role in BOOKINGS_ROLES]
            ramped = ZERO
            for x in quota:
                k = pidx(p) - pidx(month(x.hire)) + 1
                ramped += Decimal(x.role.quota) * curve.get(x.role.ramp, {}).get(k, Decimal("1"))
            sbc = sum((Decimal(x.role.equity) / 12 * Decimal(x.days(p)) / Decimal(calendar.monthrange(int(p[:4]), int(p[5:7]))[1])
                       for x in team), ZERO)
            opens = sum(1 for r in reqs if r["department"] == d and 0 < pidx(r["planned_start_date"][:7]) - pidx(p) <= 2)
            rows.append({"scenario": v, "period": p, "department": d, "headcount_beginning": str(len(begin)),
                         "new_hires": str(sum(1 for x in team if month(x.hire) == p)),
                         "attrition": str(sum(1 for x in team if x.exit and month(x.exit) == p)),
                         "headcount_ending": str(len(end)), "open_requisitions": str(opens),
                         "monthly_cash_payroll_cost": f"{reg[(p, d)]:.2f}",
                         "monthly_gaap_payroll_cost": f"{reg[(p, d)] + q(sbc):.2f}", "monthly_sbc": f"{q(sbc):.2f}",
                         "quota_capacity_arr": f"{sum((Decimal(x.role.quota) for x in quota), ZERO):.2f}",
                         "ramped_quota_capacity_arr": f"{q(ramped):.2f}",
                         "source": f"{v}_Employees.csv (heads, quota) and {'Actual and Forecast' if v == 'Forecast' else v}"
                                   f"_payroll_register.csv (cash payroll); SBC = equity_sbc_annual for days employed"})
    write(os.path.join(dst, f"{v}_Headcount_Plan.csv"), fields, rows)


def write_sbc_schedule(dst, org, v, notes) -> None:
    """Reads the {V}_Employees.csv just written to ``dst``."""
    rows = schedule_rows(dst, org, v, prange(*WINDOW[v]))
    write(os.path.join(dst, f"{v}_SBC_Schedule.csv"), SCHEDULE_FIELDS, rows)
    total = sum((r["total_sbc"] for r in rows), ZERO)
    notes.append(f"{v}_SBC_Schedule.csv: {len(rows)} months, stock comp {total:,.0f} from equity_sbc_annual")


def write_chart_of_accounts(dst, v) -> None:
    path = os.path.join(dst, f"{v}_chart_of_accounts.csv")
    fields, rows = read(path)
    rows = [r for r in rows if r["account_number"] not in REMOVED_ACCOUNTS]
    have = {r["account_number"]: r for r in rows}
    for _, number, name, etype in PAYROLL_COLUMNS:
        row = have.get(number) or {}
        row.update({"account_number": number, "account_name": name, "statement": "Income Statement",
                    "statement_category": "Operating Expense", "account_group": "Labor", "expense_type": etype,
                    "description": PAYROLL_DESCRIPTIONS[number]})
        if number not in have:
            rows.append(row)
    for cc, number in COGS_ACCOUNT.items():
        have[number]["description"] = (f"Payroll of {cc} (wages, bonus, payroll tax, benefits, 401(k) match, severance), "
                                       f"from the payroll register")
    for number, name, desc in COMMISSION_ACCOUNTS:
        old = have.get(number)
        if old and old["account_name"] != name:
            moved = {**old, "account_number": SALES_TRAVEL_ACCOUNT}
            if SALES_TRAVEL_ACCOUNT in have:
                raise ValueError(f"{v}: {number} {old['account_name']} cannot move to {SALES_TRAVEL_ACCOUNT}")
            rows.append(moved)
            have[SALES_TRAVEL_ACCOUNT] = moved
        row = old or {}
        row.update({"account_number": number, "account_name": name, "statement": "Income Statement",
                    "statement_category": "Operating Expense", "account_group": "Sales Expense",
                    "expense_type": "Commissions", "description": desc})
        if not old:
            rows.append(row)
    added = [(number, name, category, group, SBC_EXPENSE_TYPE,
              f"Stock comp from equity_sbc_annual on {v}_Employees.csv for days employed ({side})")
             for side, (number, name, category, group) in SBC_ACCOUNTS.items()]
    added += [(number, *spec) for number, spec in VENDOR_ACCOUNTS.items()]
    added.append(CONTRACTOR_ACCOUNT)
    for number, name, category, group, etype, desc in added:
        row = have.get(number)
        if row is None:
            row = {"account_number": number}
            rows.append(row)
            have[number] = row
        row.update({"account_name": name, "statement": "Income Statement", "statement_category": category,
                    "account_group": group, "expense_type": etype, "description": desc})
    for number, name, category, group, etype in BS_ACCOUNTS.values():
        if number not in have:
            rows.append({"account_number": number, "account_name": name, "statement": "Balance Sheet",
                         "statement_category": category, "account_group": group, "expense_type": etype,
                         "description": name})
    rows.sort(key=lambda r: r["account_number"])
    write(path, fields, rows)


def write_bands(dst) -> None:
    fields, _ = read(os.path.join(dst, "Compensation_Bands.csv"))
    rows = []
    for r in ROLES:
        salary = Decimal(r.salary)
        bonus = salary * r.variable if r.plan == B else ZERO
        variable = bonus + (r.variable if r.plan in (C, I) else ZERO)
        health = HEALTH_MONTHLY["2026"] * 12
        tax = (salary + variable) * TAX_RATE
        match = (salary + bonus + (r.variable if r.plan == I else ZERO)) * Decimal("0.035")
        cash = salary + variable + tax + health + match
        rows.append({"department": department_of(r.unit), "role": r.role, "level": r.level,
                     "salary_midpoint": str(r.salary), "salary_low": f"{salary * Decimal('0.88'):.0f}",
                     "salary_high": f"{salary * Decimal('1.15'):.0f}", "variable_comp_target": f"{variable:.0f}",
                     "equity_sbc_annual": str(r.equity), "benefits_load_pct": f"{(tax + health + match) / (salary + variable):.4f}",
                     "fully_loaded_cash_cost_midpoint": f"{cash:.0f}",
                     "fully_loaded_gaap_cost_midpoint": f"{cash + r.equity:.0f}",
                     "quota_carrying": "Yes" if r.quota and r.plan != C or r.role in BOOKINGS_ROLES else "No",
                     "annual_quota_arr": str(r.quota), "productivity_ramp_months": str(r.ramp)})
    write(os.path.join(dst, "Compensation_Bands.csv"), fields, rows)


def write_allocation_rules(dst, actual_register) -> None:
    fields, _ = read(os.path.join(dst, "Department_Allocation_Rules.csv"))
    line_of = {"SUP-TIER1": "Cost of Revenue", "CS-IMPL": "Cost of Revenue"}
    dept_line = {"Sales": "Sales and Marketing", "Marketing": "Sales and Marketing", "Customer Success": "Sales and Marketing",
                 "Engineering": "Research and Development", "Product": "Research and Development",
                 "Finance": "General and Administrative", "G&A": "General and Administrative",
                 "Support": "General and Administrative"}
    june: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    ccs: dict[tuple[str, str], set[str]] = defaultdict(set)
    for r in actual_register:
        if r["period"] == CLOSE:
            key = (r["department"], line_of.get(r["cost_center"], dept_line[r["department"]]))
            june[key] += r["total_payroll_cost"]
            ccs[key].add(r["cost_center"])
    dept_total: dict[str, Decimal] = defaultdict(Decimal)
    for (d, _), amt in june.items():
        dept_total[d] += amt
    rows = []
    for (d, line), amt in sorted(june.items()):
        rows.append({"department": d, "statement_category": line, "sub_department_mapping": ", ".join(sorted(ccs[(d, line)])),
                     "allocation_description": f"{d} cost centers posting to {line}",
                     "allocation_pct": f"{amt / dept_total[d]:.4f}", "management_view_include": "Yes",
                     "accounting_view_include": "Yes"})
    write(os.path.join(dst, "Department_Allocation_Rules.csv"), fields, rows)


def check_payroll_share(src: str, registers: dict[str, list[dict]], notes: list[str]) -> None:
    """Payroll by P&L line against the summary P&L line: at most PAYROLL_SHARE_CAP, so the line's other accounts
    (software, hosting, programs, facilities) keep a share."""
    over = []
    for v in VERSIONS:
        lines = {r["period"][:7]: r for r in read(os.path.join(src, f"{v}_income_statement.csv"))[1]}
        pay: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
        for r in registers[v]:
            line = "cost_of_revenue" if r["cost_center"] in COGS_ACCOUNT else PNL_LINE[r["department"]]
            pay[(line, r["period"])] += r["total_payroll_cost"]
        shares: dict[str, list[Decimal]] = defaultdict(list)
        for (line, p), amt in pay.items():
            share = amt / num(lines[p][line])
            shares[line].append(share)
            if share > PAYROLL_SHARE_CAP:
                over.append(f"{v} {p} {line} {share:.1%}")
        notes.append(f"{v} payroll share of its P&L line: " + "; ".join(
            f"{line} {min(s):.0%}-{max(s):.0%}" for line, s in sorted(shares.items())))
    if over:
        raise ValueError(f"payroll above {PAYROLL_SHARE_CAP:.0%} of its P&L line: {', '.join(over[:8])}"
                         + (f" (+{len(over) - 8} more)" if len(over) > 8 else ""))


if __name__ == "__main__":
    for line in build(sys.argv[1], sys.argv[2]):
        print(line)
