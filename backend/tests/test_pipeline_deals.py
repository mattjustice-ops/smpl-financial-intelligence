import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.reporting.pipeline_deals import build_opp_pipeline, closed_new_business_acv

ORG = uuid.uuid4()
COLUMNS = (
    "organization_id", "period", "opportunity_id", "customer_name", "opportunity_type", "stage",
    "amount_arr", "probability", "segment", "marketing_channel", "owner", "version",
)


def _table(db: Session, name: str, rows: list[dict[str, str]]) -> None:
    db.execute(text(f'create table "{name}" ({", ".join(f"{c} text" for c in COLUMNS)})'))
    for r in rows:
        db.execute(
            text(f'insert into "{name}" ({", ".join(COLUMNS)}) values ({", ".join(":" + c for c in COLUMNS)})'),
            {c: r.get(c, "") for c in COLUMNS} | {"organization_id": str(ORG)},
        )


def _deal(period: str, deal_id: str, deal_type: str, arr: str, prob: str = "1.0", stage: str = "Closed Won", **kw):
    return {"period": period, "opportunity_id": deal_id, "customer_name": deal_id, "opportunity_type": deal_type,
            "stage": stage, "amount_arr": arr, "probability": prob, **kw}


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    with Session(engine) as session:
        yield session


def test_closed_and_open_deals_by_month(db):
    _table(db, "actual_opportunities", [
        _deal("2026-05", "A1", "New Business", "100000"),
        _deal("2026-06", "A2", "New Business", "150000"),
        _deal("2026-06", "A3", "New Business", "130000"),
        _deal("2026-06", "A4", "Churn", "50000", stage="Commit"),
        _deal("2026-07", "A5", "New Business", "999999"),
    ])
    _table(db, "forecast_opportunities", [
        _deal("2026-06", "F0", "New Business", "500000", "0.5", "Proposal", version="Forecast"),
        _deal("2026-07", "F1", "New Business", "200000", "0.8", "Commit", version="Forecast"),
        _deal("2026-07", "F2", "New Business", "100000", "0.35", "Evaluation", version="Forecast"),
        _deal("2026-07", "F3", "Expansion", "40000", "0.5", "Proposal", version="Forecast"),
        _deal("2026-07", "F4", "New Business", "70000", "0.5", "Proposal", version="Actual"),
    ])

    pipe = build_opp_pipeline(db, ORG, as_of="2026-06")

    assert sorted(pipe) == ["2026-05", "2026-06", "2026-07"]
    june = pipe["2026-06"]["New Business"]
    assert (june["count"], june["total"], june["weighted"], june["expected"]) == (2, 280000.0, 280000.0, 2.0)
    assert {d["outcome"] for d in june["deals"]} == {"won"}
    assert pipe["2026-06"]["Churn"]["total"] == 50000.0

    july = pipe["2026-07"]["New Business"]
    assert (july["count"], july["total"], july["weighted"], july["expected"]) == (2, 300000.0, 195000.0, 1.15)
    assert [d["id"] for d in july["deals"]] == ["F1", "F2"]
    assert (july["deals"][0]["prob"], july["deals"][0]["stage"], july["deals"][0]["outcome"]) == (80, "Commit", "open")
    assert pipe["2026-07"]["Expansion"]["weighted"] == 20000.0


def test_acv_is_closed_new_business_average(db):
    _table(db, "actual_opportunities", [
        _deal("2026-05", "A1", "New Business", "100000"),
        _deal("2026-06", "A2", "New Business", "150000"),
        _deal("2026-06", "A3", "Expansion", "900000"),
    ])
    pipe = build_opp_pipeline(db, ORG, as_of="2026-06")
    assert closed_new_business_acv(pipe, as_of="2026-06") == 125000.0


def test_no_deal_tables_gives_empty_pipeline(db):
    assert build_opp_pipeline(db, ORG, as_of="2026-06") == {}
    assert closed_new_business_acv({}, as_of="2026-06") is None
