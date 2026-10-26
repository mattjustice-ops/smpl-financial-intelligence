"""Trial-balance rollup. Numbers are the review's June and Campfire cases, scaled down."""

from __future__ import annotations

from app.services.reporting.gl_income_statement import OPEX_LINE_BY_DEPARTMENT
from app.services.reporting.gl_rollup import (
    build_rollup,
    is_depreciation,
    iter_nodes,
    labor_bucket,
    opex_contains_cost_of_revenue,
    same_fact,
    trees_by_period,
)


def _row(**kwargs):
    base = {
        "period": "2026-06",
        "account_id": "100",
        "account_name": "Account",
        "statement_category": "Operating Expense",
        "account_group": "",
        "account_type": "",
        "account_subtype": "",
        "department": "",
        "expense_type": "",
        "vendor": "",
        "memo": "",
        "amount": 0.0,
        "period_status": "closed",
    }
    base.update(kwargs)
    return base


def _find(tree, label):
    for line in tree["lines"]:
        for node in iter_nodes(line):
            if node["label"] == label:
                return node
    return None


def test_labor_rules_do_not_catch_tax_or_hosting_by_name() -> None:
    assert labor_bucket("Income Tax") is None
    assert labor_bucket("Payroll Taxes")[0] == "payroll_tax"
    hosting = build_rollup(
        [_row(account_id="6400", account_name="Cloud Hosting", statement_category="Operating Expense", amount=12.0)]
    )
    assert hosting["totals"]["opex"] == 12.0
    assert "cogs" not in hosting["totals"]


def test_blank_function_beside_a_named_function_is_named_for_what_is_missing() -> None:
    tree = build_rollup(
        [
            _row(account_id="1", account_name="Rent", department="Finance", amount=10.0),
            _row(account_id="2", account_name="Legal Fees", department="", amount=4.0),
        ],
        department_aliases={"Finance": "ga"},
    )
    labels = [node["label"] for line in tree["lines"] for node in iter_nodes(line)]
    assert any(label.startswith("No function") for label in labels)
    assert tree["totals"]["opex"] == 14.0


def test_same_fact_folds_plurals_and_not_different_names() -> None:
    assert same_fact("Software tools", "Software tool")
    assert same_fact("Travel & Entertainment", "Travel and entertainment")
    assert not same_fact("Software", "Software tools")


def test_depreciation_moves_and_amortization_alone_does_not() -> None:
    assert is_depreciation(_row(account_name="Depreciation and Amortization"))
    assert is_depreciation(_row(account_name="Rent", account_subtype="Depreciation"))
    assert not is_depreciation(_row(account_name="Amortized commissions"))


def test_campfire_accounts_without_department_or_expense_type() -> None:
    tree = build_rollup(
        [
            _row(account_id="4000", account_name="Subscription Revenue", statement_category="Revenue", amount=-100.0),
            _row(account_id="", account_name="REVENUE", statement_category="Revenue", amount=-100.0),
            _row(account_id="5000", account_name="Cost of Goods Sold - Software", statement_category="COGS", amount=40.0),
            _row(account_id="6000", account_name="Salaries and Wages", amount=100.0),
            _row(account_id="6100", account_name="Bonus Expense", amount=10.0),
            _row(account_id="6200", account_name="Sales Commissions", amount=5.0),
            _row(account_id="6300", account_name="Travel and Entertainment", amount=20.0),
            _row(account_id="6400", account_name="Software and Subscriptions", amount=30.0),
            _row(account_id="6500", account_name="Depreciation and Amortization", amount=8.0),
        ]
    )

    assert _find(tree, "No department") is None
    compensation = _find(tree, "Compensation")
    assert compensation is not None
    assert {child["label"] for child in compensation["children"]} == {
        "Base salaries · Salaries and Wages",
        "Bonuses · Bonus Expense",
        "Commissions · Sales Commissions",
    }
    assert _find(tree, "Travel and Entertainment") is not None
    assert _find(tree, "Software and Subscriptions") is not None
    assert _find(tree, "Unassigned") is None
    assert compensation["amount"] == 115.0
    assert tree["totals"]["opex"] == 165.0
    assert tree["totals"]["da"] == 8.0
    assert tree["totals"]["cogs"] == 40.0
    assert not opex_contains_cost_of_revenue(tree)
    cost = next(line for line in tree["lines"] if line["statement_line"] == "cogs")
    names = [node["label"] for node in iter_nodes(cost)]
    assert any("Cost of Goods Sold - Software" in name for name in names)
    assert all("Software and Subscriptions" not in name for name in names)
    revenue = next(line for line in tree["lines"] if line["statement_line"] == "revenue")
    assert revenue["amount"] == 100.0
    assert "Subscription Revenue" in revenue["label"]
    assert all(node["role"] != "plug" for node in iter_nodes(revenue))


def test_control_total_that_does_not_match_becomes_a_plug() -> None:
    tree = build_rollup(
        [
            _row(account_id="4000", account_name="Subscription Revenue", statement_category="Revenue", amount=-90.0),
            _row(account_id="", account_name="REVENUE", statement_category="Revenue", amount=-100.0),
        ]
    )
    revenue = _find(tree, "Revenue")
    plug = next(child for child in revenue["children"] if child["role"] == "plug")
    assert plug["label"] == "Items not yet mapped"
    assert plug["amount"] == 10.0
    assert revenue["amount"] == 100.0


def test_support_on_cost_of_revenue_stays_there_when_aliased_to_ga() -> None:
    tree = build_rollup(
        [
            _row(
                account_id="5100",
                account_name="Customer Support",
                statement_category="Cost of Revenue",
                department="Support",
                amount=50.0,
            )
        ],
        department_aliases={"Support": "ga"},
    )
    assert tree["totals"]["cogs"] == 50.0
    assert "opex" not in tree["totals"]
    assert not opex_contains_cost_of_revenue(tree)


def test_june_departments_keep_software_accounts_apart() -> None:
    tree = build_rollup(
        [
            _row(account_id="7100", account_name="Travel and Entertainment", department="Finance", expense_type="Travel and Entertainment", amount=1_544.0),
            _row(account_id="7200", account_name="Software Tools", department="Finance", expense_type="Software", amount=14_917.0),
            _row(account_id="7300", account_name="Computer Equipment and Supplies", department="G&A", expense_type="Software", amount=29_581.0),
            _row(account_id="7201", account_name="Software Tools", department="G&A", expense_type="Software", amount=31_531.0),
            _row(account_id="7101", account_name="Travel and Entertainment", department="G&A", expense_type="Travel and Entertainment", amount=7_188.0),
            _row(
                account_id="8100",
                account_name="Cloud Hosting",
                statement_category="Cost of Revenue",
                department="Support",
                expense_type="Cloud Hosting",
                amount=669_295.0,
            ),
        ],
        department_aliases={"Finance": "ga", "G&A": "ga", "Support": "ga"},
    )

    finance_software = _find(tree, "Software · Software Tools")
    assert finance_software is not None
    assert finance_software["amount"] == 14_917.0
    assert finance_software["children"] == []
    software = _find(tree, "Software")
    assert software is not None
    assert {child["label"] for child in software["children"]} == {
        "Computer Equipment and Supplies",
        "Software Tools",
    }
    assert software["amount"] == 61_112.0
    cost = next(line for line in tree["lines"] if line["statement_line"] == "cogs")
    assert cost["amount"] == 669_295.0
    assert "Cloud Hosting" in cost["label"]
    assert not opex_contains_cost_of_revenue(tree)


def test_two_vendors_open_and_a_memo_stays_evidence() -> None:
    tree = build_rollup(
        [
            _row(account_id="7100", account_name="Travel and Entertainment", expense_type="Travel and Entertainment", vendor="Uber for Business", amount=10.0, memo="FATE conference"),
            _row(account_id="7100", account_name="Travel and Entertainment", expense_type="Travel and Entertainment", vendor="The Beekman Hotel", amount=20.0, memo="Lodging"),
        ]
    )
    travel = _find(tree, "Operating expenses · Travel and Entertainment")
    assert {child["label"] for child in travel["children"]} == {"The Beekman Hotel", "Uber for Business"}
    assert "FATE conference" in travel["evidence"] or any("FATE conference" in child["evidence"] for child in travel["children"])
    assert all(child["role"] != "memo" for child in iter_nodes(travel))
    assert "vendor" not in travel


def test_one_vendor_is_named_on_the_account() -> None:
    tree = build_rollup(
        [
            _row(account_id="7200", account_name="Software Tools", expense_type="Software", vendor="Northwind", amount=100.0, memo="Annual renewal"),
        ]
    )
    named = [node for line in tree["lines"] for node in iter_nodes(line) if node.get("vendor") == "Northwind"]
    assert len(named) == 1
    assert named[0]["children"] == []
    assert "Software Tools" in named[0]["label"]
    assert "Northwind" in named[0]["evidence"]
    assert "Annual renewal" in named[0]["evidence"]


def test_mixed_blank_department_is_named_and_preliminary_month_is_omitted() -> None:
    tree = build_rollup(
        [
            _row(account_id="1", account_name="Rent", department="Finance", amount=10.0),
            _row(account_id="2", account_name="Legal Fees", department="", amount=4.0),
            _row(account_id="3", account_name="Bonus Expense", period="2026-10", period_status="preliminary", amount=99.0),
        ]
    )
    assert _find(tree, "No department · Legal Fees")["amount"] == 4.0
    assert _find(tree, "Bonus Expense") is None
    assert _find(tree, "Bonuses") is None


def test_same_name_accounts_keep_separate_numbers() -> None:
    tree = build_rollup(
        [
            _row(account_id="4000", account_name="Subscription Revenue", statement_category="Revenue", amount=-100.0),
            _row(account_id="4010", account_name="Subscription Revenue", statement_category="Revenue", amount=-15.0),
        ]
    )
    revenue = next(line for line in tree["lines"] if line["statement_line"] == "revenue")
    assert {child["account_number"]: child["amount"] for child in revenue["children"]} == {"4000": 100.0, "4010": 15.0}
    assert all(child["label"] == "Subscription Revenue" for child in revenue["children"])
    assert "4000" not in revenue["label"]


def test_a_single_account_keeps_its_number_off_the_label() -> None:
    tree = build_rollup(
        [_row(account_id="6400", account_name="Cloud Hosting", statement_category="Cost of Revenue", amount=12.0)]
    )
    cost = next(line for line in tree["lines"] if line["statement_line"] == "cogs")
    assert cost["account_number"] == "6400"
    assert "6400" not in cost["label"]
    assert "Cloud Hosting" in cost["label"]


def test_reporting_tree_carries_the_chart_number() -> None:
    trees = trees_by_period(
        [
            {
                "period": "2026-06",
                "statement_category": "Revenue",
                "account_number": "4000",
                "account_name": "Subscription Revenue",
                "amount": -100.0,
            },
            {
                "period": "2026-06",
                "statement_category": "Revenue",
                "account_number": "4100",
                "account_name": "Recurring Services",
                "amount": -20.0,
            },
        ]
    )
    revenue = next(line for line in trees["2026-06"]["lines"] if line["statement_line"] == "revenue")
    assert [(child["account_number"], child["label"]) for child in revenue["children"]] == [
        ("4000", "Subscription Revenue"),
        ("4100", "Recurring Services"),
    ]


def test_the_reporting_query_keeps_the_account_number() -> None:
    import inspect

    from app.services.reporting.gl_income_statement import fetch_gl_pl_rows

    source = inspect.getsource(fetch_gl_pl_rows)
    assert "account_number" in source
    assert "group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10" in source


def test_reporting_tree_keeps_statement_lines_and_separate_departments() -> None:
    trees = trees_by_period(
        [
            {
                "period": "2026-06",
                "statement": "Income Statement",
                "statement_category": "Operating Expense",
                "account_name": "Software Tools",
                "department": "Finance",
                "expense_type": "Software",
                "amount": 14_917.0,
            },
            {
                "period": "2026-06",
                "statement_category": "Operating Expense",
                "account_name": "Software Tools",
                "department": "G&A",
                "expense_type": "Software",
                "amount": 31_531.0,
            },
            {
                "period": "2026-06",
                "statement_category": "Operating Expense",
                "account_name": "Travel and Entertainment",
                "department": "Finance",
                "expense_type": "Travel and Entertainment",
                "amount": 1_544.0,
            },
            {
                "period": "2026-06",
                "statement_category": "Operating Expense",
                "account_name": "Travel and Entertainment",
                "department": "G&A",
                "expense_type": "Travel and Entertainment",
                "amount": 7_188.0,
            },
            {
                "period": "2026-06",
                "statement_category": "Cost of Revenue",
                "account_name": "Cloud Hosting",
                "department": "Support",
                "expense_type": "Cloud Hosting",
                "amount": 669_295.0,
            },
            {
                "period": "2026-06",
                "statement": "Balance Sheet",
                "statement_category": "Asset",
                "account_name": "Cash",
                "amount": 30_000_000.0,
            },
        ],
        department_aliases=OPEX_LINE_BY_DEPARTMENT,
    )
    tree = trees["2026-06"]
    opex = next(line for line in tree["lines"] if line["line_key"] == "opex")
    assert opex["label"] == "Operating expenses"
    general = next(child for child in opex["children"] if child["line_key"] == "ga")
    assert general["label"] == "General and administrative"
    labels = [node["label"] for node in iter_nodes(general)]
    assert "Finance" in labels
    assert "G&A" in labels
    amounts = {node["amount"] for node in iter_nodes(general)}
    assert 14_917.0 in amounts
    assert 31_531.0 in amounts
    assert 14_917.0 + 31_531.0 not in amounts
    assert 1_544.0 in amounts
    assert 7_188.0 in amounts
    cost = next(line for line in tree["lines"] if line["line_key"] == "cogs")
    assert cost["label"] == "Cost of revenue"
    assert cost["amount"] == 669_295.0
    assert not opex_contains_cost_of_revenue(tree)
    assert "Cash" not in [node["label"] for line in tree["lines"] for node in iter_nodes(line)]
