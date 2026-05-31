"""Orchestrate financial statement generation from gl_actuals."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.services.financial_statements.engine import build_financial_statements
from app.services.financial_statements.repository import fetch_gl_rows
from app.services.financial_statements.schemas import FinancialStatementsPackage


def run_financial_statements(
    session: Session,
    organization_id: uuid.UUID,
    *,
    period_start: date,
    period_end: date,
    subsidiary: Optional[str] = None,
    version: str = "Actual",
) -> FinancialStatementsPackage:
    """Build income statement, balance sheet, and cash flow for the org and period."""
    rows = fetch_gl_rows(
        session,
        organization_id,
        period_start=period_start,
        period_end=period_end,
        subsidiary=subsidiary,
        version=version,
    )
    return build_financial_statements(
        rows,
        organization_id=organization_id,
        period_start=period_start,
        period_end=period_end,
    )
