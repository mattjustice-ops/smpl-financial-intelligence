"""June revenue cuts appear only when every dollar is tagged and the total ties."""

from app.services.reporting.board_modules_payload import revenue_mix_views


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
