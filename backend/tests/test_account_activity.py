"""A schedule explains an account only when it adds up to that account."""

from app.services.reporting.account_activity import (
    attach_account_activity,
    attach_commission_payouts,
    commission_payout_facts,
    schedule_activity,
)


def _tree(label: str, amount: float) -> dict:
    return {"lines": [{"label": label, "amount": amount, "statement_line": "revenue", "children": []}]}


def test_implementation_count_and_fee_attach_when_they_tie() -> None:
    tree = _tree("Implementation & Onboarding Revenue", 10500)
    attach_account_activity(tree, implementation_rows=[
        {"implementation_fee": "2000", "win_probability": "1"},
        {"implementation_fee": "3500", "win_probability": "1"},
        {"implementation_fee": "5000", "win_probability": "1"},
    ])
    measures = {row["label"]: row["value"] for row in tree["lines"][0]["measures"]}
    assert measures == {"implementations": 3, "average implementation fee": 3500}


def test_a_schedule_that_does_not_tie_is_not_the_why() -> None:
    tree = _tree("Implementation & Onboarding Revenue", 999)
    attach_account_activity(tree, implementation_rows=[
        {"implementation_fee": "2000", "win_probability": "1"},
    ])
    assert "measures" not in tree["lines"][0]


def test_weighted_deals_count_expected_customers() -> None:
    activity = schedule_activity([
        {"implementation_fee": "1000", "win_probability": "0.5"},
        {"implementation_fee": "1500", "win_probability": "0.5"},
    ], "implementation_fee")
    assert activity is not None
    assert activity["count"] == 1
    assert activity["total"] == 2500
    assert activity["average"] == 2500


def test_recurring_services_count_customers_when_the_fees_tie() -> None:
    tree = _tree("Recurring Services Revenue", 400)
    attach_account_activity(tree, recurring_rows=[
        {"recurring_services_revenue": "100"},
        {"recurring_services_revenue": "300"},
    ])
    measures = {row["label"]: row["value"] for row in tree["lines"][0]["measures"]}
    assert measures == {"customers on recurring services": 2, "average recurring services fee": 200}


def test_another_account_does_not_inherit_the_schedule() -> None:
    tree = _tree("Cloud Hosting", 10500)
    attach_account_activity(tree, implementation_rows=[
        {"implementation_fee": "10500", "win_probability": "1"},
    ])
    assert "measures" not in tree["lines"][0]


_ROSTER = [
    {"employee_id": "E1", "employee_name": "Alex Rivera", "commission_target": "120000"},
    {"employee_id": "E2", "employee_name": "Blair Chen", "commission_target": "60000"},
]
_PAYOUTS = [
    {"rep_id": "E1", "rep_name": "Alex Rivera", "commission_amount": "8000"},
    {"rep_id": "E1", "commission_amount": "4000"},
    {"rep_id": "E2", "rep_name": "Blair Chen", "commission_amount": "4000"},
]


def test_paid_versus_monthly_commission_quota() -> None:
    facts, paid = commission_payout_facts(_PAYOUTS, _ROSTER)
    assert paid == 16000
    assert facts == [
        {"label": "Payouts", "paid": 16000, "quota": 15000},
        {"label": "Alex Rivera", "paid": 12000, "quota": 10000},
        {"label": "Blair Chen", "paid": 4000, "quota": 5000},
    ]


def test_commission_line_gets_the_comparison_when_payouts_are_that_amount() -> None:
    tree = {
        "lines": [{
            "label": "Commissions",
            "amount": 16000,
            "children": [{"label": "Sales Commissions", "amount": 16000, "children": []}],
        }]
    }
    attach_commission_payouts(tree, _PAYOUTS, _ROSTER)
    child = tree["lines"][0]["children"][0]
    assert child["payouts"][0] == {"label": "Payouts", "paid": 16000, "quota": 15000}
    assert "payouts" not in tree["lines"][0]


def test_payouts_do_not_explain_a_different_amount_or_another_role() -> None:
    short = _tree("Sales Commissions", 9000)
    attach_commission_payouts(short, _PAYOUTS, _ROSTER)
    assert "payouts" not in short["lines"][0]

    salaries = _tree("Base salaries", 16000)
    attach_commission_payouts(salaries, _PAYOUTS, _ROSTER)
    assert "payouts" not in salaries["lines"][0]


def test_compensation_bridge_attaches_when_the_department_total_ties() -> None:
    from app.services.reporting.account_activity import attach_compensation_bridge

    tree = {"lines": [{
        "id": "opex|department:Sales|compensation",
        "role": "compensation",
        "label": "Compensation",
        "amount": 80000,
        "children": [],
    }]}
    attach_compensation_bridge(tree, [{
        "department": "Sales",
        "beginning": 70000,
        "ending": 80000,
        "ties": True,
        "bars": [
            {"label": "Hires", "amount": 12000, "heads": 2},
            {"label": "Departures", "amount": -3000, "heads": 1},
            {"label": "GL reconciling", "amount": 1000},
        ],
    }])
    facts = tree["lines"][0]["bridge"]["facts"]
    assert [fact["label"] for fact in facts] == ["Hires", "Departures", "GL reconciling"]
    assert facts[0]["heads"] == 2
    assert "heads" not in facts[2]


def test_compensation_bridge_does_not_attach_when_the_total_differs() -> None:
    from app.services.reporting.account_activity import attach_compensation_bridge

    tree = {"lines": [{
        "id": "opex|department:Sales|compensation",
        "role": "compensation",
        "label": "Compensation",
        "amount": 90000,
        "children": [],
    }]}
    attach_compensation_bridge(tree, [{
        "department": "Sales",
        "beginning": 70000,
        "ending": 80000,
        "ties": True,
        "bars": [{"label": "Hires", "amount": 10000, "heads": 1}],
    }])
    assert "bridge" not in tree["lines"][0]


def test_a_paid_person_without_a_quota_is_not_compared() -> None:
    facts, paid = commission_payout_facts(
        [{"rep_id": "E9", "rep_name": "Casey", "commission_amount": "1000"}],
        [],
    )
    assert facts is None
    assert paid == 1000
