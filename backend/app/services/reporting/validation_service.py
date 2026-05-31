"""Centralized reusable validation result types and helpers."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class ValidationCheck(BaseModel):
    scenario: str
    period: str
    validation_name: str
    status: Literal["pass", "warning", "fail"]
    expected_value: Decimal | None = None
    actual_value: Decimal | None = None
    variance: Decimal | None = None
    source_tables_used: list[str] = Field(default_factory=list)


def compare_values(
    *,
    scenario: str,
    period: str,
    validation_name: str,
    expected_value: Decimal,
    actual_value: Decimal,
    source_tables_used: list[str],
    tolerance: Decimal = Decimal("1.00"),
) -> ValidationCheck:
    variance = actual_value - expected_value
    return ValidationCheck(
        scenario=scenario,
        period=period,
        validation_name=validation_name,
        status="pass" if abs(variance) <= tolerance else "fail",
        expected_value=expected_value,
        actual_value=actual_value,
        variance=variance,
        source_tables_used=source_tables_used,
    )


def warning(
    *,
    scenario: str,
    period: str,
    validation_name: str,
    source_tables_used: list[str],
    actual_value: Decimal | None = None,
) -> ValidationCheck:
    return ValidationCheck(
        scenario=scenario,
        period=period,
        validation_name=validation_name,
        status="warning",
        actual_value=actual_value,
        source_tables_used=source_tables_used,
    )
