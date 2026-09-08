"""The claim verifier soft-strips table cells it cannot match, and it matches on sign.

Every cash-bridge outflow is stored as a positive magnitude, so a deck that writes
payroll as "-$2.47M" finds nothing in the evidence map and the cell is replaced with
an em-dash. That shipped to a board: slide 5 showed blank Payroll / Vendor / Commissions
/ Capex cells while the Key Takeaways beside them -- exempt from stripping -- quoted the
same figures correctly. These tests pin the deterministic restore that runs afterwards.
"""

from app.services.reporting.export.prompt5_deck import (
    _postprocess_prompt5_script,
    _reinject_cash_bridge_rows,
    _reinject_gtm_channel_rows,
)

PAYLOAD = {
    "cash_liquidity": {
        "bridge_table": {
            "columns": ["Line Item", "Actual", "Budget"],
            "rows": [
                {"label": "Beginning cash", "actual": "$29.50M", "budget": "$29.60M"},
                {"label": "Collections", "actual": "$7.13M", "budget": "$8.91M"},
                {"label": "Payroll", "actual": "$2.47M", "budget": "$4.00M"},
                {"label": "Vendor payments", "actual": "$3.66M", "budget": "$1.40M"},
                {"label": "Commissions", "actual": "$199.9K", "budget": "$370.8K"},
                {"label": "Capex", "actual": "$147.0K", "budget": "$220.0K"},
                {"label": "Ending cash", "actual": "$30.00M", "budget": "$27.91M"},
            ],
        }
    },
    "gtm_performance": {
        "channels": [
            {
                "name": "Paid Search",
                "spend": "$85K",
                "spend_budget": "$8K",
                "pipeline": "$470K",
                "mqls": 68.0,
                "efficiency_x": 5.5,
                "win_rate_pct": 30.0,
            },
            {
                "name": "Paid Social",
                "spend": "$59K",
                "spend_budget": "$2K",
                "pipeline": "$323K",
                "mqls": 47.0,
                "efficiency_x": 5.5,
                "win_rate_pct": 30.0,
            },
        ]
    },
}


def test_stripped_bridge_cells_are_restored_in_array_rows():
    script = """
      const bridgeRows = [
        ["Beginning cash", "$29.50M", "$29.60M"],
        ["Collections", "$7.13M", "$8.91M"],
        ["Payroll", "\u2014", "\u2014"],
        ["Vendor payments", "\u2014", "-$1.40M"],
        ["Commissions", "\u2014", "\u2014"],
        ["Capex", "\u2014", "\u2014"],
        ["Ending cash", "$30.00M", "$27.91M"],
      ];
    """
    out = _reinject_cash_bridge_rows(script, PAYLOAD)
    assert '["Payroll", "$2.47M", "$4.00M"]' in out
    assert '["Vendor payments", "$3.66M", "$1.40M"]' in out
    assert '["Commissions", "$199.9K", "$370.8K"]' in out
    assert '["Capex", "$147.0K", "$220.0K"]' in out
    assert "\u2014" not in out, "no bridge cell should remain stripped"


def test_stripped_bridge_cells_are_restored_in_object_rows():
    """The shipped reference script uses the object shape, so it must work too."""
    script = """
      const rows = [
        { label: "Payroll", actual: "\u2014", budget: "\u2014" },
        { label: "Capex", actual: "\u2014", budget: "$220.0K" },
      ];
    """
    out = _reinject_cash_bridge_rows(script, PAYLOAD)
    assert '{ label: "Payroll", actual: "$2.47M", budget: "$4.00M" }' in out
    assert '{ label: "Capex", actual: "$147.0K", budget: "$220.0K" }' in out


def test_negative_outflows_are_normalised_to_the_payload_magnitude():
    """The sign flip is the whole bug: the deck writes -$2.47M, evidence holds +2474745."""
    script = 'const r = [["Payroll", "-$2.47M", "-$4.00M"]];'
    out = _reinject_cash_bridge_rows(script, PAYLOAD)
    assert '["Payroll", "$2.47M", "$4.00M"]' in out
    assert "-$2.47M" not in out


def test_gtm_channel_cells_are_restored():
    script = """
      const gtm = [
        ["Paid Search", "\u2014", "$8.1K", "\u2014", "68", "5.5x", "30.0%"],
        ["Paid Social", "\u2014", "\u2014", "\u2014", "47", "5.5x", "30.0%"],
      ];
    """
    out = _reinject_gtm_channel_rows(script, PAYLOAD)
    assert '["Paid Search", "$85K", "$8K", "$470K", "68", "5.5x", "30.0%"]' in out
    assert '["Paid Social", "$59K", "$2K", "$323K", "47", "5.5x", "30.0%"]' in out


def test_rows_absent_from_the_payload_are_left_alone():
    """Reinjection must not invent cells for a line the payload does not carry."""
    script = 'const r = [["Interest", "\u2014", "\u2014"], ["Payroll", "\u2014", "\u2014"]];'
    out = _reinject_cash_bridge_rows(script, PAYLOAD)
    assert '["Interest", "\u2014", "\u2014"]' in out, "untouched line stays as the deck wrote it"
    assert '["Payroll", "$2.47M", "$4.00M"]' in out


def test_a_genuinely_absent_payload_value_still_renders_as_an_em_dash():
    """json.dumps escapes the dash to \\u2014, which is the same character to JS.

    The two reinjectors that already ship do the same thing, so assert on the rendered
    meaning rather than the byte form.
    """
    payload = {
        "cash_liquidity": {"bridge_table": {"rows": [{"label": "Capex", "actual": None, "budget": None}]}}
    }
    out = _reinject_cash_bridge_rows('const r = [["Capex", "$1.00M", "$2.00M"]];', payload)
    dash = '"\u2014"' if '"\u2014"' in out else '"\\u2014"'
    assert f'["Capex", {dash}, {dash}]' in out
    assert "$1.00M" not in out, "a stale value must not survive a null payload cell"


def test_postprocess_wires_both_restores_in():
    script = """
      const b = [["Payroll", "\u2014", "\u2014"]];
      const g = [["Paid Search", "\u2014", "\u2014", "\u2014", "68", "5.5x", "30.0%"]];
    """
    out = _postprocess_prompt5_script(script, PAYLOAD)
    assert '"$2.47M"' in out and '"$85K"' in out


def test_empty_payload_is_a_no_op():
    script = 'const r = [["Payroll", "\u2014", "\u2014"]];'
    assert _reinject_cash_bridge_rows(script, {}) == script
    assert _reinject_gtm_channel_rows(script, {}) == script
