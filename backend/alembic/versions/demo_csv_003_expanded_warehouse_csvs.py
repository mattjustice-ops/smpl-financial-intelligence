"""support expanded warehouse CSV dataset

Revision ID: demo_csv_003
Revises: demo_csv_002
Create Date: 2026-05-16
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "demo_csv_003"
down_revision: Union[str, None] = "demo_csv_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("pk_headcount_plan", "headcount_plan", type_="primary")
    op.add_column("headcount_plan", sa.Column("version", sa.String(length=64), server_default="Actual", nullable=False))
    op.add_column("headcount_plan", sa.Column("payroll_tax_rate", sa.Numeric(precision=18, scale=6), nullable=True))
    op.add_column("headcount_plan", sa.Column("benefits_rate", sa.Numeric(precision=18, scale=6), nullable=True))
    op.add_column("headcount_plan", sa.Column("total_people_cost", sa.Numeric(precision=18, scale=2), nullable=True))
    op.create_primary_key(
        "pk_headcount_plan",
        "headcount_plan",
        ["organization_id", "version", "period", "department"],
    )

    op.drop_constraint("pk_gl_actuals", "gl_actuals", type_="primary")
    op.add_column("gl_actuals", sa.Column("version", sa.String(length=64), server_default="Actual", nullable=False))
    op.add_column("gl_actuals", sa.Column("statement_category", sa.String(length=128), nullable=True))
    op.add_column("gl_actuals", sa.Column("account_group", sa.String(length=128), nullable=True))
    op.add_column("gl_actuals", sa.Column("expense_type", sa.String(length=128), nullable=True))
    op.add_column("gl_actuals", sa.Column("department", sa.String(length=256), server_default="", nullable=False))
    op.add_column("gl_actuals", sa.Column("cost_center", sa.String(length=128), server_default="", nullable=False))
    op.add_column("gl_actuals", sa.Column("sub_department", sa.String(length=256), server_default="", nullable=False))
    op.add_column("gl_actuals", sa.Column("vendor_id", sa.String(length=128), server_default="", nullable=False))
    op.add_column("gl_actuals", sa.Column("vendor_name", sa.String(length=512), nullable=True))
    op.add_column("gl_actuals", sa.Column("source_file", sa.String(length=256), server_default="", nullable=False))
    op.add_column("gl_actuals", sa.Column("source_record_id", sa.String(length=256), server_default="", nullable=False))
    op.add_column("gl_actuals", sa.Column("notes", sa.Text(), nullable=True))
    op.create_primary_key(
        "pk_gl_actuals",
        "gl_actuals",
        [
            "organization_id",
            "version",
            "period",
            "account_number",
            "department",
            "cost_center",
            "sub_department",
            "source_file",
            "source_record_id",
            "subsidiary",
            "source_system",
        ],
    )

    op.create_table(
        "warehouse_csv_rows",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("csv_kind", sa.String(length=128), nullable=False),
        sa.Column("source_filename", sa.String(length=512), nullable=True),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "organization_id",
            "csv_kind",
            "source_row_number",
            name="pk_warehouse_csv_rows",
        ),
    )


def downgrade() -> None:
    op.drop_table("warehouse_csv_rows")
    op.drop_constraint("pk_headcount_plan", "headcount_plan", type_="primary")
    op.drop_column("headcount_plan", "total_people_cost")
    op.drop_column("headcount_plan", "benefits_rate")
    op.drop_column("headcount_plan", "payroll_tax_rate")
    op.drop_column("headcount_plan", "version")
    op.create_primary_key(
        "pk_headcount_plan",
        "headcount_plan",
        ["organization_id", "period", "department"],
    )

    op.drop_constraint("pk_gl_actuals", "gl_actuals", type_="primary")
    op.drop_column("gl_actuals", "notes")
    op.drop_column("gl_actuals", "source_record_id")
    op.drop_column("gl_actuals", "source_file")
    op.drop_column("gl_actuals", "vendor_name")
    op.drop_column("gl_actuals", "vendor_id")
    op.drop_column("gl_actuals", "sub_department")
    op.drop_column("gl_actuals", "cost_center")
    op.drop_column("gl_actuals", "department")
    op.drop_column("gl_actuals", "expense_type")
    op.drop_column("gl_actuals", "account_group")
    op.drop_column("gl_actuals", "statement_category")
    op.drop_column("gl_actuals", "version")
    op.create_primary_key(
        "pk_gl_actuals",
        "gl_actuals",
        ["organization_id", "period", "account_number", "subsidiary", "source_system"],
    )
