"""Explain cash-bridge C4 residual without plugging Other operating.

Customers clear C4 from a tied-out GL cash spine (AP rollforward for vendor
cash; payroll/commission cash-true registers that reconcile to the GL) and/or
mapping GL accounts into bridge buckets, then rebuilding Table Update.
Never plug Other operating for unexplained cash.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import table_exists
from app.services.reporting.account_maps import load_account_maps
from app.services.reporting.gl_one_book import ONE_BOOK_SQL
from app.services.warehouse.compile_schedules import (
    _dec,
    _sum_period_amount,
    _vendor_cash_paid,
    cash_costs,
    money,
)


def bridge_residual_breakdown(
    db: Session,
    organization_id: uuid.UUID,
    period: str,
) -> dict[str, Any]:
    """Named bridge lines, residual, cash-true coverage, and unbucketed GL."""
    month = str(period or "")[:7]
    org = str(organization_id)
    empty: dict[str, Any] = {
        "period": month,
        "bridge": None,
        "residual": None,
        "cash_true": {},
        "missing_cash_true": [],
        "unbucketed_gl": [],
        "how_to_clear": [],
    }
    if len(month) != 7 or month[4] != "-" or not table_exists(db, "actual_cash_flow_bridge"):
        return empty

    row = db.execute(
        text(
            """
            select beginning_cash, ending_cash,
                   coalesce(nullif(cash_collections_from_invoices,''), nullif(collections,''), nullif(cash_collections,'')) as collections,
                   payroll_cash_out, commission_cash_out, vendor_cash_out_n30,
                   tax_cash_out, interest_cash_out, other_operating_cash_out, capex,
                   financing_to_maintain_cash_floor, bridge_check, source_filename, notes
            from actual_cash_flow_bridge
            where organization_id = :org and left(cast(period as text), 7) = :period
            limit 1
            """
        ),
        {"org": org, "period": month},
    ).mappings().first()
    if not row:
        return empty

    bridge = {key: (None if row.get(key) in (None, "") else str(row.get(key))) for key in row.keys()}
    residual = _dec(row.get("bridge_check"))

    payroll_reg = _sum_period_amount(db, "actual_payroll_register", org, month, "total_payroll_cost")
    commission_paid = _sum_period_amount(
        db, "actual_commission_payouts", org, month, "commission_amount"
    )
    vendor_paid = _vendor_cash_paid(db, org, month)
    vendor_from_gl = "AP rollforward" in str(row.get("notes") or "") or str(
        row.get("source_filename") or ""
    ).startswith("compiled:gl")
    cash_true = {
        "payroll_register": None if payroll_reg is None else money(payroll_reg),
        "commission_payouts": None if commission_paid is None else money(commission_paid),
        "vendor_payments": None if vendor_paid is None else money(vendor_paid),
        "vendor_from_gl_ap_rollforward": bool(vendor_from_gl and row.get("vendor_cash_out_n30")),
    }
    missing = []
    if payroll_reg is None:
        missing.append("actual_payroll_register")
    if commission_paid is None:
        missing.append("actual_commission_payouts")
    # Vendor payment files are optional when the bridge already used GL AP rollforward.
    if vendor_paid is None and not cash_true["vendor_from_gl_ap_rollforward"]:
        missing.append("actual_vendor_payments (or complete GL AP for rollforward)")

    unbucketed = _unbucketed_gl_rows(db, organization_id, month)
    notes = str(row.get("notes") or "")
    how: list[str] = []
    if "Data gaps:" in notes or "gl-incomplete" in str(row.get("source_filename") or ""):
        how.append(
            "Complete the tied-out GL for this close (cash, AP balances, and vendor "
            "purchases) so vendor cash can compile from the AP rollforward. "
            "Do not plug Other operating."
        )
    if missing:
        how.append(
            "Cash-true registers incomplete for this month: "
            + ", ".join(missing)
            + ". Load detail that reconciles to the GL — accrual P&L is not cash paid."
        )
    if residual and not missing:
        how.append(
            f"Named lines miss ending cash by {money(residual)}. Identify the real cash "
            "movement in the GL (fees, lease, accrued payouts, etc.), map it to the right "
            "bridge bucket (including other_operating only if that is the true class), "
            "then Build on Table Update. Do not plug the residual."
        )
    if unbucketed:
        how.append(
            "On Mapping, assign unbucketed GL accounts to payroll, commission, vendor, "
            "interest, tax, or other_operating. Then Build the statements on Table Update."
        )
    if not how and residual:
        how.append(
            "Named GL cash lines still miss ending cash. Confirm the GL cash spine ties "
            "out, then rebuild Table Update. Do not plug Other operating."
        )
    if not residual:
        how.append("Bridge foots. No residual to clear.")

    return {
        "period": month,
        "bridge": bridge,
        "residual": money(residual),
        "cash_true": cash_true,
        "missing_cash_true": missing,
        "unbucketed_gl": unbucketed[:40],
        "how_to_clear": how,
    }


def _unbucketed_gl_rows(
    db: Session, organization_id: uuid.UUID, period: str
) -> list[dict[str, Any]]:
    if not table_exists(db, "gl_actuals"):
        return []
    maps = load_account_maps(db, organization_id)
    rows = db.execute(
        text(
            f"""
            select coalesce(account_number, '') as account_number,
                   coalesce(account_group, '') as account_group,
                   coalesce(account_name, '') as account_name,
                   sum(cast(amount as numeric)) as amount
            from gl_actuals
            where organization_id = :org
              and lower(version) = 'actual'
              and to_char(period, 'YYYY-MM') = :period
              and {ONE_BOOK_SQL}
            group by 1, 2, 3
            having abs(sum(cast(amount as numeric))) > 0.005
            order by abs(sum(cast(amount as numeric))) desc
            """
        ),
        {"org": str(organization_id), "period": period},
    ).mappings().all()

    classified = cash_costs(
        [(str(r["account_group"]), str(r["account_name"]), r["amount"]) for r in rows],
        account_maps=maps,
        account_numbers=[str(r["account_number"]) for r in rows],
    )
    # Rebuild per-row classification the same way cash_costs does for listing.
    out: list[dict[str, Any]] = []
    for raw in rows:
        account = str(raw["account_number"] or "").strip()
        group = str(raw["account_group"] or "")
        name = str(raw["account_name"] or "")
        amount = _dec(raw["amount"])
        mapped = maps.get(account, "").strip().lower() if account else ""
        bucket = _row_bucket(mapped, group, name)
        if bucket:
            continue
        # Skip pure BS / revenue / cash spine noise from the residual helper list.
        kind = group.strip().lower()
        if kind in {"revenue", "cash", "ar", "ap", "equity", "deferred revenue", "pp&e", "current assets"}:
            continue
        out.append(
            {
                "account_number": account,
                "account_group": group,
                "account_name": name,
                "amount": money(amount),
                "suggested_line": _suggest_bridge_line(group, name),
            }
        )
    _ = classified  # retained for future parity checks
    return out


def _row_bucket(mapped: str, group: str, name: str) -> str | None:
    if mapped in {"payroll", "commission", "vendor", "interest", "tax", "exclude", "revenue"}:
        return mapped
    kind = str(group or "").strip().lower()
    label = str(name or "").strip().lower()
    if "commission" in label:
        return "commission"
    if kind == "labor" or (kind == "cogs" and "labor" in label):
        return "payroll"
    if kind == "interest":
        return "interest"
    if kind == "taxes":
        return "tax"
    if kind in {
        "marketing expense",
        "technology expense",
        "g&a expense",
        "sales expense",
        "r&d expense",
        "research and development",
        "rd expense",
    } or (kind == "cogs" and "labor" not in label):
        return "vendor"
    return None


def _suggest_bridge_line(group: str, name: str) -> str | None:
    return _row_bucket("", group, name)


_NONCASH_TOKENS = (
    "bad debt",
    "allowance",
    "depreci",
    "amort",
    "stock-based",
    "stock based",
    "sbc",
    "unrealized",
    "impairment",
    "fair value",
    "non-cash",
    "noncash",
)


def read_bridge_residual(
    db: Session, organization_id: uuid.UUID, period: str
) -> Decimal | None:
    """bridge_check for the close month, or None when no bridge row."""
    month = str(period or "")[:7]
    if len(month) != 7 or month[4] != "-" or not table_exists(db, "actual_cash_flow_bridge"):
        return None
    found = db.execute(
        text(
            """
            select bridge_check
            from actual_cash_flow_bridge
            where organization_id = :org and left(cast(period as text), 7) = :period
            limit 1
            """
        ),
        {"org": str(organization_id), "period": month},
    ).first()
    if found is None or found[0] in (None, ""):
        return None
    try:
        return _dec(found[0])
    except Exception:
        return None


def cash_bridge_mapping_candidates(
    db: Session,
    organization_id: uuid.UUID,
    period: str,
    *,
    residual: Decimal | None = None,
) -> list[dict[str, Any]]:
    """GL accounts to open in Mapping when named cash lines miss ending cash.

    Statement classification can be complete while the cash bridge still fails.
    ERPs hand unbalanced books — Mapping must still surface review items.
    """
    month = str(period or "")[:7]
    if len(month) != 7 or month[4] != "-" or not table_exists(db, "gl_actuals"):
        return []
    if residual is None:
        residual = read_bridge_residual(db, organization_id, month)
    if residual is None or abs(residual) < Decimal("0.005"):
        return []

    maps = load_account_maps(db, organization_id)
    rows = db.execute(
        text(
            f"""
            select coalesce(account_number, '') as account_number,
                   coalesce(account_name, '') as account_name,
                   coalesce(account_group, '') as account_group,
                   coalesce(expense_type, '') as expense_type,
                   coalesce(statement, '') as statement,
                   sum(cast(amount as numeric)) as amount
            from gl_actuals
            where organization_id = :org
              and lower(version) = 'actual'
              and to_char(period, 'YYYY-MM') = :period
              and {ONE_BOOK_SQL}
            group by 1, 2, 3, 4, 5
            having abs(sum(cast(amount as numeric))) > 0.005
            """
        ),
        {"org": str(organization_id), "period": month},
    ).mappings().all()

    out: list[dict[str, Any]] = []
    abs_residual = abs(residual)
    for raw in rows:
        account = str(raw["account_number"] or "").strip()
        if not account:
            continue
        saved = (maps.get(account) or "").strip().lower()
        if saved in {
            "payroll",
            "commission",
            "vendor",
            "interest",
            "tax",
            "other_operating",
            "exclude",
        }:
            continue
        name = str(raw["account_name"] or "")
        group = str(raw["account_group"] or "")
        expense = str(raw["expense_type"] or "")
        statement = str(raw["statement"] or "")
        amount = _dec(raw["amount"])
        blob = f"{name} {group} {expense}".lower()
        heuristic = _row_bucket("", group, name)
        hint: str | None = None
        reason: str | None = None
        if any(token in blob for token in _NONCASH_TOKENS) and heuristic in {
            "vendor",
            "payroll",
            "commission",
        }:
            hint, reason = "exclude", "noncash_in_cash_bucket"
        elif "balance" in statement.lower() and any(
            token in blob
            for token in ("accrued", "lease", "other liab", "other liability")
        ):
            hint, reason = "other_operating", "balance_sheet_cash_adjacent"
        elif heuristic == "vendor" and abs(amount - abs_residual) <= abs_residual * Decimal(
            "2"
        ):
            # Near the residual — owner decides vendor vs other_operating vs exclude.
            hint, reason = "other_operating", "near_cash_bridge_residual"
        elif "other" in blob and "income" in statement.lower():
            hint, reason = "other_operating", "other_pnl"
        if not hint:
            continue
        out.append(
            {
                "account_id": account,
                "account_number": account,
                "name": name or account,
                "amount": float(amount),
                "statement_hint": hint,
                "status": "open",
                "reason": reason,
                "cash_bridge_residual": money(residual),
            }
        )
    out.sort(key=lambda row: abs(float(row.get("amount") or 0)), reverse=True)
    return out[:25]
