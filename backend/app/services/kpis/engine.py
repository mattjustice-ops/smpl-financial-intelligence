"""Pure SaaS KPI calculation engine.

No DB or framework dependencies. Each metric is a small function that returns
either a Decimal or None (when the denominator is 0, i.e. undefined). The
top-level `calculate_kpis(KpiInputs)` returns a `KpiResults` dataclass with
every metric populated.

Rate values are returned in **ratio form** (0..1), not percentage points.
A NRR of 1.05 means 105% net retention. Multiply by 100 for display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

ZERO = Decimal("0")
ONE = Decimal("1")
TWELVE = Decimal("12")
FOUR = Decimal("4")
HUNDRED = Decimal("100")
MONEY = Decimal("0.01")
RATE = Decimal("0.0001")


def _q_money(v: Decimal) -> Decimal:
    return v.quantize(MONEY, rounding=ROUND_HALF_UP)


def _q_rate(v: Decimal) -> Decimal:
    return v.quantize(RATE, rounding=ROUND_HALF_UP)


def _safe_ratio(num: Decimal, den: Decimal) -> Optional[Decimal]:
    if den == ZERO:
        return None
    return _q_rate(num / den)


def _to_decimal(v, default: Decimal = ZERO) -> Decimal:
    if v is None:
        return default
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


# ---------------------------------------------------------------------------
# Input / output dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KpiInputs:
    """Period-anchored inputs for the KPI engine.

    All money values are in the org's reporting currency, Decimal-typed.
    Rate inputs (e.g. `gross_margin`) are ratios in 0..1.
    """

    period_start: date
    period_end: date

    # MRR waterfall (current period)
    beginning_mrr: Decimal = ZERO
    ending_mrr: Decimal = ZERO
    new_mrr: Decimal = ZERO
    expansion_mrr: Decimal = ZERO
    contraction_mrr: Decimal = ZERO
    churn_mrr: Decimal = ZERO
    reactivation_mrr: Decimal = ZERO

    # ARR snapshots (optional — defaults to MRR * 12)
    beginning_arr: Optional[Decimal] = None
    ending_arr: Optional[Decimal] = None

    # Customers
    active_customers_beginning: int = 0
    active_customers_ending: int = 0
    new_customers: int = 0
    churned_customers: int = 0

    # Bookings / pipeline
    new_bookings_arr: Decimal = ZERO
    total_pipeline: Decimal = ZERO
    target_bookings: Optional[Decimal] = None

    # Financial
    revenue: Decimal = ZERO
    prior_period_revenue: Optional[Decimal] = None
    sales_marketing_expense: Decimal = ZERO
    prior_period_sales_marketing_expense: Optional[Decimal] = None
    operating_expense: Optional[Decimal] = None
    gross_margin: Decimal = Decimal("0.7")  # fallback when not provided
    net_burn: Optional[Decimal] = None  # positive = burning cash

    # Period length in whole months (used by LTV / CAC payback)
    period_months: int = 1


@dataclass(frozen=True)
class KpiResults:
    period_start: date
    period_end: date

    # Recurring revenue
    arr: Decimal
    mrr: Decimal
    beginning_arr: Decimal
    ending_arr: Decimal

    # Retention
    nrr: Optional[Decimal]
    grr: Optional[Decimal]
    logo_churn_rate: Optional[Decimal]
    gross_mrr_churn_rate: Optional[Decimal]
    net_mrr_churn_rate: Optional[Decimal]

    # Unit economics
    arpa: Optional[Decimal]
    cac: Optional[Decimal]
    cac_payback_months: Optional[Decimal]
    ltv: Optional[Decimal]
    ltv_to_cac: Optional[Decimal]

    # Growth / efficiency
    revenue_growth_rate: Optional[Decimal]
    operating_margin: Optional[Decimal]
    rule_of_40: Optional[Decimal]
    magic_number: Optional[Decimal]
    sales_efficiency: Optional[Decimal]
    pipeline_coverage: Optional[Decimal]
    burn_multiple: Optional[Decimal]

    inputs_used: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "period_start": self.period_start,
            "period_end": self.period_end,
            "arr": self.arr,
            "mrr": self.mrr,
            "beginning_arr": self.beginning_arr,
            "ending_arr": self.ending_arr,
            "nrr": self.nrr,
            "grr": self.grr,
            "logo_churn_rate": self.logo_churn_rate,
            "gross_mrr_churn_rate": self.gross_mrr_churn_rate,
            "net_mrr_churn_rate": self.net_mrr_churn_rate,
            "arpa": self.arpa,
            "cac": self.cac,
            "cac_payback_months": self.cac_payback_months,
            "ltv": self.ltv,
            "ltv_to_cac": self.ltv_to_cac,
            "revenue_growth_rate": self.revenue_growth_rate,
            "operating_margin": self.operating_margin,
            "rule_of_40": self.rule_of_40,
            "magic_number": self.magic_number,
            "sales_efficiency": self.sales_efficiency,
            "pipeline_coverage": self.pipeline_coverage,
            "burn_multiple": self.burn_multiple,
            "inputs_used": self.inputs_used,
        }


# ---------------------------------------------------------------------------
# Individual calculations
# ---------------------------------------------------------------------------


def calculate_arr(mrr: Decimal) -> Decimal:
    return _q_money(_to_decimal(mrr) * TWELVE)


def calculate_nrr(
    beginning_mrr: Decimal,
    expansion_mrr: Decimal,
    reactivation_mrr: Decimal,
    contraction_mrr: Decimal,
    churn_mrr: Decimal,
) -> Optional[Decimal]:
    begin = _to_decimal(beginning_mrr)
    num = begin + _to_decimal(expansion_mrr) + _to_decimal(reactivation_mrr) - _to_decimal(contraction_mrr) - _to_decimal(churn_mrr)
    return _safe_ratio(num, begin)


def calculate_grr(
    beginning_mrr: Decimal,
    contraction_mrr: Decimal,
    churn_mrr: Decimal,
) -> Optional[Decimal]:
    begin = _to_decimal(beginning_mrr)
    num = begin - _to_decimal(contraction_mrr) - _to_decimal(churn_mrr)
    return _safe_ratio(num, begin)


def calculate_logo_churn_rate(
    churned_customers: int, active_customers_beginning: int
) -> Optional[Decimal]:
    if active_customers_beginning == 0:
        return None
    return _q_rate(Decimal(churned_customers) / Decimal(active_customers_beginning))


def calculate_gross_mrr_churn_rate(
    churn_mrr: Decimal, beginning_mrr: Decimal
) -> Optional[Decimal]:
    return _safe_ratio(_to_decimal(churn_mrr), _to_decimal(beginning_mrr))


def calculate_net_mrr_churn_rate(nrr: Optional[Decimal]) -> Optional[Decimal]:
    """1 - NRR. Positive = net contraction, negative = net growth."""
    if nrr is None:
        return None
    return _q_rate(ONE - nrr)


def calculate_arpa(
    revenue: Decimal,
    period_months: int,
    active_customers_beginning: int,
    active_customers_ending: int,
) -> Optional[Decimal]:
    """Average monthly revenue per account (ARPA)."""
    avg_customers = (Decimal(active_customers_beginning) + Decimal(active_customers_ending)) / Decimal(2)
    if avg_customers == ZERO or period_months == 0:
        return None
    monthly_rev = _to_decimal(revenue) / Decimal(period_months)
    return _q_money(monthly_rev / avg_customers)


def calculate_cac(
    sales_marketing_expense: Decimal, new_customers: int
) -> Optional[Decimal]:
    if new_customers == 0:
        return None
    return _q_money(_to_decimal(sales_marketing_expense) / Decimal(new_customers))


def calculate_cac_payback_months(
    cac: Optional[Decimal],
    new_mrr: Decimal,
    new_customers: int,
    gross_margin: Decimal,
) -> Optional[Decimal]:
    """CAC / (new_mrr_per_customer * gross_margin)."""
    if cac is None or new_customers == 0 or _to_decimal(gross_margin) == ZERO:
        return None
    per_customer_mrr = _to_decimal(new_mrr) / Decimal(new_customers)
    contribution = per_customer_mrr * _to_decimal(gross_margin)
    if contribution == ZERO:
        return None
    return _q_rate(cac / contribution)


def calculate_ltv(
    arpa: Optional[Decimal],
    gross_margin: Decimal,
    gross_mrr_churn_rate: Optional[Decimal],
) -> Optional[Decimal]:
    """ARPA * gross_margin / monthly_gross_mrr_churn_rate.

    ARPA here is already monthly. The result is total contribution margin per
    customer over their expected lifetime.
    """
    if arpa is None or gross_mrr_churn_rate is None:
        return None
    rate = _to_decimal(gross_mrr_churn_rate)
    if rate == ZERO:
        return None
    return _q_money(arpa * _to_decimal(gross_margin) / rate)


def calculate_ltv_to_cac(
    ltv: Optional[Decimal], cac: Optional[Decimal]
) -> Optional[Decimal]:
    if ltv is None or cac is None or cac == ZERO:
        return None
    return _q_rate(ltv / cac)


def calculate_revenue_growth_rate(
    revenue: Decimal, prior_period_revenue: Optional[Decimal]
) -> Optional[Decimal]:
    if prior_period_revenue is None:
        return None
    prior = _to_decimal(prior_period_revenue)
    if prior == ZERO:
        return None
    return _q_rate((_to_decimal(revenue) - prior) / prior)


def calculate_operating_margin(
    revenue: Decimal, operating_expense: Optional[Decimal]
) -> Optional[Decimal]:
    if operating_expense is None:
        return None
    rev = _to_decimal(revenue)
    if rev == ZERO:
        return None
    return _q_rate((rev - _to_decimal(operating_expense)) / rev)


def calculate_rule_of_40(
    revenue_growth_rate: Optional[Decimal],
    operating_margin: Optional[Decimal],
) -> Optional[Decimal]:
    """Sum of growth and margin, expressed as a ratio (40 == 0.40)."""
    if revenue_growth_rate is None or operating_margin is None:
        return None
    return _q_rate(revenue_growth_rate + operating_margin)


def calculate_magic_number(
    current_period_revenue: Decimal,
    prior_period_revenue: Optional[Decimal],
    prior_period_sales_marketing_expense: Optional[Decimal],
) -> Optional[Decimal]:
    """Quarterly SaaS Magic Number.

    Assumes inputs are quarter totals. The * 4 annualizes the delta in revenue.
    """
    if prior_period_revenue is None or prior_period_sales_marketing_expense is None:
        return None
    sm = _to_decimal(prior_period_sales_marketing_expense)
    if sm == ZERO:
        return None
    delta = _to_decimal(current_period_revenue) - _to_decimal(prior_period_revenue)
    return _q_rate(delta * FOUR / sm)


def calculate_sales_efficiency(
    new_bookings_arr: Decimal, sales_marketing_expense: Decimal
) -> Optional[Decimal]:
    sm = _to_decimal(sales_marketing_expense)
    if sm == ZERO:
        return None
    return _q_rate(_to_decimal(new_bookings_arr) / sm)


def calculate_pipeline_coverage(
    total_pipeline: Decimal, target_bookings: Optional[Decimal]
) -> Optional[Decimal]:
    if target_bookings is None:
        return None
    tb = _to_decimal(target_bookings)
    if tb == ZERO:
        return None
    return _q_rate(_to_decimal(total_pipeline) / tb)


def calculate_burn_multiple(
    net_burn: Optional[Decimal],
    new_bookings_arr: Decimal,
    expansion_mrr: Decimal,
    contraction_mrr: Decimal,
    churn_mrr: Decimal,
) -> Optional[Decimal]:
    """Burn multiple = net_burn / net_new_arr.

    Net new ARR uses bookings - (contraction + churn) * 12, annualizing the
    monthly down-sell components into the ARR delta.
    """
    if net_burn is None:
        return None
    net_new_arr = (
        _to_decimal(new_bookings_arr)
        + (_to_decimal(expansion_mrr) - _to_decimal(contraction_mrr) - _to_decimal(churn_mrr)) * TWELVE
    )
    if net_new_arr == ZERO:
        return None
    return _q_rate(_to_decimal(net_burn) / net_new_arr)


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------


def calculate_kpis(inputs: KpiInputs) -> KpiResults:
    mrr = _to_decimal(inputs.ending_mrr)
    arr = calculate_arr(mrr)
    beginning_arr = (
        _to_decimal(inputs.beginning_arr)
        if inputs.beginning_arr is not None
        else calculate_arr(inputs.beginning_mrr)
    )
    ending_arr = (
        _to_decimal(inputs.ending_arr) if inputs.ending_arr is not None else arr
    )

    nrr = calculate_nrr(
        inputs.beginning_mrr,
        inputs.expansion_mrr,
        inputs.reactivation_mrr,
        inputs.contraction_mrr,
        inputs.churn_mrr,
    )
    grr = calculate_grr(inputs.beginning_mrr, inputs.contraction_mrr, inputs.churn_mrr)
    logo_churn = calculate_logo_churn_rate(
        inputs.churned_customers, inputs.active_customers_beginning
    )
    gross_mrr_churn = calculate_gross_mrr_churn_rate(
        inputs.churn_mrr, inputs.beginning_mrr
    )
    net_mrr_churn = calculate_net_mrr_churn_rate(nrr)

    arpa = calculate_arpa(
        inputs.revenue,
        inputs.period_months,
        inputs.active_customers_beginning,
        inputs.active_customers_ending,
    )
    cac = calculate_cac(inputs.sales_marketing_expense, inputs.new_customers)
    cac_payback = calculate_cac_payback_months(
        cac, inputs.new_mrr, inputs.new_customers, inputs.gross_margin
    )
    ltv = calculate_ltv(arpa, inputs.gross_margin, gross_mrr_churn)
    ltv_cac = calculate_ltv_to_cac(ltv, cac)

    rev_growth = calculate_revenue_growth_rate(inputs.revenue, inputs.prior_period_revenue)
    op_margin = calculate_operating_margin(inputs.revenue, inputs.operating_expense)
    ro40 = calculate_rule_of_40(rev_growth, op_margin)
    magic = calculate_magic_number(
        inputs.revenue,
        inputs.prior_period_revenue,
        inputs.prior_period_sales_marketing_expense,
    )
    sales_eff = calculate_sales_efficiency(
        inputs.new_bookings_arr, inputs.sales_marketing_expense
    )
    pipeline = calculate_pipeline_coverage(inputs.total_pipeline, inputs.target_bookings)
    burn = calculate_burn_multiple(
        inputs.net_burn,
        inputs.new_bookings_arr,
        inputs.expansion_mrr,
        inputs.contraction_mrr,
        inputs.churn_mrr,
    )

    return KpiResults(
        period_start=inputs.period_start,
        period_end=inputs.period_end,
        arr=arr,
        mrr=_q_money(mrr),
        beginning_arr=_q_money(beginning_arr),
        ending_arr=_q_money(ending_arr),
        nrr=nrr,
        grr=grr,
        logo_churn_rate=logo_churn,
        gross_mrr_churn_rate=gross_mrr_churn,
        net_mrr_churn_rate=net_mrr_churn,
        arpa=arpa,
        cac=cac,
        cac_payback_months=cac_payback,
        ltv=ltv,
        ltv_to_cac=ltv_cac,
        revenue_growth_rate=rev_growth,
        operating_margin=op_margin,
        rule_of_40=ro40,
        magic_number=magic,
        sales_efficiency=sales_eff,
        pipeline_coverage=pipeline,
        burn_multiple=burn,
    )
