"""Revenue cuts appear only when every dollar is tagged and the total ties. Share is the year-to-date amount."""

from app.services.reporting.board_modules_payload import attach_revenue_mix_months, revenue_mix_columns, revenue_mix_views


def test_industry_segment_and_concentration_when_the_total_ties() -> None:
    by_customer = {"a": 500.0, "b": 300.0, "c": 200.0}
    attributes = {
        "a": ("Software", "Enterprise"),
        "b": ("Healthcare", "Mid-market"),
        "c": ("Software", "SMB"),
    }
    mix = revenue_mix_views(by_customer, attributes, 1000.0)
    assert mix is not None
    assert mix["total"] == 1000.0
    assert [row["label"] for row in mix["views"]["industry"]] == ["Software", "Healthcare"]
    assert mix["views"]["industry"][0]["amount"] == 700.0
    assert [row["label"] for row in mix["views"]["segment"]] == ["Enterprise", "Mid-market", "SMB"]
    assert mix["views"]["concentration"] == [{"label": "Largest customer", "amount": 500.0}]


def test_a_cut_is_left_off_when_a_dollar_is_untagged() -> None:
    by_customer = {"a": 500.0, "b": 500.0}
    attributes = {"a": ("Software", "Enterprise"), "b": ("", "Enterprise")}
    mix = revenue_mix_views(by_customer, attributes, 1000.0)
    assert mix is not None
    assert "industry" not in mix["views"]
    assert [row["label"] for row in mix["views"]["segment"]] == ["Enterprise"]


def test_nothing_is_returned_when_recognition_misses_the_books() -> None:
    assert revenue_mix_views({"a": 1000.0}, {"a": ("Software", "Enterprise")}, 1001.5) is None


def test_share_rows_carry_year_to_date_and_budget_on_the_same_label() -> None:
    june = revenue_mix_views(
        {"a": 60.0, "b": 40.0},
        {"a": ("Software", "Enterprise"), "b": ("Healthcare", "SMB")},
        100.0,
    )
    ytd = revenue_mix_views(
        {"a": 200.0, "b": 300.0},
        {"a": ("Software", "Enterprise"), "b": ("Healthcare", "SMB")},
        500.0,
    )
    budget = revenue_mix_views(
        {"a": 180.0, "b": 220.0},
        {"a": ("Software", "Enterprise"), "b": ("Healthcare", "SMB")},
        400.0,
    )
    table = revenue_mix_columns(june, ytd, budget)
    assert table is not None
    assert table["total"] == 100.0
    assert table["ytd_total"] == 500.0
    assert table["views"]["industry"] == [
        {"label": "Healthcare", "amount": 40.0, "ytd": 300.0, "budget": 220.0},
        {"label": "Software", "amount": 60.0, "ytd": 200.0, "budget": 180.0},
    ]
    assert [row["label"] for row in table["views"]["concentration"]] == ["Largest customer"]
    assert table["views"]["concentration"][0]["ytd"] == 300.0


def test_actual_months_follow_the_year_to_date_group() -> None:
    attributes = {"a": ("Software", "Enterprise"), "b": ("Healthcare", "SMB")}
    by_period = {"2026-01": {"a": 10.0, "b": 40.0}, "2026-06": {"a": 50.0, "b": 0.0}}
    ytd_customers = {"a": 60.0, "b": 40.0}
    june = revenue_mix_views(by_period["2026-06"], attributes, 50.0)
    ytd = revenue_mix_views(ytd_customers, attributes, 100.0)
    table = revenue_mix_columns(june, ytd, None)
    attach_revenue_mix_months(
        table,
        ytd_customers,
        by_period,
        ["2026-01", "2026-06"],
        attributes,
        {"2026-01": 50.0, "2026-06": 50.0},
    )
    software = next(row for row in table["views"]["industry"] if row["label"] == "Software")
    assert table["periods"] == ["2026-01", "2026-06"]
    assert software["months"] == {"2026-01": 10.0, "2026-06": 50.0}
    largest = table["views"]["concentration"][0]
    assert largest["ytd"] == 60.0
    assert largest["months"]["2026-01"] == 10.0
    assert largest["months"]["2026-06"] == 50.0

    attach_revenue_mix_months(
        table,
        ytd_customers,
        by_period,
        ["2026-01"],
        attributes,
        {"2026-01": 80.0},
    )
    assert software["months"]["2026-01"] is None
