import math
import uuid

import pytest

from app.services.predictive_planning import prior_history
from app.services.predictive_planning.prior_history import _arr_levels, _gtm_series
from app.services.readiness import sales_team_inputs
from app.services.readiness.sales_team_inputs import closer_attrition_by_quarter


def _mrr(bop, eop):
    return {"arr_bop": bop, "arr_eop": eop}


def test_arr_levels_prepend_first_bop_and_stop_at_close():
    mrr = {
        "2025-01": _mrr(100.0, 102.0),
        "2025-02": _mrr(102.0, 104.0),
        "2025-03": _mrr(104.0, 107.0),
        "2025-04": _mrr(107.0, 109.0),
    }
    levels, periods = _arr_levels(mrr, "2025-03")
    assert periods == ["2024-12", "2025-01", "2025-02", "2025-03"]
    assert levels == [100.0, 102.0, 104.0, 107.0]


def test_arr_levels_restart_after_a_gap_or_missing_month_end():
    mrr = {
        "2025-01": _mrr(100.0, 102.0),
        "2025-03": _mrr(104.0, 107.0),
        "2025-04": _mrr(107.0, None),
        "2025-05": _mrr(109.0, 111.0),
        "2025-06": _mrr(111.0, 112.0),
    }
    levels, periods = _arr_levels(mrr, "2025-06")
    assert periods == ["2025-04", "2025-05", "2025-06"]
    assert levels == [109.0, 111.0, 112.0]


def _funnel_row(mqls, pipe, won):
    return {"mqls": mqls, "pipeline_arr_created": pipe, "closed_won_arr": won}


def test_gtm_series_cpl_against_same_month_a_year_earlier():
    funnel = {
        "2024-01": _funnel_row(100, 300.0, 100.0),
        "2025-01": _funnel_row(100, 300.0, 100.0),
        "2025-02": _funnel_row(50, 300.0, 100.0),
    }
    programs = {
        "2024-01": {"Paid": 1000.0},
        "2025-01": {"Paid": 1500.0, "Events": 500.0},
        "2025-02": {"Paid": 1000.0},
    }
    out = _gtm_series(funnel, programs)
    assert out["cpl_periods"] == ["2025-01"]
    assert out["cpl_log_ratios"] == pytest.approx([math.log(20.0 / 10.0)])


def test_gtm_series_skips_months_without_spend_or_mqls():
    funnel = {"2024-01": _funnel_row(0, 1.0, 1.0), "2025-01": _funnel_row(100, 1.0, 1.0)}
    programs = {"2024-01": {"Paid": 1000.0}, "2025-01": {"Paid": 1000.0}}
    assert _gtm_series(funnel, programs)["cpl_log_ratios"] == []
    assert _gtm_series(funnel, {})["cpl_log_ratios"] == []


def test_gtm_series_coverage_needs_all_three_months_of_a_quarter():
    funnel = {
        "2025-01": _funnel_row(1, 300.0, 100.0),
        "2025-02": _funnel_row(1, 200.0, 100.0),
        "2025-03": _funnel_row(1, 400.0, 100.0),
        "2025-04": _funnel_row(1, 300.0, 100.0),
        "2025-05": _funnel_row(1, None, 100.0),
        "2025-06": _funnel_row(1, 300.0, 100.0),
    }
    out = _gtm_series(funnel, {})
    assert out["pipeline_cover_periods"] == ["2025-Q1"]
    assert out["pipeline_cover"] == pytest.approx([3.0])


def test_build_prior_history_without_closed_arr_reads_nothing_else(monkeypatch):
    monkeypatch.setattr(prior_history, "_read_statement_table", lambda *a, **k: [])
    monkeypatch.setattr(prior_history, "_aggregate_mrr_by_period", lambda rows: {})

    def fail(*a, **k):
        raise AssertionError("no closed ARR, nothing else to read")

    monkeypatch.setattr(prior_history, "_scenario_funnel", fail)
    monkeypatch.setattr(prior_history, "closer_attrition_by_quarter", fail)
    history = prior_history.build_prior_history(None, uuid.uuid4(), as_of="2026-06")
    assert history == {"monthly_ending_arr": [], "periods": [], "source": "warehouse"}


def _roster(monkeypatch, employees):
    monkeypatch.setattr(sales_team_inputs, "_rows", lambda db, table, org: employees if table == "forecast_employees" else None)
    monkeypatch.setattr(sales_team_inputs, "_quota_types", lambda db, org, missing: {"AE": "Bookings ARR"})


def _ae(hire, term=""):
    return {"department": "Sales", "role": "AE", "hire_date": hire, "termination_date": term}


def test_closer_attrition_annualises_quarterly_exits(monkeypatch):
    _roster(
        monkeypatch,
        [_ae("2024-01-15"), _ae("2024-01-15"), _ae("2024-01-15"), _ae("2024-01-15", "2024-05-20"),
         {"department": "Sales", "role": "SDR", "hire_date": "2024-01-01", "termination_date": "2024-04-01"}],
    )
    out = closer_attrition_by_quarter(None, uuid.uuid4(), "2024-01", "2024-07")
    assert out["periods"] == ["2024-Q1", "2024-Q2"]
    assert out["pp"][0] == 0.0
    assert out["pp"][1] == pytest.approx(1 / ((4 + 3 + 3) / 3) * 4 * 100)


def test_closer_attrition_starts_at_the_first_full_quarter(monkeypatch):
    _roster(monkeypatch, [_ae("2024-02-01"), _ae("2024-02-01")])
    out = closer_attrition_by_quarter(None, uuid.uuid4(), "2023-01", "2024-12")
    assert out["periods"] == ["2024-Q2", "2024-Q3", "2024-Q4"]


def test_closer_attrition_empty_without_closers(monkeypatch):
    _roster(monkeypatch, [{"department": "Sales", "role": "SDR", "hire_date": "2024-01-01"}])
    assert closer_attrition_by_quarter(None, uuid.uuid4(), "2024-01", "2024-12") == {"periods": [], "pp": []}
