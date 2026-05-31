"""Forecast GL detail routing and gl_actuals sync."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.schemas.demo_csv import ForecastGlDetailRow
from app.services.demo_csv.detector import detect_csv_kind
from app.services.demo_csv.loader import _kind_from_filename, _row_to_payload
from app.services.forecast_gl_detail.service import forecast_gl_payload_to_gl_actuals


def test_forecast_gl_detail_filename_kind() -> None:
    assert _kind_from_filename("Forecast_gl_detail.csv") == "forecast_gl_detail"


def test_detects_forecast_gl_detail_headers() -> None:
    headers = [
        "scenario",
        "period",
        "line_type",
        "statement_category",
        "department",
        "sub_department",
        "account_group",
        "expense_type",
        "gl_account",
        "management_view_include",
        "accounting_view_include",
        "sbc_flag",
        "one_time_flag",
        "non_cash_flag",
        "forecast_amount",
        "source",
        "notes",
    ]
    assert detect_csv_kind(headers) == "forecast_gl_detail"


def test_row_to_payload_omits_version_column() -> None:
    row = ForecastGlDetailRow.model_validate(
        {
            "scenario": "Forecast",
            "period": "2026-06",
            "gl_account": "4000 Subscription Revenue",
            "forecast_amount": "100",
        }
    )
    payload = _row_to_payload("forecast_gl_detail", row, version_hint="Forecast")
    assert "version" not in payload
    assert payload["scenario"] == "Forecast"


def test_forecast_gl_payload_maps_account_and_amount() -> None:
    org = uuid.uuid4()
    payload = forecast_gl_payload_to_gl_actuals(
        org,
        {
            "scenario": "Forecast",
            "period": date(2026, 6, 1),
            "line_type": "Revenue",
            "statement_category": "Revenue",
            "department": "Revenue",
            "sub_department": "Revenue",
            "account_group": "Subscription Revenue",
            "expense_type": "Recurring",
            "gl_account": "4000 Subscription Revenue",
            "forecast_amount": Decimal("1000"),
            "management_view_include": "Yes",
            "source": "test",
        },
        row_index=1,
    )
    assert payload["version"] == "Forecast"
    assert payload["account_number"] == "4000"
    assert payload["account_name"] == "Subscription Revenue"
    assert payload["amount"] == Decimal("1000")
    assert payload["source_system"] == "forecast_gl_detail"


def test_gl_warehouse_table_names_include_both_marts() -> None:
    from app.services.forecast_gl_detail.service import GL_WAREHOUSE_TABLE_NAMES

    assert "gl_actuals" in GL_WAREHOUSE_TABLE_NAMES
    assert "forecast_gl_detail" in GL_WAREHOUSE_TABLE_NAMES
