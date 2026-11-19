"""The close schedules compile from customer files, not from a summary the customer will not have."""

from decimal import Decimal

from app.services.warehouse.compile_schedules import (
    bookings_and_movements,
    bridge_plug,
    cash_costs,
    movements_from_history,
    rollup_arr,
    rollup_deferred,
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


def test_the_bridge_residual_lands_on_statement_cash() -> None:
    beginning = Decimal("30000000.00")
    ending = Decimal("27573580.46")
    collections = Decimal("887226.90")
    payroll = Decimal("4000000")
    commission = Decimal("280199.36")
    vendor = Decimal("2000000")
    tax = Decimal("0")
    interest = Decimal("40000")
    capex = Decimal("40250")
    other = bridge_plug(beginning, ending, collections, payroll, commission, vendor, tax, interest, capex)
    assert (
        beginning + collections - payroll - commission - vendor - tax - interest - capex - other
    ) == ending


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
