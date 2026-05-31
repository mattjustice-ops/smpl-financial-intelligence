"""Build income statement, balance sheet, and cash flow from GL rows."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from app.services.financial_statements.mapping import (
    BALANCE_SHEET,
    BS_ASSET,
    BS_EQUITY,
    BS_LIABILITY,
    CASH_FLOW,
    CF_FINANCING,
    CF_INVESTING,
    CF_OPERATING,
    INCOME_STATEMENT,
    IS_COGS,
    IS_OPEX,
    IS_OTHER_EXPENSE,
    IS_OTHER_INCOME,
    IS_REVENUE,
    normalize_bs_bucket,
    normalize_cf_bucket,
    normalize_is_bucket,
    normalize_statement,
)
from app.services.financial_statements.repository import GlRow, prior_period_for_bs
from app.services.financial_statements.schemas import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatementsPackage,
    IncomeStatement,
    StatementLine,
    StatementSection,
)
from app.services.mrr.repository import month_start

ZERO = Decimal("0")
MONEY = Decimal("0.01")


def _q(v: Decimal) -> Decimal:
    return v.quantize(MONEY, rounding=ROUND_HALF_UP)


def _sum_amounts(rows: list[GlRow]) -> Decimal:
    return _q(sum((r.amount for r in rows), ZERO))


def _currency(rows: list[GlRow], default: str = "USD") -> str:
    for r in rows:
        if r.currency:
            return r.currency
    return default


def _filter_statement(rows: list[GlRow], statement_type: str) -> list[GlRow]:
    return [r for r in rows if normalize_statement(r.statement) == statement_type]


def _filter_period(rows: list[GlRow], period: date) -> list[GlRow]:
    p = month_start(period)
    return [r for r in rows if month_start(r.period) == p]


def _account_label(r: GlRow) -> str:
    return r.account_name or r.account_number


def _is_cash_account(r: GlRow) -> bool:
    name = (r.account_name or "").lower()
    num = (r.account_number or "").strip()
    return name == "cash" or num == "1000"


def _is_accounts_receivable(r: GlRow) -> bool:
    return "receivable" in (r.account_name or "").lower()


def _is_accounts_payable(r: GlRow) -> bool:
    return "payable" in (r.account_name or "").lower() and "receivable" not in (r.account_name or "").lower()


def _is_deferred_revenue(r: GlRow) -> bool:
    return "deferred revenue" in (r.account_name or "").lower()


def build_income_statement(
    rows: list[GlRow],
    *,
    period_start: date,
    period_end: date,
    currency: str,
) -> IncomeStatement:
    """P&L: sum activity in [period_start, period_end] by category bucket."""
    pl_rows = _filter_statement(rows, INCOME_STATEMENT)
    by_bucket: dict[str, list[GlRow]] = defaultdict(list)
    for r in pl_rows:
        by_bucket[normalize_is_bucket(r.category, r.account_name)].append(r)

    def section_for_bucket(bucket: str, title: str, section_id: str) -> StatementSection:
        bucket_rows = by_bucket.get(bucket, [])
        lines = [
            StatementLine(
                line_id=f"{section_id}_{r.account_number}",
                label=_account_label(r),
                amount=_q(r.amount),
                account_number=r.account_number,
                category=r.category,
            )
            for r in sorted(bucket_rows, key=lambda x: x.account_number)
        ]
        return StatementSection(
            section_id=section_id,
            title=title,
            lines=lines,
            subtotal=_sum_amounts(bucket_rows),
        )

    revenue_sec = section_for_bucket(IS_REVENUE, "Revenue", "revenue")
    cogs_sec = section_for_bucket(IS_COGS, "Cost of Goods Sold", "cogs")
    opex_sec = section_for_bucket(IS_OPEX, "Operating Expenses", "opex")
    other_in_sec = section_for_bucket(IS_OTHER_INCOME, "Other Income", "other_income")
    other_ex_sec = section_for_bucket(IS_OTHER_EXPENSE, "Other Expense", "other_expense")

    total_revenue = revenue_sec.subtotal or ZERO
    total_cogs = cogs_sec.subtotal or ZERO
    total_opex = opex_sec.subtotal or ZERO
    other_in = other_in_sec.subtotal or ZERO
    other_ex = other_ex_sec.subtotal or ZERO

    gross_profit = _q(total_revenue + total_cogs)
    operating_income = _q(gross_profit + total_opex)
    net_income = _q(operating_income + other_in + other_ex)

    sections = [revenue_sec, cogs_sec, opex_sec]
    if other_in_sec.lines:
        sections.append(other_in_sec)
    if other_ex_sec.lines:
        sections.append(other_ex_sec)

    return IncomeStatement(
        period_start=period_start,
        period_end=period_end,
        currency=currency,
        sections=sections,
        total_revenue=total_revenue,
        total_cogs=total_cogs,
        gross_profit=gross_profit,
        total_operating_expense=total_opex,
        operating_income=operating_income,
        net_income=net_income,
    )


def build_balance_sheet(
    rows: list[GlRow],
    *,
    as_of: date,
    currency: str,
) -> BalanceSheet:
    """Balance sheet snapshot at month-end `as_of`."""
    bs_rows = _filter_statement(rows, BALANCE_SHEET)
    snapshot = _filter_period(bs_rows, as_of)
    by_bucket: dict[str, list[GlRow]] = defaultdict(list)
    for r in snapshot:
        by_bucket[normalize_bs_bucket(r.category, r.account_name)].append(r)

    def section(bucket: str, title: str, section_id: str) -> StatementSection:
        bucket_rows = by_bucket.get(bucket, [])
        lines = [
            StatementLine(
                line_id=f"bs_{section_id}_{r.account_number}",
                label=_account_label(r),
                amount=_q(r.amount),
                account_number=r.account_number,
                category=r.category,
            )
            for r in sorted(bucket_rows, key=lambda x: x.account_number)
        ]
        return StatementSection(
            section_id=section_id,
            title=title,
            lines=lines,
            subtotal=_sum_amounts(bucket_rows),
        )

    assets = section(BS_ASSET, "Assets", "assets")
    liabilities = section(BS_LIABILITY, "Liabilities", "liabilities")
    equity = section(BS_EQUITY, "Equity", "equity")

    total_assets = assets.subtotal or ZERO
    total_liabilities = liabilities.subtotal or ZERO
    total_equity = equity.subtotal or ZERO
    total_le = _q(total_liabilities + total_equity)
    check = _q(total_assets - total_le)

    return BalanceSheet(
        as_of=month_start(as_of),
        currency=currency,
        sections=[assets, liabilities, equity],
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        total_liabilities_and_equity=total_le,
        check=check,
    )


def _balance_for_account(bs_rows: list[GlRow], period: date, predicate) -> Decimal:
    total = ZERO
    for r in _filter_period(bs_rows, period):
        if predicate(r):
            total += r.amount
    return _q(total)


def build_cash_flow_statement(
    rows: list[GlRow],
    *,
    period_start: date,
    period_end: date,
    income: IncomeStatement,
    currency: str,
) -> CashFlowStatement:
    """Indirect-method cash flow from P&L + balance sheet changes.

    When GL rows are tagged `Cash Flow`, those amounts are used for the
    corresponding section; otherwise investing/financing default to zero and
    operating is derived from net income and working-capital adjustments.
    """
    bs_rows = _filter_statement(rows, BALANCE_SHEET)
    cf_tagged = _filter_statement(rows, CASH_FLOW)
    p_begin = prior_period_for_bs(period_start)
    p_end = month_start(period_end)
    if not _filter_period(bs_rows, p_begin):
        p_begin = month_start(period_start)

    net_income = income.net_income

    # Working capital adjustments (increase in asset = use of cash).
    ar_begin = _balance_for_account(bs_rows, p_begin, _is_accounts_receivable)
    ar_end = _balance_for_account(bs_rows, p_end, _is_accounts_receivable)
    ap_begin = _balance_for_account(bs_rows, p_begin, _is_accounts_payable)
    ap_end = _balance_for_account(bs_rows, p_end, _is_accounts_payable)
    dr_begin = _balance_for_account(bs_rows, p_begin, _is_deferred_revenue)
    dr_end = _balance_for_account(bs_rows, p_end, _is_deferred_revenue)

    delta_ar = _q(ar_end - ar_begin)
    delta_ap = _q(ap_end - ap_begin)
    delta_dr = _q(dr_end - dr_begin)

    adj_ar = _q(-delta_ar)
    adj_ap = _q(delta_ap)
    adj_dr = _q(delta_dr)

    wc_lines = [
        StatementLine(
            line_id="cf_delta_ar",
            label="Change in accounts receivable",
            amount=adj_ar,
            indent_level=1,
        ),
        StatementLine(
            line_id="cf_delta_ap",
            label="Change in accounts payable",
            amount=adj_ap,
            indent_level=1,
        ),
        StatementLine(
            line_id="cf_delta_dr",
            label="Change in deferred revenue",
            amount=adj_dr,
            indent_level=1,
        ),
    ]
    wc_total = _q(adj_ar + adj_ap + adj_dr)

    # Direct-tagged cash flow lines in range (summed).
    op_direct = ZERO
    inv_direct = ZERO
    fin_direct = ZERO
    pl_cf_rows = [r for r in cf_tagged if month_start(period_start) <= month_start(r.period) <= p_end]
    for r in pl_cf_rows:
        bucket = normalize_cf_bucket(r.category, r.account_name)
        if bucket == CF_INVESTING:
            inv_direct += r.amount
        elif bucket == CF_FINANCING:
            fin_direct += r.amount
        else:
            op_direct += r.amount
    op_direct = _q(op_direct)
    inv_direct = _q(inv_direct)
    fin_direct = _q(fin_direct)

    cash_from_operations = _q(net_income + wc_total + op_direct)
    cash_from_investing = inv_direct
    cash_from_financing = fin_direct

    cash_begin = _balance_for_account(bs_rows, p_begin, _is_cash_account)
    cash_end = _balance_for_account(bs_rows, p_end, _is_cash_account)
    net_change_in_cash = _q(cash_end - cash_begin)
    computed_change = _q(cash_from_operations + cash_from_investing + cash_from_financing)
    reconciliation_delta = _q(net_change_in_cash - computed_change)

    operating_section = StatementSection(
        section_id="operating",
        title="Cash from operating activities",
        lines=[
            StatementLine(
                line_id="cf_net_income",
                label="Net income",
                amount=net_income,
                is_subtotal=False,
            ),
            *wc_lines,
            StatementLine(
                line_id="cf_op_subtotal",
                label="Net cash from operating activities",
                amount=cash_from_operations,
                is_subtotal=True,
            ),
        ],
        subtotal=cash_from_operations,
    )
    investing_section = StatementSection(
        section_id="investing",
        title="Cash from investing activities",
        lines=[
            StatementLine(
                line_id="cf_investing_total",
                label="Investing activities",
                amount=cash_from_investing,
            )
        ],
        subtotal=cash_from_investing,
    )
    financing_section = StatementSection(
        section_id="financing",
        title="Cash from financing activities",
        lines=[
            StatementLine(
                line_id="cf_financing_total",
                label="Financing activities",
                amount=cash_from_financing,
            )
        ],
        subtotal=cash_from_financing,
    )

    return CashFlowStatement(
        period_start=period_start,
        period_end=period_end,
        currency=currency,
        method="indirect",
        sections=[operating_section, investing_section, financing_section],
        net_income=net_income,
        cash_from_operations=cash_from_operations,
        cash_from_investing=cash_from_investing,
        cash_from_financing=cash_from_financing,
        net_change_in_cash=net_change_in_cash,
        cash_beginning=cash_begin,
        cash_ending=cash_end,
        reconciliation_delta=reconciliation_delta,
    )


def build_financial_statements(
    rows: list[GlRow],
    *,
    organization_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> FinancialStatementsPackage:
    currency = _currency(rows)
    income = build_income_statement(
        rows, period_start=period_start, period_end=period_end, currency=currency
    )
    balance = build_balance_sheet(rows, as_of=period_end, currency=currency)
    cashflow = build_cash_flow_statement(
        rows,
        period_start=period_start,
        period_end=period_end,
        income=income,
        currency=currency,
    )
    return FinancialStatementsPackage(
        organization_id=str(organization_id),
        period_start=period_start,
        period_end=period_end,
        currency=currency,
        income_statement=income,
        balance_sheet=balance,
        cash_flow_statement=cashflow,
        source_row_count=len(rows),
    )
