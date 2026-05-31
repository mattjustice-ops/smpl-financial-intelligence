"""Workforce operating model constants."""

from __future__ import annotations

WORKFORCE_DEPARTMENTS: tuple[str, ...] = (
    "Sales",
    "Marketing",
    "R&D",
    "Product",
    "Customer Success",
    "Support",
    "G&A",
    "Finance",
    "HR / People",
    "Operations",
)

GTM_DEPARTMENTS: frozenset[str] = frozenset({"Sales", "Marketing"})

ACTIVE_EMPLOYMENT_STATUSES: frozenset[str] = frozenset(
    {"active", "on leave", "leave", "paid leave", "unpaid leave"}
)

APPROVED_REQ_STATUSES: frozenset[str] = frozenset({"approved", "open", "committed", "in process"})

PNL_LINE_MAP: dict[str, str] = {
    "sales_and_marketing": "Sales and Marketing",
    "sm": "Sales and Marketing",
    "sales & marketing": "Sales and Marketing",
    "research_and_development": "Research and Development",
    "r_and_d": "Research and Development",
    "r&d": "Research and Development",
    "rd": "Research and Development",
    "general_and_administrative": "General and Administrative",
    "g_and_a": "General and Administrative",
    "ga": "General and Administrative",
    "g&a": "General and Administrative",
    "cost_of_revenue": "Cost of Revenue",
    "cogs": "Cost of Revenue",
}

DEFAULT_BENEFITS_LOAD_PCT = 0.25
