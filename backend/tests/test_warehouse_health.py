"""Tests for customer warehouse health checks."""

from __future__ import annotations

from app.services.ops.warehouse_health import _outlook_hydration_issues


def test_outlook_hydration_rejects_missing_jan_beginning() -> None:
    issues = _outlook_hydration_issues(
        close_month="2026-06",
        start_period="2026-01",
        arr_waterfall={
            "Beginning": [None, None, None, None, None, 83445000.0],
            "Ending": [None, None, None, None, None, 85308020.62],
        },
    )
    assert any("Jan beginning" in issue for issue in issues)


def test_outlook_hydration_accepts_full_year_actuals() -> None:
    issues = _outlook_hydration_issues(
        close_month="2026-06",
        start_period="2026-01",
        arr_waterfall={
            "Beginning": [75000000.0, 76310000.0, 77815000.0, 79505000.0, 81385000.0, 83445000.0],
            "Ending": [76310000.0, 77815000.0, 79505000.0, 81385000.0, 83445000.0, 85308020.62],
        },
    )
    assert issues == []
