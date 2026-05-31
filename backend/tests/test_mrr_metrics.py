"""Unit tests for ARR bridge + NRR/GRR/churn/expansion metrics."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.mrr.engine import CompanyMrrSummary
from app.services.mrr.metrics import arr_bridge, compute_period_metrics

PERIOD = date(2026, 2, 1)


def _summary(**kwargs) -> CompanyMrrSummary:
    base = dict(
        period=PERIOD,
        beginning_mrr=Decimal("0"),
        new_mrr=Decimal("0"),
        expansion_mrr=Decimal("0"),
        contraction_mrr=Decimal("0"),
        churn_mrr=Decimal("0"),
        reactivation_mrr=Decimal("0"),
        ending_mrr=Decimal("0"),
        active_customers_beginning=0,
        active_customers_ending=0,
        new_customers=0,
        churned_customers=0,
        reactivated_customers=0,
    )
    base.update(kwargs)
    return CompanyMrrSummary(**base)


def test_arr_bridge_multiplies_each_bucket_by_twelve() -> None:
    s = _summary(
        beginning_mrr=Decimal("1000"),
        new_mrr=Decimal("100"),
        expansion_mrr=Decimal("50"),
        contraction_mrr=Decimal("10"),
        churn_mrr=Decimal("5"),
        reactivation_mrr=Decimal("20"),
        ending_mrr=Decimal("1155"),
    )
    bridge = arr_bridge(s)
    assert bridge.beginning_arr == Decimal("12000.00")
    assert bridge.new_arr == Decimal("1200.00")
    assert bridge.expansion_arr == Decimal("600.00")
    assert bridge.contraction_arr == Decimal("120.00")
    assert bridge.churn_arr == Decimal("60.00")
    assert bridge.reactivation_arr == Decimal("240.00")
    assert bridge.ending_arr == Decimal("13860.00")


def test_nrr_grr_clean_growth() -> None:
    s = _summary(
        beginning_mrr=Decimal("1000"),
        new_mrr=Decimal("100"),
        expansion_mrr=Decimal("200"),
        contraction_mrr=Decimal("50"),
        churn_mrr=Decimal("100"),
        reactivation_mrr=Decimal("0"),
        ending_mrr=Decimal("1150"),
        active_customers_beginning=10,
        churned_customers=1,
    )
    m = compute_period_metrics(s)
    # NRR = (1000 + 200 - 50 - 100) / 1000 = 1.05
    assert m.nrr == Decimal("1.0500")
    # GRR = (1000 - 100 - 50) / 1000 = 0.85
    assert m.grr == Decimal("0.8500")
    assert m.gross_mrr_churn_rate == Decimal("0.1000")
    assert m.expansion_rate == Decimal("0.2000")
    assert m.logo_churn_rate == Decimal("0.1000")
    # Net new = 100 + 200 + 0 - 50 - 100 = 150
    assert m.net_new_mrr == Decimal("150.00")


def test_metrics_when_no_starting_mrr_returns_none() -> None:
    s = _summary(
        beginning_mrr=Decimal("0"),
        new_mrr=Decimal("500"),
        ending_mrr=Decimal("500"),
    )
    m = compute_period_metrics(s)
    assert m.nrr is None
    assert m.grr is None
    assert m.gross_mrr_churn_rate is None
    assert m.expansion_rate is None
    assert m.logo_churn_rate is None
    assert m.net_new_mrr == Decimal("500.00")


def test_metrics_treat_reactivation_as_growth_for_nrr() -> None:
    """Reactivation contributes positively to NRR (it's win-back revenue)."""
    s = _summary(
        beginning_mrr=Decimal("1000"),
        reactivation_mrr=Decimal("100"),
        ending_mrr=Decimal("1100"),
    )
    m = compute_period_metrics(s)
    # NRR = (1000 + 0 + 100 - 0 - 0) / 1000 = 1.10
    assert m.nrr == Decimal("1.1000")
    # GRR excludes reactivation and expansion: (1000 - 0 - 0) / 1000 = 1.00
    assert m.grr == Decimal("1.0000")
