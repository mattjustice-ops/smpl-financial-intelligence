"""Named close-load removal stays on one load and never touches Budget or Forecast."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.services.close_context.named_load_remove import (
    apply_load_stamp,
    list_period_loads,
    parse_load_display_name,
    removal_statements,
    remove_csv_load,
    remove_named_load,
    stamp_csv_period_load,
)


def test_name_removal_is_scoped_to_actual_rows() -> None:
    statements = removal_statements(
        system="NetSuite",
        dataset="General ledger",
        period="2026-06",
        scope="name",
    )
    sql = "\n".join(item[0] for item in statements)
    assert "gl_actuals" in sql
    assert "version = 'Actual'" in sql
    assert "Budget" not in sql
    assert "Forecast" not in sql
    params = statements[-1][1]
    assert params["load_name"] == "NetSuite · General ledger · 2026-06"
    assert params["source_system"] == "NetSuite"
    assert "invoices" not in sql


def test_system_removal_keeps_other_months() -> None:
    statements = removal_statements(
        system="NetSuite",
        dataset=None,
        period="2026-06",
        scope="system",
    )
    joined = "\n".join(item[0] for item in statements)
    assert "invoices" in joined
    assert "gl_actuals" in joined
    assert "version = 'Actual'" in joined
    physical = [params for sql, params in statements if 'delete from "gl_actuals"' in sql][0]
    assert physical["month_like"] == "% · 2026-06"
    assert physical["system_like"] == "NetSuite · %"


def test_unknown_dataset_is_refused() -> None:
    with pytest.raises(ValueError, match="dataset"):
        removal_statements(system="NetSuite", dataset="ARR waterfall", period="2026-06", scope="name")


def test_plan_rows_are_not_stamped() -> None:
    payload = {"version": "Budget", "source_file": "", "source_system": "demo"}
    apply_load_stamp("gl_actuals", payload, load_name="NetSuite · General ledger · 2026-06", source_system="NetSuite")
    assert "load_name" not in payload
    assert payload["source_system"] == "demo"


def test_actual_rows_receive_the_load_name() -> None:
    payload = {"version": "Actual", "source_file": "", "source_system": "demo"}
    apply_load_stamp("gl_actuals", payload, load_name="NetSuite · General ledger · 2026-06", source_system="NetSuite")
    assert payload["load_name"] == "NetSuite · General ledger · 2026-06"
    assert payload["source_file"] == "NetSuite · General ledger · 2026-06"
    assert payload["source_system"] == "NetSuite"


def test_remove_reports_zero_when_nothing_is_tagged() -> None:
    org_id = uuid.uuid4()
    db = MagicMock()
    db.get.return_value = MagicMock(id=org_id)
    result = MagicMock()
    result.rowcount = 0
    db.execute.return_value = result
    db.scalars.return_value.first.return_value = None

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "app.services.close_context.close_workflow_service.record_load_receipt",
            lambda *args, **kwargs: MagicMock(id=uuid.uuid4()),
        )
        patch.setattr("app.services.workspace.pipeline_ledger.record_pipeline_event", lambda *args, **kwargs: None)
        payload = remove_named_load(
            db,
            org_id,
            system="NetSuite",
            dataset="Invoices",
            as_of_period="2026-06",
            scope="name",
        )
    assert payload["deleted_rows"] == 0
    assert "nothing was deleted" in payload["message"]
    executed = [str(call.args[0]) for call in db.execute.call_args_list]
    invoice_sql = [sql for sql in executed if "invoices" in sql]
    assert invoice_sql
    assert all("Budget" not in sql and "Forecast" not in sql for sql in invoice_sql)
    assert any("load_name = :load_name" in sql for sql in invoice_sql)


def test_calculated_rows_are_not_customer_loads() -> None:
    from app.services.close_context.named_load_remove import is_customer_load_name

    assert is_customer_load_name("Compiled · ledger · 2026-07") is False
    assert is_customer_load_name("Compiled · opportunities · 2026-08") is False
    assert is_customer_load_name("CSV · Actual_gl_detail.csv · 2026-07") is True
    assert is_customer_load_name("compiled:subscriptions:2026-07") is False


def test_load_name_parses_june_and_july() -> None:
    assert parse_load_display_name("Campfire · General ledger · 2026-06") == (
        "Campfire",
        "General ledger",
        "2026-06",
    )
    system, dataset, period = parse_load_display_name("CSV · Actual_GL.csv · 2026-07")
    assert system == "CSV"
    assert dataset == "Actual_GL.csv"
    assert period == "2026-07"
    assert parse_load_display_name("unnamed row") is None


def test_period_list_is_empty_without_named_rows() -> None:
    db = MagicMock()
    db.execute.return_value.all.return_value = []
    db.scalars.return_value.all.return_value = []
    db.scalars.return_value.first.return_value = None
    assert list_period_loads(db, uuid.uuid4(), "2026-06") == []


def test_budget_csv_is_not_named_or_removed() -> None:
    db = MagicMock()
    stamped = stamp_csv_period_load(
        db,
        uuid.uuid4(),
        filename="Forecast_gl_detail.csv",
        as_of_period="2026-07",
        csv_kind="gl_actuals",
        applied=1,
        rejected=0,
    )
    assert stamped == {"stamped": False, "load_name": None}
    db.execute.assert_not_called()
    with pytest.raises(ValueError, match="Budget"):
        remove_csv_load(db, uuid.uuid4(), dataset="Budget_gl_detail.csv", as_of_period="2026-06")


def test_csv_remove_deletes_actual_rows_and_leaves_the_close_month() -> None:
    org_id = uuid.uuid4()
    db = MagicMock()
    db.get.return_value = MagicMock(id=org_id)
    db.execute.return_value.rowcount = 4

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "app.services.close_context.named_load_remove._table_flags",
            lambda _db: [
                {
                    "table": "gl_actuals",
                    "load_name": True,
                    "source_filename": False,
                    "source_file": True,
                    "version": True,
                    "updated_at": True,
                    "csv_kind": False,
                }
            ],
        )
        patch.setattr(
            "app.services.close_context.close_workflow_service.record_load_receipt",
            lambda *args, **kwargs: MagicMock(id=uuid.uuid4()),
        )
        patch.setattr("app.services.workspace.pipeline_ledger.record_pipeline_event", lambda *args, **kwargs: None)
        payload = remove_csv_load(db, org_id, dataset="Actual_GL.csv", as_of_period="2026-07")

    executed = [str(call.args[0]) for call in db.execute.call_args_list]
    sql = "\n".join(executed)
    assert "gl_actuals" in sql
    assert "version = 'Actual'" in sql
    assert "close_month" not in sql
    assert "Budget" not in sql
    assert payload["deleted_rows"] == 4
    assert payload["load_name"] == "CSV · Actual_GL.csv · 2026-07"
    assert "close month stays" in payload["message"]
