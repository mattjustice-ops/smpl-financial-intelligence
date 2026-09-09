"""A tie-out check must sum every component of the total it validates.

Both bugs these tests guard against produced the same failure mode: a check
omitted a line the source total included, so correct data was reported as
broken. Thirty of thirty-seven reported failures on the demo org were this,
which is worse than no validation because it trains everyone to ignore the
banner and hides the real breaks among the noise.
"""

from __future__ import annotations

from decimal import Decimal

from app.services.dashboard.waterfall_attribution_service import (
    cash_flow_attribution_view,
)
from app.services.financial_statements.financial_statement_mapper import (
    BALANCE_SHEET_LINES,
)
from app.services.financial_statements.financial_statement_service import (
    ensure_balance_formulas,
)

# Every bridge column that moves cash, and so must reach the tie-out.
BRIDGE_FLOW_COLUMNS = (
    "cash_collections_from_invoices",
    "payroll_cash_out",
    "commission_cash_out",
    "vendor_cash_out_n30",
    "tax_cash_out",
    "interest_cash_out",
    "other_operating_cash_out",
    "capex",
    "financing_to_maintain_cash_floor",
)


def _bridge_row() -> dict[str, str]:
    """A bridge month that foots exactly, with every outflow line populated."""
    return {
        "period": "2026-06",
        "beginning_cash": "29497900.00",
        "cash_collections_from_invoices": "7128500.00",
        "payroll_cash_out": "2474700.00",
        "commission_cash_out": "199900.00",
        "vendor_cash_out_n30": "3662500.00",
        "tax_cash_out": "102200.00",
        "interest_cash_out": "40000.00",
        "other_operating_cash_out": "250000.00",
        "capex": "147000.00",
        "financing_to_maintain_cash_floor": "0.00",
        # 29,497,900 + 7,128,500 - 6,729,300 - 147,000 = 29,750,100
        "ending_cash": "29750100.00",
    }


def test_every_bridge_flow_column_reaches_the_waterfall(monkeypatch) -> None:
    """No cash-moving column may be silently dropped on the way to the tie-out.

    interest_cash_out and other_operating_cash_out were never mapped, so the
    tie-out summed eight of ten flows while ending_cash reflected all ten.
    """
    row = _bridge_row()

    monkeypatch.setattr(
        "app.services.dashboard.waterfall_attribution_service.fetch_scenario_rows",
        lambda *a, **k: [("Actual", "2026-06", "actual_cash_flow_bridge", row)],
    )

    rows = cash_flow_attribution_view(None, "00000000-0000-0000-0000-000000000001")
    amounts = {r.waterfall_type: Decimal(str(r.amount)) for r in rows}

    beginning = amounts.pop("beginning_cash")
    ending = amounts.pop("ending_cash")

    assert beginning + sum(amounts.values()) == ending, (
        "bridge flows must foot to ending_cash; a missing mapping reports a "
        f"break on data that ties. got flows={sorted(amounts)}"
    )

    total_populated = sum(
        Decimal(row[c]) for c in BRIDGE_FLOW_COLUMNS if Decimal(row[c]) != 0
    )
    total_mapped = sum(abs(v) for v in amounts.values())
    assert total_mapped == total_populated, (
        "every populated flow column must appear in the waterfall"
    )


def test_balance_check_is_zero_when_the_sheet_balances() -> None:
    """Recomputed totals must include every balance the source carries.

    other_liabilities was omitted from total_liabilities, so a sheet that
    balanced reported a balance_check equal to that omitted amount.
    """
    row = {
        "cash": "30000000.00",
        "accounts_receivable": "9000000.00",
        "prepaids_and_other_current": "2000000.00",
        "ppe_net": "4600000.00",
        "other_assets": "1400000.00",
        "accounts_payable": "6000000.00",
        "deferred_revenue": "1200000.00",
        "debt": "5000000.00",
        "other_liabilities": "2500000.00",
        "equity": "32300000.00",
    }
    out = ensure_balance_formulas(row)

    assert Decimal(str(out["total_assets"])) == Decimal("47000000.00")
    assert Decimal(str(out["total_liabilities"])) == Decimal("14700000.00")
    assert Decimal(str(out["balance_check"])) == Decimal("0"), (
        "a balanced sheet must report balance_check of zero"
    )


def test_other_balances_are_visible_line_items() -> None:
    """A balance folded into a total must also be shown on its own line.

    other_liabilities carried $2.5M that appeared in no line item, so the
    statement could not be reconciled by reading it.
    """
    columns = {m.source_column for m in BALANCE_SHEET_LINES}
    assert "other_assets" in columns
    assert "other_liabilities" in columns
