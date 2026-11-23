"""Customer-grain forward columns and close insight facts table.

Revision ID: close_grain_001
Revises: customer_onboard_001
Create Date: 2026-11-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "close_grain_001"
down_revision: Union[str, None] = "customer_onboard_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

HISTORY = "actual_customer_arr_history"
FORWARD_COLS = [
    ("parent_id", sa.Text()),
    ("subsidiary_id", sa.Text()),
    ("product_code", sa.Text()),
    ("product_name", sa.Text()),
    ("is_core_product", sa.Text()),
    ("uom", sa.Text()),
    ("qty_this_month", sa.Text()),
    ("qty_last_month", sa.Text()),
    ("billing_cadence", sa.Text()),
    ("classification_subtype", sa.Text()),
    ("first_month_revenue", sa.Text()),
    ("latest_new_business_date", sa.Text()),
    ("last_new_business_revenue", sa.Text()),
    ("contract_id", sa.Text()),
    ("succeeds_contract_id", sa.Text()),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if HISTORY in tables:
        existing = {col["name"] for col in inspector.get_columns(HISTORY)}
        for name, col_type in FORWARD_COLS:
            if name not in existing:
                op.add_column(HISTORY, sa.Column(name, col_type, nullable=True))

    if "actual_close_insight_facts" not in tables:
        op.create_table(
            "actual_close_insight_facts",
            sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
            sa.Column("source_row_number", sa.Integer(), nullable=False),
            sa.Column("source_filename", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("version", sa.Text(), nullable=True),
            sa.Column("period", sa.Text(), nullable=False),
            sa.Column("packs", JSONB(), nullable=True),
            sa.PrimaryKeyConstraint("organization_id", "source_row_number", name="pk_actual_close_insight_facts"),
        )
        op.create_index(
            "ix_actual_close_insight_facts_org_period",
            "actual_close_insight_facts",
            ["organization_id", "period"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "actual_close_insight_facts" in tables:
        op.drop_index("ix_actual_close_insight_facts_org_period", table_name="actual_close_insight_facts")
        op.drop_table("actual_close_insight_facts")
    if HISTORY in tables:
        existing = {col["name"] for col in inspector.get_columns(HISTORY)}
        for name, _col_type in FORWARD_COLS:
            if name in existing:
                op.drop_column(HISTORY, name)
