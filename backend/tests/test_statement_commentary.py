"""Statement commentary: paragraphs that tie, blank detail, and the compensation sentence."""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import openpyxl

from app.services import validation_engine as ve
from app.services.reporting.statement_commentary import (
    build_statement_commentary,
    commentary_workbook,
    missing_review_keys,
    present_commentary,
    text_problem,
)


def _books() -> tuple[dict, dict, list]:
    def row(**values):
        return values

    actual_is = {
        "2026-04": row(revenue=90, cogs=30, gross_profit=60, total_opex=20, da=5, interest=2, tax=3, net_income=30, sm=10, rd=6, ga=4),
        "2026-05": row(revenue=80, cogs=20, gross_profit=60, total_opex=30, da=5, interest=2, tax=3, net_income=20, sm=12, rd=10, ga=8),
        "2026-06": row(revenue=100, cogs=30, gross_profit=70, total_opex=40, da=5, interest=2, tax=3, net_income=20, sm=16, rd=14, ga=10),
    }
    # Q1 is Jan-Mar. One month missing on purpose is not this fixture.
    for period, revenue in (("2026-01", 70), ("2026-02", 75), ("2026-03", 85)):
        actual_is[period] = row(
            revenue=revenue, cogs=20, gross_profit=revenue - 20, total_opex=25, da=5, interest=2, tax=3,
            net_income=revenue - 20 - 25 - 5 - 2 - 3, sm=10, rd=8, ga=7,
        )
    actual_bs = {
        "2026-06": row(cash=30, ar=10, total_assets=80, total_liabilities=40, total_le=80),
        "2026-05": row(cash=28, ar=9, total_assets=76, total_liabilities=38, total_le=76),
    }
    actual_cfs = {
        "2026-06": row(cfo=12, cfi=-4, cff=2, net_change=10, ending_cash=30),
        "2026-05": row(cfo=8, cfi=-2, cff=1, net_change=7, ending_cash=28),
    }
    ts = {
        "Actual": {
            "is": actual_is,
            "bs": actual_bs,
            "cfs": actual_cfs,
            "gl_opex": {
                "2026-06": {"sm|Sales|Salaries": 20_000, "sm|Sales|Travel": 5},
                "2026-05": {"sm|Sales|Salaries": 8_000},
            },
        },
        "Budget": {
            "is": {"2026-06": row(revenue=90, cogs=25, gross_profit=65, total_opex=35, da=5, interest=2, tax=3, net_income=20)},
            "bs": {"2026-06": row(cash=27, total_assets=70, total_liabilities=35, total_le=70)},
            "cfs": {"2026-06": row(cfo=9, cfi=-3, cff=1, net_change=7, ending_cash=27)},
            "gl_opex": {"2026-06": {"sm|Sales|Salaries": 15_000, "ga|Finance|Rent": 1_000}},
        },
        "Forecast": {"is": {}, "bs": {}, "cfs": {}},
    }
    history = {
        "is": {"2025-06": row(revenue=50, cogs=15, gross_profit=35, total_opex=20, da=4, interest=1, tax=2, net_income=8)},
        "bs": {"2025-06": row(cash=10, total_assets=40, total_liabilities=20, total_le=40)},
        "cfs": {"2025-06": row(cfo=4, cfi=-1, cff=0, net_change=3, ending_cash=10)},
    }
    bridge = {
        "id": "mom",
        "available": True,
        "from": {"total": 100},
        "to": {"total": 180},
        "bars": [
            {"id": "hires", "amount": 50},
            {"id": "departures", "amount": -20},
            {"id": "rate", "amount": 10},
            {"id": "reconciling", "amount": 40},
        ],
    }
    return ts, history, [bridge]


def _comparison(package, comparison_id):
    return next(item for item in package["comparisons"] if item["id"] == comparison_id)


def _statement(package, comparison_id, statement_id):
    return next(item for item in _comparison(package, comparison_id)["statements"] if item["id"] == statement_id)


def _line(statement, line_id):
    return next(item for item in statement["lines"] if item["id"] == line_id)


def test_month_story_ties_and_compensation_stays_at_three_parts() -> None:
    ts, history, bridges = _books()
    package = build_statement_commentary(close="2026-06", ts=ts, history=history, labor_bridges=bridges)
    income = _statement(package, "mom", "income_statement")
    assert income["ties"] is True
    compensation = _line(income, "compensation")
    text = compensation["commentary"].lower()
    assert "hires $50.00" in text
    assert "departures -$20.00" in text
    assert "everything else $50.00" in text
    assert "rate" not in text
    assert "mix" not in text
    assert income["paragraph"].endswith(compensation["commentary"])
    overview = _comparison(package, "mom")["overview"]
    assert "Income" not in overview
    assert income["paragraph"] in overview
    assert _statement(package, "mom", "balance_sheet")["paragraph"] in overview
    assert _statement(package, "mom", "cash_flow")["paragraph"] in overview


def test_account_detail_stays_blank_when_the_other_side_is_missing() -> None:
    ts, history, bridges = _books()
    package = build_statement_commentary(close="2026-06", ts=ts, history=history, labor_bridges=bridges)
    income = _statement(package, "mom", "income_statement")
    travel = next(row for row in income["accounts"] if row["label"] == "Travel")
    assert travel["comparison_amount"] is None
    assert travel["variance"] is None
    assert travel["review_required"] is False
    sales = next(row for row in income["departments"] if row["label"] == "Sales")
    assert sales["variance"] is None
    assert sales["commentary"] == "Department comparison is incomplete."
    salaries = next(row for row in income["accounts"] if row["label"] == "Salaries")
    assert salaries["variance"] == 12_000
    assert salaries["review_required"] is True
    yoy = _statement(package, "yoy", "income_statement")
    assert yoy["accounts"] == []
    assert yoy["accounts_note"] == "Account and department detail is not used on this comparison."
    assert _line(yoy, "revenue")["variance"] == 50
    forecast = _comparison(package, "forecast")
    assert forecast["available"] is False
    assert forecast["note"] == "No forecast for June 2026."
    assert forecast["statements"] == []


def test_budget_account_needs_both_sides_and_small_lines_do_not_require_review() -> None:
    ts, history, bridges = _books()
    package = build_statement_commentary(close="2026-06", ts=ts, history=history, labor_bridges=bridges)
    income = _statement(package, "budget", "income_statement")
    rent = next(row for row in income["accounts"] if row["label"] == "Rent")
    assert rent["current"] is None
    assert rent["variance"] is None
    assert rent["commentary"] == "No comparison amount."
    revenue = _line(income, "revenue")
    assert revenue["review_required"] is True
    assert revenue["variance"] == 10
    assert _line(income, "sm")["review_required"] is False


def test_quarter_sums_the_months_and_does_not_invent_accounts() -> None:
    ts, history, bridges = _books()
    package = build_statement_commentary(close="2026-06", ts=ts, history=history, labor_bridges=bridges)
    qoq = _statement(package, "qoq", "income_statement")
    # Q2 revenue 90+80+100 = 270. Q1 70+75+85 = 230.
    assert _line(qoq, "revenue")["variance"] == 40
    assert qoq["accounts"] == []
    assert all(line["id"] != "compensation" for line in qoq["lines"])


def test_missing_quarter_month_is_blank_not_zero() -> None:
    ts, history, bridges = _books()
    del ts["Actual"]["is"]["2026-04"]
    package = build_statement_commentary(close="2026-06", ts=ts, history=history, labor_bridges=bridges)
    revenue = _line(_statement(package, "qoq", "income_statement"), "revenue")
    assert revenue["current"] is None
    assert revenue["variance"] is None
    assert "no comparison" in revenue["commentary"].lower()


def test_broken_net_income_walk_does_not_claim_a_tie() -> None:
    ts, history, bridges = _books()
    ts["Actual"]["is"]["2026-06"]["net_income"] = 99
    package = build_statement_commentary(close="2026-06", ts=ts, history=history, labor_bridges=bridges)
    income = _statement(package, "mom", "income_statement")
    assert income["ties"] is False
    assert "do not equal" in income["tie_note"]


def test_unavailable_bridge_states_the_reason_and_stops() -> None:
    ts, history, _bridges = _books()
    bridges = [{"id": "mom", "available": False, "reason": "No GL compensation for May 2026."}]
    package = build_statement_commentary(close="2026-06", ts=ts, history=history, labor_bridges=bridges)
    compensation = _line(_statement(package, "mom", "income_statement"), "compensation")
    assert compensation["commentary"] == "No GL compensation for May 2026."
    assert "$" not in compensation["commentary"]
    assert compensation["review_required"] is True


def test_edits_flow_into_the_paragraph_and_a_new_number_fails() -> None:
    ts, history, bridges = _books()
    package = build_statement_commentary(close="2026-06", ts=ts, history=history, labor_bridges=bridges)
    revenue = _line(_statement(package, "mom", "income_statement"), "revenue")
    assert text_problem(package, {revenue["key"]: "Revenue rose $20.00."}, {}) is None
    assert text_problem(package, {revenue["key"]: "Revenue rose $7.00."}, {}) == "line_does_not_tie"
    assert text_problem(package, {}, {"mom": "Collections were $123.45."}) == "addition_does_not_tie"
    assert text_problem(package, {}, {"mom": "Revenue rose $20.00."}) is None
    presented = present_commentary(package, {"edits": {revenue["key"]: "Revenue rose $20.00."}})
    paragraph = _statement(presented, "mom", "income_statement")["paragraph"]
    assert "Revenue rose $20.00." in paragraph


def test_workbook_leaves_the_blank_forecast_blank() -> None:
    ts, history, bridges = _books()
    package = build_statement_commentary(close="2026-06", ts=ts, history=history, labor_bridges=bridges)
    raw = commentary_workbook(package, allowed=False)
    book = openpyxl.load_workbook(io.BytesIO(raw))
    assert book["Cover"]["B3"].value == "Not allowed yet"
    assert "Executive summary" in book.sheetnames
    assert "NI walk" in book.sheetnames
    assert "Labor bridge" in book.sheetnames
    assert "Watch list" in book.sheetnames
    forecast = book["Forecast M"]
    assert forecast["A2"].value == "No forecast for June 2026."
    assert forecast["B2"].value is None
    assert forecast["C2"].value is None
    assert forecast["D2"].value is None
    mom = book["MoM"]
    assert isinstance(mom["D3"].value, str) and mom["D3"].value.startswith("=")


def _blob(sections: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        status="COMPLETE",
        sections_json=dict(sections or {"kpis": True}),
        built_at=datetime.now(timezone.utc),
        updated_at=None,
    )


def test_allow_waits_for_the_required_line_reviews() -> None:
    org_id = uuid.uuid4()
    blob = _blob()
    db = MagicMock()
    db.scalars.return_value.first.return_value = blob
    package = {
        "comparisons": [
            {
                "id": "mom",
                "available": True,
                "statements": [
                    {
                        "lines": [
                            {"key": "mom|income_statement|revenue", "review_required": True},
                            {"key": "mom|income_statement|sm", "review_required": False},
                        ],
                        "departments": [],
                        "accounts": [{"key": "mom|income_statement|Sales|Travel", "review_required": False}],
                    }
                ],
            }
        ]
    }
    try:
        ve.record_allow(db, org_id, "2026-06", allowed_by="Owner", commentary_package=package)
        raise AssertionError("allow should wait")
    except ValueError as exc:
        assert str(exc) == "commentary_review_open"
    ve.save_commentary(
        db,
        org_id,
        "2026-06",
        reviews={"mom|income_statement|revenue": True},
        edits={},
        additions={},
        reviewed_by="Owner",
        package=package,
    )
    allowed = ve.record_allow(db, org_id, "2026-06", allowed_by="Owner", commentary_package=package)
    assert allowed["allowed"] is True
    assert missing_review_keys(package, blob.sections_json["commentary"]) == []
