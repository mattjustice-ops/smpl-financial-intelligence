"""Unit tests for unified outlook payload helpers."""

from __future__ import annotations

from app.services.reporting.three_statement_payload import (
    _calculate_cfs_row,
    _enrich_is,
    _normalize_bs_display,
    _normalize_mrr_metrics,
    _wf_row_from_mrr,
)


def test_normalize_mrr_metrics_derives_net_new_and_retention() -> None:
    metrics = _normalize_mrr_metrics(
        {
            "arr_bop": 86_100_000.0,
            "arr_nb": 1_200_000.0,
            "arr_exp": 500_000.0,
            "arr_react": 100_000.0,
            "arr_cont": 200_000.0,
            "arr_churn": 300_000.0,
            "arr_eop": 87_400_000.0,
        }
    )

    assert metrics["arr_nn"] == 1_300_000.0
    assert round(metrics["grr"], 4) == round((86_100_000 - 200_000 - 300_000) / 86_100_000, 4)
    assert round(metrics["nrr"], 4) == round((86_100_000 + 1_300_000) / 86_100_000, 4)


def test_build_arr_waterfall_table_uses_actual_through_close() -> None:
    """Actual months through close_month must come from actual_mrr, not forecast."""
    from unittest.mock import MagicMock
    import uuid

    from app.services.reporting.three_statement_payload import build_arr_waterfall_table

    org_id = uuid.uuid4()
    db = MagicMock()

    def fake_read(_db, _org, table_name):
        if table_name == "actual_mrr_waterfall":
            return [
                {
                    "period": "2026-06",
                    "beginning_arr": 83_445_000.0,
                    "new_business_arr": 1_920_000.0,
                    "expansion_arr": 980_000.0,
                    "contraction_arr": 225_000.0,
                    "churn_arr": 115_000.0,
                    "reactivation_arr": 95_000.0,
                    "ending_arr": 86_100_000.0,
                }
            ]
        if table_name == "forecast_mrr_waterfall":
            return [
                {
                    "period": "2026-07",
                    "beginning_arr": 86_100_000.0,
                    "new_business_arr": 1_866_715.0,
                    "expansion_arr": 995_197.0,
                    "contraction_arr": 371_121.0,
                    "churn_arr": 612_563.0,
                    "reactivation_arr": 307_478.0,
                    "ending_arr": 88_076_000.0,
                }
            ]
        return []

    import app.services.reporting.three_statement_payload as payload_mod

    original = payload_mod._read_statement_table
    payload_mod._read_statement_table = fake_read
    try:
        table = build_arr_waterfall_table(
            db,
            org_id,
            as_of="2026-06",
            start_period="2026-01",
            end_period="2026-12",
        )
    finally:
        payload_mod._read_statement_table = original

    assert table["Ending"][5] == 86_100_000.0
    assert table["Ending"][6] == 88_076_000.0
    assert table["Beginning"][5] == 83_445_000.0


def test_wf_row_from_mrr_uses_negative_movement_signs() -> None:
    row = _wf_row_from_mrr(
        {
            "arr_bop": 86_100_000.0,
            "arr_nb": 1_200_000.0,
            "arr_exp": 500_000.0,
            "arr_react": 100_000.0,
            "arr_cont": 200_000.0,
            "arr_churn": 300_000.0,
            "arr_eop": 87_400_000.0,
        }
    )

    assert row["Beginning"] == 86_100_000.0
    assert row["Contraction"] == -200_000.0
    assert row["Churn"] == -300_000.0
    assert row["Ending"] == 87_400_000.0


def test_enrich_is_maps_tax_expense_and_derived_lines() -> None:
    row: dict[str, float | None] = {
        "revenue": 7_350_000.0,
        "gross_profit": 5_145_000.0,
        "sm": 2_499_000.0,
        "rd": 1_176_000.0,
        "ga": 808_500.0,
        "ebitda": 661_500.0,
        "da": 110_250.0,
        "interest": 40_000.0,
        "tax": 102_250.0,
        "net_income": 409_000.0,
    }
    _enrich_is(row)

    assert row["tax"] == 102_250.0
    assert row["op_income"] == 551_250.0
    assert row["pretax"] == 511_250.0


def test_normalize_bs_display_sets_board_aliases_only() -> None:
    row: dict[str, float | None] = {
        "dr": 1_176_000.0,
        "total_liabilities": 4_236_000.0,
        "equity": 51_077_800.0,
    }
    _normalize_bs_display(row)

    assert row["deferred_rev"] == 1_176_000.0
    assert row["total_le"] == 55_313_800.0


def test_bs_field_specs_prefers_short_warehouse_column_names() -> None:
    from app.services.reporting.three_statement_payload import BS_FIELD_SPECS, _period_dict_from_field_specs

    rows = [
        {
            "period": "2026-06",
            "cash": 50_257_902.27,
            "prepaids_and_other_current_assets": "",
            "property_and_equipment_net": None,
            "prepaids_and_other_current": 2_010_000.0,
            "ppe_net": 4_619_250.0,
        }
    ]
    bs = _period_dict_from_field_specs(rows, BS_FIELD_SPECS)["2026-06"]

    assert bs["prepaids"] == 2_010_000.0
    assert bs["prepaids_and_other_current_assets"] == 2_010_000.0
    assert bs["ppe"] == 4_619_250.0
    assert bs["property_and_equipment_net"] == 4_619_250.0


def test_calculate_cfs_row_uses_balance_sheet_deltas() -> None:
    is_row = {"net_income": 409_000.0, "da": 110_250.0, "sbc": 73_500.0}
    prior_bs = {
        "ar": 8_529_083.27,
        "ap": 5_497_518.52,
        "dr": 1_120_000.0,
        "prepaids": 2_025_000.0,
        "ppe": 4_876_500.0,
        "debt": 5_000_000.0,
        "cash": 49_755_808.25,
    }
    bs_row = {
        "ar": 9_065_000.0,
        "ap": 6_048_779.27,
        "dr": 1_176_000.0,
        "prepaids": 2_010_000.0,
        "ppe": 4_619_250.0,
        "debt": 5_000_000.0,
        "cash": 50_257_902.27,
    }

    cfs = _calculate_cfs_row(is_row, bs_row, prior_bs)

    assert cfs["chg_ar"] == -535_916.73
    assert cfs["chg_ap"] == 551_260.75
    assert cfs["chg_dr"] == 56_000.0
    assert cfs["chg_prepaids"] == 15_000.0
    assert cfs["capex"] == -147_000.0
    assert cfs["net_change"] == 502_094.02
    assert cfs["cfo"] == 649_094.02
