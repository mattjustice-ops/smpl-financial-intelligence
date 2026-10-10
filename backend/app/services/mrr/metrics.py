"""ARR bridge + retention/growth metrics derived from a CompanyMrrSummary.

Definitions used here (standard SaaS):
  - ARR             = MRR * 12 (applied per bucket for the bridge)
  - GRR (Gross Retention) = (beginning - churn - contraction) / beginning
  - NRR (Net Retention)   = (beginning + expansion + reactivation - contraction - churn)
                          / beginning
    Retention is measured on the Customer Success bucket (customers past the New Business period)
    when the summary has customer buckets; otherwise on all customers, and ``retention_base`` says so.
  - Gross MRR Churn Rate  = churn / beginning
  - Expansion Rate        = expansion / beginning
  - Logo Churn Rate       = churned_customers / active_customers_beginning
  - Net New MRR           = new + expansion + reactivation - contraction - churn

When `beginning` is 0, rate metrics return None (undefined) instead of NaN/zero
to avoid misleading dashboards.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from app.services.mrr.engine import CompanyMrrSummary, quantize_money

ZERO = Decimal("0")
TWELVE = Decimal("12")
RATE_PLACES = Decimal("0.0001")
CUSTOMER_SUCCESS_BASE = "customer_success"
ALL_CUSTOMERS = "all_customers"


def _q_rate(v: Decimal) -> Decimal:
    return v.quantize(RATE_PLACES, rounding=ROUND_HALF_UP)


def _safe_ratio(numerator: Decimal, denominator: Decimal) -> Optional[Decimal]:
    if denominator == ZERO:
        return None
    return _q_rate(numerator / denominator)


@dataclass(frozen=True)
class ArrBridge:
    """ARR view of the same waterfall (each bucket * 12)."""

    period: date
    beginning_arr: Decimal
    new_arr: Decimal
    expansion_arr: Decimal
    contraction_arr: Decimal
    churn_arr: Decimal
    reactivation_arr: Decimal
    ending_arr: Decimal

    def as_dict(self) -> dict[str, object]:
        return {
            "period": self.period,
            "beginning_arr": self.beginning_arr,
            "new_arr": self.new_arr,
            "expansion_arr": self.expansion_arr,
            "contraction_arr": self.contraction_arr,
            "churn_arr": self.churn_arr,
            "reactivation_arr": self.reactivation_arr,
            "ending_arr": self.ending_arr,
        }


def arr_bridge(summary: CompanyMrrSummary) -> ArrBridge:
    return ArrBridge(
        period=summary.period,
        beginning_arr=quantize_money(summary.beginning_mrr * TWELVE),
        new_arr=quantize_money(summary.new_mrr * TWELVE),
        expansion_arr=quantize_money(summary.expansion_mrr * TWELVE),
        contraction_arr=quantize_money(summary.contraction_mrr * TWELVE),
        churn_arr=quantize_money(summary.churn_mrr * TWELVE),
        reactivation_arr=quantize_money(summary.reactivation_mrr * TWELVE),
        ending_arr=quantize_money(summary.ending_mrr * TWELVE),
    )


@dataclass(frozen=True)
class PeriodMetrics:
    period: date
    nrr: Optional[Decimal]
    grr: Optional[Decimal]
    gross_mrr_churn_rate: Optional[Decimal]
    expansion_rate: Optional[Decimal]
    logo_churn_rate: Optional[Decimal]
    net_new_mrr: Decimal
    retention_base: str = ALL_CUSTOMERS
    retention_beginning_mrr: Decimal = ZERO

    def as_dict(self) -> dict[str, object]:
        return {
            "period": self.period,
            "nrr": self.nrr,
            "grr": self.grr,
            "gross_mrr_churn_rate": self.gross_mrr_churn_rate,
            "expansion_rate": self.expansion_rate,
            "logo_churn_rate": self.logo_churn_rate,
            "net_new_mrr": self.net_new_mrr,
            "retention_base": self.retention_base,
            "retention_beginning_mrr": self.retention_beginning_mrr,
        }


def compute_period_metrics(summary: CompanyMrrSummary) -> PeriodMetrics:
    begin = summary.beginning_mrr
    lines = summary.bucket_lines_mrr
    if lines is not None and summary.customer_success_beginning_mrr is not None:
        base, basis = summary.customer_success_beginning_mrr, CUSTOMER_SUCCESS_BASE
        exp, react = lines["expansion"], lines["reactivation"]
        cont, churn = lines["contraction"], lines["churn"]
    else:
        base, basis = begin, ALL_CUSTOMERS
        exp, react = summary.expansion_mrr, summary.reactivation_mrr
        cont, churn = summary.contraction_mrr, summary.churn_mrr
    grr_num = base - churn - cont
    nrr_num = base + exp + react - cont - churn
    net_new = quantize_money(
        summary.new_mrr
        + summary.expansion_mrr
        + summary.reactivation_mrr
        - summary.contraction_mrr
        - summary.churn_mrr
    )

    logo_churn = (
        None
        if summary.active_customers_beginning == 0
        else _q_rate(
            Decimal(summary.churned_customers)
            / Decimal(summary.active_customers_beginning)
        )
    )

    return PeriodMetrics(
        period=summary.period,
        nrr=_safe_ratio(nrr_num, base),
        grr=_safe_ratio(grr_num, base),
        gross_mrr_churn_rate=_safe_ratio(summary.churn_mrr, begin),
        expansion_rate=_safe_ratio(summary.expansion_mrr, begin),
        logo_churn_rate=logo_churn,
        net_new_mrr=net_new,
        retention_base=basis,
        retention_beginning_mrr=base,
    )


__all__ = [
    "ArrBridge",
    "CompanyMrrSummary",
    "PeriodMetrics",
    "arr_bridge",
    "compute_period_metrics",
]
