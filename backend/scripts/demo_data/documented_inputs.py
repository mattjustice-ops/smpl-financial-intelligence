"""Inputs the build reproduces and does not calculate.

December 31, 2023 ARR is the Actual ARR waterfall's January 2024 beginning balance. No customer
ARR exists before that date, so the customer history opens at this total.

December 31, 2025 ARR is the customer master's starting_arr_jan_2026. The history must land on
that total. June 2026 cash is the input balance sheet's June cash, checked with --close-cash-from.
"""

from decimal import Decimal

OPENING_ARR_PERIOD = "2023-12"
OPENING_ARR_WATERFALL_MONTH = "2024-01"
OPENING_ARR = Decimal("52000000.00")
OPENING_ARR_METRIC = "December 31, 2023 ARR"
OPENING_ARR_NOTE = (
    "Documented input: December 31, 2023 ending ARR. No customer ARR exists before this date. "
    "January 2024 begins here."
)
