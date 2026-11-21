"""The close schedules compile from customer files, not from a summary the customer will not have."""

from decimal import Decimal

from app.services.warehouse.compile_schedules import (
    arr_from_subscription_book,
    bookings_and_movements,
    unexplained_cash,
    cash_costs,
    movements_from_history,
    rollup_arr,
    rollup_deferred,
    rollup_pipeline,
)
from app.services.warehouse.event_labels import EventLabels, labels_from_json


def _opp(kind: str, amount: str, waterfall: str, status: str) -> dict:
    return {
        "opportunity_type": kind,
        "waterfall_type": waterfall,
        "pipeline_movement_type": waterfall,
        "close_status": status,
        "amount_arr": amount,
    }


def test_july_opportunities_become_bookings_and_a_waterfall() -> None:
    rows = [
        _opp("New Business", "1680043.49", "Closed Won", "Open"),
        _opp("Expansion", "895677.31", "Closed Won", "Open"),
        _opp("Reactivation", "276730.20", "Closed Won", "Open"),
        _opp("Churn", "507862.59", "Churn", "Churn"),
        _opp("Contraction", "334008.91", "Contraction", "Contraction"),
    ]
    bookings, lines = bookings_and_movements(rows, EventLabels())
    assert bookings == Decimal("2852451.00")
    beginning = Decimal("81716634.22")
    rolled = rollup_arr(beginning, lines)
    assert rolled["new"] == Decimal("1680043.49")
    assert rolled["expansion"] == Decimal("895677.31")
    assert rolled["churn"] == Decimal("507862.59")
    assert rolled["contraction"] == Decimal("334008.91")
    assert rolled["ending"] == (
        beginning
        + rolled["new"]
        + rolled["expansion"]
        + rolled["reactivation"]
        - rolled["contraction"]
        - rolled["churn"]
    )
    assert rolled["ending"] != beginning


def test_a_companys_own_word_replaces_the_default_booking() -> None:
    labels = labels_from_json({"movements": {"logo": "new"}, "closed_won": ["booked"]})
    bookings, lines = bookings_and_movements(
        [
            {
                "opportunity_type": "logo",
                "waterfall_type": "Booked",
                "pipeline_movement_type": "",
                "close_status": "Open",
                "amount_arr": "100",
            },
            _opp("New Business", "50", "Closed Won", "Open"),
        ],
        labels,
    )
    assert bookings == Decimal("100")
    assert lines["new"] == Decimal("150")


def test_the_subscription_book_opens_the_month_and_churn_is_a_customer_who_left() -> None:
    subscriptions = [
        {"customer_id": "A", "start_date": "2024-01-01", "end_date": "2024-01-30", "current_arr": "100"},
        {"customer_id": "A", "start_date": "2024-01-31", "end_date": "2024-12-31", "current_arr": "80"},
        {"customer_id": "B", "start_date": "2024-01-01", "end_date": "2024-01-30", "current_arr": "50"},
        {"customer_id": "C", "start_date": "2024-01-31", "end_date": "2024-12-31", "current_arr": "30"},
    ]
    opportunities = [
        {**_opp("Contraction", "20", "Contraction", "Contraction"), "customer_id": "A"},
        {**_opp("New Business", "30", "Closed Won", "Closed Won"), "customer_id": "C"},
        {**_opp("Churn", "50", "Churn", "Churn"), "customer_id": "B"},
        {**_opp("Renewal", "80", "Renewed", "Renewed"), "customer_id": "A"},
    ]
    booked = arr_from_subscription_book(subscriptions, opportunities, "2024-01", EventLabels())
    assert booked is not None
    assert booked["beginning"] == Decimal("150")
    assert booked["ending"] == Decimal("110")
    assert booked["lines"]["new"] == Decimal("30")
    assert booked["lines"]["contraction"] == Decimal("20")
    assert booked["lines"]["churn"] == Decimal("50")
    assert booked["tied"] is True


def test_customer_history_uses_the_labeled_movement() -> None:
    beginning, lines = movements_from_history(
        [
            {"waterfall_line": "new_logo", "movement_type": "New Business", "beginning_arr": "80", "movement_arr": "10"},
            {"waterfall_line": "contraction", "movement_type": "Contraction", "beginning_arr": "20", "movement_arr": "-3"},
        ],
        EventLabels(),
    )
    assert beginning == Decimal("100")
    assert lines["new"] == Decimal("10")
    assert lines["contraction"] == Decimal("3")


def test_deferred_revenue_is_prior_plus_billings_minus_recognized() -> None:
    rolled = rollup_deferred(Decimal("4700868.96"), Decimal("7269950.42"), Decimal("7319058.52"))
    assert rolled["ending"] == Decimal("4651760.86")
    assert rolled["beginning"] + rolled["billings"] - rolled["recognized"] == rolled["ending"]


def test_pipeline_waterfall_identity_ties() -> None:
    rolled = rollup_pipeline(
        Decimal("1000"),
        Decimal("400"),
        Decimal("250"),
        Decimal("100"),
        Decimal("50"),
    )
    assert rolled["ending"] == Decimal("1000")
    assert (
        rolled["beginning"]
        + rolled["created"]
        - rolled["won"]
        - rolled["lost"]
        - rolled["slipped"]
        == rolled["ending"]
    )


def test_pipeline_waterfall_clamps_when_won_exceeds_open() -> None:
    rolled = rollup_pipeline(
        Decimal("100"),
        Decimal("20"),
        Decimal("200"),
        Decimal("40"),
        Decimal("10"),
    )
    assert rolled["ending"] == Decimal("0")
    assert rolled["lost"] == Decimal("0")
    assert rolled["slipped"] == Decimal("0")
    assert rolled["won"] == Decimal("200")


def test_pipeline_waterfall_scales_lost_and_slipped_to_residual() -> None:
    rolled = rollup_pipeline(
        Decimal("100"),
        Decimal("0"),
        Decimal("20"),
        Decimal("60"),
        Decimal("40"),
    )
    # residual after won = 80; lost+slipped = 100 → scale to 80
    assert rolled["ending"] == Decimal("0")
    assert rolled["lost"] + rolled["slipped"] == Decimal("80")
    assert (
        rolled["beginning"]
        + rolled["created"]
        - rolled["won"]
        - rolled["lost"]
        - rolled["slipped"]
        == rolled["ending"]
    )


def test_unexplained_cash_is_ending_minus_measured_lines() -> None:
    beginning = Decimal("30000000.00")
    ending = Decimal("27573580.46")
    collections = Decimal("887226.90")
    payroll = Decimal("4000000")
    commission = Decimal("280199.36")
    vendor = Decimal("2000000")
    tax = Decimal("0")
    interest = Decimal("40000")
    capex = Decimal("40250")
    gap = unexplained_cash(beginning, ending, collections, payroll, commission, vendor, tax, interest, capex)
    measured = beginning + collections - payroll - commission - vendor - tax - interest - capex
    assert gap == ending - measured
    # Gap is disclosed — it does not force the bridge to foot via "other".
    assert measured + gap == ending


def test_a_tax_benefit_is_not_a_cash_payment() -> None:
    costs = cash_costs(
        [
            ("Revenue", "Subscription Revenue", "-7319058.52"),
            ("Labor", "Base Salaries", "100"),
            ("COGS", "Customer Support Labor COGS", "40"),
            ("COGS", "Cloud Hosting COGS", "25"),
            ("Sales Expense", "Sales Commissions", "15"),
            ("Marketing Expense", "Paid Search", "8"),
            ("Taxes", "Tax Expense", "-50"),
            ("Interest", "Interest Expense", "4"),
            ("D&A", "Depreciation and Amortization", "9"),
        ]
    )
    assert costs["recognized"] == Decimal("7319058.52")
    assert costs["payroll"] == Decimal("140")
    assert costs["vendor"] == Decimal("33")
    assert costs["commission"] == Decimal("15")
    assert costs["tax"] == Decimal("0")
    assert costs["interest"] == Decimal("4")
