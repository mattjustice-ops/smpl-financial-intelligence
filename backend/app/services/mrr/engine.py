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

Returning customers (prior_mrr == 0, had_historical_mrr) get a ReturnType from the onboarding
policy (questions 4.10 winback window and 4.11 pauses) and the customer's Departure:
  - RESTART:                recorded pause, any length of absence           -> REACTIVATION
  - WINBACK:                recorded termination, back within the window     -> REACTIVATION
  - RETURNING_NEW_BUSINESS: recorded termination, back after the window      -> NEW
  - UNKNOWN:                no departure on record, policy unanswered, or no evidence of
                            pause vs termination where the two are treated differently
                                                                             -> REACTIVATION
A return is never moved to NEW without a recorded termination and an answered window.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any, Iterable, Mapping, Optional

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


class ReturnType(str, Enum):
    WINBACK = "winback"
    RESTART = "restart_after_pause"
    RETURNING_NEW_BUSINESS = "returning_new_business"
    UNKNOWN = "unknown_return"


@dataclass(frozen=True)
class ReturnPolicy:
    """Onboarding answers 4.10 and 4.11.

    ``winback_window_months``: a terminated customer back within this many calendar months
    (counted from the first month without MRR to the month of return, inclusive) is a winback;
    later it is new business. ``None`` with ``no_window`` False means 4.10 is unanswered.
    ``pause_treatment``: "removes_arr", "keeps_arr", "not_offered", or None (unanswered).
    """

    winback_window_months: Optional[int] = None
    no_window: bool = False
    pause_treatment: Optional[str] = None

    @property
    def window_answered(self) -> bool:
        return self.no_window or self.winback_window_months is not None


@dataclass(frozen=True)
class Departure:
    """What a returning customer left from.

    ``churn_period``: first month with no MRR. ``prior_mrr``: MRR in the month before it (the
    baseline for "above the customer's level before leaving"). ``paused``: True for a recorded
    pause, False for a recorded termination, None when the source does not say.
    """

    churn_period: date
    prior_mrr: Decimal
    paused: Optional[bool] = None


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month


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
    # Returning customers only. baseline_mrr is the MRR before leaving; restored + above_baseline
    # explain the returned MRR and are not additional movements.
    return_type: Optional[ReturnType] = None
    months_away: Optional[int] = None
    baseline_mrr: Optional[Decimal] = None
    restored_mrr: Optional[Decimal] = None
    above_baseline_mrr: Optional[Decimal] = None
    return_note: Optional[str] = None

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
            "return_type": self.return_type.value if self.return_type else None,
            "months_away": self.months_away,
            "baseline_mrr": self.baseline_mrr,
            "restored_mrr": self.restored_mrr,
            "above_baseline_mrr": self.above_baseline_mrr,
            "return_note": self.return_note,
        }


def _to_decimal(value: object) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def classify_return(
    period: date, departure: Optional[Departure], policy: Optional[ReturnPolicy]
) -> tuple[ReturnType, Optional[int], Optional[str]]:
    """Return type, months away, and why the type is UNKNOWN (or a policy conflict)."""
    if departure is None:
        return ReturnType.UNKNOWN, None, "no departure on record for this customer"
    away = months_between(departure.churn_period, period)
    pause_treatment = policy.pause_treatment if policy else None
    paused = departure.paused
    if paused:
        note = "recorded pause, but 4.11 says pauses keep ARR" if pause_treatment == "keeps_arr" else None
        return ReturnType.RESTART, away, note
    if paused is None and pause_treatment in ("keeps_arr", "not_offered"):
        paused = False
    if policy is None or not policy.window_answered:
        return ReturnType.UNKNOWN, away, "winback window (4.10) not answered"
    within = policy.no_window or away <= (policy.winback_window_months or 0)
    if paused is None:
        note = "pause or termination not recorded"
        if not within:
            note += "; past the winback window, so a termination would make this new business"
        return ReturnType.UNKNOWN, away, note
    return (ReturnType.WINBACK if within else ReturnType.RETURNING_NEW_BUSINESS), away, None


def classify_customer(
    customer_id: str,
    period: date,
    prior_mrr: Decimal,
    current_mrr: Decimal,
    had_historical_mrr: bool,
    *,
    departure: Optional[Departure] = None,
    policy: Optional[ReturnPolicy] = None,
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
    ret: dict[str, Any] = {}

    if prior == ZERO and current > ZERO:
        if had_historical_mrr:
            return_type, away, note = classify_return(period, departure, policy)
            ret = {"return_type": return_type, "months_away": away, "return_note": note}
            if return_type is ReturnType.RETURNING_NEW_BUSINESS:
                new_mrr = current
                movement = MovementType.NEW
            else:
                reactivation_mrr = current
                movement = MovementType.REACTIVATION
                if departure is not None:
                    baseline = max(quantize_money(_to_decimal(departure.prior_mrr)), ZERO)
                    restored = min(current, baseline)
                    ret.update(baseline_mrr=baseline, restored_mrr=restored, above_baseline_mrr=current - restored)
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
        **ret,
    )


def compute_waterfall(
    period: date,
    prior_mrr_by_customer: Mapping[str, Decimal],
    current_mrr_by_customer: Mapping[str, Decimal],
    historical_active_customers: Iterable[str],
    departures: Optional[Mapping[str, Departure]] = None,
    policy: Optional[ReturnPolicy] = None,
) -> list[CustomerMrrMovement]:
    """Build customer-level MRR waterfall rows for a single period.

    Args:
        period: Anchor date for the row (typically first of the month).
        prior_mrr_by_customer: customer_id → MRR at end of prior month.
        current_mrr_by_customer: customer_id → MRR at end of current month.
        historical_active_customers: Customers that had positive MRR in ANY
            period before `prior_mrr_by_customer`. Used to distinguish NEW
            from REACTIVATION.
        departures: customer_id → Departure for returning customers.
        policy: onboarding return policy (4.10 / 4.11).
    """
    history = set(historical_active_customers)
    customer_ids = set(prior_mrr_by_customer) | set(current_mrr_by_customer)
    departures = departures or {}

    rows: list[CustomerMrrMovement] = []
    for cid in sorted(customer_ids):
        row = classify_customer(
            customer_id=cid,
            period=period,
            prior_mrr=prior_mrr_by_customer.get(cid, ZERO),
            current_mrr=current_mrr_by_customer.get(cid, ZERO),
            had_historical_mrr=cid in history,
            departure=departures.get(cid),
            policy=policy,
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
    # Reactivated customers by return type; returning_new_* is the part of new that came back.
    winback_customers: int = 0
    restarted_customers: int = 0
    unknown_return_customers: int = 0
    returning_new_customers: int = 0
    returning_new_mrr: Decimal = ZERO
    reactivation_above_baseline_mrr: Decimal = ZERO
    reactivation_without_baseline_mrr: Decimal = ZERO

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
            "winback_customers": self.winback_customers,
            "restarted_customers": self.restarted_customers,
            "unknown_return_customers": self.unknown_return_customers,
            "returning_new_customers": self.returning_new_customers,
            "returning_new_mrr": self.returning_new_mrr,
            "reactivation_above_baseline_mrr": self.reactivation_above_baseline_mrr,
            "reactivation_without_baseline_mrr": self.reactivation_without_baseline_mrr,
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
    by_return: dict[ReturnType, int] = {t: 0 for t in ReturnType}
    returning_new_mrr = ZERO
    above_baseline = ZERO
    without_baseline = ZERO

    for r in rows:
        if r.return_type is not None:
            by_return[r.return_type] += 1
        if r.return_type is ReturnType.RETURNING_NEW_BUSINESS:
            returning_new_mrr += r.new_mrr
        if r.movement_type == MovementType.REACTIVATION:
            if r.above_baseline_mrr is None:
                without_baseline += r.reactivation_mrr
            else:
                above_baseline += r.above_baseline_mrr
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
        winback_customers=by_return[ReturnType.WINBACK],
        restarted_customers=by_return[ReturnType.RESTART],
        unknown_return_customers=by_return[ReturnType.UNKNOWN],
        returning_new_customers=by_return[ReturnType.RETURNING_NEW_BUSINESS],
        returning_new_mrr=quantize_money(returning_new_mrr),
        reactivation_above_baseline_mrr=quantize_money(above_baseline),
        reactivation_without_baseline_mrr=quantize_money(without_baseline),
    )
