"""Cash flow GL drilldown service tests."""

from __future__ import annotations

from decimal import Decimal

from app.services.dashboard.cash_flow_gl_drilldown_service import (
    CASH_BALANCE_TYPES,
    CASH_DRILLDOWN_TYPES,
    gl_entry_matches,
)
from app.services.management_pl.gl_hierarchy import GlEntry


def _entry(**kwargs) -> GlEntry:
    defaults = {
        "period": "2026-06",
        "version": "Forecast",
        "account_number": "6000",
        "account_name": "Engineering Payroll",
        "account_group": "Engineering Payroll",
        "section_key": "research_and_development",
        "department": "R&D",
        "source_department": "Engineering",
        "expense_type": "Payroll",
        "amount": Decimal("-10000"),
    }
    defaults.update(kwargs)
    return GlEntry(**defaults)


def test_cash_drilldown_type_sets() -> None:
    assert "payroll_cash_out" in CASH_DRILLDOWN_TYPES
    assert "beginning_cash" in CASH_BALANCE_TYPES
    assert "beginning_cash" not in CASH_DRILLDOWN_TYPES


def test_gl_entry_matches_payroll_not_commission() -> None:
    payroll = _entry(account_group="Engineering Payroll", account_name="Engineering Payroll")
    commission = _entry(account_group="Commissions", account_name="Sales Commissions")
    raw = {}
    assert gl_entry_matches("payroll_cash_out", payroll, raw)
    assert not gl_entry_matches("payroll_cash_out", commission, raw)
    assert gl_entry_matches("commission_cash_out", commission, raw)


def test_gl_entry_matches_vendor_with_vendor_name() -> None:
    entry = _entry(account_group="Software", account_name="SaaS Tools", amount=Decimal("-500"))
    raw = {"vendor_name": "Acme SaaS Co"}
    assert gl_entry_matches("vendor_cash_out", entry, raw)


def test_gl_entry_matches_revenue_collections() -> None:
    entry = _entry(
        account_number="4000",
        account_name="Subscription Revenue",
        account_group="Subscription Revenue",
        department="Revenue",
        amount=Decimal("25000"),
    )
    assert gl_entry_matches("cash_collections", entry, {})
