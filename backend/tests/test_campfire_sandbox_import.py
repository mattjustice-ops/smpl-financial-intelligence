"""Campfire sandbox rows stay on one company and one load name."""

from __future__ import annotations

import uuid

from app.services.campfire.sandbox_import import (
    customer_payloads,
    gl_activity_payloads,
    invoice_payloads,
)


def test_customer_rows_carry_the_load_name() -> None:
    rows, rejected = customer_payloads(
        [{"id": "c1", "name": "Northwind", "status": "active"}, {"id": "", "name": "Missing"}],
        organization_id=uuid.uuid4(),
        load_name="Campfire · Customers · 2026-06",
    )
    assert rejected == 1
    assert rows[0]["customer_id"] == "c1"
    assert rows[0]["load_name"] == "Campfire · Customers · 2026-06"
    assert rows[0]["source_crm"] == "Campfire"


def test_invoice_without_a_loaded_customer_is_skipped() -> None:
    rows, rejected = invoice_payloads(
        [{"id": "inv-1", "client": "c-missing", "total_amount": "10.00"}],
        organization_id=uuid.uuid4(),
        load_name="Campfire · Invoices · 2026-06",
        known_customers=set(),
    )
    assert rows == []
    assert rejected == 1


def test_gl_department_lines_replace_the_total() -> None:
    statement = {
        "income_statement": [
            {
                "account_number": "6000",
                "account_name": "Salaries",
                "hierarchy": ["OPERATING_EXPENSES"],
                "2026-06-01_Total": "100.00",
                "2026-06-01_Research and Development": "100.00",
                "2026-07-01_Total": "50.00",
            }
        ]
    }
    rows = gl_activity_payloads(
        statement,
        organization_id=uuid.uuid4(),
        load_name="Campfire · General ledger · 2026-06",
        month="2026-06",
        subsidiary="Campfire, LLC",
        currency="USD",
    )
    assert len(rows) == 1
    assert rows[0]["department"] == "Research and Development"
    assert rows[0]["version"] == "Actual"
    assert rows[0]["source_system"] == "Campfire"
    assert rows[0]["subsidiary"] == "Campfire, LLC"
    assert str(rows[0]["period"]) == "2026-06-01"
