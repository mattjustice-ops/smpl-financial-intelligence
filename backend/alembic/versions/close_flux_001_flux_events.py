"""Close flux-event grain for statement commentary.

Revision ID: close_flux_001
Revises: close_grain_001
Create Date: 2026-11-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID

revision: str = "close_flux_001"
down_revision: Union[str, None] = "close_grain_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "actual_close_flux_events"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if TABLE in tables:
        return
    op.create_table(
        TABLE,
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("source_filename", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("version", sa.Text(), nullable=True),
        sa.Column("period", sa.Text(), nullable=False),
        sa.Column("section", sa.Text(), nullable=False),
        sa.Column("account_number", sa.Text(), nullable=True),
        sa.Column("account_name", sa.Text(), nullable=True),
        sa.Column("event_kind", sa.Text(), nullable=False),
        sa.Column("counterparty", sa.Text(), nullable=True),
        sa.Column("counterparty_id", sa.Text(), nullable=True),
        sa.Column("department", sa.Text(), nullable=True),
        sa.Column("tag", sa.Text(), nullable=True),
        sa.Column("amount", sa.Text(), nullable=True),
        sa.Column("prior_amount", sa.Text(), nullable=True),
        sa.Column("tx_count", sa.Text(), nullable=True),
        sa.Column("prior_tx_count", sa.Text(), nullable=True),
        sa.Column("is_credit", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("organization_id", "source_row_number", name="pk_actual_close_flux_events"),
    )
    op.create_index(
        "ix_actual_close_flux_events_org_period_section",
        TABLE,
        ["organization_id", "period", "section"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if TABLE not in set(inspector.get_table_names()):
        return
    op.drop_index("ix_actual_close_flux_events_org_period_section", table_name=TABLE)
    op.drop_table(TABLE)
