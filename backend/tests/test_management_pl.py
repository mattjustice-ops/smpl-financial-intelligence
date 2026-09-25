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
    assert maps["2026-01"]["subscription_revenue"] == Decimal("1000")
    assert maps["2026-01"]["cost_of_revenue"] == Decimal("200")
    assert maps["2026-01"]["sales_and_marketing"] == Decimal("300")
    assert maps["2026-01"]["gross_profit"] == Decimal("800")
    assert maps["2026-01"]["ebitda"] == Decimal("500")


def test_income_maps_from_gl_splits_subscription_and_services() -> None:
    gl = {
        ("2026-06", "revenue", "Subscription Revenue", "4000 Subscription Revenue"): Decimal("7000000"),
        ("2026-06", "revenue", "Services Revenue", "4100 Professional Services"): Decimal("350000"),
    }
    maps = _income_maps_from_gl(gl, ("2026-06",))
    assert maps["2026-06"]["revenue"] == Decimal("7350000")
    assert maps["2026-06"]["subscription_revenue"] == Decimal("7000000")
    assert maps["2026-06"]["services_revenue"] == Decimal("350000")


def test_merge_gl_primary_preserves_is_revenue_split() -> None:
    is_maps = {
        "2026-06": {
            "revenue": Decimal("7350000"),
            "subscription_revenue": Decimal("7000000"),
            "services_revenue": Decimal("350000"),
            "cost_of_revenue": Decimal("100"),
            "sales_and_marketing": Decimal("50"),
            "research_and_development": Decimal("40"),
            "general_and_administrative": Decimal("30"),
            "gross_profit": Decimal("7250000"),
            "total_opex": Decimal("120"),
            "ebitda": Decimal("7129880"),
        }
    }
    gl_maps = {
        "2026-06": {
            "revenue": Decimal("9999999"),
            "cost_of_revenue": Decimal("2200000"),
            "sales_and_marketing": Decimal("100"),
            "research_and_development": Decimal("0"),
            "general_and_administrative": Decimal("0"),
            "customer_success": Decimal("0"),
            "gross_profit": Decimal("5150000"),
            "total_opex": Decimal("100"),
            "ebitda": Decimal("5050000"),
        }
    }
    merged = _merge_gl_primary(is_maps, gl_maps, ("2026-06",))
    assert merged["2026-06"]["subscription_revenue"] == Decimal("7000000")
    assert merged["2026-06"]["services_revenue"] == Decimal("350000")
    assert merged["2026-06"]["revenue"] == Decimal("7350000")
    assert merged["2026-06"]["cost_of_revenue"] == Decimal("100")
    assert merged["2026-06"]["sales_and_marketing"] == Decimal("50")
    assert merged["2026-06"]["ebitda"] == Decimal("7129880")


def test_spec_pl_lines_prefer_is_subscription_services() -> None:
    from app.services.management_pl.period_engine import build_period_context
    from app.services.management_pl.pl_builder import build_spec_pl_lines

    ctx = build_period_context(fiscal_year=2026, as_of_period="2026-06", period_mode="cm")
    outlook = {
        "2026-06": {
            "revenue": Decimal("7350000"),
            "subscription_revenue": Decimal("7000000"),
            "services_revenue": Decimal("350000"),
        }
    }
    budget = {
        "2026-06": {
            "revenue": Decimal("7720000"),
            "subscription_revenue": Decimal("7400000"),
            "services_revenue": Decimal("320000"),
        }
    }
    # GL wrongly names only total as subscription — must NOT override IS.
    gl_act = {("2026-06", "Revenue", "Subscription Revenue"): Decimal("7350000")}
    gl_bud = {("2026-06", "Revenue", "Subscription Revenue"): Decimal("7720000")}
    lines = build_spec_pl_lines(
        ctx=ctx,
        gl_act=gl_act,
        gl_bud=gl_bud,
        gl_fcst={},
        outlook=outlook,
        budget=budget,
        actual_is=outlook,
        budget_is=budget,
        forecast_is={},
    )
    by_id = {ln.id: ln for ln in lines}
    assert by_id["subscription_revenue"].metrics.actual == Decimal("7000000")
    assert by_id["services_revenue"].metrics.actual == Decimal("350000")
    assert by_id["total_revenue"].metrics.actual == Decimal("7350000")
    assert (
        by_id["subscription_revenue"].metrics.actual + by_id["services_revenue"].metrics.actual
        == by_id["total_revenue"].metrics.actual
    )
    assert by_id["subscription_revenue"].metrics.budget == Decimal("7400000")
    assert by_id["services_revenue"].metrics.budget == Decimal("320000")
    assert (
        by_id["subscription_revenue"].metrics.budget + by_id["services_revenue"].metrics.budget
        == by_id["total_revenue"].metrics.budget
    )


def test_spec_pl_lines_revenue_split_completes_missing_half_and_ties() -> None:
    """When IS has total + services only, subscription = revenue − services (not GL)."""
    from app.services.management_pl.period_engine import build_period_context
    from app.services.management_pl.pl_builder import build_spec_pl_lines

    ctx = build_period_context(fiscal_year=2026, as_of_period="2026-06", period_mode="cm")
    actual_is = {
        "2026-06": {
            "revenue": Decimal("7350000"),
            "services_revenue": Decimal("350000"),
            # subscription missing — must be derived, not taken from GL
        }
    }
    budget_is = {
        "2026-06": {
            "revenue": Decimal("7720000"),
            "subscription_revenue": Decimal("7400000"),
            # services missing
        }
    }
    gl_act = {
        ("2026-06", "Revenue", "Subscription Revenue"): Decimal("9999999"),
        ("2026-06", "Revenue", "Services Revenue"): Decimal("1"),
    }
    gl_bud = {
        ("2026-06", "Revenue", "Subscription Revenue"): Decimal("1"),
        ("2026-06", "Revenue", "Services Revenue"): Decimal("9999999"),
    }
    lines = build_spec_pl_lines(
        ctx=ctx,
        gl_act=gl_act,
        gl_bud=gl_bud,
        gl_fcst={},
        outlook=actual_is,
        budget=budget_is,
        actual_is=actual_is,
        budget_is=budget_is,
        forecast_is={},
    )
    by_id = {ln.id: ln for ln in lines}
    assert by_id["subscription_revenue"].metrics.actual == Decimal("7000000")
    assert by_id["services_revenue"].metrics.actual == Decimal("350000")
    assert by_id["total_revenue"].metrics.actual == Decimal("7350000")
    assert by_id["subscription_revenue"].metrics.budget == Decimal("7400000")
    assert by_id["services_revenue"].metrics.budget == Decimal("320000")
    assert by_id["total_revenue"].metrics.budget == Decimal("7720000")


def test_spec_pl_lines_actual_budget_match_income_statement_rollups() -> None:
    """When GL rollups disagree with IS, Mgmt P&L Actual and Budget follow IS."""
    from app.services.management_pl.period_engine import build_period_context
    from app.services.management_pl.pl_builder import build_spec_pl_lines

    ctx = build_period_context(fiscal_year=2026, as_of_period="2026-06", period_mode="cm")
    is_actual = {
        "2026-06": {
            "revenue": Decimal("7350000"),
            "subscription_revenue": Decimal("7000000"),
            "services_revenue": Decimal("350000"),
            "cost_of_revenue": Decimal("2100000"),
            "sales_and_marketing": Decimal("2500000"),
            "research_and_development": Decimal("1200000"),
            "general_and_administrative": Decimal("800000"),
            "gross_profit": Decimal("5250000"),
            "total_opex": Decimal("4500000"),
            "ebitda": Decimal("750000"),
            "depreciation_and_amortization": Decimal("100000"),
            "interest_expense": Decimal("20000"),
            "tax_expense": Decimal("5000"),
        }
    }
    is_budget = {
        "2026-06": {
            "revenue": Decimal("7720000"),
            "subscription_revenue": Decimal("7400000"),
            "services_revenue": Decimal("320000"),
            "cost_of_revenue": Decimal("2200000"),
            "sales_and_marketing": Decimal("2600000"),
            "research_and_development": Decimal("1250000"),
            "general_and_administrative": Decimal("850000"),
            "gross_profit": Decimal("5520000"),
            "total_opex": Decimal("4700000"),
            "ebitda": Decimal("820000"),
            "depreciation_and_amortization": Decimal("110000"),
            "interest_expense": Decimal("22000"),
            "tax_expense": Decimal("6000"),
        }
    }
    # Divergent GL totals — must not win over IS for rollup lines.
    gl_act = {
        ("2026-06", "Revenue", "Subscription Revenue"): Decimal("9000000"),
        ("2026-06", "COGS", "Hosting"): Decimal("3000000"),
        ("2026-06", "Sales", "Payroll"): Decimal("4000000"),
        ("2026-06", "Engineering", "Payroll"): Decimal("2000000"),
        ("2026-06", "G&A", "Payroll"): Decimal("1500000"),
    }
    gl_bud = {
        ("2026-06", "Revenue", "Subscription Revenue"): Decimal("9100000"),
        ("2026-06", "COGS", "Hosting"): Decimal("3100000"),
        ("2026-06", "Sales", "Payroll"): Decimal("4100000"),
        ("2026-06", "Engineering", "Payroll"): Decimal("2100000"),
        ("2026-06", "G&A", "Payroll"): Decimal("1600000"),
    }
    lines = build_spec_pl_lines(
        ctx=ctx,
        gl_act=gl_act,
        gl_bud=gl_bud,
        gl_fcst={},
        outlook=is_actual,
        budget=is_budget,
        actual_is=is_actual,
        forecast_is={},
    )
    by_id = {ln.id: ln for ln in lines}
    assert by_id["total_revenue"].metrics.actual == Decimal("7350000")
    assert by_id["total_revenue"].metrics.budget == Decimal("7720000")
    assert by_id["total_cogs"].metrics.actual == Decimal("2100000")
    assert by_id["total_cogs"].metrics.budget == Decimal("2200000")
    assert by_id["total_sm"].metrics.actual == Decimal("2500000")
    assert by_id["total_sm"].metrics.budget == Decimal("2600000")
    assert by_id["total_rd"].metrics.actual == Decimal("1200000")
    assert by_id["total_rd"].metrics.budget == Decimal("1250000")
    assert by_id["total_ga_section"].metrics.actual == Decimal("800000")
    assert by_id["total_ga_section"].metrics.budget == Decimal("850000")
    assert by_id["gross_profit"].metrics.actual == Decimal("5250000")
    assert by_id["gross_profit"].metrics.budget == Decimal("5520000")
    assert by_id["total_opex"].metrics.actual == Decimal("4500000")
    assert by_id["total_opex"].metrics.budget == Decimal("4700000")
    assert by_id["ebitda"].metrics.actual == Decimal("750000")
    assert by_id["ebitda"].metrics.budget == Decimal("820000")
    assert by_id["operating_income"].metrics.actual == Decimal("650000")
    assert by_id["operating_income"].metrics.budget == Decimal("710000")
    assert by_id["net_income"].metrics.actual == Decimal("625000")
    assert by_id["net_income"].metrics.budget == Decimal("682000")


def test_merge_gl_preferred_keeps_income_statement_rollups() -> None:
    is_maps = {"2026-01": {"revenue": Decimal("1"), "cost_of_revenue": Decimal("1"), "sales_and_marketing": Decimal("2")}}
    gl_maps = {
        "2026-01": {
            "revenue": Decimal("1000"),
            "cost_of_revenue": Decimal("100"),
            "sales_and_marketing": Decimal("300"),
            "gross_profit": Decimal("900"),
            "total_opex": Decimal("300"),
            "ebitda": Decimal("600"),
        }
    }
    merged = _merge_gl_preferred(is_maps, gl_maps, ("2026-01",))
    assert merged["2026-01"]["revenue"] == Decimal("1")
    assert merged["2026-01"]["cost_of_revenue"] == Decimal("1")
    assert merged["2026-01"]["sales_and_marketing"] == Decimal("2")


def test_merge_gl_primary_prefers_is_rollups_over_gl() -> None:
    is_maps = {
        "2026-01": {
            "revenue": Decimal("1"),
            "cost_of_revenue": Decimal("1"),
            "sales_and_marketing": Decimal("999"),
            "research_and_development": Decimal("0"),
            "general_and_administrative": Decimal("0"),
            "gross_profit": Decimal("0"),
            "total_opex": Decimal("999"),
            "ebitda": Decimal("-999"),
        },
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
    assert merged["2026-01"]["revenue"] == Decimal("1")
    assert merged["2026-01"]["sales_and_marketing"] == Decimal("999")
    assert merged["2026-01"]["ebitda"] == Decimal("-999")
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
