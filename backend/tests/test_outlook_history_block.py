"""Outlook HISTORY / FUNNEL blocks and retention calculated from loaded ARR movements."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import app.services.reporting.three_statement_payload as payload_mod
from app.services.reporting.three_statement_payload import _normalize_mrr_metrics

ORG = uuid.uuid4()


def test_normalize_mrr_metrics_ignores_loaded_rates() -> None:
    metrics = _normalize_mrr_metrics(
        {
            "arr_bop": 86_100_000.0,
            "arr_nb": 1_920_000.0,
            "arr_exp": 980_000.0,
            "arr_react": 95_000.0,
            "arr_cont": 225_000.0,
            "arr_churn": 115_000.0,
            "arr_eop": 88_755_000.0,
            "grr": 0.95,
            "nrr": 1.20,
        }
    )

    assert metrics["grr"] == (86_100_000 - 225_000 - 115_000) / 86_100_000
    assert metrics["nrr"] == (86_100_000 + 980_000 + 95_000 - 225_000 - 115_000) / 86_100_000


def test_normalize_mrr_metrics_leaves_rate_missing_without_components() -> None:
    metrics = _normalize_mrr_metrics({"arr_bop": 86_100_000.0, "arr_cont": 225_000.0, "grr": 0.99})

    assert metrics["grr"] is None
    assert metrics["nrr"] is None


def test_scenario_funnel_sums_loaded_fields_after_close(monkeypatch) -> None:
    rows = [
        ("Forecast", "2026-06", "forecast_marketing_pipeline", {"mqls": 400}),
        ("Forecast", "2026-07", "forecast_marketing_pipeline", {"mqls": 100, "expected_closed_won_arr": 50_000}),
        ("Forecast", "2026-07", "forecast_marketing_pipeline", {"mqls": "50", "closed_won_arr": ""}),
    ]
    monkeypatch.setattr(
        "app.services.dashboard.query_utils.fetch_scenario_rows",
        lambda *a, **k: iter(rows),
    )

    out = payload_mod._scenario_funnel(MagicMock(), ORG, "Forecast", "2026-01", "2026-12", after="2026-06")

    assert out == {"2026-07": {"mqls": 150.0, "closed_won_arr": 50_000.0}}


def test_build_history_block_covers_two_prior_fiscal_years(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_ts(_db, _org, *, as_of, start_period, end_period, only):
        captured.update(as_of=as_of, start=start_period, end=end_period, only=only)
        return {"Actual": {"is": {"2025-12": {"revenue": 7_000_000.0}}, "gl_programs": {"2025-12": {"x": 1.0}}}}

    def fake_read(_db, _org, table_name):
        assert table_name == "actual_mrr_waterfall"
        return [
            {
                "period": "2025-12",
                "beginning_arr": 80_000_000.0,
                "new_business_arr": 1_000_000.0,
                "expansion_arr": 500_000.0,
                "reactivation_arr": 0.0,
                "contraction_arr": 200_000.0,
                "churn_arr": 600_000.0,
                "ending_arr": 80_700_000.0,
                "gross_retention_rate": 0.5,
            },
            {"period": "2023-12", "beginning_arr": 1.0, "ending_arr": 1.0},
        ]

    monkeypatch.setattr(payload_mod, "build_ts_data", fake_ts)
    monkeypatch.setattr(payload_mod, "_read_statement_table", fake_read)
    monkeypatch.setattr(payload_mod, "_scenario_funnel", lambda *a, **k: {"2025-12": {"mqls": 900.0}})
    monkeypatch.setattr(
        "app.services.reporting.board_workforce.history_heads",
        lambda _db, _org, periods: {periods[-1]: 410},
    )

    block = payload_mod.build_history_block(MagicMock(), ORG, start_period="2026-01")

    assert block["start_period"] == "2024-01"
    assert block["end_period"] == "2025-12"
    assert len(block["periods"]) == 24
    assert captured == {"as_of": "2025-12", "start": "2024-01", "end": "2025-12", "only": ("Actual",)}
    assert list(block["arr"]) == ["2025-12"]
    assert block["arr"]["2025-12"]["grr"] == (80_000_000 - 200_000 - 600_000) / 80_000_000
    assert block["arr"]["2025-12"]["arr_nn"] == 700_000.0
    assert block["is"]["2025-12"]["revenue"] == 7_000_000.0
    assert block["funnel"] == {"2025-12": {"mqls": 900.0}}
    assert block["heads"] == {"2025-12": 410}
    assert block["bs"] == {} and block["cfs"] == {}
