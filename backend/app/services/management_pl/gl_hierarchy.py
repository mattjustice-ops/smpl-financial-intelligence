"""Management P&L GL classification and default account-group hierarchy."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from app.services.financial_statements.mapping import IS_COGS, IS_OPEX, IS_REVENUE, normalize_is_bucket

SBC_KEYWORDS = ("stock", "sbc", "equity comp", "share-based")
RESTRUCT_KEYWORDS = ("restruct", "severance", "exit", "one-time", "onetime")
NON_OP_KEYWORDS = ("interest", "non-operating", "non operating", "other income")


@dataclass(frozen=True)
class GlEntry:
    period: str
    version: str
    account_number: str
    account_name: str
    account_group: str
    section_key: str
    department: str
    source_department: str
    expense_type: str
    amount: Decimal
    is_sbc: bool = False
    is_restruct: bool = False
    is_non_op: bool = False
    is_non_recurring: bool = False


@dataclass(frozen=True)
class HierarchyTemplate:
    section_key: str
    section_label: str
    department: str | None
    account_groups: tuple[str, ...]


# Default CFO hierarchy when GL rows lack account_group detail.
MANAGEMENT_HIERARCHY: tuple[HierarchyTemplate, ...] = (
    HierarchyTemplate("revenue", "Revenue", None, ("Subscription Revenue", "Services Revenue", "Other Revenue")),
    HierarchyTemplate(
        "cogs",
        "COGS",
        None,
        (
            "Hosting",
            "Support Payroll",
            "Third Party Data",
            "Infrastructure",
            "Payment Processing",
            "Customer Support Tools",
            "Other COGS",
        ),
    ),
    HierarchyTemplate(
        "sales_and_marketing",
        "Sales & Marketing",
        "Sales & Marketing",
        (
            "Payroll",
            "Commissions",
            "Advertising",
            "Events",
            "Software",
            "Contractors",
            "Travel",
            "Marketing Programs",
            "Other S&M",
        ),
    ),
    HierarchyTemplate(
        "research_and_development",
        "R&D",
        "R&D",
        (
            "Engineering Payroll",
            "Product Payroll",
            "Cloud Infrastructure",
            "Development Tools",
            "Contractors",
            "Other R&D",
        ),
    ),
    HierarchyTemplate(
        "general_and_administrative",
        "G&A",
        "G&A",
        (
            "Finance Payroll",
            "HR Payroll",
            "Legal",
            "Insurance",
            "Audit",
            "Recruiting",
            "Software",
            "Office",
            "Other G&A",
        ),
    ),
    HierarchyTemplate(
        "customer_success",
        "Customer Success",
        "Customer Success",
        ("CSM Payroll", "Support Tools", "Training", "Travel", "Other CS"),
    ),
)

COGS_ACCOUNT_NAMES: frozenset[str] = frozenset(
    {
        "Cloud Hosting COGS",
        "Customer Support Labor COGS",
        "Customer Success Labor COGS",
        "Third Party Product Fees COGS",
        "Payment Processing COGS",
    }
)

# Raw CSV department → management P&L OpEx stack (Chart B)
OPEX_STACK_SM_DEPTS: frozenset[str] = frozenset({"Sales", "Marketing"})
OPEX_STACK_RD_DEPTS: frozenset[str] = frozenset({"Engineering", "Product"})
OPEX_STACK_GA_DEPTS: frozenset[str] = frozenset({"G&A", "Finance", "Customer Success", "Support"})

GL_DRILLDOWN_DEPARTMENTS: tuple[str, ...] = (
    "Sales",
    "Marketing",
    "Engineering",
    "Product",
    "Customer Success",
    "Support",
    "G&A",
    "Finance",
)

RAW_DEPT_TO_SECTION: dict[str, str] = {
    "Sales": "sales_and_marketing",
    "Marketing": "sales_and_marketing",
    "Engineering": "research_and_development",
    "Product": "research_and_development",
    "Customer Success": "customer_success",
    "Support": "customer_success",
    "G&A": "general_and_administrative",
    "Finance": "general_and_administrative",
    "Revenue": "revenue",
}


def is_cogs_account(account_name: str) -> bool:
    name = (account_name or "").strip()
    if name in COGS_ACCOUNT_NAMES:
        return True
    return name.endswith(" COGS")


def cogs_display_group(account_name: str) -> str:
    mapping = {
        "Cloud Hosting COGS": "Cloud Hosting",
        "Customer Support Labor COGS": "Support Labor",
        "Customer Success Labor COGS": "CS Labor COGS",
        "Third Party Product Fees COGS": "Third Party / Product",
        "Payment Processing COGS": "Payment Processing",
    }
    return mapping.get(account_name, account_name.replace(" COGS", ""))


def normalize_source_department(raw_dept: str) -> str:
    return (raw_dept or "").strip() or "Unallocated"


COGS_KEYWORDS = (
    "hosting",
    "infrastructure",
    "cloud",
    "support payroll",
    "payment process",
    "third party",
    "data",
    "customer support",
    "delivery",
    "cogs",
    "cost of",
)

DEPT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Sales & Marketing": ("sales", "marketing", "s&m", "demand", "gtm"),
    "R&D": ("r&d", "research", "engineering", "product dev", "development"),
    "G&A": ("g&a", "general", "admin", "finance", "hr", "legal", "corporate"),
    "Customer Success": ("customer success", "cs ", "csm", "support", "success"),
    "Product": ("product",),
    "Finance": ("finance", "accounting"),
    "Operations": ("operations", "ops"),
}


def _match_any(text: str, needles: Iterable[str]) -> bool:
    lower = text.lower()
    return any(n in lower for n in needles)


def resolve_department(raw_dept: str, section_key: str, account: str, group: str) -> str:
    blob = f"{raw_dept} {account} {group}".lower()
    for dept, needles in DEPT_KEYWORDS.items():
        if _match_any(blob, needles):
            return dept
    if section_key == "sales_and_marketing":
        return "Sales & Marketing"
    if section_key == "research_and_development":
        return "R&D"
    if section_key == "general_and_administrative":
        return "G&A"
    if section_key == "customer_success":
        return "Customer Success"
    return raw_dept.strip() or "Unassigned"


def resolve_section_and_group(
    *,
    account_name: str,
    account_group: str,
    category: str,
    expense_type: str,
    department: str,
    amount: Decimal,
) -> tuple[str, str]:
    """Return (section_key, account_group_label)."""
    acct = account_name or ""
    group = (account_group or expense_type or category or "Other").strip()
    if not group:
        group = "Other"
    raw_dept = normalize_source_department(department)
    bucket = normalize_is_bucket(category, acct)
    blob = f"{acct} {group} {expense_type} {category}".lower()

    if is_cogs_account(acct) or bucket == IS_COGS or _match_any(blob, COGS_KEYWORDS):
        return "cogs", cogs_display_group(acct)

    if bucket == IS_REVENUE or (amount > 0 and _match_any(blob, ("revenue", "subscription", "services"))):
        if "service" in blob:
            return "revenue", "Services Revenue"
        if "subscription" in blob:
            return "revenue", "Subscription Revenue"
        return "revenue", group if group != "Other" else "Other Revenue"

    section = RAW_DEPT_TO_SECTION.get(raw_dept, "general_and_administrative")

    template = next((t for t in MANAGEMENT_HIERARCHY if t.section_key == section), None)
    if template:
        for label in template.account_groups:
            if _match_any(blob, (label.lower().split()[0], label.lower())):
                return section, label
        if "payroll" in blob or "salary" in blob:
            if section == "sales_and_marketing":
                return section, "Payroll" if "commission" not in blob else "Commissions"
            if section == "research_and_development":
                return section, "Engineering Payroll" if "product" not in blob else "Product Payroll"
            if section == "customer_success":
                return section, "CSM Payroll"
            if section == "general_and_administrative":
                return section, "Finance Payroll" if "finance" in blob else "HR Payroll"
        if "software" in blob or "saas" in blob:
            return section, "Software"
        if "travel" in blob:
            return section, "Travel"
        if "market" in blob or "advert" in blob:
            return section, "Marketing Programs"
        other = template.account_groups[-1]
        return section, group if group not in ("Other", "opex") else other

    return section, group


def classify_raw_gl_row(raw: dict) -> GlEntry | None:
    amount = Decimal(str(raw.get("amount") or 0))
    if amount == 0:
        return None
    acct_name = str(raw.get("account_name") or raw.get("account_number") or "Unknown")
    acct_num = str(raw.get("account_number") or "")
    group = str(raw.get("account_group") or raw.get("category") or "")
    dept = normalize_source_department(str(raw.get("department") or ""))
    etype = str(raw.get("expense_type") or "")
    category = str(raw.get("category") or raw.get("statement_category") or "")
    statement = str(raw.get("statement") or "").strip()
    if statement and "income" not in statement.lower() and statement.lower() not in {"income statement", "opex"}:
        return None
    period = raw.get("period")
    if period is None:
        return None
    if hasattr(period, "strftime"):
        ps = period.strftime("%Y-%m")
    else:
        ps = str(period)[:7]

    section_key, ag = resolve_section_and_group(
        account_name=acct_name,
        account_group=group,
        category=category,
        expense_type=etype,
        department=dept,
        amount=amount,
    )
    blob = f"{acct_name} {group} {etype}".lower()
    mgmt = str(raw.get("management_view_include") or "Yes").strip().lower()
    if mgmt not in ("yes", "y", "true", "1"):
        return None
    expense_amount = abs(amount) if amount < 0 else amount
    if section_key != "revenue":
        amount = -expense_amount

    sbc_flag = str(raw.get("sbc_flag") or "").strip().lower()
    is_non_recurring = "accounting true-up" in acct_name.lower() or _match_any(blob, RESTRUCT_KEYWORDS)
    mapped_dept = resolve_department(dept, section_key, acct_name, ag)
    return GlEntry(
        period=ps,
        version=str(raw.get("version") or raw.get("scenario") or "Actual"),
        account_number=acct_num,
        account_name=acct_name,
        account_group=ag,
        section_key=section_key,
        department=mapped_dept,
        source_department=dept,
        expense_type=etype,
        amount=amount,
        is_sbc=sbc_flag in ("yes", "y", "true", "1") or _match_any(blob, SBC_KEYWORDS),
        is_restruct=_match_any(blob, RESTRUCT_KEYWORDS),
        is_non_op=_match_any(blob, NON_OP_KEYWORDS),
        is_non_recurring=is_non_recurring,
    )
