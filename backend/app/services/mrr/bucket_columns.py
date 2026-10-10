"""New Business and Customer Success columns of the loaded {version}_MRR_Waterfall files.

Amounts are positive like contraction_arr and churn_arr; ``sign`` says which way a line moves ARR.
The existing movement columns (new_business_arr, expansion_arr, ...) stay for bookings and commissions.
"""

from __future__ import annotations

from typing import Any, Mapping

# waterfall_type, column, sign, label
NEW_BUSINESS_LINES: tuple[tuple[str, str, int, str], ...] = (
    ("new_logo", "new_logo_arr", 1, "New Logo"),
    ("winback", "winback_arr", 1, "Winback"),
    ("first_year_expansion", "first_year_expansion_arr", 1, "First-Year Expansion"),
    ("first_year_contraction", "first_year_contraction_arr", -1, "First-Year Contraction"),
    ("no_start", "no_start_arr", -1, "No-Start"),
)
CUSTOMER_SUCCESS_LINES: tuple[tuple[str, str, int], ...] = (
    ("expansion", "customer_success_expansion_arr", 1),
    ("contraction", "customer_success_contraction_arr", -1),
    ("churn", "customer_success_churn_arr", -1),
    ("reactivation", "customer_success_reactivation_arr", 1),
)
NEW_BUSINESS_TOTAL_COLUMN = "new_business_bucket_arr"
CUSTOMER_SUCCESS_BEGINNING_COLUMN = "customer_success_beginning_arr"
# Memo row in the ARR waterfall: the GRR / NRR base, not a movement.
CUSTOMER_SUCCESS_BEGINNING = "customer_success_beginning"
CUSTOMER_SUCCESS_BEGINNING_LABEL = "Customer Success Beginning ARR (retention base)"
# Memo row: new_business_arr (new movements), which ties to closed-won bookings. A long-pause return booked as a
# new deal is a winback here, so the bookings figure cannot be rebuilt from the bucket lines.
CLOSED_WON_NEW_BUSINESS = "closed_won_new_business"
CLOSED_WON_NEW_BUSINESS_LABEL = "Closed-Won New Business ARR (bookings)"

BUCKET_COLUMNS = (
    *(col for _, col, _, _ in NEW_BUSINESS_LINES),
    NEW_BUSINESS_TOTAL_COLUMN,
    CUSTOMER_SUCCESS_BEGINNING_COLUMN,
    *(col for _, col, _ in CUSTOMER_SUCCESS_LINES),
)


def has_bucket_columns(raw: Mapping[str, Any]) -> bool:
    return all(raw.get(col) not in (None, "") for col in BUCKET_COLUMNS)
