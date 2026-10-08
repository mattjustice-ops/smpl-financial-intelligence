"""Budget promotion: tie-out checks, budget-year-scoped replace, commission tables."""

from __future__ import annotations

import sqlite3
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.services.budget_version_service as bvs
import app.services.demo_csv.loader as loader
from app.services.budget_promotion_checks import budget_promotion_failures

YEAR = 2027
PERIODS = [f"{YEAR}-{m:02d}" for m in range(1, 13)]


def _valid_tables() -> dict[str, list[dict[str, str]]]:
    """FY2027 tables that tie: NB capitalized over 60 months, renewal expensed, 5% payroll tax expensed."""
    schedule, rollforward, bs, cfs = [], [], [], []
    dc = 1_000_000.0
    for p in PERIODS:
        nb, ren = 15_000.0, 2_000.0
        schedule.append(
            {"period": p, "plan_id": "PLAN-AE-NEW", "commission_base_arr": "100000", "commission_rate": "0.15",
             "commission_payout": str(nb), "capitalize": "Y", "capitalized_amount": str(nb),
             "expensed_amount": "0", "amortization_months": "60"}
        )
        schedule.append(
            {"period": p, "plan_id": "PLAN-RENEWAL", "commission_base_arr": "100000", "commission_rate": "0.02",
             "commission_payout": str(ren), "capitalize": "N", "capitalized_amount": "0",
             "expensed_amount": str(ren), "amortization_months": "0"}
        )
        amort = 20_000.0
        beg, end = dc, dc + nb - amort
        dc = end
        current = 240_000.0
        rollforward.append(
            {"period": p, "beginning_deferred_commissions": str(beg), "capitalized_commissions": str(nb),
             "commission_amortization": str(amort), "ending_deferred_commissions": str(end),
             "current_portion": str(current), "noncurrent_portion": str(end - current),
             "expensed_commissions": str(ren), "total_commission_payouts": str(nb + ren),
             "payroll_tax_on_commissions": str((nb + ren) * 0.05), "amortization_months": "60", "notes": ""}
        )
        bs.append({"period": p, "deferred_commissions_current": str(current),
                   "deferred_commissions_noncurrent": str(end - current)})
        cfs.append({"period": p, "change_in_deferred_commissions": str(beg - end)})
    return {
        "budget_mrr_waterfall": [{"period": p, "ending_arr": "1"} for p in PERIODS],
        "budget_income_statement": [{"period": p, "revenue": "1"} for p in PERIODS],
        "budget_cash_flow_statement": cfs,
        "budget_balance_sheet": bs,
        "budget_bookings_summary": [{"period": p, "new_business_arr": "1"} for p in PERIODS],
        "budget_commission_schedule": schedule,
        "budget_deferred_commissions_rollforward": rollforward,
    }


def _rf(tables, period):
    return next(r for r in tables["budget_deferred_commissions_rollforward"] if r["period"] == period)


def test_valid_tables_pass() -> None:
    assert budget_promotion_failures(_valid_tables(), YEAR) == []


def test_without_commission_tables_core_still_checked() -> None:
    t = _valid_tables()
    del t["budget_commission_schedule"], t["budget_deferred_commissions_rollforward"]
    assert budget_promotion_failures(t, YEAR) == []


def test_requires_budget_year() -> None:
    assert any("no budget year" in f for f in budget_promotion_failures(_valid_tables(), None))


def test_period_outside_budget_year() -> None:
    t = _valid_tables()
    t["budget_income_statement"][0]["period"] = "2026-01"
    failures = budget_promotion_failures(t, YEAR)
    assert any("outside FY2027: 2026-01" in f for f in failures)
    assert any("budget_income_statement: no row for 2027-01" in f for f in failures)


def test_invalid_and_duplicate_periods() -> None:
    t = _valid_tables()
    t["budget_mrr_waterfall"][0]["period"] = "2027-13"
    t["budget_bookings_summary"].append(dict(t["budget_bookings_summary"][0]))
    failures = budget_promotion_failures(t, YEAR)
    assert any("budget_mrr_waterfall: 1 row(s) without a valid period" in f for f in failures)
    assert any("budget_bookings_summary: more than one row for 2027-01" in f for f in failures)


def test_missing_core_table() -> None:
    t = _valid_tables()
    del t["budget_balance_sheet"]
    assert any("budget_balance_sheet is not in the version" in f for f in budget_promotion_failures(t, YEAR))


def test_commission_tables_promoted_together() -> None:
    t = _valid_tables()
    del t["budget_commission_schedule"]
    assert any("promoted together" in f for f in budget_promotion_failures(t, YEAR))


def test_rollforward_must_foot_and_continue() -> None:
    t = _valid_tables()
    _rf(t, "2027-03")["ending_deferred_commissions"] = str(float(_rf(t, "2027-03")["ending_deferred_commissions"]) + 5)
    failures = budget_promotion_failures(t, YEAR)
    assert any("2027-03: beginning + capitalized − amortization ≠ ending" in f for f in failures)
    assert any("2027-03: current + noncurrent ≠ ending" in f for f in failures)
    assert any("2027-04: beginning" in f and "2027-03 ending" in f for f in failures)


def test_rollforward_missing_value() -> None:
    t = _valid_tables()
    _rf(t, "2027-05")["commission_amortization"] = ""
    assert any("2027-05: missing or non-numeric commission_amortization" in f
               for f in budget_promotion_failures(t, YEAR))


def test_schedule_split_and_capitalize_flag() -> None:
    t = _valid_tables()
    t["budget_commission_schedule"][0]["expensed_amount"] = "10"
    t["budget_commission_schedule"][1]["capitalize"] = "Y"
    failures = budget_promotion_failures(t, YEAR)
    assert any("2027-01 PLAN-AE-NEW: capitalized" in f and "≠ payout" in f for f in failures)
    assert any("2027-01 PLAN-RENEWAL: capitalize is Y but" in f for f in failures)


def test_rollforward_ties_to_schedule() -> None:
    t = _valid_tables()
    _rf(t, "2027-02")["expensed_commissions"] = "2500"
    failures = budget_promotion_failures(t, YEAR)
    assert any("2027-02: expensed 2,500.00 ≠ commission schedule expensed 2,000.00" in f for f in failures)


def test_capitalized_may_include_payroll_tax_only() -> None:
    t = _valid_tables()
    rf = _rf(t, "2027-06")
    tax = float(rf["payroll_tax_on_commissions"])
    cap = float(rf["capitalized_commissions"])
    rf["capitalized_commissions"] = str(cap + tax)
    assert not any("2027-06: capitalized" in f for f in budget_promotion_failures(t, YEAR))

    rf["capitalized_commissions"] = str(cap + tax + 1)
    assert any("2027-06: capitalized" in f and "doesn't tie" in f for f in budget_promotion_failures(t, YEAR))


def test_balance_sheet_and_cash_flow_tie_to_rollforward() -> None:
    t = _valid_tables()
    t["budget_balance_sheet"][6]["deferred_commissions_current"] = "1"
    t["budget_cash_flow_statement"][7]["change_in_deferred_commissions"] = "0"
    failures = budget_promotion_failures(t, YEAR)
    assert any("budget_balance_sheet 2027-07: deferred_commissions_current" in f for f in failures)
    assert any("budget_cash_flow_statement 2027-08: change_in_deferred_commissions" in f for f in failures)


@pytest.fixture()
def sqlite_session():
    sqlite3.register_adapter(uuid.UUID, str)
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("create table budget_balance_sheet (organization_id text, period text, cash real)"))
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _periods_left(session, org) -> list[str]:
    return [
        r[0]
        for r in session.execute(
            text("select period from budget_balance_sheet where organization_id = :o order by period"),
            {"o": str(org)},
        )
    ]


def test_period_scoped_delete_keeps_other_budget_years(sqlite_session) -> None:
    org, other = uuid.uuid4(), uuid.uuid4()
    for o in (org, other):
        for p in ("2026-11", "2026-12", "2027-01", "2027-02"):
            sqlite_session.execute(
                text("insert into budget_balance_sheet values (:o, :p, 1)"), {"o": str(o), "p": p}
            )
    loader._delete_org_rows(
        sqlite_session, org, table_name="budget_balance_sheet", replace_periods={"2027-01", "2027-02"}
    )
    assert _periods_left(sqlite_session, org) == ["2026-11", "2026-12"]
    assert len(_periods_left(sqlite_session, other)) == 4

    loader._delete_org_rows(sqlite_session, org, table_name="budget_balance_sheet", replace_periods=set())
    assert _periods_left(sqlite_session, org) == ["2026-11", "2026-12"]

    loader._delete_org_rows(sqlite_session, org, table_name="budget_balance_sheet")
    assert _periods_left(sqlite_session, org) == []
    assert len(_periods_left(sqlite_session, other)) == 4


def test_period_scoped_delete_matches_date_like_periods(sqlite_session) -> None:
    org = uuid.uuid4()
    for p in ("2026-12-01", "2027-01-01"):
        sqlite_session.execute(text("insert into budget_balance_sheet values (:o, :p, 1)"), {"o": str(org), "p": p})
    loader._delete_org_rows(sqlite_session, org, table_name="budget_balance_sheet", replace_periods={"2027-01"})
    assert _periods_left(sqlite_session, org) == ["2026-12-01"]


def _capture_loads(monkeypatch) -> dict[str, dict]:
    captured: dict[str, dict] = {}

    def _capture(session, organization_id, *, table_name, rows, filename=None, replace_periods=None):  # noqa: ANN001
        captured[table_name] = {"rows": rows, "replace_periods": replace_periods, "filename": filename}
        return len(rows)

    monkeypatch.setattr(loader, "load_physical_table_rows", _capture)
    return captured


def test_promote_budget_tables_replaces_only_its_months(monkeypatch) -> None:
    captured = _capture_loads(monkeypatch)
    version_id = uuid.uuid4()
    loaded = loader.promote_budget_tables(
        None,
        uuid.uuid4(),
        tables={
            "budget_balance_sheet": [
                {"period": "2027-01-01", "cash": "1"},
                {"period": "2027-02", "cash": "2", "version": "Actual"},
                {"period": "2027-03", "cash": "3"},
            ],
            "budget_commission_schedule": [{"period": "2027-01", "plan_id": "PLAN-AE-NEW"}],
            "budget_deferred_commissions_rollforward": [{"period": "2027-01"}],
            "budget_gl_detail": [{"period": "2027-01"}],
        },
        budget_version_id=version_id,
        as_of_period="2026-12",
    )
    assert set(loaded) == {
        "budget_balance_sheet", "budget_commission_schedule", "budget_deferred_commissions_rollforward"
    }
    bs = captured["budget_balance_sheet"]
    assert bs["replace_periods"] == {"2027-01", "2027-03"}
    assert [r["period"] for r in bs["rows"]] == ["2027-01", "2027-03"]
    assert all(r["version"] == "Budget" and r["budget_version_id"] == str(version_id) for r in bs["rows"])
    assert captured["budget_commission_schedule"]["filename"] == "Budget_commission_schedule.csv"


def test_promote_budget_tables_rejects_row_without_period(monkeypatch) -> None:
    _capture_loads(monkeypatch)
    with pytest.raises(ValueError, match="budget_income_statement"):
        loader.promote_budget_tables(
            None,
            uuid.uuid4(),
            tables={"budget_income_statement": [{"period": "", "revenue": "1"}]},
            budget_version_id=uuid.uuid4(),
            as_of_period="2026-12",
        )


class _FakeDb:
    def __init__(self) -> None:
        self.committed = False

    def scalars(self, _stmt):  # noqa: ANN001
        return SimpleNamespace(all=lambda: [])

    def add(self, _obj) -> None:  # noqa: ANN001
        pass

    def commit(self) -> None:
        self.committed = True

    def refresh(self, _obj) -> None:  # noqa: ANN001
        pass


def _version(tables) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(), status="draft", budget_year=YEAR, as_of_period="2026-12",
        results={"tables": tables}, promoted_at=None, table_manifest=None,
    )


def _patch_service(monkeypatch, version) -> dict:
    org = SimpleNamespace(id=uuid.uuid4(), active_budget_version_id=None)
    calls: dict = {}
    monkeypatch.setattr(bvs, "require_org_promoter", lambda db, oid: (org, uuid.uuid4()))
    monkeypatch.setattr(bvs, "get_organization_or_404", lambda db, oid: org)
    monkeypatch.setattr(bvs, "get_budget_version", lambda db, oid, vid: version)

    def _promote(db, organization_id, *, tables, budget_version_id, as_of_period, clear_periods):  # noqa: ANN001
        calls["tables"] = tables
        calls["clear_periods"] = clear_periods
        return {k: len(v) for k, v in tables.items()}

    monkeypatch.setattr(bvs, "promote_budget_tables", _promote)
    return calls


def test_promote_budget_version_rejects_tables_that_dont_tie(monkeypatch) -> None:
    tables = _valid_tables()
    _rf(tables, "2027-04")["current_portion"] = "0"
    version = _version(tables)
    calls = _patch_service(monkeypatch, version)
    db = _FakeDb()
    with pytest.raises(HTTPException) as exc:
        bvs.promote_budget_version(db, uuid.uuid4(), version.id)
    assert exc.value.status_code == 422
    assert any("2027-04" in f for f in exc.value.detail["failures"])
    assert "tables" not in calls
    assert not db.committed
    assert version.status == "draft"


def test_promote_budget_version_writes_commission_tables(monkeypatch) -> None:
    version = _version(_valid_tables())
    calls = _patch_service(monkeypatch, version)
    db = _FakeDb()
    bvs.promote_budget_version(db, uuid.uuid4(), version.id)
    assert {"budget_commission_schedule", "budget_deferred_commissions_rollforward"} <= set(calls["tables"])
    assert calls["clear_periods"] == set(PERIODS)
    assert version.status == "final"
    assert db.committed


def test_promote_clears_budget_year_of_tables_the_version_lacks(sqlite_session, monkeypatch) -> None:
    _capture_loads(monkeypatch)
    org = uuid.uuid4()
    sqlite_session.execute(
        text("create table budget_commission_schedule (organization_id text, period text, plan_id text)")
    )
    for p in ("2026-12", "2027-01", "2027-12"):
        sqlite_session.execute(
            text("insert into budget_commission_schedule values (:o, :p, 'PLAN-AE-NEW')"), {"o": str(org), "p": p}
        )
    loader.promote_budget_tables(
        sqlite_session,
        org,
        tables={"budget_balance_sheet": [{"period": p, "cash": "1"} for p in PERIODS]},
        budget_version_id=uuid.uuid4(),
        as_of_period="2026-12",
        clear_periods=set(PERIODS),
    )
    left = sqlite_session.execute(
        text("select period from budget_commission_schedule where organization_id = :o"), {"o": str(org)}
    ).scalars().all()
    assert left == ["2026-12"]
