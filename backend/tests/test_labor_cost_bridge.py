"""Workforce prints labor facts only from a FINAL company bridge whose heads match."""

from app.services.commentary.labor_cost_bridge import labor_cost_bridge, render_workforce

AUGUST = {
    "status": "FINAL",
    "page_headcount": 79,
    "heads": {"opening": 79, "hires": 3, "departures": 3, "ending": 79},
    "labor_thousands": {"prior": 987.3, "current": 1040.0},
    "bars_thousands": {
        "hires": 38.2,
        "departures": -38.2,
        "mix": 16.4,
        "rate": 7.7,
        "timing": 11.4,
        "benefits": 7.2,
        "one_time": 8.0,
        "reconciling": 2.0,
    },
    "people": {"timing": 2, "one_time": 1, "benefits": 79, "hires": 3, "departures": 3},
    "phrases": {
        "timing": "one severance payment",
        "one_time": "one sign-on bonus",
        "benefits": "the August 1 medical renewal",
    },
    "plan_thousands": {"variance": -68.9, "planned_heads": 85},
    "settings": {"group_key_version": 1, "bar_order_version": 1, "plan_version": "budget", "scope": "company"},
    "departments": [
        {"key": "hires", "amount_thousands": 100.0},
        {"key": "mix", "amount_thousands": 40.0},
    ],
}


def test_august_sample_folds_reconciling_and_hides_private_events():
    evidence = labor_cost_bridge(AUGUST)
    assert evidence["ships"] is True
    assert evidence["status"] == "pass"
    assert evidence["display"]["labor_change"] == "$52.70k"
    assert evidence["display"]["labor_current"] == "$1.04M"
    assert evidence["display"]["labor_prior"] == "$987.30k"
    assert evidence["display"]["plan_gap"] == "−$68.90k"
    assert [bar["key"] for bar in evidence["printed_bars"]] == ["mix", "timing", "one_time", "rate", "benefits"]
    assert [bar["display"] for bar in evidence["printed_bars"]] == ["$16.40k", "$11.40k", "$8.00k", "$7.70k", "$7.20k"]
    assert evidence["folded"] == [{"key": "reconciling", "amount": 2000.0, "display": "$2.00k"}]
    assert evidence["other_items"] == {"amount": 2000.0, "display": "$2.00k"}
    assert evidence["volume_counts"] == {"hires": 3, "departures": 3, "nets": True}
    private = {bar["key"]: bar for bar in evidence["printed_bars"] if bar["privacy"]}
    assert set(private) == {"timing", "one_time"}
    assert private["timing"]["label"] == "partial-month pay for mid-month departures"
    assert private["one_time"]["label"] == "one-time pay"
    assert "people" not in private["timing"] and "people" not in private["one_time"]
    text = render_workforce(evidence, "August", "July")
    assert "one severance payment" not in text
    assert "one sign-on bonus" not in text
    assert text == (
        "Headcount was flat at 79 in August, with 3 hires replacing 3 departures, "
        "but labor cost increased $52.70k from July to $1.04M. "
        "A shift toward higher-cost groups added $16.40k of mix, "
        "and partial-month pay for mid-month departures accounted for $11.40k. "
        "The rest came from one-time pay ($8.00k), pay adjustments ($7.70k), "
        "the August 1 medical renewal ($7.20k) and other items ($2.00k). "
        "Labor came in $68.90k under plan, with 79 heads against 85 planned."
    )
    assert all(check["ok"] for check in evidence["checks"])


def test_provisional_bridge_does_not_ship():
    provisional = {**AUGUST, "status": "PROVISIONAL"}
    evidence = labor_cost_bridge(provisional)
    assert evidence["ships"] is False
    assert evidence["status"] == "withheld"
    assert evidence["reason"] == "bridge is PROVISIONAL"
    assert evidence["printed_bars"] == []
    assert render_workforce(evidence, "August", "July") == ""


def test_headcount_mismatch_does_not_ship():
    mismatch = {**AUGUST, "page_headcount": 222}
    evidence = labor_cost_bridge(mismatch)
    assert evidence["ships"] is False
    assert evidence["reason"] == "bridge heads 79 differ from the page headcount 222"
    assert evidence["printed_bars"] == []
    assert render_workforce(evidence, "June", "May") == ""
