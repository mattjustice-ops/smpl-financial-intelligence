"""A schedule explains an account only when it adds up to that account."""

from app.services.reporting.account_activity import attach_account_activity, schedule_activity


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
