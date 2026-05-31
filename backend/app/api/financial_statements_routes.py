"""HTTP routes for normalized financial statements."""

from __future__ import annotations

import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.financial_statements.financial_statement_service import (
    NormalizedStatementResponse,
    SummaryResponse,
    ValidationResult,
    statement,
    summary,
)
from app.services.organizations import get_organization_or_404

financial_statements_router = APIRouter(
    prefix="/financial-statements", tags=["financial-statements"]
)


def _validate(start_period: date, end_period: date) -> None:
    if end_period < start_period:
        raise HTTPException(status_code=400, detail="end_period must be >= start_period")


@financial_statements_router.get("/run", response_model=SummaryResponse)
def run_financial_statements_endpoint(
    organization_id: uuid.UUID = Query(..., description="Tenant organization UUID"),
    scenario: str = Query("Combined"),
    start_period: date = Query(..., description="Inclusive start date"),
    end_period: date = Query(..., description="Inclusive end date"),
    db: Session = Depends(get_db),
) -> SummaryResponse:
    get_organization_or_404(db, organization_id)
    _validate(start_period, end_period)
    return summary(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)


@financial_statements_router.get("/income-statement", response_model=NormalizedStatementResponse)
def income_statement_endpoint(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> NormalizedStatementResponse:
    get_organization_or_404(db, organization_id)
    _validate(start_period, end_period)
    return statement(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period, statement_type="income_statement")


@financial_statements_router.get("/balance-sheet", response_model=NormalizedStatementResponse)
def balance_sheet_endpoint(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> NormalizedStatementResponse:
    get_organization_or_404(db, organization_id)
    _validate(start_period, end_period)
    return statement(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period, statement_type="balance_sheet")


@financial_statements_router.get("/cash-flow", response_model=NormalizedStatementResponse)
def cash_flow_endpoint(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> NormalizedStatementResponse:
    get_organization_or_404(db, organization_id)
    _validate(start_period, end_period)
    return statement(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period, statement_type="cash_flow")


@financial_statements_router.get("/summary", response_model=SummaryResponse)
def summary_endpoint(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> SummaryResponse:
    get_organization_or_404(db, organization_id)
    _validate(start_period, end_period)
    return summary(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)


@financial_statements_router.get("/validation", response_model=list[ValidationResult])
def validation_endpoint(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> list[ValidationResult]:
    get_organization_or_404(db, organization_id)
    _validate(start_period, end_period)
    return summary(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period).validation
