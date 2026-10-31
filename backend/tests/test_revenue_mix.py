"""Revenue cuts appear only when every dollar is tagged and the total ties. Share is the year-to-date amount."""

from app.services.reporting.board_modules_payload import revenue_mix_columns, revenue_mix_views


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
