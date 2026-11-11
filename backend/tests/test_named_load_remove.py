"""Named close-load removal stays on one load and never touches Budget or Forecast."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.services.close_context.named_load_remove import (
    apply_load_stamp,
    removal_statements,
    remove_named_load,
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
