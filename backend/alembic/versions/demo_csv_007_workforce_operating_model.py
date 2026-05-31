"""HRIS-style workforce operating model tables

Revision ID: demo_csv_007
Revises: demo_csv_006
Create Date: 2026-05-19
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "demo_csv_007"
down_revision: Union[str, None] = "demo_csv_006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tenant_col() -> sa.Column:
    return sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def _tenant_fk() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE")


def _money(name: str, *, nullable: bool = True) -> sa.Column:
    return sa.Column(name, sa.Numeric(precision=18, scale=2), nullable=nullable)


def _ratio(name: str, *, nullable: bool = True) -> sa.Column:
    return sa.Column(name, sa.Numeric(precision=18, scale=6), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "workforce_employees",
        _tenant_col(),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("employee_id", sa.String(length=128), nullable=False),
        sa.Column("department", sa.String(length=128), nullable=False),
        sa.Column("sub_department", sa.String(length=128), nullable=True),
        sa.Column("role", sa.String(length=256), nullable=False),
        sa.Column("level", sa.String(length=64), nullable=True),
        sa.Column("region", sa.String(length=64), nullable=True),
        sa.Column("hire_date", sa.Date(), nullable=True),
        sa.Column("termination_date", sa.Date(), nullable=True),
        sa.Column("employment_status", sa.String(length=64), nullable=False, server_default="Active"),
        _money("salary_annual"),
        _money("bonus_annual"),
        _money("commission_annual"),
        _money("equity_sbc_annual"),
        _ratio("benefits_load_pct"),
        _money("quota_capacity_arr"),
        _ratio("productivity_ramp_pct"),
        sa.Column("months_to_full_productivity", sa.Integer(), nullable=True),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "version", "employee_id", name="pk_workforce_employees"),
    )

    op.create_table(
        "workforce_open_requisitions",
        _tenant_col(),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("req_id", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=256), nullable=False),
        sa.Column("department", sa.String(length=128), nullable=False),
        sa.Column("sub_department", sa.String(length=128), nullable=True),
        sa.Column("hiring_manager", sa.String(length=256), nullable=True),
        sa.Column("target_hire_date", sa.Date(), nullable=True),
        sa.Column("planned_start_date", sa.Date(), nullable=True),
        sa.Column("priority", sa.String(length=32), nullable=True),
        sa.Column("approved_status", sa.String(length=64), nullable=False, server_default="Approved"),
        sa.Column("requisition_type", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("level", sa.String(length=64), nullable=True),
        sa.Column("region", sa.String(length=64), nullable=True),
        _money("salary_annual_override"),
        _money("quota_capacity_arr_override"),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "version", "req_id", name="pk_workforce_open_requisitions"),
    )

    op.create_table(
        "workforce_hiring_ramp_assumptions",
        _tenant_col(),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("department", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=256), nullable=False),
        sa.Column("level", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("month_offset", sa.Integer(), nullable=False),
        sa.Column("productivity_pct", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint(
            "organization_id",
            "version",
            "department",
            "role",
            "level",
            "month_offset",
            name="pk_workforce_hiring_ramp_assumptions",
        ),
    )

    op.create_table(
        "workforce_compensation_bands",
        _tenant_col(),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("department", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=256), nullable=False),
        sa.Column("level", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("region", sa.String(length=64), nullable=False, server_default=""),
        _money("base_salary_annual", nullable=False),
        _ratio("bonus_target_pct"),
        _money("commission_annual"),
        _money("equity_sbc_annual"),
        _ratio("benefits_load_pct"),
        _money("default_quota_capacity_arr"),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint(
            "organization_id",
            "version",
            "department",
            "role",
            "level",
            "region",
            name="pk_workforce_compensation_bands",
        ),
    )

    op.create_table(
        "workforce_department_allocation_rules",
        _tenant_col(),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("rule_id", sa.String(length=128), nullable=False),
        sa.Column("department", sa.String(length=128), nullable=False),
        sa.Column("pnl_line", sa.String(length=128), nullable=False),
        sa.Column("allocation_pct", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("effective_start", sa.Date(), nullable=True),
        sa.Column("effective_end", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "version", "rule_id", name="pk_workforce_department_allocation_rules"),
    )

    op.create_table(
        "workforce_period_summary",
        _tenant_col(),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("department", sa.String(length=128), nullable=False),
        sa.Column("filled_headcount", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("planned_hire_headcount", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("total_headcount_fte", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        _money("base_payroll_monthly", nullable=False),
        _money("bonus_monthly", nullable=False),
        _money("commission_monthly", nullable=False),
        _money("equity_sbc_monthly", nullable=False),
        _money("benefits_load_monthly", nullable=False),
        _money("total_people_cost_monthly", nullable=False),
        _money("quota_capacity_arr", nullable=False),
        _money("productive_quota_capacity_arr", nullable=False),
        sa.Column("derived_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "version", "period", "department", name="pk_workforce_period_summary"),
    )


def downgrade() -> None:
    for table in (
        "workforce_period_summary",
        "workforce_department_allocation_rules",
        "workforce_compensation_bands",
        "workforce_hiring_ramp_assumptions",
        "workforce_open_requisitions",
        "workforce_employees",
    ):
        op.drop_table(table)
