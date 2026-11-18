"""A later close keeps an earlier month's loaded rows."""

from app.services.demo_csv.loader import rows_for_named_close


def test_first_load_keeps_the_whole_file() -> None:
    rows = [{"period": "2026-06"}, {"period": "2026-07"}]
    assert rows_for_named_close(rows, as_of_period="2026-07", earlier_load=False) == rows


def test_later_month_keeps_only_its_own_period_when_an_earlier_load_exists() -> None:
    rows = [
        {"period": "2026-06"},
        {"period": "2026-07"},
        {"Period": "2026-08"},
    ]
    kept = rows_for_named_close(rows, as_of_period="2026-08", earlier_load=True)
    assert kept == [{"Period": "2026-08"}]


def test_a_file_without_periods_stays_whole() -> None:
    rows = [{"customer_id": "C1"}, {"customer_id": "C2"}]
    assert rows_for_named_close(rows, as_of_period="2026-08", earlier_load=True) == rows
