"""Budget promotion: tie-out checks, budget-year-scoped replace, commission tables."""

from __future__ import annotations

import sqlite3
import uuid

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
        conn.execute(text(
            "create table budget_balance_sheet "
            "(organization_id text, budget_version_id text, period text, cash real)"
        ))
        conn.execute(text(
            "create table budget_versions "
            "(id text, organization_id text, status text, budget_year integer)"
        ))
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _insert_bs(session, org, version_id, period, cash) -> None:  # noqa: ANN001
    session.execute(
        text("insert into budget_balance_sheet values (:o, :v, :p, :c)"),
        {"o": str(org), "v": version_id, "p": period, "c": cash},
    )


def _insert_version(session, org, version_id, status, year) -> None:  # noqa: ANN001
    session.execute(
        text("insert into budget_versions values (:id, :o, :s, :y)"),
        {"id": version_id, "o": str(org), "s": status, "y": year},
    )


def test_promotion_delete_touches_only_its_own_version(sqlite_session) -> None:
    org, other_org = uuid.uuid4(), uuid.uuid4()
    v1, v2 = str(uuid.uuid4()), str(uuid.uuid4())
    for o in (org, other_org):
        _insert_bs(sqlite_session, o, None, "2026-12", 1)
        _insert_bs(sqlite_session, o, v1, "2027-01", 2)
        _insert_bs(sqlite_session, o, v2, "2027-01", 3)
    loader._delete_org_rows(sqlite_session, org, table_name="budget_balance_sheet", replace_budget_version_id=v2)
    left = sqlite_session.execute(
        text("select coalesce(budget_version_id, 'loaded') from budget_balance_sheet where organization_id = :o"),
        {"o": str(org)},
    ).scalars().all()
    assert sorted(left) == sorted(["loaded", v1])
    assert sqlite_session.execute(
        text("select count(*) from budget_balance_sheet where organization_id = :o"), {"o": str(other_org)}
    ).scalar() == 3


def test_reporting_reads_each_years_final_and_loaded_budget_otherwise(sqlite_session) -> None:
    from app.services.dashboard.query_utils import fetch_table_rows

    org = uuid.uuid4()
    superseded, final, draft = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    _insert_version(sqlite_session, org, superseded, "superseded", 2027)
    _insert_version(sqlite_session, org, final, "final", 2027)
    _insert_version(sqlite_session, org, draft, "draft", 2027)
    _insert_bs(sqlite_session, org, None, "2026-12", 26)
    _insert_bs(sqlite_session, org, None, "2027-01", 99)
    _insert_bs(sqlite_session, org, superseded, "2027-01", 1)
    _insert_bs(sqlite_session, org, final, "2027-01", 2)
    _insert_bs(sqlite_session, org, draft, "2027-01", 3)

    rows = fetch_table_rows(sqlite_session, "budget_balance_sheet", org)
    assert sorted((r["period"], r["cash"]) for r in rows) == [("2026-12", 26), ("2027-01", 2)]

    sqlite_session.execute(text("update budget_versions set status = 'superseded' where id = :id"), {"id": final})
    rows = fetch_table_rows(sqlite_session, "budget_balance_sheet", org)
    assert sorted((r["period"], r["cash"]) for r in rows) == [("2026-12", 26), ("2027-01", 99)]


def _capture_loads(monkeypatch) -> dict[str, dict]:
    captured: dict[str, dict] = {}

    def _capture(session, organization_id, *, table_name, rows, filename=None, replace_budget_version_id=None):  # noqa: ANN001
        captured[table_name] = {"rows": rows, "replace": replace_budget_version_id, "filename": filename}
        return len(rows)

    monkeypatch.setattr(loader, "load_physical_table_rows", _capture)
    return captured


def test_promote_budget_tables_stamps_rows_and_replaces_only_this_version(monkeypatch) -> None:
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
    assert bs["replace"] == str(version_id)
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


@pytest.fixture()
def orm_session():
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    from sqlalchemy.ext.compiler import compiles

    from app.db.base import Base
    from app.models.budget_version import BudgetVersion
    from app.models.organization import Organization

    @compiles(JSONB, "sqlite")
    def _compile_jsonb_sqlite(_type, compiler, **kw):  # noqa: ANN001
        return compiler.visit_JSON(_type, **kw)

    @compiles(PG_UUID, "sqlite")
    def _compile_uuid_sqlite(_type, compiler, **kw):  # noqa: ANN001
        return "CHAR(36)"

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Organization.__table__, BudgetVersion.__table__])
    session = sessionmaker(bind=engine)()
    org = Organization(id=uuid.uuid4(), name="Budget Co", status="active", plan="growth")
    session.add(org)
    session.commit()
    yield session, org
    session.close()


def _service_patches(monkeypatch, org) -> dict:  # noqa: ANN001
    calls: dict = {}
    monkeypatch.setattr(bvs, "require_org_promoter", lambda db, oid: (org, None))
    monkeypatch.setattr(bvs, "resolve_org_reporting_window", lambda db, o, as_of_period=None: ("2026-12", None, None))

    def _promote(db, organization_id, *, tables, budget_version_id, as_of_period):  # noqa: ANN001
        calls.setdefault("promoted", []).append(budget_version_id)
        return {k: len(v) for k, v in tables.items()}

    monkeypatch.setattr(bvs, "promote_budget_tables", _promote)
    return calls


def _draft(db, org, name, year=YEAR, tables=None):  # noqa: ANN001
    return bvs.save_budget_draft(
        db, org.id, version_name=name, budget_year=year, tables=tables or _valid_tables()
    )


def test_version_names_must_differ(orm_session, monkeypatch) -> None:
    db, org = orm_session
    _service_patches(monkeypatch, org)
    first = _draft(db, org, "FY2027 Plan A")
    with pytest.raises(HTTPException) as exc:
        _draft(db, org, "  fy2027 plan a ")
    assert exc.value.status_code == 409
    assert "already exists" in exc.value.detail
    again = bvs.save_budget_draft(
        db, org.id, version_name="FY2027 Plan A", budget_year=YEAR, tables=_valid_tables(), version_id=first.id
    )
    assert again.id == first.id
    with pytest.raises(HTTPException) as exc:
        _draft(db, org, "   ")
    assert exc.value.status_code == 422


def test_promotion_keeps_versions_and_supersedes_only_the_same_year(orm_session, monkeypatch) -> None:
    db, org = orm_session
    calls = _service_patches(monkeypatch, org)
    fy27_a = _draft(db, org, "FY2027 Plan A")
    fy27_b = _draft(db, org, "FY2027 Plan B")
    tables_28 = {
        k: [dict(r, period=r["period"].replace("2027", "2028")) for r in rows] for k, rows in _valid_tables().items()
    }
    fy28 = _draft(db, org, "FY2028 Plan", year=2028, tables=tables_28)

    bvs.promote_budget_version(db, org.id, fy27_a.id)
    bvs.promote_budget_version(db, org.id, fy28.id)
    bvs.promote_budget_version(db, org.id, fy27_b.id)

    statuses = {v.version_name: v.status for v in bvs.list_budget_versions(db, org.id)}
    assert statuses == {"FY2027 Plan A": "superseded", "FY2027 Plan B": "final", "FY2028 Plan": "final"}
    assert calls["promoted"] == [fy27_a.id, fy28.id, fy27_b.id]


def test_rejection_says_how_to_fix_and_writes_nothing(orm_session, monkeypatch) -> None:
    db, org = orm_session
    calls = _service_patches(monkeypatch, org)
    tables = _valid_tables()
    _rf(tables, "2027-04")["current_portion"] = "0"
    draft = _draft(db, org, "Broken", tables=tables)
    with pytest.raises(HTTPException) as exc:
        bvs.promote_budget_version(db, org.id, draft.id)
    assert exc.value.status_code == 422
    assert any("2027-04" in f for f in exc.value.detail["failures"])
    assert "save a new draft" in exc.value.detail["how_to_fix"]
    assert str(draft.id) in exc.value.detail["how_to_fix"]
    assert "promoted" not in calls
    assert bvs.get_budget_version(db, org.id, draft.id).status == "draft"


