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


def test_verified_requires_complete_freeze() -> None:
    from app.services.reporting.export.validation_labels import apply_freeze_to_trust

    base = ExportValidationSummary(
        status="pass",
        passed_count=2,
        warning_count=0,
        failed_count=0,
        as_of_period="2026-06",
        trust_status="verified",
        trust_label="Verified",
    )
    without_freeze = apply_freeze_to_trust(base, freeze_status="missing")
    assert without_freeze.trust_status == "needs_review"
    assert without_freeze.close_ready_phase1 is False

    with_freeze = apply_freeze_to_trust(base, freeze_status="COMPLETE", freeze_built_at="2026-07-13T12:00:00+00:00")
    assert with_freeze.trust_status == "verified"
    assert with_freeze.close_ready_phase1 is True
    assert with_freeze.freeze_status == "COMPLETE"

    stale = apply_freeze_to_trust(base, freeze_status="STALE")
    assert stale.trust_status == "needs_review"
    assert stale.close_ready_phase1 is False
