"""Engine headcount export replaces the rest-of-year total. May and June stay the roster."""

from datetime import date
from decimal import Decimal

from app.services.reporting.board_workforce import apply_engine_plan_after_close
from app.services.demo_csv.loader import PROMOTABLE_BUDGET_TABLES, PROMOTABLE_FORECAST_TABLES
from app.services.workforce.legacy_headcount import LegacyHeadcountSnapshot


def _row(period: date, department: str, ending: int, hires: int, exits: int, source: str = "engine") -> LegacyHeadcountSnapshot:
    return LegacyHeadcountSnapshot(
        period=period,
        department=department,
        headcount_beginning=Decimal(ending - hires + exits),
        new_hires=Decimal(hires),
        attrition=Decimal(exits),
        headcount_ending=Decimal(ending),
        plan_source=source,
    )


def test_engine_plan_replaces_only_open_months() -> None:
    months = [date(2026, m, 1) for m in range(1, 13)]
    roster = [247] * 12
    plan = [
        _row(date(2026, 6, 1), "Sales", 99, 1, 0),
        _row(date(2026, 7, 1), "Sales", 40, 2, 1),
        _row(date(2026, 7, 1), "Marketing", 20, 1, 0),
        _row(date(2026, 7, 1), "Other", 10, 0, 0, source="upload"),
    ]
    total, hires, exits = apply_engine_plan_after_close(roster, plan, months, date(2026, 6, 1))
    assert total[5] == 247
    assert hires[5] is None
    assert total[6] == 60
    assert hires[6] == 3
    assert exits[6] == 1
    assert total[7] == 247


def test_export_tables_are_promotable() -> None:
    for name in (
        "forecast_headcount_plan_upload",
        "forecast_open_requisitions",
        "forecast_opportunities",
        "forecast_pipeline_waterfall",
        "forecast_cash_flow_bridge",
        "forecast_marketing_pipeline",
    ):
        assert name in PROMOTABLE_FORECAST_TABLES
    for name in ("budget_cash_flow_bridge", "budget_headcount_plan", "budget_marketing_pipeline", "budget_commission_schedule"):
        assert name in PROMOTABLE_BUDGET_TABLES
