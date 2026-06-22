"""Tests for board module payload builders."""

from __future__ import annotations

import uuid
from datetime import date

from app.services.reporting.board_modules_payload import (
    _parse_quota_period,
    build_gtm_payload,
    build_sales_payload,
)


class _FakeMappings:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return iter(self._rows)


class _FakeSession:
    def __init__(self, *, regclass: set[str], rows_by_table: dict[str, list[dict]] | None = None):
        self.regclass = regclass
        self.rows_by_table = rows_by_table or {}

    def execute(self, statement, params=None):
        sql = str(statement)
        if "to_regclass" in sql:
            name = (params or {}).get("name", "").replace("public.", "")
            table = name.strip('"')
            return type("R", (), {"scalar": lambda self: table if table in self.regclass else None})()
        if "select * from" in sql:
            table = sql.split('"')[1]
            org_id = (params or {}).get("organization_id")
            rows = [
                row
                for row in self.rows_by_table.get(table, [])
                if str(row.get("organization_id", org_id)) == str(org_id)
            ]
            return _FakeMappings(rows)
        return _FakeMappings([])

    def scalars(self, _statement):
        return type("S", (), {"all": lambda self: []})()


def test_parse_quota_period_variants() -> None:
    assert _parse_quota_period("2026-06", fallback_year=2026) == "2026-06"
    assert _parse_quota_period("Q2-2026", fallback_year=2026) == "2026-06"
    assert _parse_quota_period(date(2026, 3, 1), fallback_year=2026) == "2026-03"


def test_build_gtm_payload_aggregates_channels() -> None:
    org_id = uuid.uuid4()
    db = _FakeSession(
        regclass={"actual_marketing_pipeline"},
        rows_by_table={
            "actual_marketing_pipeline": [
                {
                    "organization_id": str(org_id),
                    "period": "2026-01",
                    "marketing_channel": "Paid Search",
                    "marketing_spend": "100000",
                    "pipeline_arr_created": "250000",
                    "closed_won_arr": "50000",
                    "mqls": "100",
                },
                {
                    "organization_id": str(org_id),
                    "period": "2026-02",
                    "marketing_channel": "Paid Search",
                    "marketing_spend": "50000",
                    "pipeline_arr_created": "150000",
                    "closed_won_arr": "25000",
                    "mqls": "50",
                },
            ]
        },
    )
    payload = build_gtm_payload(
        db,
        org_id,
        start_period="2026-01",
        as_of_period="2026-02",
    )
    assert "Paid Search" in payload
    ch = payload["Paid Search"]
    assert ch["spend"] == 0.15
    assert ch["pipe"] == 0.4
    assert ch["mqls"] == 150


def test_build_sales_payload_monthly_rollups() -> None:
    org_id = uuid.uuid4()
    db = _FakeSession(
        regclass={"actual_sales_quotas", "budget_sales_quotas"},
        rows_by_table={
            "actual_sales_quotas": [
                {
                    "organization_id": str(org_id),
                    "rep_id": "R1",
                    "rep_name": "Rep One",
                    "region": "West",
                    "role": "Account Executive",
                    "quota_period": "2026-01",
                    "quota_arr": "100000",
                    "closed_won_arr_to_date": "90000",
                },
                {
                    "organization_id": str(org_id),
                    "rep_id": "R1",
                    "rep_name": "Rep One",
                    "region": "West",
                    "role": "Account Executive",
                    "quota_period": "2026-02",
                    "quota_arr": "100000",
                    "closed_won_arr_to_date": "95000",
                },
            ],
            "budget_sales_quotas": [
                {
                    "organization_id": str(org_id),
                    "rep_id": "R1",
                    "quota_period": "2026-01",
                    "quota_arr": "110000",
                }
            ],
        },
    )
    payload = build_sales_payload(
        db,
        org_id,
        start_period="2026-01",
        as_of_period="2026-02",
        end_period="2026-12",
    )
    assert payload["monthly"]["2026-01"]["quota"] == 100000.0
    assert payload["monthly"]["2026-01"]["bud_quota"] == 110000.0
    assert payload["monthly"]["2026-02"]["attained"] == 95000.0
    assert payload["regions"]["West"]["ytd_attained"] == 185000.0
    assert len(payload["reps"]) == 1
