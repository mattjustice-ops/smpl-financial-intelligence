"""Strict validation gates for promote, board, export, and commentary."""

from __future__ import annotations

from fastapi import HTTPException

from app.services.reporting.export.schemas import ExportValidationSummary


def validation_blocked(summary: ExportValidationSummary, *, strict: bool = True) -> bool:
    if summary.failed_count > 0:
        return True
    if strict and summary.warning_count > 0:
        return True
    return summary.status == "fail"


def raise_if_validation_blocked(
    summary: ExportValidationSummary,
    *,
    action: str,
    strict: bool = True,
) -> None:
    if not validation_blocked(summary, strict=strict):
        return
    raise HTTPException(
        status_code=409,
        detail={
            "code": "validation_blocked",
            "action": action,
            "message": f"{action} blocked: resolve validation issues before continuing.",
            "validation": summary.model_dump(mode="json"),
        },
    )
