"""Tests for board module payload builders."""

from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace

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

    def scalars(self):
        return iter([])


class _FakeSession:
    def __init__(self, *, regclass: set[str], rows_by_table: dict[str, list[dict]] | None = None):
        self.regclass = regclass
        self.rows_by_table = rows_by_table or {}

    def execute(self, statement, params=None):
        sql = str(statement)
        if "to_regclass" in sql:
            name = (params or {}).get("name", "").replace("public.", "")
            table = name.strip('"')
            found = table if table in self.regclass else None
            return type("R", (), {"scalar": lambda _self: found})()
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

    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))


def test_parse_quota_period_variants() -> None:
    assert _parse_quota_period("2026-06") == "2026-06"
    assert _parse_quota_period(date(2026, 3, 1)) == "2026-03"
    assert _parse_quota_period("Mar 2026") == "2026-03"


def test_parse_quota_period_does_not_invent_a_month() -> None:
    assert _parse_quota_period("Q2-2026") is None
    assert _parse_quota_period("2026") is None
    assert _parse_quota_period("June") is None


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
    assert "spend" not in ch and "eff" not in ch, "channel spend is never taken from the marketing tables"
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
    assert payload["regions"]["West"]["close_quota"] == 100000.0
    assert payload["regions"]["West"]["close_attained"] == 95000.0
    assert "budget_fc" not in payload


def _quota_row(org_id, period, *, emp, region, role="Account Executive", quota="100000", attained="90000", annual=None):
    row = {
        "organization_id": str(org_id),
        "employee_id": emp,
        "rep_name": f"Rep {emp}",
        "region": region,
        "role": role,
        "period": period,
        "monthly_quota_arr": quota,
        "quota_attainment_actual_arr": attained,
    }
    if annual is not None:
        row["annual_quota_arr"] = annual
    return row


def _pipe_row(org_id, period, otype, *, beg, created, won, lost, slipped, end, cov):
    return {
        "organization_id": str(org_id),
        "period": period,
        "opportunity_type": otype,
        "beginning_pipeline_arr": beg,
        "new_pipeline_created": created,
        "closed_won_arr": won,
        "closed_lost_arr": lost,
        "slipped_arr": slipped,
        "ending_pipeline_arr": end,
        "pipeline_coverage": cov,
    }


def test_build_sales_payload_uses_loaded_columns_regions_and_flags_missing_close() -> None:
    org_id = uuid.uuid4()
    db = _FakeSession(
        regclass={"actual_sales_quotas"},
        rows_by_table={
            "actual_sales_quotas": [
                _quota_row(org_id, "2026-04", emp="ASALES-1", region="EMEA", annual="1100000"),
                _quota_row(org_id, "2026-05", emp="ASALES-1", region="EMEA", annual="1100000"),
                _quota_row(org_id, "2026-05", emp="ASALES-2", region="Nordics", role="Sales Development Rep", quota="0", attained="0"),
            ]
        },
    )
    payload = build_sales_payload(db, org_id, start_period="2026-01", as_of_period="2026-06", end_period="2026-12")
    assert payload["quota_through"] == "2026-05"
    assert "2026-06" not in payload["monthly"]
    assert payload["monthly"]["2026-05"]["attained"] == 90000.0
    assert payload["monthly"]["2026-05"]["reps"] == 2
    assert set(payload["regions"]) == {"EMEA", "Nordics"}, "regions come from the loaded rows, not a fixed list"
    assert payload["regions"]["EMEA"]["close_quota"] is None, "close-month quota not loaded is flagged, not zero"
    assert payload["regions"]["Nordics"]["ytd_pct"] is None
    reps = {r["id"]: r for r in payload["reps"]}
    assert set(reps) == {"ASALES-1", "ASALES-2"}
    assert reps["ASALES-1"]["annual_q"] == 1100000.0
    assert reps["ASALES-2"]["annual_q"] is None and reps["ASALES-2"]["pct"] is None
    assert reps["ASALES-2"]["region"] == "Nordics"
    assert "Sales Development Rep" in payload["roles"]


def test_build_sales_payload_pipeline_from_loaded_waterfall() -> None:
    org_id = uuid.uuid4()
    db = _FakeSession(
        regclass={"actual_sales_quotas", "actual_pipeline_waterfall", "forecast_pipeline_waterfall"},
        rows_by_table={
            "actual_sales_quotas": [_quota_row(org_id, "2026-06", emp="ASALES-1", region="East")],
            "actual_pipeline_waterfall": [
                _pipe_row(org_id, "2026-06", "New Business", beg="100", created="50", won="20", lost="10", slipped="5", end="115", cov="3"),
                _pipe_row(org_id, "2026-06", "Expansion", beg="40", created="10", won="5", lost="2", slipped="1", end="42", cov="2.4"),
                _pipe_row(org_id, "2026-06", "Churn", beg="9", created="9", won="9", lost="0", slipped="0", end="9", cov="1"),
            ],
            "forecast_pipeline_waterfall": [
                _pipe_row(org_id, "2026-07", "New Business", beg="115", created="60", won="20", lost="10", slipped="5", end="140", cov="3"),
            ],
        },
    )
    payload = build_sales_payload(db, org_id, start_period="2026-01", as_of_period="2026-06", end_period="2026-12")
    june = payload["pipeline"]["2026-06"]
    assert june["ending"] == 157.0, "booking types only; churn rows are not pipeline"
    assert june["created"] == 60.0 and june["beginning"] == 140.0 and june["slipped"] == 6.0
    assert june["coverage"] == 3.0, "coverage is the loaded New Business value, not a computed ratio"
    assert set(june["by_type"]) == {"New Business", "Expansion", "Churn"}
    assert payload["pipeline_types"] == ["New Business", "Expansion"]
    assert payload["pipeline_fc"]["2026-07"]["created"] == 60.0
