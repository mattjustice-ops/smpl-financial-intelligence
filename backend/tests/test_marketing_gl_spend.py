"""Marketing spend comes only from the GL program accounts; marketing tables supply volumes."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.services.marketing import service

ORG = uuid.uuid4()


def _gl(amount, name, *, expense_type="Marketing Programs", period="2026-06"):
    return {
        "period": period,
        "statement": "Income Statement",
        "statement_category": "Operating Expense",
        "category": "Operating Expense",
        "account_group": "Marketing Expense",
        "expense_type": expense_type,
        "account_name": name,
        "department": "Marketing",
        "amount": amount,
    }


CHANNEL_ROWS = [
    {"period": "2026-06", "marketing_channel": "Paid Search", "marketing_spend": "40000", "mqls": "100", "sqls": "20", "pipeline_arr_created": "500000", "closed_won_arr": "50000"},
    {"period": "2026-06", "marketing_channel": "Referral", "marketing_spend": "10000", "mqls": "50", "sqls": "10", "pipeline_arr_created": "300000", "closed_won_arr": "100000"},
]
GL_ROWS = [
    _gl(150000.0, "Paid Search"),
    _gl(90000.0, "Events and Webinars"),
    _gl(400000.0, "Base Salaries", expense_type="Salaries and Wages"),
]


@pytest.fixture(autouse=True)
def _sources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "_table_exists", lambda db, name: name == "actual_marketing_pipeline")
    monkeypatch.setattr(service, "_fetch_rows", lambda db, name, org: list(CHANNEL_ROWS) if name == "actual_marketing_pipeline" else [])
    monkeypatch.setattr(service, "fetch_gl_pl_rows", lambda db, org, version: list(GL_ROWS) if version == "Actual" else [])


def test_total_spend_is_gl_program_spend_and_ratios_use_it() -> None:
    resp = service.performance_summary(object(), ORG, scenario="Actual", start_period="2026-06", end_period="2026-06")
    (row,) = resp.rows
    assert row.marketing_spend == Decimal("240000.00")
    assert row.marketing_table_spend == Decimal("50000.00")
    assert row.mqls == Decimal("150")
    assert row.cost_per_mql == Decimal("1600.00")


def test_channel_rows_carry_volumes_only_and_gl_accounts_carry_spend() -> None:
    rows = service.channel_performance(object(), ORG, scenario="Actual", start_period="2026-06", end_period="2026-06").rows
    channels = {r.marketing_channel: r for r in rows if r.row_kind == "channel"}
    accounts = {r.marketing_channel: r for r in rows if r.row_kind == "gl_account"}

    assert set(channels) == {"Paid Search", "Referral"}
    assert all(r.marketing_spend == 0 for r in channels.values())
    assert channels["Paid Search"].pipeline_arr_created == Decimal("500000.00")
    assert {k: r.marketing_spend for k, r in accounts.items()} == {
        "GL: Events and Webinars": Decimal("90000.00"),
        "GL: Paid Search": Decimal("150000.00"),
    }
    assert sum(r.marketing_spend for r in rows) == Decimal("240000.00")


def test_gap_between_marketing_tables_and_gl_is_a_warning() -> None:
    resp = service.performance_summary(object(), ORG, scenario="Actual", start_period="2026-06", end_period="2026-06")
    (gap,) = [c for c in resp.validation if c.validation_name == "marketing_table_spend_vs_gl_program_spend"]
    assert gap.status == "warning"
    assert gap.expected_value == Decimal("240000.00")
    assert gap.actual_value == Decimal("50000.00")
    assert gap.variance == Decimal("-190000.00")


def test_no_gl_program_accounts_means_no_spend_not_table_spend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "fetch_gl_pl_rows", lambda db, org, version: [])
    (row,) = service.performance_summary(object(), ORG, scenario="Actual", start_period="2026-06", end_period="2026-06").rows
    assert row.marketing_spend == 0
    assert row.marketing_table_spend == Decimal("50000.00")
