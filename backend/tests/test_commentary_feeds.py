"""Count and size attach only when the feed equals the line."""

from app.services.reporting.commentary_feeds import attach_commentary_feeds


def _node(label: str, amount: float, **extra) -> dict:
    node = {"label": label, "amount": amount, "children": []}
    node.update(extra)
    return {"lines": [node]}


def _measures(tree: dict) -> dict:
    return {row["label"]: row["value"] for row in tree["lines"][0]["measures"]}


_PAYROLL = [
    {"employee_id": "E1", "department": "Sales", "gl_account": "61xx", "regular_wages": "6000", "bonus": "1000", "employer_payroll_tax": "560"},
    {"employee_id": "E2", "department": "Sales", "gl_account": "61xx", "regular_wages": "4000", "bonus": "500", "employer_payroll_tax": "360"},
]
_PRIOR = [
    {"employee_id": "E1", "department": "Sales", "gl_account": "61xx", "regular_wages": "6000", "bonus": "1000", "employer_payroll_tax": "560"},
]


def test_salaries_name_headcount_average_hires_and_departures() -> None:
    tree = _node("Base Salaries", 10000, id="opex|department:Sales|acct:6100", account_number="6100")
    attach_commentary_feeds(tree, payroll_rows=_PAYROLL, prior_payroll_rows=_PRIOR)
    assert _measures(tree) == {
        "employees": 2,
        "average salary": 5000,
        "hires": 1,
        "departures": 0,
    }


def test_payroll_tax_uses_the_tax_column_and_a_wage_total_does_not() -> None:
    tax = _node("Payroll Taxes", 920, id="opex|department:Sales|acct:6110", account_number="6110")
    attach_commentary_feeds(tax, payroll_rows=_PAYROLL, prior_payroll_rows=_PRIOR)
    assert _measures(tax)["employees"] == 2
    assert _measures(tax)["average payroll tax"] == 460

    wages_on_tax = _node("Payroll Taxes", 10000, id="opex|department:Sales|acct:6110", account_number="6110")
    attach_commentary_feeds(wages_on_tax, payroll_rows=_PAYROLL, prior_payroll_rows=_PRIOR)
    assert "measures" not in wages_on_tax["lines"][0]


def test_unsplit_labor_uses_the_account_the_register_names() -> None:
    tree = _node(
        "Customer Success Labor COGS",
        3000,
        id="cogs|department:Customer Success|acct:5020",
        account_number="5020",
    )
    attach_commentary_feeds(tree, payroll_rows=[
        {"employee_id": "C1", "department": "Customer Success", "gl_account": "5020", "regular_wages": "2000", "total_payroll_cost": "3000"},
    ], prior_payroll_rows=[])
    assert _measures(tree) == {
        "employees": 1,
        "average payroll cost": 3000,
        "hires": 1,
        "departures": 0,
    }


def test_another_department_does_not_inherit_the_register() -> None:
    tree = _node("Base Salaries", 10000, id="opex|department:Engineering|acct:6100", account_number="6100")
    attach_commentary_feeds(tree, payroll_rows=_PAYROLL, prior_payroll_rows=_PRIOR)
    assert "measures" not in tree["lines"][0]


def test_subscription_names_customers_and_who_started_or_ended() -> None:
    tree = _node("Subscription Revenue", 4000)
    attach_commentary_feeds(
        tree,
        recognition_rows=[
            {"customer_id": "C1", "revenue_type": "Subscription", "recognized_revenue": "1000"},
            {"customer_id": "C2", "revenue_type": "Subscription", "recognized_revenue": "3000"},
            {"customer_id": "C3", "revenue_type": "Recurring Services", "recognized_revenue": "4000"},
        ],
        prior_recognition_rows=[
            {"customer_id": "C1", "revenue_type": "Subscription", "recognized_revenue": "1000"},
            {"customer_id": "C9", "revenue_type": "Subscription", "recognized_revenue": "500"},
        ],
    )
    assert _measures(tree) == {
        "customers": 2,
        "average subscription revenue": 2000,
        "customers added": 1,
        "customers ended": 1,
    }


def test_recurring_services_does_not_take_the_subscription_count() -> None:
    tree = _node("Recurring Services Revenue", 4000)
    attach_commentary_feeds(tree, recognition_rows=[
        {"customer_id": "C1", "revenue_type": "Subscription", "recognized_revenue": "4000"},
    ])
    assert "measures" not in tree["lines"][0]


def test_an_existing_schedule_is_not_replaced() -> None:
    tree = _node("Subscription Revenue", 4000)
    tree["lines"][0]["measures"] = [{"label": "implementations", "value": 3}]
    attach_commentary_feeds(tree, recognition_rows=[
        {"customer_id": "C1", "revenue_type": "Subscription", "recognized_revenue": "4000"},
    ])
    assert tree["lines"][0]["measures"] == [{"label": "implementations", "value": 3}]


def test_prepaid_contracts_attach_when_amortization_ties() -> None:
    tree = _node(
        "Insurance",
        400,
        id="opex|department:G&A|acct:6520",
        account_number="6520",
    )
    attach_commentary_feeds(tree, prepaid_rows=[
        {"account_number": "6520", "department": "G&A", "contract_id": "P1", "amortization": "100"},
        {"account_number": "6520", "department": "G&A", "contract_id": "P2", "amortization": "300"},
        {"account_number": "6520", "department": "Engineering", "contract_id": "P3", "amortization": "400"},
    ])
    assert _measures(tree) == {"prepaid contracts": 2, "average amortization": 200}


def test_prepaid_does_not_explain_a_different_amount() -> None:
    tree = _node("Insurance", 50, id="opex|department:G&A|acct:6520", account_number="6520")
    attach_commentary_feeds(tree, prepaid_rows=[
        {"account_number": "6520", "department": "G&A", "contract_id": "P1", "amortization": "400"},
    ])
    assert "measures" not in tree["lines"][0]


def test_hires_are_omitted_when_the_prior_month_is_not_loaded() -> None:
    tree = _node("Base Salaries", 10000, id="opex|department:Sales|acct:6100", account_number="6100")
    attach_commentary_feeds(tree, payroll_rows=_PAYROLL, prior_payroll_rows=None)
    labels = {row["label"] for row in tree["lines"][0]["measures"]}
    assert labels == {"employees", "average salary"}
