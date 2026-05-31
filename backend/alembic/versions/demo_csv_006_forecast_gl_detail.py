"""forecast_gl_detail typed mart

Revision ID: demo_csv_006
Revises: demo_csv_005
Create Date: 2026-05-19
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "demo_csv_006"
down_revision: Union[str, None] = "demo_csv_005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tenant_col() -> sa.Column:
    return sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "forecast_gl_detail" in inspector.get_table_names():
        cols = {c["name"]: c for c in inspector.get_columns("forecast_gl_detail")}
        amount_col = cols.get("forecast_amount")
        if amount_col is not None and "numeric" in str(amount_col["type"]).lower():
            return
        op.rename_table("forecast_gl_detail", "forecast_gl_detail_legacy")

    op.create_table(
        "forecast_gl_detail",
        _tenant_col(),
        sa.Column("scenario", sa.String(length=64), nullable=False, server_default="Forecast"),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("line_type", sa.String(length=64), nullable=True),
        sa.Column("statement_category", sa.String(length=128), nullable=True),
        sa.Column("department", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("sub_department", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("account_group", sa.String(length=128), nullable=True),
        sa.Column("expense_type", sa.String(length=128), nullable=True),
        sa.Column("gl_account", sa.String(length=256), nullable=False),
        sa.Column("management_view_include", sa.String(length=8), nullable=False, server_default="Yes"),
        sa.Column("accounting_view_include", sa.String(length=8), nullable=False, server_default="Yes"),
        sa.Column("sbc_flag", sa.String(length=8), nullable=False, server_default="No"),
        sa.Column("one_time_flag", sa.String(length=8), nullable=False, server_default="No"),
        sa.Column("non_cash_flag", sa.String(length=8), nullable=False, server_default="No"),
        sa.Column("forecast_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("source", sa.String(length=256), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "organization_id",
            "scenario",
            "period",
            "gl_account",
            "department",
            "account_group",
            "expense_type",
            "sub_department",
            name="pk_forecast_gl_detail",
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "forecast_gl_detail" in inspector.get_table_names():
        op.drop_table("forecast_gl_detail")
    if "forecast_gl_detail_legacy" in inspector.get_table_names():
        op.rename_table("forecast_gl_detail_legacy", "forecast_gl_detail")
