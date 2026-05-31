"""Semantic dimensions for GL, pipeline, and opportunity reporting."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class GlSemanticTags:
    statement_category: str
    financial_section: str
    department: str
    account_group: str
    expense_type: str
    reporting_category: str
    functional_area: str


@dataclass(frozen=True)
class OpportunitySemanticTags:
    pipeline_movement: str
    stage: str
    region: str
    segment: str
    owner: str
    marketing_channel: str
    arr_band: str


def _match(text: str, *needles: str) -> bool:
    lower = text.lower()
    return any(n in lower for n in needles)


def classify_gl_row(
    *,
    account: str | None,
    department: str | None,
    account_group: str | None,
    expense_type: str | None,
    amount: Decimal,
) -> GlSemanticTags:
    acct = (account or "").strip()
    dept = (department or "Unassigned").strip()
    group = (account_group or expense_type or "Other").strip()
    etype = (expense_type or group or "Other").strip()

    if _match(acct, "revenue", "subscription", "services"):
        stmt = "Revenue"
        section = "Subscription Revenue" if "subscription" in acct.lower() else "Services Revenue"
    elif amount < 0 or _match(group, "expense", "opex", "cost"):
        stmt = "Operating Expenses"
        if _match(dept, "sales"):
            section = "Sales"
        elif _match(dept, "marketing"):
            section = "Marketing"
        elif _match(dept, "engineer", "r&d", "product"):
            section = "Engineering"
        else:
            section = "G&A"
    else:
        stmt = "Other"
        section = group

    if _match(etype, "people", "payroll", "salary", "benefit"):
        exp_type = "People"
    elif _match(etype, "software", "saas", "license"):
        exp_type = "Software"
    elif _match(etype, "hosting", "cloud", "infrastructure"):
        exp_type = "Hosting"
    elif _match(etype, "marketing", "event", "paid"):
        exp_type = "Marketing Programs"
    else:
        exp_type = etype

    return GlSemanticTags(
        statement_category=stmt,
        financial_section=section,
        department=dept,
        account_group=group,
        expense_type=exp_type,
        reporting_category=f"{stmt} / {section}",
        functional_area=dept,
    )


def classify_opportunity(
    *,
    stage: str | None,
    region: str | None,
    segment: str | None,
    owner: str | None,
    marketing_channel: str | None,
    arr_impact: Decimal,
    movement: str | None = None,
) -> OpportunitySemanticTags:
    st = (stage or "Unknown").strip()
    arr = abs(arr_impact)
    if arr >= Decimal("500000"):
        band = "Enterprise (500k+)"
    elif arr >= Decimal("100000"):
        band = "Mid-Market (100k-500k)"
    elif arr >= Decimal("25000"):
        band = "SMB (25k-100k)"
    else:
        band = "Small (<25k)"

    return OpportunitySemanticTags(
        pipeline_movement=movement or st,
        stage=st,
        region=(region or "Unknown").strip(),
        segment=(segment or "Unknown").strip(),
        owner=(owner or "Unknown").strip(),
        marketing_channel=(marketing_channel or "Unknown").strip(),
        arr_band=band,
    )


SOURCE_OF_TRUTH: dict[str, str] = {
    "arr": "MRR / ARR waterfall (actual_mrr_waterfall, budget_mrr_waterfall, forecast_mrr_waterfall)",
    "pipeline": "Pipeline waterfall (not marketing_pipeline)",
    "opportunity_drilldown": "Opportunity movements",
    "deferred_revenue": "Deferred revenue waterfall",
    "cash_flow": "Cash flow bridge",
    "cash_flow_statement": "Cash flow statement",
    "balance_sheet": "Balance sheet",
    "marketing": "Marketing pipeline (GTM only)",
}

# Canonical CSV names — see executive_reporting_governance.SOURCE_HIERARCHY
SOURCE_HIERARCHY = {
    "arr": SOURCE_OF_TRUTH["arr"],
    "pipeline": SOURCE_OF_TRUTH["pipeline"],
    "opportunity_movements": SOURCE_OF_TRUTH["opportunity_drilldown"],
    "gtm": SOURCE_OF_TRUTH["marketing"],
    "revenue": "deferred_revenue_waterfall + income_statement",
    "cash": SOURCE_OF_TRUTH["cash_flow"],
    "gl": "gl_detail",
}
