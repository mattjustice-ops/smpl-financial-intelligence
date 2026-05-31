"""Pure MRR classification engine.

No DB or framework dependencies: takes plain inputs and returns dataclasses.
Use this module in unit tests and from the higher-level service layer.

Classification rules (per customer, per period):
  - NEW:         prior_mrr == 0 AND current_mrr > 0 AND not had_historical_mrr
  - REACTIVATION:prior_mrr == 0 AND current_mrr > 0 AND had_historical_mrr
  - EXPANSION:   prior_mrr > 0  AND current_mrr > prior_mrr
  - CONTRACTION: prior_mrr > 0  AND 0 < current_mrr < prior_mrr
  - CHURN:       prior_mrr > 0  AND current_mrr == 0
  - UNCHANGED:   prior_mrr > 0  AND current_mrr == prior_mrr
  - (skipped)    prior_mrr == 0 AND current_mrr == 0  (customer not active in either month)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Iterable, Mapping, Optional

ZERO = Decimal("0")
TWO_PLACES = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    """Round to 2 decimal places, half-up (cents)."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class MovementType(str, Enum):
    NEW = "new"
    EXPANSION = "expansion"
    CONTRACTION = "contraction"
    CHURN = "churn"
    REACTIVATION = "reactivation"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class CustomerMrrMovement:
    """One customer's MRR movement for a given period.

    The 6 movement components are mutually exclusive (only one is non-zero per
    row), except `beginning_mrr` and `ending_mrr`, which mirror the customer's
    prior/current snapshots. This keeps customer-level rows directly summable
    into a company-level waterfall.
    """

    customer_id: str
    period: date
    beginning_mrr: Decimal
    new_mrr: Decimal
    expansion_mrr: Decimal
    contraction_mrr: Decimal
    churn_mrr: Decimal
    reactivation_mrr: Decimal
    ending_mrr: Decimal
    movement_type: MovementType

    def as_dict(self) -> dict[str, object]:
        return {
            "customer_id": self.customer_id,
            "period": self.period,
            "beginning_mrr": self.beginning_mrr,
            "new_mrr": self.new_mrr,
            "expansion_mrr": self.expansion_mrr,
            "contraction_mrr": self.contraction_mrr,
            "churn_mrr": self.churn_mrr,
            "reactivation_mrr": self.reactivation_mrr,
            "ending_mrr": self.ending_mrr,
            "movement_type": self.movement_type.value,
        }


def _to_decimal(value: object) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def classify_customer(
    customer_id: str,
    period: date,
    prior_mrr: Decimal,
    current_mrr: Decimal,
    had_historical_mrr: bool,
) -> Optional[CustomerMrrMovement]:
    """Classify one customer's MRR movement.

    Returns None when prior_mrr and current_mrr are both 0 (customer is not
    active in either month — no waterfall row).

    Negative MRR is treated as 0 for classification purposes; the engine
    normalizes inputs but does not raise so it stays usable on noisy data.
    """
    prior = max(quantize_money(_to_decimal(prior_mrr)), ZERO)
    current = max(quantize_money(_to_decimal(current_mrr)), ZERO)

    if prior == ZERO and current == ZERO:
        return None

    new_mrr = ZERO
    expansion_mrr = ZERO
    contraction_mrr = ZERO
    churn_mrr = ZERO
    reactivation_mrr = ZERO

    if prior == ZERO and current > ZERO:
        if had_historical_mrr:
            reactivation_mrr = current
            movement = MovementType.REACTIVATION
        else:
            new_mrr = current
            movement = MovementType.NEW
    elif prior > ZERO and current == ZERO:
        churn_mrr = prior
        movement = MovementType.CHURN
    elif current > prior:
        expansion_mrr = current - prior
        movement = MovementType.EXPANSION
    elif current < prior:
        contraction_mrr = prior - current
        movement = MovementType.CONTRACTION
    else:
        movement = MovementType.UNCHANGED

    return CustomerMrrMovement(
        customer_id=customer_id,
        period=period,
        beginning_mrr=prior,
        new_mrr=quantize_money(new_mrr),
        expansion_mrr=quantize_money(expansion_mrr),
        contraction_mrr=quantize_money(contraction_mrr),
        churn_mrr=quantize_money(churn_mrr),
        reactivation_mrr=quantize_money(reactivation_mrr),
        ending_mrr=current,
        movement_type=movement,
    )


def compute_waterfall(
    period: date,
    prior_mrr_by_customer: Mapping[str, Decimal],
    current_mrr_by_customer: Mapping[str, Decimal],
    historical_active_customers: Iterable[str],
) -> list[CustomerMrrMovement]:
    """Build customer-level MRR waterfall rows for a single period.

    Args:
        period: Anchor date for the row (typically first of the month).
        prior_mrr_by_customer: customer_id → MRR at end of prior month.
        current_mrr_by_customer: customer_id → MRR at end of current month.
        historical_active_customers: Customers that had positive MRR in ANY
            period before `prior_mrr_by_customer`. Used to distinguish NEW
            from REACTIVATION.
    """
    history = set(historical_active_customers)
    customer_ids = set(prior_mrr_by_customer) | set(current_mrr_by_customer)

    rows: list[CustomerMrrMovement] = []
    for cid in sorted(customer_ids):
        row = classify_customer(
            customer_id=cid,
            period=period,
            prior_mrr=prior_mrr_by_customer.get(cid, ZERO),
            current_mrr=current_mrr_by_customer.get(cid, ZERO),
            had_historical_mrr=cid in history,
        )
        if row is not None:
            rows.append(row)
    return rows


@dataclass(frozen=True)
class CompanyMrrSummary:
    period: date
    beginning_mrr: Decimal
    new_mrr: Decimal
    expansion_mrr: Decimal
    contraction_mrr: Decimal
    churn_mrr: Decimal
    reactivation_mrr: Decimal
    ending_mrr: Decimal
    active_customers_beginning: int
    active_customers_ending: int
    new_customers: int
    churned_customers: int
    reactivated_customers: int

    def as_dict(self) -> dict[str, object]:
        return {
            "period": self.period,
            "beginning_mrr": self.beginning_mrr,
            "new_mrr": self.new_mrr,
            "expansion_mrr": self.expansion_mrr,
            "contraction_mrr": self.contraction_mrr,
            "churn_mrr": self.churn_mrr,
            "reactivation_mrr": self.reactivation_mrr,
            "ending_mrr": self.ending_mrr,
            "active_customers_beginning": self.active_customers_beginning,
            "active_customers_ending": self.active_customers_ending,
            "new_customers": self.new_customers,
            "churned_customers": self.churned_customers,
            "reactivated_customers": self.reactivated_customers,
        }


def summarize_company(
    period: date, rows: Iterable[CustomerMrrMovement]
) -> CompanyMrrSummary:
    """Aggregate customer-level rows into a single company-level summary row.

    Identity check: beginning_mrr + new + expansion + reactivation
                    - contraction - churn == ending_mrr.
    """
    beginning = ZERO
    new = ZERO
    expansion = ZERO
    contraction = ZERO
    churn = ZERO
    reactivation = ZERO
    ending = ZERO

    active_begin = 0
    active_end = 0
    new_customers = 0
    churned_customers = 0
    reactivated_customers = 0

    for r in rows:
        beginning += r.beginning_mrr
        new += r.new_mrr
        expansion += r.expansion_mrr
        contraction += r.contraction_mrr
        churn += r.churn_mrr
        reactivation += r.reactivation_mrr
        ending += r.ending_mrr

        if r.beginning_mrr > ZERO:
            active_begin += 1
        if r.ending_mrr > ZERO:
            active_end += 1
        if r.movement_type == MovementType.NEW:
            new_customers += 1
        elif r.movement_type == MovementType.CHURN:
            churned_customers += 1
        elif r.movement_type == MovementType.REACTIVATION:
            reactivated_customers += 1

    return CompanyMrrSummary(
        period=period,
        beginning_mrr=quantize_money(beginning),
        new_mrr=quantize_money(new),
        expansion_mrr=quantize_money(expansion),
        contraction_mrr=quantize_money(contraction),
        churn_mrr=quantize_money(churn),
        reactivation_mrr=quantize_money(reactivation),
        ending_mrr=quantize_money(ending),
        active_customers_beginning=active_begin,
        active_customers_ending=active_end,
        new_customers=new_customers,
        churned_customers=churned_customers,
        reactivated_customers=reactivated_customers,
    )
