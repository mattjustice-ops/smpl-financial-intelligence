"""Tests for plain-language validation labels (Close Peak §6c)."""

from __future__ import annotations

from decimal import Decimal

from app.services.reporting.export.schemas import ExportValidationSummary
from app.services.reporting.export.validation_labels import (
    apply_customer_validation_labels,
    customer_label_for,
)
from app.services.reporting.validation_service import ValidationCheck


def test_known_check_has_customer_label() -> None:
    title, detail = customer_label_for("cash_bridge_ending_cash_ties_balance_sheet_cash")
    assert "balance sheet" in title.lower() or "balance sheet" in detail.lower()
    assert detail


def test_unknown_check_gets_readable_fallback() -> None:
    title, detail = customer_label_for("some_future_internal_check")
    assert "some future internal check" in title.lower()
    assert detail


def test_apply_customer_validation_labels_enriches_summary() -> None:
    summary = ExportValidationSummary(
        status="warning",
        passed_count=1,
        warning_count=1,
        failed_count=0,
        checks=[
            ValidationCheck(
                scenario="Actual",
                period="2026-06",
                validation_name="arr_waterfall_ties",
                status="pass",
                expected_value=Decimal("1"),
                actual_value=Decimal("1"),
                variance=Decimal("0"),
            ),
            ValidationCheck(
                scenario="Actual",
                period="2026-06",
                validation_name="cash_collections_missing",
                status="warning",
            ),
        ],
    )
    enriched = apply_customer_validation_labels(summary, as_of_period="2026-06")
    assert enriched.as_of_period == "2026-06"
    assert enriched.trust_status == "needs_review"
    assert enriched.trust_label == "Needs review"
    assert enriched.checks[0].customer_label
    assert "ARR" in (enriched.checks[0].customer_label or "")
    assert enriched.checks[1].customer_label
