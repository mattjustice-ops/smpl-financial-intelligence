"""A later close keeps an earlier month's loaded rows."""

from app.services.demo_csv.loader import rows_for_named_close
from app.services.reporting.gl_one_book import ONE_BOOK_SQL


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


def test_an_actual_close_on_an_existing_book_keeps_only_that_months_actuals() -> None:
    from app.services.demo_csv.loader import gl_payloads_for_close

    rows = [
        {"period": "2026-06", "version": "Actual"},
        {"period": "2026-07", "version": "Forecast"},
        {"period": "2026-07", "version": "Actual"},
    ]
    kept = gl_payloads_for_close(
        rows,
        as_of_period="2026-07",
        earlier_book=True,
        version_hint="Actual",
    )
    assert kept == [{"period": "2026-07", "version": "Actual"}]


def test_the_first_actual_file_keeps_history_and_drops_forecast_rows() -> None:
    from app.services.demo_csv.loader import gl_payloads_for_close

    rows = [
        {"period": "2026-06", "version": "Actual"},
        {"period": "2026-07", "version": "Forecast"},
    ]
    kept = gl_payloads_for_close(
        rows,
        as_of_period="2026-07",
        earlier_book=False,
        version_hint="Actual",
    )
    assert kept == [{"period": "2026-06", "version": "Actual"}]


def test_statement_read_keeps_an_unnamed_book() -> None:
    assert ONE_BOOK_SQL.lstrip().startswith("( load_name is null") or ONE_BOOK_SQL.lstrip().startswith("(\n  load_name is null")
