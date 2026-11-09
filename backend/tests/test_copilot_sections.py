from app.services.commentary.copilot_sections import (
    COPILOT_SECTION_MISSING,
    assemble_copilot_answer,
    sections_from_model,
    split_copilot_sections,
)


def test_markdown_answer_keeps_three_sections_when_the_middle_is_missing() -> None:
    raw = (
        "##\n"
        "1. Primary Driver + Variance Context\n"
        "Pipeline created in June was $3.68M.\n"
        "## 3. RECOMMENDED ACTION + BOARD SUMMARY "
        "Cash remains strong at $30.00M (ts.Actual.bs.2026-06.cash)."
    )
    primary, cause, action = split_copilot_sections(raw)
    assert "Pipeline created" in primary
    assert cause == ""
    assert "Cash remains" in action
    assert "ts.Actual" not in action

    shown = assemble_copilot_answer(primary, cause, action)
    assert shown.count("1. Primary Driver + Variance Context") == 1
    assert "2. Financial and Operational Root Cause" in shown
    assert COPILOT_SECTION_MISSING in shown
    assert "3. Recommended Action + Board Summary" in shown
    assert "##" not in shown


def test_json_fields_win_over_a_single_answer_string() -> None:
    primary, cause, action = sections_from_model(
        {
            "answer": "1. Primary Driver + Variance Context\nignored",
            "primary_driver": "New business was the variance.",
            "root_cause": "Win rate fell.",
            "recommended_action": "Review pipeline coverage.",
        }
    )
    assert primary.startswith("New business")
    assert cause.startswith("Win rate")
    assert action.startswith("Review pipeline")
