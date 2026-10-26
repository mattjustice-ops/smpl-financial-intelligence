"""The source of a number is the records that add up to it."""

import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.reporting.source_trace import build_source_trace

ORG = uuid.uuid4()


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    with Session(engine) as session:
        session.execute(text(
            "create table gl_actuals (organization_id text, version text, period text, account_number text, "
            "account_name text, statement text, statement_category text, category text, account_group text, "
            "department text, expense_type text, vendor_name text, source_record_id text, notes text, amount real)"
        ))
        session.execute(text(
            "create table actual_opportunities (organization_id text, period text, opportunity_id text, "
            "customer_name text, opportunity_type text, stage text, amount_arr text, probability text, owner text)"
        ))
        session.execute(text(
            "create table forecast_opportunities (organization_id text, version text, forecast_period text, "
            "opportunity_id text, customer_name text, opportunity_type text, stage text, amount_arr text, probability text, owner text)"
        ))
        yield session


def _gl(db: Session, number: str, name: str, category: str, vendor: str, amount: float, record: str, *, period: str = "2026-06") -> None:
    db.execute(
        text(
            "insert into gl_actuals values (:org, 'Actual', :period, :number, :name, '', :category, '', '', '', '', :vendor, :record, '', :amount)"
        ),
        {"org": str(ORG), "period": period, "number": number, "name": name, "category": category, "vendor": vendor, "record": record, "amount": amount},
    )


def _deal(db: Session, table: str, period_column: str, period: str, deal_id: str, deal_type: str, arr: str, stage: str, prob: str = "1") -> None:
    version = "" if table == "actual_opportunities" else ", 'Forecast'"
    columns = "organization_id, period" if table == "actual_opportunities" else "organization_id, version, forecast_period"
    db.execute(
        text(
            f"insert into {table} ({columns}, opportunity_id, customer_name, opportunity_type, stage, amount_arr, probability, owner) "
            f"values (:org{version}, :period, :id, :customer, :kind, :stage, :arr, :prob, 'Ada')"
        ),
        {"org": str(ORG), "period": period, "id": deal_id, "customer": deal_id, "kind": deal_type, "stage": stage, "arr": arr, "prob": prob},
    )


def test_a_short_account_lists_the_lines_and_the_vendors(db: Session):
    _gl(db, "6400", "Cloud Hosting", "Cost of Revenue", "Northwind", 80, "je-1")
    _gl(db, "6400", "Cloud Hosting", "Cost of Revenue", "Northwind", 20, "je-2")
    _gl(db, "6400", "Cloud Hosting", "Cost of Revenue", "Fabrikam", 50, "je-3")

    trace = build_source_trace(db, ORG, period="2026-06", close="2026-06", grain="account", account_number="6400")

    assert trace["account_total"] == 150
    assert trace["note"] == "These journal entries total the account."
    assert [row["vendor"] for row in trace["vendors"]] == ["Northwind", "Fabrikam"]
    assert sum(row["amount"] for row in trace["vendors"]) == 150
    assert [row["id"] for row in trace["entries"]] == ["je-1", "je-3", "je-2"]
    assert sum(row["amount"] for row in trace["entries"]) == 150
    assert trace["bookings"] is None


def test_a_long_journal_stays_a_count_until_someone_asks_for_the_lines(db: Session):
    for index in range(30):
        _gl(db, "4000", "Subscription Revenue", "Revenue", "", -10, f"je-{index}")

    hidden = build_source_trace(db, ORG, period="2026-06", close="2026-06", grain="account", account_number="4000")
    shown = build_source_trace(
        db, ORG, period="2026-06", close="2026-06", grain="account", account_number="4000", include_entries=True
    )

    assert hidden["account_total"] == 300
    assert hidden["entries"] is None
    assert hidden["entries_available"] is True
    assert hidden["note"] == "30 journal entries. They total the account."
    assert hidden["vendors"] is None
    assert len(shown["entries"]) == 30
    assert sum(row["amount"] for row in shown["entries"]) == 300


def test_closed_deals_sit_beside_revenue_and_do_not_add_into_it(db: Session):
    _gl(db, "4000", "Subscription Revenue", "Revenue", "", -100, "je-1")
    _deal(db, "actual_opportunities", "period", "2026-06", "Won Co", "New Business", "40", "Closed Won")
    _deal(db, "actual_opportunities", "period", "2026-06", "Lost Co", "New Business", "15", "Closed Lost")

    trace = build_source_trace(db, ORG, period="2026-06", close="2026-06", grain="sub_rev")

    assert trace["account_total"] == 100
    assert trace["bookings"]["total"] == 40
    assert trace["bookings"]["lost_total"] == 15
    assert "not added into this revenue account" in trace["bookings"]["note"]
    assert trace["bookings"]["deals"][0]["customer"] == "Won Co"
    assert trace["bookings"]["lost"][0]["customer"] == "Lost Co"


def test_a_statement_line_opens_to_its_accounts(db: Session):
    _gl(db, "6400", "Cloud Hosting", "Cost of Revenue", "Northwind", 80, "je-1")
    _gl(db, "6500", "Support", "Cost of Revenue", "", 20, "je-2")

    trace = build_source_trace(db, ORG, period="2026-06", close="2026-06", grain="cogs")

    assert [(row["number"], row["amount"]) for row in trace["accounts"]] == [("6400", 80), ("6500", 20)]
    assert trace["account_total"] == 100
    assert trace["entries"] is None
    assert "Open an account" in trace["note"]


def test_a_forecast_month_is_the_pipeline_and_has_no_journal(db: Session):
    _gl(db, "4000", "Subscription Revenue", "Revenue", "", -999, "je-1", period="2026-07")
    _deal(db, "forecast_opportunities", "forecast_period", "2026-07", "Open Co", "New Business", "80", "Proposal", "0.5")

    bookings = build_source_trace(db, ORG, period="2026-07", close="2026-06", grain="opportunities")
    revenue = build_source_trace(db, ORG, period="2026-07", close="2026-06", grain="sub_rev")
    cost = build_source_trace(db, ORG, period="2026-07", close="2026-06", grain="cogs")

    assert bookings["accounts"] is None
    assert bookings["bookings"]["total"] == 40
    assert bookings["bookings"]["deals"][0]["probability"] == 50
    assert "no journal entries" in bookings["note"]
    assert revenue["accounts"] is None
    assert revenue["bookings"]["total"] == 40
    assert "no ledger" in revenue["note"]
    assert cost["bookings"] is None
    assert "no ledger" in cost["note"]


def test_a_waterfall_line_is_only_that_movement(db: Session):
    _deal(db, "actual_opportunities", "period", "2026-06", "Won Co", "New Business", "40", "Closed Won")
    _deal(db, "actual_opportunities", "period", "2026-06", "Lost Co", "New Business", "15", "Closed Lost")
    _deal(db, "actual_opportunities", "period", "2026-06", "Grow Co", "Expansion", "10", "Closed Won")
    _deal(db, "actual_opportunities", "period", "2026-06", "Left Co", "Churn", "8", "Churn")
    _deal(db, "actual_opportunities", "period", "2026-05", "Old Co", "New Business", "99", "Closed Won")

    new_business = build_source_trace(
        db, ORG, period="2026-06", close="2026-06", grain="opportunities", deal_type="New Business"
    )
    churn = build_source_trace(
        db, ORG, period="2026-06", close="2026-06", grain="opportunities", deal_type="Churn"
    )

    assert new_business["accounts"] is None
    assert new_business["bookings"]["deals"] == []
    assert new_business["bookings"]["total"] is None
    assert "not loaded" in new_business["note"]
    assert churn["bookings"]["total"] == -8
    assert "reduction in ARR" in churn["note"]


def _history(db: Session, table: str, period: str, customer: str, movement: str, line: str, amount: str) -> None:
    db.execute(
        text(
            f"insert into {table} (organization_id, version, period, customer_id, customer_name, movement_type, "
            "waterfall_line, movement_arr, opportunity_id) "
            "values (:org, :version, :period, :customer, :customer, :movement, :line, :amount, :opp)"
        ),
        {
            "org": str(ORG),
            "version": "Forecast" if table.startswith("forecast_") else "Actual",
            "period": period,
            "customer": customer,
            "movement": movement,
            "line": line,
            "amount": amount,
            "opp": customer,
        },
    )


def test_new_business_is_every_first_year_movement(db: Session):
    db.execute(text(
        "create table actual_customer_arr_history (organization_id text, version text, period text, "
        "customer_id text, customer_name text, movement_type text, waterfall_line text, movement_arr text, "
        "opportunity_id text)"
    ))
    _history(db, "actual_customer_arr_history", "2026-06", "Won Co", "New Business", "new_logo", "40")
    _history(db, "actual_customer_arr_history", "2026-06", "Back Co", "Reactivation", "winback", "10")
    _history(db, "actual_customer_arr_history", "2026-06", "Grow Co", "Expansion", "first_year_expansion", "5")
    _history(db, "actual_customer_arr_history", "2026-06", "Shrink Co", "Contraction", "first_year_contraction", "-3")
    _history(db, "actual_customer_arr_history", "2026-06", "Gone Co", "Churn", "no_start", "2")
    _history(db, "actual_customer_arr_history", "2026-06", "Later Co", "Expansion", "expansion", "99")
    _history(db, "actual_customer_arr_history", "2026-05", "Old Co", "New Business", "new_logo", "77")
    _deal(db, "actual_opportunities", "period", "2026-06", "Crm Co", "New Business", "999", "Closed Won")

    trace = build_source_trace(
        db, ORG, period="2026-06", close="2026-06", grain="opportunities", deal_type="New Business"
    )

    assert [(row["customer"], row["type"], row["stage"], row["amount"]) for row in trace["bookings"]["deals"]] == [
        ("Won Co", "New Logo", "New Business", 40),
        ("Back Co", "Winback", "Reactivation", 10),
        ("Grow Co", "First-Year Expansion", "Expansion", 5),
        ("Shrink Co", "First-Year Contraction", "Contraction", -3),
        ("Gone Co", "No-Start", "Churn", -2),
    ]
    assert trace["bookings"]["total"] == 50
    assert "winback" in trace["note"]
    assert "reduce" in trace["note"]

    other_month = build_source_trace(
        db, ORG, period="2026-07", close="2026-07", grain="opportunities", deal_type="New Business"
    )
    assert other_month["bookings"]["deals"] == []
    assert other_month["bookings"]["total"] == 0
    assert "No new business customer movements" in other_month["note"]


def test_a_first_year_expansion_is_listed_only_under_new_business(db: Session):
    db.execute(text(
        "create table actual_customer_arr_history (organization_id text, version text, period text, "
        "customer_id text, customer_name text, movement_type text, waterfall_line text, movement_arr text, "
        "opportunity_id text)"
    ))
    _history(db, "actual_customer_arr_history", "2026-06", "BlueRiver Legal", "Expansion", "first_year_expansion", "23281.66")
    _history(db, "actual_customer_arr_history", "2026-06", "Apex Works", "Expansion", "first_year_expansion", "16591.71")
    _history(db, "actual_customer_arr_history", "2026-06", "Kept Co", "Expansion", "expansion", "100")
    _history(db, "actual_customer_arr_history", "2026-06", "Back Co", "Reactivation", "winback", "10")
    _history(db, "actual_customer_arr_history", "2026-06", "Returned Co", "Reactivation", "reactivation", "7")
    _deal(db, "actual_opportunities", "period", "2026-06", "BlueRiver Legal", "Expansion", "23281.66", "Closed Won")
    _deal(db, "actual_opportunities", "period", "2026-06", "Apex Works", "Expansion", "16591.71", "Closed Won")
    _deal(db, "actual_opportunities", "period", "2026-06", "Kept Co", "Expansion", "100", "Closed Won")

    new_business = build_source_trace(
        db, ORG, period="2026-06", close="2026-06", grain="opportunities", deal_type="New Business"
    )
    expansion = build_source_trace(
        db, ORG, period="2026-06", close="2026-06", grain="opportunities", deal_type="Expansion"
    )
    reactivation = build_source_trace(
        db, ORG, period="2026-06", close="2026-06", grain="opportunities", deal_type="Reactivation"
    )

    assert [row["customer"] for row in new_business["bookings"]["deals"]] == ["Back Co", "BlueRiver Legal", "Apex Works"]
    assert new_business["bookings"]["total"] == 39883.37
    assert [(row["customer"], row["amount"]) for row in expansion["bookings"]["deals"]] == [("Kept Co", 100)]
    assert "not listed here" in expansion["note"]
    assert [(row["customer"], row["amount"]) for row in reactivation["bookings"]["deals"]] == [("Returned Co", 7)]
    assert "winback" in reactivation["note"]


def test_forecast_new_business_uses_loaded_movements(db: Session):
    db.execute(text(
        "create table forecast_customer_arr_history (organization_id text, version text, period text, "
        "customer_id text, customer_name text, movement_type text, waterfall_line text, movement_arr text, "
        "opportunity_id text)"
    ))
    _history(db, "forecast_customer_arr_history", "2026-07", "Back Co", "Reactivation", "winback", "12")
    _deal(db, "forecast_opportunities", "forecast_period", "2026-07", "Open Co", "New Business", "80", "Proposal", "0.5")

    trace = build_source_trace(
        db, ORG, period="2026-07", close="2026-06", grain="opportunities", deal_type="New Business"
    )

    assert trace["bookings"]["total"] == 12
    assert trace["bookings"]["deals"][0]["type"] == "Winback"
    assert "has not closed" in trace["note"]


def test_forecast_new_business_stays_the_pipeline_until_movements_are_loaded(db: Session):
    _deal(db, "forecast_opportunities", "forecast_period", "2026-07", "Open Co", "New Business", "80", "Proposal", "0.5")

    trace = build_source_trace(
        db, ORG, period="2026-07", close="2026-06", grain="opportunities", deal_type="New Business"
    )

    assert trace["bookings"]["total"] == 40
    assert trace["bookings"]["deals"][0]["customer"] == "Open Co"


def test_a_forecast_waterfall_line_is_the_open_pipeline_for_that_movement(db: Session):
    _deal(db, "forecast_opportunities", "forecast_period", "2026-07", "Open Co", "Churn", "80", "Renewal", "0.5")
    _deal(db, "forecast_opportunities", "forecast_period", "2026-07", "Other Co", "Expansion", "20", "Proposal", "1")

    trace = build_source_trace(
        db, ORG, period="2026-07", close="2026-06", grain="opportunities", deal_type="Churn"
    )

    assert trace["accounts"] is None
    assert trace["bookings"]["total"] == -40
    assert trace["bookings"]["deals"][0]["customer"] == "Open Co"
    assert "no journal entries" in trace["note"]


def test_the_rest_of_a_movement_stays_available_past_the_first_page(db: Session):
    for index in range(3):
        _deal(db, "actual_opportunities", "period", "2026-06", f"Co {index}", "Expansion", str(10 + index), "Closed Won")

    trace = build_source_trace(
        db, ORG, period="2026-06", close="2026-06", grain="opportunities", deal_type="Expansion", deal_offset=2
    )

    assert trace["bookings"]["deal_count"] == 3
    assert trace["bookings"]["total"] == 33
    assert len(trace["bookings"]["deals"]) == 1


def test_actual_bookings_keep_lost_deals_out_of_the_total(db: Session):
    _deal(db, "actual_opportunities", "period", "2026-06", "Won Co", "Expansion", "25", "Closed Won")
    _deal(db, "actual_opportunities", "period", "2026-06", "Lost Co", "New Business", "70", "Closed Lost")

    trace = build_source_trace(db, ORG, period="2026-06", close="2026-06", grain="opportunities")

    assert trace["bookings"]["total"] == 25
    assert trace["bookings"]["lost_total"] == 70
    assert "Recognized revenue is the ledger" in trace["note"]
