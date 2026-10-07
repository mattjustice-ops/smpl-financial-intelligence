"""Balance sheet and cash flow built from GL detail (gl_actuals).

Method: docs/soc2/controls/financial_dashboard_cf_re_logic.md.

  * Balance sheet rows in the GL are activity. Rows with source_system "Opening Balance"
    are the opening trial balance at the cutoff month. A balance is opening + all
    activity through the month.
  * Retained earnings is never read from GL activity: it is the opening retained
    earnings plus GL net income from the month after the cutoff through the prior
    month. The current month's net income is its own line.
  * Cash flow (indirect): net income, plus non-cash items, plus working capital changes,
    then investing and financing. Non-cash items are the balance sheet activity tagged
    department "Balance Sheet Activity" (depreciation against PP&E, stock comp credited
    to APIC, ...), shown as D&A (from the P&L), stock comp and other. Tagged activity is
    excluded from working capital, investing and financing.
  * Checks: CFO = NI + non-cash + working capital; net = CFO + investing + financing;
    ending = beginning + net; ending = balance sheet cash.
  * Budget and Forecast balances continue from Actual: Actual activity before the
    version's first balance sheet month, then the version's own activity.

Sign rule: GL amounts are debit-positive. Liabilities and equity are shown positive.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any, Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import table_exists
from app.services.reporting.gl_income_statement import (
    GL_VERSION_BY_SCENARIO,
    build_income_statement_rows,
    fetch_gl_pl_rows,
)

OPENING_SOURCE = "opening balance"
NON_CASH_DEPARTMENT = "balance sheet activity"

BS_LINE_BY_TYPE: dict[str, str] = {
    "cash": "cash",
    "accounts receivable": "accounts_receivable",
    "ar": "accounts_receivable",
    "prepaids": "prepaids_and_other_current_assets",
    "current assets": "prepaids_and_other_current_assets",
    "deferred commissions": "deferred_commissions_current",
    "deferred commissions noncurrent": "deferred_commissions_noncurrent",
    "fixed assets": "property_and_equipment_net",
    "pp&e": "property_and_equipment_net",
    "other assets": "other_assets",
    "accounts payable": "accounts_payable",
    "ap": "accounts_payable",
    "deferred revenue": "deferred_revenue",
    "debt": "debt",
    "other liabilities": "other_liabilities",
    "equity": "equity",
}

ASSET_LINES = (
    "cash",
    "accounts_receivable",
    "prepaids_and_other_current_assets",
    "deferred_commissions_current",
    "property_and_equipment_net",
    "deferred_commissions_noncurrent",
    "other_assets",
)
LIABILITY_LINES = ("accounts_payable", "deferred_revenue", "debt", "other_liabilities")
EQUITY_LINES = ("paid_in_capital", "apic_stock_compensation", "retained_earnings_account")

# Capitalized contract costs (ASC 340-40) are operating: payouts are operating cash out and
# amortization is in the P&L, so both portions move through working capital, not investing.
WORKING_CAPITAL = {
    "accounts_receivable": "change_in_accounts_receivable",
    "prepaids_and_other_current_assets": "change_in_prepaids",
    "deferred_commissions_current": "change_in_deferred_commissions",
    "deferred_commissions_noncurrent": "change_in_deferred_commissions",
    "accounts_payable": "change_in_accounts_payable",
    "deferred_revenue": "change_in_deferred_revenue",
    "other_liabilities": "change_in_other_liabilities",
}
INVESTING = {"property_and_equipment_net": "capital_expenditures", "other_assets": "change_in_other_assets"}
FINANCING = {"debt": "debt_issuance_repayment", "paid_in_capital": "equity_issuance"}
NON_CASH_LABEL = {"apic_stock_compensation": "stock_based_compensation"}


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def classify_bs_line(row: dict[str, Any]) -> str | None:
    """Balance sheet line for one GL row; ``None`` for P&L rows, ``unmapped`` if unknown."""
    if "balance" not in _norm(row.get("statement")):
        return None
    line = BS_LINE_BY_TYPE.get(_norm(row.get("expense_type"))) or BS_LINE_BY_TYPE.get(_norm(row.get("account_group")))
    if line != "equity":
        return line or "unmapped"
    name = _norm(row.get("account_name"))
    if "retained" in name:
        return "retained_earnings_account"
    if "stock comp" in name or "sbc" in name:
        return "apic_stock_compensation"
    return "paid_in_capital"


def build_balance_sheet_and_cash_flow(
    bs_rows: Iterable[dict[str, Any]],
    pl_rows: Iterable[dict[str, Any]],
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    """Monthly balance sheet and cash flow (mapper column names) from GL rows."""
    bs_rows = list(bs_rows)
    income = build_income_statement_rows(pl_rows)
    opening = {str(r.get("period") or "")[:7] for r in bs_rows if _norm(r.get("source_system")) == OPENING_SOURCE}
    cutoff = max(opening) if opening else None

    activity: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    non_cash: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    retained_base = 0.0
    for r in bs_rows:
        period = str(r.get("period") or "")[:7]
        line = classify_bs_line(r)
        if not period or line is None:
            continue
        amount = float(r.get("amount") or 0.0)
        is_opening = _norm(r.get("source_system")) == OPENING_SOURCE
        if line == "retained_earnings_account":
            if is_opening:
                retained_base += -amount
            continue
        activity[period][line] += amount
        if not is_opening and _norm(r.get("department")) == NON_CASH_DEPARTMENT:
            non_cash[period][line] += amount

    periods = sorted(set(activity) | {p for p in income if cutoff is None or p > cutoff})
    running: dict[str, float] = defaultdict(float)
    retained = retained_base
    balance: dict[str, dict[str, float]] = {}
    cash_flow: dict[str, dict[str, float]] = {}
    prior_cash: float | None = None
    for p in periods:
        for line, amount in activity[p].items():
            running[line] += amount
        net_income = income.get(p, {}).get("net_income", 0.0) if cutoff is None or p > cutoff else 0.0

        b = {line: running[line] for line in ASSET_LINES}
        b.update({line: -running[line] for line in LIABILITY_LINES})
        b["paid_in_capital"] = -running["paid_in_capital"]
        b["apic_stock_compensation"] = -running["apic_stock_compensation"]
        b["retained_earnings"] = retained
        b["current_period_net_income"] = net_income
        b["equity"] = b["paid_in_capital"] + b["apic_stock_compensation"] + retained + net_income
        b["total_assets"] = sum(b[line] for line in ASSET_LINES)
        b["total_liabilities"] = sum(b[line] for line in LIABILITY_LINES)
        b["total_liabilities_and_equity"] = b["total_liabilities"] + b["equity"]
        b["balance_check"] = b["total_assets"] - b["total_liabilities_and_equity"]
        if running["unmapped"]:
            b["unmapped"] = running["unmapped"]
        balance[p] = b
        retained += net_income

        if prior_cash is not None:
            cash_flow[p] = _cash_flow_month(p, activity[p], non_cash[p], income.get(p, {}), net_income, prior_cash, b["cash"])
        prior_cash = b["cash"]
    return balance, cash_flow


def _cash_flow_month(
    period: str,
    activity: dict[str, float],
    non_cash: dict[str, float],
    income: dict[str, float],
    net_income: float,
    beginning_cash: float,
    balance_sheet_cash: float,
) -> dict[str, float]:
    cf: dict[str, float] = defaultdict(float)
    cf["beginning_cash"] = beginning_cash
    cf["net_income"] = net_income
    cf["depreciation_and_amortization"] = income.get("da", 0.0)
    non_cash_total = -sum(non_cash.values())
    for line, amount in non_cash.items():
        if line in NON_CASH_LABEL:
            cf[NON_CASH_LABEL[line]] += -amount
    # D&A's balance sheet side (PP&E, prepaids, ...) is tagged non-cash; whatever non-cash
    # activity is not D&A or a labeled item shows as other non-cash.
    cf["other_non_cash"] = non_cash_total - cf["depreciation_and_amortization"] - sum(
        cf[label] for label in NON_CASH_LABEL.values()
    )
    for line, amount in activity.items():
        cash_effect = -(amount - non_cash.get(line, 0.0))
        if line in WORKING_CAPITAL:
            cf[WORKING_CAPITAL[line]] += cash_effect
        elif line in INVESTING:
            cf[INVESTING[line]] += cash_effect
        elif line in FINANCING:
            cf[FINANCING[line]] += cash_effect
        elif line == "apic_stock_compensation":
            cf["equity_issuance"] += cash_effect
        elif line not in ("cash",):
            cf["unclassified"] += cash_effect
    cf["non_cash_total"] = non_cash_total
    cf["working_capital_total"] = sum(cf[k] for k in set(WORKING_CAPITAL.values()))
    cf["net_cash_from_operating_activities"] = net_income + cf["non_cash_total"] + cf["working_capital_total"] + cf["unclassified"]
    cf["net_cash_from_investing_activities"] = sum(cf[k] for k in INVESTING.values())
    cf["net_cash_from_financing_activities"] = sum(cf[k] for k in FINANCING.values())
    cf["net_change_in_cash"] = (
        cf["net_cash_from_operating_activities"]
        + cf["net_cash_from_investing_activities"]
        + cf["net_cash_from_financing_activities"]
    )
    cf["ending_cash"] = beginning_cash + cf["net_change_in_cash"]
    cf["balance_sheet_cash"] = balance_sheet_cash
    cf["cash_check"] = cf["ending_cash"] - balance_sheet_cash
    return dict(cf)


def fetch_gl_bs_rows(db: Session, organization_id: uuid.UUID, version: str) -> list[dict[str, Any]]:
    if not table_exists(db, "gl_actuals"):
        return []
    result = db.execute(
        text(
            """
            select to_char(period, 'YYYY-MM') as period, statement, account_group, expense_type,
                   account_name, department, source_system, sum(amount) as amount
            from gl_actuals
            where organization_id = :org and lower(version) = lower(:version)
              and lower(coalesce(statement, '')) like 'balance%'
            group by 1, 2, 3, 4, 5, 6, 7
            """
        ),
        {"org": str(organization_id), "version": version},
    )
    return [dict(r) for r in result.mappings()]


def chain_rows(
    version: str,
    actual_bs: list[dict[str, Any]],
    actual_pl: list[dict[str, Any]],
    version_bs: list[dict[str, Any]],
    version_pl: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
    """Rows for one version: Actual before the version's first balance sheet month, then the version."""
    if version == "Actual":
        return actual_bs, actual_pl, None
    if not version_bs:
        return [], [], None
    start = min(str(r["period"])[:7] for r in version_bs)
    bs = [r for r in actual_bs if str(r["period"])[:7] < start] + version_bs
    pl = [r for r in actual_pl if str(r["period"])[:7] < start] + [r for r in version_pl if str(r["period"])[:7] >= start]
    return bs, pl, start


def gl_balance_sheet_and_cash_flow_by_period(
    db: Session,
    organization_id: uuid.UUID,
    scenario: str,
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    """Monthly balance sheet and cash flow for ``actual`` / ``budget`` / ``forecast`` from the GL."""
    version = GL_VERSION_BY_SCENARIO[scenario.lower()]
    actual_bs = fetch_gl_bs_rows(db, organization_id, "Actual")
    actual_pl = fetch_gl_pl_rows(db, organization_id, "Actual")
    if version == "Actual":
        bs_rows, pl_rows, start = actual_bs, actual_pl, None
    else:
        bs_rows, pl_rows, start = chain_rows(
            version,
            actual_bs,
            actual_pl,
            fetch_gl_bs_rows(db, organization_id, version),
            fetch_gl_pl_rows(db, organization_id, version),
        )
    balance, cash_flow = build_balance_sheet_and_cash_flow(bs_rows, pl_rows)
    if start:
        balance = {p: v for p, v in balance.items() if p >= start}
        cash_flow = {p: v for p, v in cash_flow.items() if p >= start}
    return balance, cash_flow
