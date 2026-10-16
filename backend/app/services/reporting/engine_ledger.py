"""General-ledger journals for a Forecast or Budget engine promotion.

The engines keep their formulas and export income statement, balance sheet and cash
flow rows. This posts those rows as journals — depreciation, capex, interest, debt —
and replaces that version's ledger for those months. The Board reads the ledger.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import delete, inspect
from sqlalchemy.orm import Session

from app.models.demo_finance import GlActual
from app.services.reporting.gl_balance_sheet import gl_balance_sheet_and_cash_flow_by_period

CENT = Decimal("0.01")
NON_CASH = "Balance Sheet Activity"

# account, name, statement, category, group, expense type, credit-normal
_PL = {
    "revenue": ("4000", "Revenue", "Income Statement", "Revenue", "Revenue", "Revenue", True),
    "cogs": ("5000", "Cost of Revenue", "Income Statement", "COGS", "COGS", "Cost of Revenue", False),
    "sm": ("6000", "Sales and Marketing", "Income Statement", "Operating Expense", "S&M", "Operating Expense", False),
    "rd": ("6100", "Research and Development", "Income Statement", "Operating Expense", "R&D", "Operating Expense", False),
    "ga": ("6200", "General and Administrative", "Income Statement", "Operating Expense", "G&A", "Operating Expense", False),
    "da": ("7000", "Depreciation and Amortization", "Income Statement", "D&A", "D&A", "D&A", False),
    "interest": ("7100", "Interest Expense", "Income Statement", "Interest", "Interest", "Interest", False),
    "tax": ("7500", "Income Tax", "Income Statement", "Tax", "Tax", "Tax", False),
}
_BS = {
    "cash": ("1000", "Cash", "Cash", "Cash"),
    "ar": ("1100", "Accounts Receivable", "AR", "Accounts Receivable"),
    "prepaids": ("1200", "Prepaids and Other Current Assets", "Current Assets", "Prepaids"),
    "dc_current": ("1250", "Deferred Commissions - Current", "Deferred Commissions", "Deferred Commissions"),
    "ppe": ("1500", "Property and Equipment Net", "PP&E", "Fixed Assets"),
    "dc_noncurrent": ("1550", "Deferred Commissions - Noncurrent", "Deferred Commissions", "Deferred Commissions Noncurrent"),
    "other_assets": ("1600", "Other Assets", "Other Assets", "Other Assets"),
    "ap": ("2000", "Accounts Payable", "AP", "Accounts Payable"),
    "dr": ("2100", "Deferred Revenue", "Deferred Revenue", "Deferred Revenue"),
    "debt": ("2500", "Debt", "Debt", "Debt"),
    "other_liabilities": ("2600", "Other Liabilities", "Other Liabilities", "Other Liabilities"),
    "equity": ("3000", "Equity", "Equity", "Equity"),
    "apic": ("3311", "APIC - Stock Compensation", "Equity", "Equity"),
}
_CREDIT = {"ap", "dr", "debt", "other_liabilities", "equity", "apic"}


def _q(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _num(row: dict[str, Any], *keys: str) -> Decimal | None:
    for key in keys:
        raw = row.get(key)
        if raw not in (None, ""):
            return _q(Decimal(str(raw)))
    return None


def _prior_month(period: str) -> str:
    year, month = int(period[:4]), int(period[5:7])
    return f"{year - 1}-12" if month == 1 else f"{year}-{month - 1:02d}"


def prior_from_balance(balance: dict[str, Any]) -> dict[str, Decimal]:
    """Reporter balance-sheet line names to the journal builder's lines."""
    return {
        "cash": _q(Decimal(str(balance.get("cash") or 0))),
        "ar": _q(Decimal(str(balance.get("accounts_receivable") or 0))),
        "prepaids": _q(Decimal(str(balance.get("prepaids_and_other_current_assets") or 0))),
        "dc_current": _q(Decimal(str(balance.get("deferred_commissions_current") or 0))),
        "dc_noncurrent": _q(Decimal(str(balance.get("deferred_commissions_noncurrent") or 0))),
        "ppe": _q(Decimal(str(balance.get("property_and_equipment_net") or 0))),
        "other_assets": _q(Decimal(str(balance.get("other_assets") or 0))),
        "ap": _q(Decimal(str(balance.get("accounts_payable") or 0))),
        "dr": _q(Decimal(str(balance.get("deferred_revenue") or 0))),
        "debt": _q(Decimal(str(balance.get("debt") or 0))),
        "other_liabilities": _q(Decimal(str(balance.get("other_liabilities") or 0))),
        "accrued": Decimal("0"),
        "equity": _q(Decimal(str(balance.get("equity") or 0))),
    }


def _line(prev: dict[str, Decimal], row: dict[str, Any], key: str, *names: str) -> Decimal:
    found = _num(row, *names)
    return prev[key] if found is None else found


def ledger_rows(
    version: str,
    months: list[str],
    income: dict[str, dict[str, Any]],
    balance: dict[str, dict[str, Any]],
    cash_flow: dict[str, dict[str, Any]],
    prior: dict[str, Decimal],
    kept: dict[str, dict[str, Decimal]] | None = None,
) -> list[dict[str, Any]]:
    """Journals whose running balances equal the engine statements.

    ``kept`` supplies month-end balances for lines the engine export does not carry
    (deferred commissions, other assets) so those balances stay on the ledger.
    """
    rows: list[dict[str, Any]] = []
    prev = dict(prior)
    held = kept or {}

    def add(period: str, key: str, amount: Decimal, label: str, *, non_cash: bool = False, note: str) -> None:
        if amount == 0:
            return
        if key in _PL:
            number, name, statement, category, group, expense, _credit = _PL[key]
        else:
            number, name, group, expense = _BS[key]
            statement, category = "Balance Sheet", group
        natural = -amount if key in _CREDIT or (key in _PL and _PL[key][6]) else amount
        rows.append({
            "version": version,
            "period": period,
            "account_number": number,
            "account_name": name,
            "statement": statement,
            "statement_category": category,
            "account_group": group,
            "expense_type": expense,
            "department": NON_CASH if non_cash else "",
            "source_record_id": f"{version}-{period}-{number}-{label}",
            "source_system": "Fixed Assets" if label in ("capex", "depreciation") else "Journal Entry",
            "source_file": f"{version}_gl_detail.csv",
            "amount": _q(natural),
            "notes": note,
        })

    for period in months:
        inc = income[period]
        bs = balance[period]
        cf = cash_flow.get(period, {})
        keep = held.get(period, {})
        revenue = _num(inc, "revenue") or Decimal("0")
        cogs = _num(inc, "cost_of_revenue", "cogs") or Decimal("0")
        sm = _num(inc, "sales_and_marketing", "sm") or Decimal("0")
        rd = _num(inc, "research_and_development", "rd") or Decimal("0")
        ga = _num(inc, "general_and_administrative", "ga") or Decimal("0")
        da = _num(inc, "depreciation_and_amortization", "da") or Decimal("0")
        interest = _num(inc, "interest_expense", "interest") or Decimal("0")
        tax = _num(inc, "tax_expense", "tax") or Decimal("0")
        ni = _num(inc, "net_income", "ni")
        if ni is None:
            ni = revenue - cogs - sm - rd - ga - da - interest - tax
        sbc = _num(cf, "stock_based_compensation", "sbc") or Decimal("0")
        capex_flow = _num(cf, "capital_expenditures", "capex") or Decimal("0")
        capex_debit = _q(-capex_flow)

        targets = {
            "cash": _line(prev, bs, "cash", "cash"),
            "ar": _line(prev, bs, "ar", "accounts_receivable", "ar"),
            "prepaids": _line(prev, bs, "prepaids", "prepaids_and_other_current", "prepaids", "prepaid_expenses"),
            "dc_current": keep.get("dc_current", _line(prev, bs, "dc_current", "deferred_commissions_current")),
            "dc_noncurrent": keep.get("dc_noncurrent", _line(prev, bs, "dc_noncurrent", "deferred_commissions_noncurrent")),
            "ppe": _line(prev, bs, "ppe", "ppe_net", "ppe", "property_and_equipment_net"),
            "other_assets": keep.get("other_assets", _line(prev, bs, "other_assets", "other_assets")),
            "ap": _line(prev, bs, "ap", "accounts_payable", "ap"),
            "dr": _line(prev, bs, "dr", "deferred_revenue", "deferred_rev", "dr"),
            "debt": _line(prev, bs, "debt", "debt"),
            "accrued": _line(prev, bs, "accrued", "accrued_commissions", "accrued_comm"),
            "equity": _line(prev, bs, "equity", "equity"),
        }
        other = _line(prev, bs, "other_liabilities", "other_liabilities")
        targets["other_liabilities"] = _q(other + targets["accrued"])

        for key, amount in (
            ("revenue", revenue), ("cogs", cogs), ("sm", sm), ("rd", rd), ("ga", ga),
            ("da", da), ("interest", interest), ("tax", tax),
        ):
            add(period, key, amount, key, note=f"{key.replace('_', ' ')} from the {version} engine")
        add(period, "ppe", -da, "depreciation", non_cash=True,
            note="depreciation journal: credit to property and equipment for this month's depreciation expense")
        add(period, "ppe", capex_debit, "capex",
            note="capex journal: debit to property and equipment")
        add(period, "cash", -capex_debit, "capex", note="capex journal: credit to cash")
        add(period, "cash", -interest, "interest_paid",
            note="interest journal: cash paid for this month's interest expense")
        ppe_gap = _q(targets["ppe"] - prev["ppe"] - capex_debit + da)
        add(period, "ppe", ppe_gap, "ppe_tie", non_cash=True,
            note="property and equipment other than this month's capex and depreciation")
        add(period, "apic", sbc, "stock_comp", non_cash=True,
            note="stock compensation journal: non-cash credit to APIC")

        debt_delta = _q(targets["debt"] - prev["debt"])
        add(period, "debt", debt_delta, "issuance" if debt_delta > 0 else "repayment",
            note="debt journal: draw" if debt_delta > 0 else "debt journal: repayment")
        add(period, "cash", debt_delta, "issuance" if debt_delta > 0 else "repayment",
            note="debt journal: cash from the draw or repayment")
        equity_gap = _q(targets["equity"] - prev["equity"] - ni - sbc)
        add(period, "equity", equity_gap, "equity_raise",
            note="equity journal: financing other than this month's earnings and stock compensation")
        add(period, "cash", equity_gap, "equity_raise", note="equity journal: cash from that financing")

        for key in ("ar", "prepaids", "dc_current", "dc_noncurrent", "other_assets", "ap", "dr"):
            delta = _q(targets[key] - prev[key])
            add(period, key, delta, "net_change", note=f"{key.replace('_', ' ')} change from the {version} engine")
        other_delta = _q(targets["other_liabilities"] - prev["other_liabilities"] - prev["accrued"])
        add(period, "other_liabilities", other_delta, "net_change",
            note=f"other liabilities, including accrued commissions, from the {version} engine")

        posted_cash = sum((r["amount"] for r in rows if r["period"] == period and r["account_number"] == "1000"), Decimal("0"))
        cash_gap = _q(targets["cash"] - prev["cash"] - posted_cash)
        add(period, "cash", cash_gap, "net_cash", note="cash: other side of this month's entries")
        prev = targets
        prev["other_liabilities"] = _q(targets["other_liabilities"] - targets["accrued"])
        prev["accrued"] = targets["accrued"]
    return rows


def _by_period(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r.get("period") or "")[:7]: r for r in rows}


def _gl_ready(session: Session) -> bool:
    bind = session.get_bind()
    if bind is None:
        return False
    return "gl_actuals" in set(inspect(bind).get_table_names())


def post_engine_ledger(
    session: Session,
    organization_id: uuid.UUID,
    version: str,
    tables: dict[str, list[dict[str, Any]]],
    *,
    income_table: str,
    balance_table: str,
    cash_flow_table: str,
) -> int:
    """Replace ``version`` ledger months with journals built from the engine's statements."""
    if not _gl_ready(session):
        return 0
    income = _by_period(tables.get(income_table) or [])
    balance = _by_period(tables.get(balance_table) or [])
    cash_flow = _by_period(tables.get(cash_flow_table) or [])
    months = [p for p in sorted(balance) if p in income]
    if not months:
        return 0
    opening_scenario = "forecast" if version == "Budget" else "actual"
    built, _flow = gl_balance_sheet_and_cash_flow_by_period(session, organization_id, opening_scenario)
    opening_month = _prior_month(months[0])
    if opening_month not in built and version == "Budget":
        built, _flow = gl_balance_sheet_and_cash_flow_by_period(session, organization_id, "actual")
    if opening_month not in built:
        raise ValueError(f"No {opening_month} balance sheet to start the {version} ledger from.")
    existing, _existing_flow = gl_balance_sheet_and_cash_flow_by_period(session, organization_id, version.lower())
    kept: dict[str, dict[str, Decimal]] = {}
    for period in months:
        have = existing.get(period)
        if not have or any(k in balance[period] for k in ("deferred_commissions_current", "other_assets")):
            continue
        kept[period] = {
            "dc_current": _q(Decimal(str(have.get("deferred_commissions_current") or 0))),
            "dc_noncurrent": _q(Decimal(str(have.get("deferred_commissions_noncurrent") or 0))),
            "other_assets": _q(Decimal(str(have.get("other_assets") or 0))),
        }
    rows = ledger_rows(version, months, income, balance, cash_flow, prior_from_balance(built[opening_month]), kept)
    start = date(int(months[0][:4]), int(months[0][5:7]), 1)
    end = date(int(months[-1][:4]), int(months[-1][5:7]), 1)
    session.execute(
        delete(GlActual).where(
            GlActual.organization_id == organization_id,
            GlActual.version == version,
            GlActual.period >= start,
            GlActual.period <= end,
        )
    )
    for row in rows:
        year, month = int(row["period"][:4]), int(row["period"][5:7])
        session.add(GlActual(
            organization_id=organization_id,
            period=date(year, month, 1),
            version=version,
            account_number=row["account_number"],
            account_name=row["account_name"],
            statement=row["statement"],
            statement_category=row["statement_category"],
            account_group=row["account_group"],
            expense_type=row["expense_type"],
            department=row["department"],
            cost_center="",
            sub_department="",
            vendor_id="",
            source_file=row["source_file"],
            source_record_id=row["source_record_id"],
            amount=row["amount"],
            currency="USD",
            subsidiary="US Parent",
            source_system=row["source_system"],
            notes=row["notes"],
        ))
    session.flush()
    return len(rows)
