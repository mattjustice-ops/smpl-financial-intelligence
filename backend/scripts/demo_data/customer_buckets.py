"""Customer buckets for the ARR waterfall: New Business (a customer's first 12 months) and Customer Success.

Rules (agreed with Matt, Oct 9 2026):
  * Age of first MRR counts months from a customer's first MRR. It restarts when the customer comes back after
    more than 6 months at zero ARR (after a churn or a pause).
  * New Business: customers under 12 months old. Lines: New logo (first MRR), Winback (back after more than 6
    months, or back at any gap while still in its first year), First-year expansion, First-year contraction and
    No-start (ARR to zero before 12 months). New Business is excluded from retention.
  * Customer Success: customers 12 months and older. Lines: Expansion, Contraction, Churn (pauses included) and
    Reactivation (back within 6 months). GRR and NRR are measured on this bucket only.
  * movement_subcategory holds expansion and contraction reasons (new feature, platform upgrade, fewer users).
    It stays blank until the source data has them.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

FIRST_YEAR_MONTHS = 12
RESTART_AFTER_MONTHS = 6
NEW_BUSINESS, CUSTOMER_SUCCESS = "New Business", "Customer Success"
ZERO = Decimal("0")

# waterfall_line -> (bucket, MRR waterfall column). Decreases are positive amounts in the waterfall, like
# contraction_arr and churn_arr.
LINES = {
    "new_logo": (NEW_BUSINESS, "new_logo_arr"),
    "winback": (NEW_BUSINESS, "winback_arr"),
    "first_year_expansion": (NEW_BUSINESS, "first_year_expansion_arr"),
    "first_year_contraction": (NEW_BUSINESS, "first_year_contraction_arr"),
    "no_start": (NEW_BUSINESS, "no_start_arr"),
    "expansion": (CUSTOMER_SUCCESS, "customer_success_expansion_arr"),
    "contraction": (CUSTOMER_SUCCESS, "customer_success_contraction_arr"),
    "churn": (CUSTOMER_SUCCESS, "customer_success_churn_arr"),
    "reactivation": (CUSTOMER_SUCCESS, "customer_success_reactivation_arr"),
}
DECREASES = frozenset({"first_year_contraction", "no_start", "contraction", "churn"})
HISTORY_BUCKET_FIELDS = ["first_mrr_period", "customer_age_months", "customer_bucket", "waterfall_line",
                         "movement_subcategory"]
NEW_BUSINESS_TOTAL = "new_business_bucket_arr"
CUSTOMER_SUCCESS_BEGINNING = "customer_success_beginning_arr"
WATERFALL_BUCKET_FIELDS = [*(LINES[k][1] for k in ("new_logo", "winback", "first_year_expansion",
                                                   "first_year_contraction", "no_start")),
                           NEW_BUSINESS_TOTAL, CUSTOMER_SUCCESS_BEGINNING,
                           *(LINES[k][1] for k in ("expansion", "contraction", "churn", "reactivation"))]


def months_between(a: str, b: str) -> int:
    ya, ma = int(a[:4]), int(a[5:7])
    yb, mb = int(b[:4]), int(b[5:7])
    return (yb - ya) * 12 + (mb - ma)


def _num(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x or "0"))


def _order(r: dict) -> tuple:
    return r["period"][:7], r["customer_id"], r["movement_type"] != "Opening balance"


def classify(rows: list[dict], start_of: dict[str, str], prior: list[dict] = ()) -> None:
    """Sets HISTORY_BUCKET_FIELDS on every row of ``rows`` (in place).

    ``start_of``: each customer's first MRR month (customer start) for customers whose history opens with a
    balance. ``prior``: rows from before ``rows`` (the Actual history a plan starts from) that set each
    customer's age and last departure; they are replayed, not changed.
    """
    first: dict[str, str] = {}
    left: dict[str, tuple[str, int]] = {}
    targets = {id(r) for r in rows}
    # A plan's opening balance shares its month with the last prior rows, so the prior rows go first.
    for r in [*sorted(prior, key=_order), *sorted(rows, key=_order)]:
        c, p, kind = r["customer_id"], r["period"][:7], r["movement_type"]
        line = ""
        if kind == "Opening balance":
            first.setdefault(c, start_of.get(c, p)[:7])
        elif kind in ("New Business", "Reactivation"):
            gone = left.pop(c, None)
            if gone is None:
                if kind == "Reactivation":
                    raise ValueError(f"{p} {c}: reactivation without a departure on record")
                line, first[c] = "new_logo", p
            elif months_between(gone[0], p) > RESTART_AFTER_MONTHS:
                line, first[c] = "winback", p
            else:
                line = "reactivation" if gone[1] >= FIRST_YEAR_MONTHS else "winback"
        else:
            if c not in first:
                first[c] = start_of[c][:7]
            age = months_between(first[c], p)
            young = age < FIRST_YEAR_MONTHS
            if kind in ("Churn", "Pause"):
                line = "no_start" if young else "churn"
                if _num(r["ending_arr"]) <= 0:
                    left[c] = (p, age)
            elif kind == "Expansion":
                line = "first_year_expansion" if young else "expansion"
            elif kind == "Contraction":
                line = "first_year_contraction" if young else "contraction"
            else:
                raise ValueError(f"{p} {c}: unknown movement {kind}")
        if id(r) not in targets:
            continue
        age = months_between(first[c], p)
        if age < 0:
            raise ValueError(f"{p} {c}: first MRR {first[c]} is after the movement")
        r["first_mrr_period"] = first[c]
        r["customer_age_months"] = age
        r["customer_bucket"] = LINES[line][0] if line else ""
        r["waterfall_line"] = line
        r.setdefault("movement_subcategory", "")


def bucket_waterfall(rows: list[dict], months: list[str]) -> dict[str, dict[str, Decimal]]:
    """Per month: the bucket line amounts (positive, like the MRR waterfall), the New Business total, and the
    Customer Success beginning ARR (customers 12 months and older with ARR at the start of the month)."""
    out = {p: {f: ZERO for f in WATERFALL_BUCKET_FIELDS} for p in months}
    arr: dict[str, Decimal] = defaultdict(lambda: ZERO)
    first: dict[str, str] = {}
    by_period: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_period[r["period"][:7]].append(r)
    for p in sorted(by_period.keys() | set(months)):
        if p in out:
            out[p][CUSTOMER_SUCCESS_BEGINNING] = sum(
                (a for c, a in arr.items() if a > 0 and months_between(first[c], p) >= FIRST_YEAR_MONTHS), ZERO)
        for r in sorted(by_period.get(p, []), key=_order):
            c = r["customer_id"]
            first[c] = r["first_mrr_period"]
            arr[c] = _num(r["ending_arr"])
            line = r["waterfall_line"]
            if line and p in out:
                out[p][LINES[line][1]] += abs(_num(r["movement_arr"]))
    for p, w in out.items():
        w[NEW_BUSINESS_TOTAL] = sum((-w[LINES[k][1]] if k in DECREASES else w[LINES[k][1]]
                                     for k, (bucket, _) in LINES.items() if bucket == NEW_BUSINESS), ZERO)
    return out
