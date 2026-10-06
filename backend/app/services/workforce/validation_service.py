"""Workforce operating model validation checks."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.reporting.period_utils import to_period
from app.services.reporting.validation_service import ValidationCheck, warning
from app.services.workforce import integration, service
from app.services.workforce.engine import q_money
from app.services.workforce.schemas import WorkforceValidationResponse


TOLERANCE = Decimal("1.00")


def _period_label(value: date | str) -> str:
    return to_period(value if isinstance(value, date) else str(value))


def run_workforce_validations(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str = "Forecast",
    start_period: date,
    end_period: date,
) -> WorkforceValidationResponse:
    version = integration.normalize_scenario(scenario)
    checks: list[ValidationCheck] = []
    plan = service.build_workforce_plan(
        session,
        organization_id,
        scenario=version,
        start_period=start_period,
        end_period=end_period,
        persist=False,
    )

    for item in plan.validations:
        checks.append(
            ValidationCheck(
                scenario=version,
                period=_period_label(item.period),
                validation_name=item.validation_name,
                status=item.status,
                expected_value=item.expected_value,
                actual_value=item.actual_value,
                variance=item.variance,
                source_tables_used=["workforce_engine"],
                customer_detail=item.message,
            )
        )

    if not integration.workforce_source_present(session, organization_id, scenario=version):
        checks.append(
            warning(
                scenario=version,
                period=_period_label(start_period),
                validation_name="workforce_source_data_missing",
                source_tables_used=[
                    f"{version.lower()}_employees",
                    "workforce_employees",
                    "workforce_open_requisitions",
                    "headcount_plan",
                    "forecast_headcount_plan",
                ],
            )
        )
    else:
        total_people_cost = sum((r.total_people_cost_monthly for r in plan.period_summary), Decimal("0"))
        if total_people_cost <= 0:
            checks.append(
                warning(
                    scenario=version,
                    period=_period_label(start_period),
                    validation_name="workforce_zero_payroll",
                    source_tables_used=["workforce_period_summary"],
                    actual_value=total_people_cost,
                )
            )
        else:
            checks.append(
                ValidationCheck(
                    scenario=version,
                    period=_period_label(start_period),
                    validation_name="workforce_payroll_derived",
                    status="pass",
                    actual_value=total_people_cost,
                    source_tables_used=["gl_actuals"],
                )
            )

    gtm = integration.load_gtm_quota_capacity(
        session,
        organization_id,
        scenario=version,
        start_period=start_period,
        end_period=end_period,
    )
    gtm_source = gtm[0].get("source") if gtm else "none"
    if gtm:
        checks.append(
            ValidationCheck(
                scenario=version,
                period=_period_label(start_period),
                validation_name="gtm_quota_capacity_source",
                status="pass",
                actual_value=sum(
                    (q_money(r.get("productive_quota_capacity_arr") or 0) for r in gtm),
                    Decimal("0"),
                ),
                source_tables_used=[str(gtm_source)],
            )
        )

    failed = sum(1 for c in checks if c.status == "fail")
    warns = sum(1 for c in checks if c.status == "warning")
    passed = sum(1 for c in checks if c.status == "pass")
    if failed:
        status = "fail"
    elif warns:
        status = "warning"
    else:
        status = "pass"

    return WorkforceValidationResponse(
        organization_id=str(organization_id),
        scenario=version,
        start_period=start_period,
        end_period=end_period,
        status=status,
        checks=checks,
        failed_count=failed,
        warning_count=warns,
        passed_count=passed,
    )
