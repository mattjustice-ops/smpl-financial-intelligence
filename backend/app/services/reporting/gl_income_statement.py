"""Income statement built from GL detail (gl_actuals) — the only P&L source.

Sign rule: GL amounts are debit-positive, credit-negative (standard accounting
export). Revenue is shown as the negated credit balance; expenses as posted.

Line mapping (in order):
  1. statement_category (or statement when the category is blank) names the line.
  2. Operating expense lines go to S&M / R&D / G&A by the category itself when it
     names the function, else by account_group, else by department.
  3. Anything that cannot be mapped is reported as ``unmapped`` and counted in
     total opex — never silently assigned.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any, Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import table_exists

LINE_BY_CATEGORY: dict[str, str] = {
    "revenue": "revenue",
    "cogs": "cogs",
    "cost of revenue": "cogs",
    "cost of goods sold": "cogs",
    "cost of sales": "cogs",
    "d&a": "da",
    "depreciation and amortization": "da",
    "interest": "interest",
    "interest expense": "interest",
    "tax": "tax",
    "taxes": "tax",
    "income tax": "tax",
    "other": "other",
    "other income": "other",
    "other expense": "other",
    "operating expense": "opex",
    "opex": "opex",
    "sales and marketing": "sm",
    "research and development": "rd",
    "general and administrative": "ga",
}

OPEX_LINE_BY_ACCOUNT_GROUP: dict[str, str] = {
    "s&m": "sm",
    "r&d": "rd",
    "g&a": "ga",
    "d&a": "da",
    "interest": "interest",
}

# Default department → P&L line. Customer Success is part of Sales. Support stays in
# opex (G&A) on the income statement; the Management P&L allocates it to cost of revenue.
OPEX_LINE_BY_DEPARTMENT: dict[str, str] = {
    "sales": "sm",
    "marketing": "sm",
    "sales and marketing": "sm",
    "customer success": "sm",
    "engineering": "rd",
    "product": "rd",
    "research and development": "rd",
    "finance": "ga",
    "g&a": "ga",
    "general and administrative": "ga",
    "all": "ga",
    "support": "ga",
}

SERVICES_REVENUE_TOKENS = ("service", "professional", "implementation", "onboarding", "support", "technical account")
IMPLEMENTATION_REVENUE_TOKENS = ("implementation", "onboarding", "professional")
SERVICES_REVENUE_LABEL = "Implementation & Onboarding"
RECURRING_SERVICES_LABEL = "Recurring Services"


def is_services_revenue(label: str) -> bool:
    """Any services revenue (recurring support/TAM or non-recurring implementation) by account text."""
    text = label.lower()
    return any(t in text for t in SERVICES_REVENUE_TOKENS)


def is_implementation_revenue(label: str) -> bool:
    """Non-recurring services: implementation, onboarding, professional services."""
    text = label.lower()
    return any(t in text for t in IMPLEMENTATION_REVENUE_TOKENS)


def services_revenue_label(label: str) -> str | None:
    """Revenue line for a services account; ``None`` when the account is not services."""
    if not is_services_revenue(label):
        return None
    return SERVICES_REVENUE_LABEL if is_implementation_revenue(label) else RECURRING_SERVICES_LABEL

GL_VERSION_BY_SCENARIO = {"actual": "Actual", "budget": "Budget", "forecast": "Forecast"}


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def classify_gl_line(row: dict[str, Any]) -> str | None:
    """Return the P&L line for one GL row, ``None`` for balance sheet rows."""
    statement = _norm(row.get("statement"))
    if "balance" in statement:
        return None
    category = _norm(row.get("statement_category")) or _norm(row.get("category")) or statement
    line = LINE_BY_CATEGORY.get(category)
    group = _norm(row.get("account_group"))
    if line == "other" and OPEX_LINE_BY_ACCOUNT_GROUP.get(group) == "interest":
        return "interest"
    if line != "opex":
        return line or "unmapped"
    if group in OPEX_LINE_BY_ACCOUNT_GROUP:
        return OPEX_LINE_BY_ACCOUNT_GROUP[group]
    return OPEX_LINE_BY_DEPARTMENT.get(_norm(row.get("department")), "unmapped")


def build_income_statement_rows(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Roll GL rows (period, amount, labels) into Board-shaped monthly IS rows."""
    sums: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for raw in rows:
        line = classify_gl_line(raw)
        if line is None:
            continue
        period = str(raw.get("period") or "")[:7]
        if not period:
            continue
        amount = float(raw.get("amount") or 0.0)
        bucket = sums[period]
        if line == "revenue":
            bucket["revenue"] += -amount
            label = f"{_norm(raw.get('account_name'))} {_norm(raw.get('account_group'))}"
            if is_implementation_revenue(label):
                bucket["impl_rev"] += -amount
            elif is_services_revenue(label):
                bucket["rec_svc_rev"] += -amount
            else:
                bucket["sub_rev"] += -amount
        else:
            bucket[line] += amount

    out: dict[str, dict[str, float]] = {}
    for period, b in sums.items():
        revenue = b.get("revenue", 0.0)
        cogs = b.get("cogs", 0.0)
        sm, rd, ga = b.get("sm", 0.0), b.get("rd", 0.0), b.get("ga", 0.0)
        unmapped = b.get("unmapped", 0.0)
        total_opex = sm + rd + ga + unmapped
        gross_profit = revenue - cogs
        ebitda = gross_profit - total_opex
        da, interest, other, tax = b.get("da", 0.0), b.get("interest", 0.0), b.get("other", 0.0), b.get("tax", 0.0)
        op_income = ebitda - da
        pretax = op_income - interest - other
        row = {
            "revenue": revenue,
            "sub_rev": b.get("sub_rev", 0.0),
            "rec_svc_rev": b.get("rec_svc_rev", 0.0),
            "impl_rev": b.get("impl_rev", 0.0),
            "svc_rev": b.get("rec_svc_rev", 0.0) + b.get("impl_rev", 0.0),
            "cogs": cogs,
            "gross_profit": gross_profit,
            "sm": sm,
            "rd": rd,
            "ga": ga,
            "total_opex": total_opex,
            "ebitda": ebitda,
            "da": da,
            "op_income": op_income,
            "interest": interest,
            "other": other,
            "pretax": pretax,
            "tax": tax,
            "net_income": pretax - tax,
        }
        if revenue:
            row["gm_pct"] = gross_profit / revenue
        if unmapped:
            row["unmapped"] = unmapped
        out[period] = row
    return out


def fetch_gl_pl_rows(db: Session, organization_id: uuid.UUID, version: str) -> list[dict[str, Any]]:
    if not table_exists(db, "gl_actuals"):
        return []
    result = db.execute(
        text(
            """
            select to_char(period, 'YYYY-MM') as period, statement, statement_category, category,
                   account_group, account_name, department, sum(amount) as amount
            from gl_actuals
            where organization_id = :org and lower(version) = lower(:version)
            group by 1, 2, 3, 4, 5, 6, 7
            """
        ),
        {"org": str(organization_id), "version": version},
    )
    return [dict(r) for r in result.mappings()]


def gl_income_statement_by_period(
    db: Session,
    organization_id: uuid.UUID,
    scenario: str,
) -> dict[str, dict[str, float]]:
    """Monthly income statement for ``actual`` / ``budget`` / ``forecast`` from the GL."""
    version = GL_VERSION_BY_SCENARIO[scenario.lower()]
    return build_income_statement_rows(fetch_gl_pl_rows(db, organization_id, version))
