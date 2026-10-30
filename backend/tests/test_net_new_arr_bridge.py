"""The ARR bridge speaks only when both periods foot. Display strings are the reference's."""

import json
from pathlib import Path

from app.services.commentary.net_new_arr_bridge import net_new_arr_bridge, render_fallback

CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "net_new_arr_bridge_tests.json").read_text(encoding="utf-8")
)


def test_bridge_matches_every_reference_case():
    assert [case["test"] for case in CASES] == [
        "T1 June close",
        "T2 partly",
        "T3 largely, larger gain",
        "T4 in line",
        "T5 both help",
        "T6 one side",
        "T7 gain to loss",
        "T8 larger decline",
        "T9 more than, losses up",
        "T10 partly, losses up",
        "T11 reactivation, churn only",
        "T12 nothing material",
        "T13 does not foot",
        "T14 missing input",
    ]
    for case in CASES:
        evidence = net_new_arr_bridge(case["input"])
        expected = case["expected"]
        assert evidence["status"] == expected["status"], case["test"]
        if expected["status"] != "pass":
            assert evidence["reason"] == expected["reason"], case["test"]
            assert render_fallback(evidence) is None
            continue
        assert evidence["facts"]["net_new_arr"] == expected["net_new_arr"], case["test"]
        assert evidence["net_change_frame"]["key"] == expected["frame"], case["test"]
        relationship = evidence["relationship"]
        assert relationship["kind"] == expected["relationship"]["kind"], case["test"]
        assert relationship.get("subtype") == expected["relationship"]["subtype"], case["test"]
        assert relationship.get("order") == expected["relationship"]["order"], case["test"]
        assert relationship.get("words") == expected["relationship"]["words"], case["test"]
        assert evidence["display"] == expected["display"], case["test"]
        assert render_fallback(evidence) == case["fallback_sentence"], case["test"]
