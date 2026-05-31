"""Management P&L workforce overlay."""

from __future__ import annotations

from decimal import Decimal

from app.services.management_pl.gl_hierarchy import GlEntry
from app.services.workforce import integration


def test_apply_workforce_pnl_replaces_open_month_opex() -> None:
    forecast = {
        "2026-06": {
            "revenue": Decimal("100000"),
            "cost_of_revenue": Decimal("20000"),
            "sales_and_marketing": Decimal("999"),
            "research_and_development": Decimal("0"),
            "general_and_administrative": Decimal("0"),
            "customer_success": Decimal("0"),
            "gross_profit": Decimal("80000"),
            "total_opex": Decimal("999"),
            "ebitda": Decimal("79001"),
        }
    }
    overlay = {"2026-06": {"sales_and_marketing": Decimal("50000")}}
    merged = integration.apply_workforce_pnl_to_income_map(forecast, overlay, {"2026-06"})
    assert merged["2026-06"]["sales_and_marketing"] == Decimal("50000")
    assert merged["2026-06"]["total_opex"] == Decimal("50000")
    assert merged["2026-06"]["ebitda"] == Decimal("30000")


def test_exclude_payroll_gl_keeps_non_payroll_rows() -> None:
    payroll = GlEntry(
        period="2026-06",
        version="Forecast",
        account_number="6100",
        account_name="Sales Payroll",
        account_group="Payroll",
        section_key="sales_and_marketing",
        department="Sales & Marketing",
        source_department="Sales",
        expense_type="Payroll",
        amount=Decimal("-50000"),
    )
    software = GlEntry(
        period="2026-06",
        version="Forecast",
        account_number="6200",
        account_name="Salesforce",
        account_group="Software",
        section_key="sales_and_marketing",
        department="Sales & Marketing",
        source_department="Sales",
        expense_type="Software",
        amount=Decimal("-5000"),
    )
    filtered = integration.exclude_payroll_gl_entries([payroll, software], {"2026-06"})
    assert filtered == [software]
