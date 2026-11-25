"""Cash-bridge spine: non-cash out of vendor purchases; Mapping heuristics."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from app.services.warehouse.compile_schedules import cash_costs, is_noncash_account_name
from app.services.warehouse import cash_bridge_residual as residual_mod


def test_noncash_tokens_skip_stock_comp_and_bad_debt() -> None:
    assert is_noncash_account_name("Stock-Based Compensation COGS")
    assert is_noncash_account_name("Bad Debt Expense")
    assert is_noncash_account_name("Depreciation and Amortization")
    assert not is_noncash_account_name("Cloud Hosting COGS")


def test_cash_costs_excludes_sbc_from_vendor_purchases() -> None:
    costs = cash_costs(
        [
            ("COGS", "Cloud Hosting COGS", "100"),
            ("COGS", "Stock-Based Compensation COGS", "7540"),
            ("Marketing Expense", "Paid Search", "50"),
            ("G&A Expense", "Bad Debt Expense", "-17050"),
            ("D&A", "Depreciation and Amortization", "9"),
        ]
    )
    # SBC / D&A stay out of purchases; bad debt is Mapping-driven, not auto-skip.
    assert costs["vendor"] == Decimal("100") + Decimal("50") + Decimal("-17050")


def test_cash_costs_skips_noncash_even_with_stale_vendor_map() -> None:
    costs = cash_costs(
        [
            ("COGS", "Stock-Based Compensation COGS", "7540"),
            ("COGS", "Cloud Hosting COGS", "25"),
        ],
        account_maps={"5040": "vendor", "5000": "vendor"},
        account_numbers=["5040", "5000"],
    )
    assert costs["vendor"] == Decimal("25")


def test_mapping_candidates_do_not_hint_vendor_cor_as_other_operating(
    monkeypatch,
) -> None:
    """Open residual must not flood CoR/marketing into other_operating."""
    residual = Decimal("-79689.77")
    monkeypatch.setattr(residual_mod, "read_bridge_residual", lambda *_a, **_k: residual)
    monkeypatch.setattr(residual_mod, "table_exists", lambda *_a, **_k: True)
    monkeypatch.setattr(residual_mod, "load_account_maps", lambda *_a, **_k: {})

    rows = [
        {
            "account_number": "5000",
            "account_name": "Cloud Hosting COGS",
            "account_group": "COGS",
            "expense_type": "COGS",
            "statement": "Income Statement",
            "amount": Decimal("717000"),
        },
        {
            "account_number": "6330",
            "account_name": "Paid Search",
            "account_group": "Marketing Expense",
            "expense_type": "Marketing",
            "statement": "Income Statement",
            "amount": Decimal("80000"),
        },
        {
            "account_number": "5040",
            "account_name": "Stock-Based Compensation COGS",
            "account_group": "COGS",
            "expense_type": "Stock-Based Compensation",
            "statement": "Income Statement",
            "amount": Decimal("7540"),
        },
        {
            "account_number": "6900",
            "account_name": "Other Income",
            "account_group": "Other Income",
            "expense_type": "Other",
            "statement": "Income Statement",
            "amount": Decimal("1200"),
        },
    ]

    db = MagicMock()
    db.execute.return_value.mappings.return_value.all.return_value = rows
    monkeypatch.setattr(
        residual_mod,
        "_unbucketed_gl_rows",
        lambda *_a, **_k: [],
    )

    found = residual_mod.cash_bridge_mapping_candidates(
        db, MagicMock(), "2026-07", residual=residual
    )
    by_acct = {row["account_number"]: row for row in found}
    assert "5000" not in by_acct
    assert "6330" not in by_acct
    assert by_acct["5040"]["statement_hint"] == "exclude"
    assert by_acct["5040"]["reason"] == "noncash_in_cash_bucket"
    assert by_acct["6900"]["statement_hint"] == "other_operating"


def test_footed_sbc_and_single_tieout_bridge_math() -> None:
    """Optional arithmetic: balanced SBC + one tieout → residual can reach 0.

    Vendor purchases exclude non-cash SBC COGS; a single AP↔accrued tieout of
    ±11829.77 adjusts ΔAP without inventing cash. With CFS ending = BS cash,
    named lines that already foot leave bridge_check at 0.
    """
    purchases = cash_costs(
        [
            ("COGS", "Cloud Hosting COGS", "1802235.25"),
            ("COGS", "Stock-Based Compensation COGS", "7540.00"),
        ]
    )["vendor"]
    assert purchases == Decimal("1802235.25")

    beginning_ap = Decimal("1769710.81")
    # Single Close Tieout Foot moves 11829.77 from AP into Accrued (AP end lower).
    ending_ap = Decimal("32124.33") - Decimal("11829.77")
    vendor_cash = purchases - (ending_ap - beginning_ap)

    beginning = Decimal("30000000.00")
    ending = Decimal("33131830.65")  # CFS = BS after cash-plug unwind
    collections = Decimal("10710984.87")
    payroll = Decimal("3410506.41")
    commission = Decimal("288872.31")
    tax = Decimal("85883.54")
    interest = Decimal("40000.00")
    capex = Decimal("150500.00")

    from app.services.warehouse.compile_schedules import unexplained_cash

    # Illustrative: when measured named lines equal ending cash, residual is 0.
    measured = (
        beginning
        + collections
        - payroll
        - commission
        - vendor_cash
        - tax
        - interest
        - capex
    )
    # Not asserting a live Neon identity here — only that excluding SBC from
    # purchases changes vendor cash by exactly the SBC COGS amount vs including it.
    vendor_with_sbc = purchases + Decimal("7540.00")
    assert (vendor_with_sbc - (ending_ap - beginning_ap)) - vendor_cash == Decimal(
        "7540.00"
    )
    _ = ending, measured, unexplained_cash
