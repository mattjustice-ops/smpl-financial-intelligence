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

Customer buckets (onboarding 4.10 restart window, 4.12 New Business period) sit beside the movement
types, which stay as above for bookings and commissions:
  - Age of first MRR counts months from a customer's first MRR and restarts when it returns after
    more than the restart window at zero MRR (after a churn or a pause).
  - New Business (age under the New Business period, excluded from retention): new_logo, winback
    (back after the window, or back at any gap while still in the period), first_year_expansion,
    first_year_contraction, no_start (MRR to zero inside the period).
  - Customer Success: expansion, contraction, churn and reactivation (back within the window after
    leaving at or past the period). GRR and NRR are measured on this bucket.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any, Iterable, Mapping, Optional, Sequence

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


SMPL_DEFAULT_RESTART_WINDOW_MONTHS = 6
SMPL_DEFAULT_NEW_BUSINESS_MONTHS = 12
NEW_BUSINESS, CUSTOMER_SUCCESS = "New Business", "Customer Success"
LINE_BUCKET = {
    "new_logo": NEW_BUSINESS,
    "winback": NEW_BUSINESS,
    "first_year_expansion": NEW_BUSINESS,
    "first_year_contraction": NEW_BUSINESS,
    "no_start": NEW_BUSINESS,
    "expansion": CUSTOMER_SUCCESS,
    "contraction": CUSTOMER_SUCCESS,
    "churn": CUSTOMER_SUCCESS,
    "reactivation": CUSTOMER_SUCCESS,
}


@dataclass(frozen=True)
class BucketPolicy:
    """Onboarding 4.10 (restart window; None = the age never restarts) and 4.12 (New Business period).

    ``defaults_used`` names the questions answered by the SMPL default because they are unanswered.
    """

    restart_window_months: Optional[int] = SMPL_DEFAULT_RESTART_WINDOW_MONTHS
    new_business_months: int = SMPL_DEFAULT_NEW_BUSINESS_MONTHS
    defaults_used: tuple[str, ...] = ()


@dataclass(frozen=True)
class CustomerAge:
    first_mrr_period: date
    age_months: int
    bucket: str
    line: str  # "" when the customer's MRR did not move


def first_mrr_period(active_months: Sequence[date], restart_window_months: Optional[int]) -> date:
    """Start of the customer's age of first MRR: its first month with MRR, moved to each return made
    after more than the restart window at zero MRR. ``active_months`` are first-of-month dates."""
    months = sorted(set(active_months))
    first = months[0]
    for prev, cur in zip(months, months[1:]):
        away = months_between(prev, cur) - 1
        if restart_window_months is not None and away > restart_window_months:
            first = cur
    return first


def customer_age(
    period: date, movement: MovementType, active_before: Sequence[date], policy: BucketPolicy
) -> Optional[CustomerAge]:
    """Age, bucket and waterfall line of one customer's movement in ``period``.

    ``active_before``: first-of-month dates before ``period`` in which the customer had MRR. None when
    the customer had MRR last month but no history says when it started (the age is unknown).
    """
    months = sorted({m for m in active_before if m < period})
    nb_months = policy.new_business_months
    if movement in (MovementType.NEW, MovementType.REACTIVATION):
        if not months:
            return CustomerAge(period, 0, NEW_BUSINESS, "new_logo")
        first = first_mrr_period(months, policy.restart_window_months)
        last = months[-1]
        gone = date(last.year + last.month // 12, last.month % 12 + 1, 1)
        window = policy.restart_window_months
        if window is not None and months_between(gone, period) > window:
            return CustomerAge(period, 0, NEW_BUSINESS, "winback")
        line = "reactivation" if months_between(first, gone) >= nb_months else "winback"
        return CustomerAge(first, months_between(first, period), LINE_BUCKET[line], line)
    if not months:
        return None
    first = first_mrr_period(months, policy.restart_window_months)
    age = months_between(first, period)
    young = age < nb_months
    line = {
        MovementType.CHURN: "no_start" if young else "churn",
        MovementType.EXPANSION: "first_year_expansion" if young else "expansion",
        MovementType.CONTRACTION: "first_year_contraction" if young else "contraction",
    }.get(movement, "")
    bucket = LINE_BUCKET[line] if line else NEW_BUSINESS if young else CUSTOMER_SUCCESS
    return CustomerAge(first, age, bucket, line)


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
    # Customer buckets; None when the customer's MRR history was not supplied.
    first_mrr_period: Optional[date] = None
    customer_age_months: Optional[int] = None
    customer_bucket: Optional[str] = None
    waterfall_line: Optional[str] = None

    @property
    def movement_mrr(self) -> Decimal:
        return abs(self.ending_mrr - self.beginning_mrr)

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
            "first_mrr_period": self.first_mrr_period,
            "customer_age_months": self.customer_age_months,
            "customer_bucket": self.customer_bucket,
            "waterfall_line": self.waterfall_line,
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
    mrr_history: Optional[Mapping[str, Sequence[date]]] = None,
    bucket_policy: Optional[BucketPolicy] = None,
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
        mrr_history: customer_id → months before ``period`` with MRR. When given, every row gets
            its age of first MRR, bucket and waterfall line under ``bucket_policy``.
    """
    history = set(historical_active_customers)
    customer_ids = set(prior_mrr_by_customer) | set(current_mrr_by_customer)
    departures = departures or {}
    buckets = bucket_policy or BucketPolicy()

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
        if row is None:
            continue
        age = None if mrr_history is None else customer_age(period, row.movement_type, mrr_history.get(cid, ()),
                                                            buckets)
        if age is not None:
            row = replace(row, first_mrr_period=age.first_mrr_period, customer_age_months=age.age_months,
                          customer_bucket=age.bucket, waterfall_line=age.line)
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
    # Customer buckets: waterfall line -> MRR moved (positive), and the Customer Success beginning MRR.
    # None when any row has no age of first MRR.
    bucket_lines_mrr: Optional[dict[str, Decimal]] = None
    customer_success_beginning_mrr: Optional[Decimal] = None

    @property
    def new_business_bucket_mrr(self) -> Optional[Decimal]:
        if self.bucket_lines_mrr is None:
            return None
        lines = self.bucket_lines_mrr
        return (lines["new_logo"] + lines["winback"] + lines["first_year_expansion"]
                - lines["first_year_contraction"] - lines["no_start"])

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
            "bucket_lines_mrr": self.bucket_lines_mrr,
            "new_business_bucket_mrr": self.new_business_bucket_mrr,
            "customer_success_beginning_mrr": self.customer_success_beginning_mrr,
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
    rows = list(rows)
    bucketed = bool(rows) and all(r.customer_bucket is not None for r in rows)
    lines = {line: ZERO for line in LINE_BUCKET}
    cs_beginning = ZERO

    for r in rows:
        if bucketed:
            if r.waterfall_line:
                lines[r.waterfall_line] += r.movement_mrr
            if r.beginning_mrr > ZERO and r.customer_bucket == CUSTOMER_SUCCESS:
                cs_beginning += r.beginning_mrr
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
        bucket_lines_mrr={k: quantize_money(v) for k, v in lines.items()} if bucketed else None,
        customer_success_beginning_mrr=quantize_money(cs_beginning) if bucketed else None,
    )
