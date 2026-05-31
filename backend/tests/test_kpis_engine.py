"""Unit tests for the SaaS KPI calculation engine."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.kpis.engine import (
    KpiInputs,
    calculate_arr,
    calculate_burn_multiple,
    calculate_cac,
    calculate_cac_payback_months,
    calculate_gross_mrr_churn_rate,
    calculate_grr,
    calculate_kpis,
    calculate_logo_churn_rate,
    calculate_ltv,
    calculate_ltv_to_cac,
    calculate_magic_number,
    calculate_net_mrr_churn_rate,
    calculate_nrr,
    calculate_operating_margin,
    calculate_pipeline_coverage,
    calculate_revenue_growth_rate,
    calculate_rule_of_40,
    calculate_sales_efficiency,
)


def _d(v: str | int | float) -> Decimal:
    return Decimal(str(v))


PERIOD_START = date(2026, 5, 1)
PERIOD_END = date(2026, 5, 31)


# ---------------------------------------------------------------------------
# ARR / MRR
# ---------------------------------------------------------------------------


def test_arr_is_mrr_times_twelve() -> None:
    assert calculate_arr(_d(10_000)) == _d("120000.00")


def test_arr_zero_mrr() -> None:
    assert calculate_arr(_d(0)) == _d("0.00")


# ---------------------------------------------------------------------------
# NRR / GRR
# ---------------------------------------------------------------------------


def test_nrr_basic() -> None:
    nrr = calculate_nrr(_d(100), expansion_mrr=_d(20), reactivation_mrr=_d(0), contraction_mrr=_d(5), churn_mrr=_d(10))
    # (100 + 20 - 5 - 10) / 100 = 1.05
    assert nrr == _d("1.0500")


def test_nrr_zero_beginning_returns_none() -> None:
    assert calculate_nrr(_d(0), _d(0), _d(0), _d(0), _d(0)) is None


def test_grr_excludes_expansion_and_reactivation() -> None:
    grr = calculate_grr(_d(100), contraction_mrr=_d(5), churn_mrr=_d(10))
    # (100 - 5 - 10) / 100 = 0.85
    assert grr == _d("0.8500")


def test_grr_zero_beginning_returns_none() -> None:
    assert calculate_grr(_d(0), _d(10), _d(10)) is None


def test_grr_never_exceeds_one() -> None:
    grr = calculate_grr(_d(100), _d(0), _d(0))
    assert grr == _d("1.0000")


# ---------------------------------------------------------------------------
# Churn rates
# ---------------------------------------------------------------------------


def test_logo_churn_basic() -> None:
    assert calculate_logo_churn_rate(churned_customers=5, active_customers_beginning=100) == _d("0.0500")


def test_logo_churn_no_active_customers() -> None:
    assert calculate_logo_churn_rate(0, 0) is None


def test_gross_mrr_churn_basic() -> None:
    assert calculate_gross_mrr_churn_rate(churn_mrr=_d(10), beginning_mrr=_d(100)) == _d("0.1000")


def test_gross_mrr_churn_zero_beginning() -> None:
    assert calculate_gross_mrr_churn_rate(_d(10), _d(0)) is None


def test_net_mrr_churn_is_one_minus_nrr() -> None:
    assert calculate_net_mrr_churn_rate(_d("1.05")) == _d("-0.0500")
    assert calculate_net_mrr_churn_rate(_d("0.90")) == _d("0.1000")
    assert calculate_net_mrr_churn_rate(None) is None


# ---------------------------------------------------------------------------
# CAC, CAC payback, LTV
# ---------------------------------------------------------------------------


def test_cac_basic() -> None:
    assert calculate_cac(sales_marketing_expense=_d(50_000), new_customers=10) == _d("5000.00")


def test_cac_no_new_customers_returns_none() -> None:
    assert calculate_cac(_d(50_000), 0) is None


def test_cac_payback_months() -> None:
    cac = _d(5000)
    new_mrr = _d(2000)  # across 10 new customers = $200/cust monthly
    months = calculate_cac_payback_months(cac, new_mrr=new_mrr, new_customers=10, gross_margin=_d("0.8"))
    # 5000 / (200 * 0.8) = 31.25
    assert months == _d("31.2500")


def test_cac_payback_zero_gross_margin() -> None:
    assert calculate_cac_payback_months(_d(5000), _d(2000), 10, _d(0)) is None


def test_cac_payback_no_new_customers() -> None:
    assert calculate_cac_payback_months(_d(5000), _d(2000), 0, _d("0.8")) is None


def test_ltv_basic() -> None:
    arpa = _d(100)  # monthly per-account revenue
    gross_margin = _d("0.8")
    churn = _d("0.02")
    # 100 * 0.8 / 0.02 = 4000
    assert calculate_ltv(arpa, gross_margin, churn) == _d("4000.00")


def test_ltv_zero_churn_returns_none() -> None:
    assert calculate_ltv(_d(100), _d("0.8"), _d(0)) is None


def test_ltv_missing_inputs() -> None:
    assert calculate_ltv(None, _d("0.8"), _d("0.02")) is None
    assert calculate_ltv(_d(100), _d("0.8"), None) is None


def test_ltv_to_cac() -> None:
    assert calculate_ltv_to_cac(_d(4000), _d(1000)) == _d("4.0000")


def test_ltv_to_cac_missing() -> None:
    assert calculate_ltv_to_cac(None, _d(1000)) is None
    assert calculate_ltv_to_cac(_d(4000), None) is None
    assert calculate_ltv_to_cac(_d(4000), _d(0)) is None


# ---------------------------------------------------------------------------
# Growth, Rule of 40, Magic Number
# ---------------------------------------------------------------------------


def test_revenue_growth_basic() -> None:
    assert calculate_revenue_growth_rate(_d(120), _d(100)) == _d("0.2000")


def test_revenue_growth_no_prior() -> None:
    assert calculate_revenue_growth_rate(_d(120), None) is None
    assert calculate_revenue_growth_rate(_d(120), _d(0)) is None


def test_operating_margin_basic() -> None:
    assert calculate_operating_margin(_d(100), _d(60)) == _d("0.4000")


def test_operating_margin_missing_opex() -> None:
    assert calculate_operating_margin(_d(100), None) is None


def test_rule_of_40_basic() -> None:
    # 30% growth + 15% margin = 0.45
    assert calculate_rule_of_40(_d("0.30"), _d("0.15")) == _d("0.4500")


def test_rule_of_40_negative_margin_still_sums() -> None:
    # 60% growth + (-20%) margin = 0.40 (passes Rule of 40)
    assert calculate_rule_of_40(_d("0.60"), _d("-0.20")) == _d("0.4000")


def test_rule_of_40_missing_input() -> None:
    assert calculate_rule_of_40(None, _d("0.20")) is None
    assert calculate_rule_of_40(_d("0.30"), None) is None


def test_magic_number_basic() -> None:
    # (120 - 100) * 4 / 50 = 1.6
    assert calculate_magic_number(_d(120), _d(100), _d(50)) == _d("1.6000")


def test_magic_number_missing_prior_sm() -> None:
    assert calculate_magic_number(_d(120), _d(100), None) is None
    assert calculate_magic_number(_d(120), _d(100), _d(0)) is None


# ---------------------------------------------------------------------------
# Sales efficiency, pipeline coverage, burn multiple
# ---------------------------------------------------------------------------


def test_sales_efficiency_basic() -> None:
    # $100k new ARR / $50k S&M = 2.0
    assert calculate_sales_efficiency(_d(100_000), _d(50_000)) == _d("2.0000")


def test_sales_efficiency_zero_sm() -> None:
    assert calculate_sales_efficiency(_d(100_000), _d(0)) is None


def test_pipeline_coverage_basic() -> None:
    # 3x coverage
    assert calculate_pipeline_coverage(_d(300_000), _d(100_000)) == _d("3.0000")


def test_pipeline_coverage_no_target() -> None:
    assert calculate_pipeline_coverage(_d(300_000), None) is None
    assert calculate_pipeline_coverage(_d(300_000), _d(0)) is None


def test_burn_multiple_basic() -> None:
    # net_burn = 100, new_bookings = 200, no expansion/contraction/churn
    # net_new_arr = 200 + (0-0-0)*12 = 200; burn_multiple = 0.5
    assert calculate_burn_multiple(_d(100), _d(200), _d(0), _d(0), _d(0)) == _d("0.5000")


def test_burn_multiple_with_mrr_movements() -> None:
    # net_new_arr = 100k + (5k - 2k - 1k)*12 = 100k + 24k = 124k
    # burn_multiple = 100k / 124k = ~0.806
    assert calculate_burn_multiple(_d(100_000), _d(100_000), _d(5_000), _d(2_000), _d(1_000)) == _d("0.8065")


def test_burn_multiple_zero_growth_returns_none() -> None:
    assert calculate_burn_multiple(_d(100), _d(0), _d(0), _d(0), _d(0)) is None


def test_burn_multiple_missing_burn() -> None:
    assert calculate_burn_multiple(None, _d(100), _d(0), _d(0), _d(0)) is None


# ---------------------------------------------------------------------------
# Top-level calculate_kpis()
# ---------------------------------------------------------------------------


def _full_inputs() -> KpiInputs:
    return KpiInputs(
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        beginning_mrr=_d(100_000),
        ending_mrr=_d(110_000),
        new_mrr=_d(15_000),
        expansion_mrr=_d(5_000),
        contraction_mrr=_d(2_000),
        churn_mrr=_d(8_000),
        reactivation_mrr=_d(0),
        active_customers_beginning=200,
        active_customers_ending=210,
        new_customers=20,
        churned_customers=10,
        new_bookings_arr=_d(180_000),
        total_pipeline=_d(600_000),
        target_bookings=_d(200_000),
        revenue=_d(110_000),
        prior_period_revenue=_d(100_000),
        sales_marketing_expense=_d(60_000),
        prior_period_sales_marketing_expense=_d(55_000),
        operating_expense=_d(95_000),
        gross_margin=_d("0.8"),
        net_burn=_d(30_000),
        period_months=1,
    )


def test_calculate_kpis_full_snapshot() -> None:
    r = calculate_kpis(_full_inputs())

    # Recurring
    assert r.arr == _d("1320000.00")  # 110000 * 12
    assert r.mrr == _d("110000.00")
    assert r.beginning_arr == _d("1200000.00")

    # Retention
    assert r.nrr == _d("0.9500")  # (100k + 5k + 0 - 2k - 8k) / 100k
    assert r.grr == _d("0.9000")  # (100k - 2k - 8k) / 100k
    assert r.logo_churn_rate == _d("0.0500")  # 10 / 200
    assert r.gross_mrr_churn_rate == _d("0.0800")  # 8k / 100k
    assert r.net_mrr_churn_rate == _d("0.0500")  # 1 - 0.95

    # Unit economics
    # avg_customers = 205; arpa = revenue / months / avg = 110000 / 1 / 205 = 536.5854
    assert r.arpa == _d("536.59")
    # CAC = 60000 / 20 = 3000
    assert r.cac == _d("3000.00")
    # CAC payback = 3000 / ((15000/20)*0.8) = 3000 / 600 = 5
    assert r.cac_payback_months == _d("5.0000")
    # LTV = 536.59 * 0.8 / 0.08 = 5365.90
    assert r.ltv == _d("5365.90")
    # LTV/CAC = 5365.90 / 3000 = 1.78863..
    assert r.ltv_to_cac == _d("1.7886")

    # Growth / efficiency
    assert r.revenue_growth_rate == _d("0.1000")  # 10/100
    assert r.operating_margin == _d("0.1364")  # (110-95)/110 ≈ 0.1364
    # rule_of_40 = 0.10 + 0.1364 = 0.2364
    assert r.rule_of_40 == _d("0.2364")
    # magic = (110 - 100) * 4 / 55 = 40/55 = 0.7273
    assert r.magic_number == _d("0.7273")
    # sales_efficiency = 180000 / 60000 = 3
    assert r.sales_efficiency == _d("3.0000")
    # pipeline_coverage = 600000 / 200000 = 3
    assert r.pipeline_coverage == _d("3.0000")
    # net_new_arr = 180000 + (5000 - 2000 - 8000)*12 = 180000 - 60000 = 120000
    # burn_multiple = 30000 / 120000 = 0.25
    assert r.burn_multiple == _d("0.2500")


def test_calculate_kpis_empty_inputs() -> None:
    """All denominators are zero — every ratio should be None, money fields zero."""
    r = calculate_kpis(KpiInputs(period_start=PERIOD_START, period_end=PERIOD_END))
    assert r.arr == _d("0.00")
    assert r.mrr == _d("0.00")
    assert r.nrr is None
    assert r.grr is None
    assert r.logo_churn_rate is None
    assert r.gross_mrr_churn_rate is None
    assert r.net_mrr_churn_rate is None
    assert r.arpa is None
    assert r.cac is None
    assert r.cac_payback_months is None
    assert r.ltv is None
    assert r.ltv_to_cac is None
    assert r.revenue_growth_rate is None
    assert r.operating_margin is None
    assert r.rule_of_40 is None
    assert r.magic_number is None
    assert r.sales_efficiency is None
    assert r.pipeline_coverage is None
    assert r.burn_multiple is None


def test_calculate_kpis_uses_provided_beginning_arr() -> None:
    r = calculate_kpis(
        KpiInputs(
            period_start=PERIOD_START,
            period_end=PERIOD_END,
            beginning_mrr=_d(100_000),
            ending_mrr=_d(110_000),
            beginning_arr=_d(1_250_000),  # override
            ending_arr=_d(1_350_000),
        )
    )
    assert r.beginning_arr == _d("1250000.00")
    assert r.ending_arr == _d("1350000.00")


def test_calculate_kpis_net_growth_yields_negative_net_churn() -> None:
    r = calculate_kpis(
        KpiInputs(
            period_start=PERIOD_START,
            period_end=PERIOD_END,
            beginning_mrr=_d(100_000),
            ending_mrr=_d(120_000),
            expansion_mrr=_d(25_000),
            contraction_mrr=_d(0),
            churn_mrr=_d(5_000),
        )
    )
    # NRR = (100k + 25k - 5k) / 100k = 1.20
    assert r.nrr == _d("1.2000")
    # net churn = 1 - 1.20 = -0.20 (i.e. 20% net expansion)
    assert r.net_mrr_churn_rate == _d("-0.2000")
