"""Management P&L period engine and service helpers."""

from __future__ import annotations

from decimal import Decimal

from app.services.management_pl.period_engine import (
    build_period_context,
    fy_budget,
    fy_outlook,
    variance,
)
from app.services.management_pl.service import (
    DEPARTMENTS,
    _fy_outlook_from_map,
    _gl_warehouse_ready,
    _income_maps_from_gl,
    _merge_gl_preferred,
    _merge_gl_primary,
    _monthly_series,
    _pct_change,
    _safe_div,
)


def test_safe_div_and_pct_change() -> None:
    assert _safe_div(Decimal("10"), Decimal("100")) == Decimal("0.1000")
    assert _safe_div(Decimal("1"), Decimal("0")) is None
    assert _pct_change(Decimal("110"), Decimal("100")) == Decimal("0.1000")


def test_department_list_includes_total_company() -> None:
    assert DEPARTMENTS[0] == "Total Company"
    assert "Sales & Marketing" in DEPARTMENTS


def test_fy_outlook_vs_budget_variance() -> None:
    ctx = build_period_context(fiscal_year=2026, as_of_period="2026-05", period_mode="fy")
    actual = {
        "2026-01": {"revenue": Decimal("100")},
        "2026-05": {"revenue": Decimal("100")},
    }
    forecast = {"2026-12": {"revenue": Decimal("200")}}
    budget = {p: {"revenue": Decimal("150")} for p in ctx.fy_periods}
    outlook_rev = fy_outlook(actual, forecast, ctx, "revenue")
    budget_rev = fy_budget(budget, ctx, "revenue")
    assert outlook_rev == Decimal("400")
    assert budget_rev == Decimal("1800")
    var, pct = variance(outlook_rev, budget_rev)
    assert var == Decimal("-1400")
    assert pct is not None


def test_income_maps_from_gl_rollup() -> None:
    gl = {
        ("2026-01", "revenue", "Subscription Revenue", "SaaS"): Decimal("1000"),
        ("2026-01", "cogs", "Hosting", "AWS"): Decimal("-200"),
        ("2026-01", "sales_and_marketing", "Payroll", "AE Payroll"): Decimal("-300"),
        ("2026-02", "revenue", "Subscription Revenue", "SaaS"): Decimal("1100"),
    }
    maps = _income_maps_from_gl(gl, ("2026-01", "2026-02"))
    assert maps["2026-01"]["revenue"] == Decimal("1000")
    assert maps["2026-01"]["cost_of_revenue"] == Decimal("200")
    assert maps["2026-01"]["sales_and_marketing"] == Decimal("300")
    assert maps["2026-01"]["gross_profit"] == Decimal("800")
    assert maps["2026-01"]["ebitda"] == Decimal("500")


def test_merge_gl_preferred_overrides_income_statement() -> None:
    ctx = build_period_context(fiscal_year=2026, as_of_period="2026-05", period_mode="fy")
    is_maps = {"2026-01": {"revenue": Decimal("1"), "cost_of_revenue": Decimal("1")}}
    gl_maps = {"2026-01": {"revenue": Decimal("1000"), "cost_of_revenue": Decimal("100"), "gross_profit": Decimal("900"), "total_opex": Decimal("0"), "ebitda": Decimal("900")}}
    merged = _merge_gl_preferred(is_maps, gl_maps, ("2026-01",))
    assert merged["2026-01"]["revenue"] == Decimal("1000")
    assert merged["2026-01"]["cost_of_revenue"] == Decimal("100")


def test_merge_gl_primary_replaces_whole_period() -> None:
    ctx = build_period_context(fiscal_year=2026, as_of_period="2026-05", period_mode="fy")
    is_maps = {
        "2026-01": {"revenue": Decimal("1"), "cost_of_revenue": Decimal("1"), "sales_and_marketing": Decimal("999")},
        "2026-02": {"revenue": Decimal("50"), "cost_of_revenue": Decimal("5")},
    }
    gl_maps = {
        "2026-01": {
            "revenue": Decimal("1000"),
            "cost_of_revenue": Decimal("100"),
            "sales_and_marketing": Decimal("300"),
            "research_and_development": Decimal("0"),
            "general_and_administrative": Decimal("0"),
            "customer_success": Decimal("0"),
            "gross_profit": Decimal("900"),
            "total_opex": Decimal("300"),
            "ebitda": Decimal("600"),
        }
    }
    merged = _merge_gl_primary(is_maps, gl_maps, ("2026-01", "2026-02"))
    assert merged["2026-01"]["revenue"] == Decimal("1000")
    assert merged["2026-01"]["sales_and_marketing"] == Decimal("300")
    assert merged["2026-01"]["ebitda"] == Decimal("600")
    assert merged["2026-02"]["revenue"] == Decimal("50")


def test_gl_warehouse_ready() -> None:
    ctx = build_period_context(fiscal_year=2026, as_of_period="2026-05", period_mode="fy")
    outlook_maps = {p: {"revenue": Decimal("100")} for p in ctx.closed_periods}
    budget_maps = {p: {"revenue": Decimal("90")} for p in ctx.fy_periods}
    assert _gl_warehouse_ready(500, outlook_maps, budget_maps, ctx) is True
    assert _gl_warehouse_ready(0, outlook_maps, budget_maps, ctx) is False


def test_fy_outlook_from_merged_map() -> None:
    ctx = build_period_context(fiscal_year=2026, as_of_period="2026-05", period_mode="fy")
    outlook = {
        "2026-01": {"revenue": Decimal("100"), "cost_of_revenue": Decimal("20"), "gross_profit": Decimal("80")},
        "2026-06": {"revenue": Decimal("200"), "cost_of_revenue": Decimal("40"), "gross_profit": Decimal("160")},
    }
    assert _fy_outlook_from_map(outlook, ctx, "revenue") == Decimal("300")
    assert _fy_outlook_from_map(outlook, ctx, "gross_profit") == Decimal("240")


def test_monthly_series_actual_vs_forecast_split() -> None:
    ctx = build_period_context(fiscal_year=2026, as_of_period="2026-05", period_mode="fy")
    outlook = {
        "2026-01": {"revenue": Decimal("100"), "cost_of_revenue": Decimal("20"), "gross_profit": Decimal("80"), "total_opex": Decimal("30"), "ebitda": Decimal("50")},
        "2026-06": {"revenue": Decimal("200"), "cost_of_revenue": Decimal("40"), "gross_profit": Decimal("160"), "total_opex": Decimal("60"), "ebitda": Decimal("100")},
    }
    budget = {
        "2026-01": {"revenue": Decimal("90"), "cost_of_revenue": Decimal("18"), "gross_profit": Decimal("72")},
        "2026-06": {"revenue": Decimal("180"), "cost_of_revenue": Decimal("36"), "gross_profit": Decimal("144")},
    }
    actual = {"2026-01": {"revenue": Decimal("95"), "cost_of_revenue": Decimal("19"), "gross_profit": Decimal("76"), "total_opex": Decimal("28"), "ebitda": Decimal("48")}}
    forecast = {"2026-06": {"revenue": Decimal("200"), "cost_of_revenue": Decimal("40"), "gross_profit": Decimal("160"), "total_opex": Decimal("60"), "ebitda": Decimal("100")}}
    series = _monthly_series(outlook, budget, actual, forecast, ctx)
    jan = next(s for s in series if s.period == "2026-01")
    jun = next(s for s in series if s.period == "2026-06")
    assert jan.is_closed is True
    assert jan.revenue_actual == Decimal("95")
    assert jan.revenue_forecast == Decimal("0")
    assert jan.gross_profit_budget == Decimal("72")
    assert jun.is_closed is False
    assert jun.revenue_actual == Decimal("0")
    assert jun.revenue_forecast == Decimal("200")
    assert jun.revenue_outlook == Decimal("200")
