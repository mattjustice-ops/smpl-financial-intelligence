"""Auth.js adapter tables for magic-link verification tokens

Revision ID: auth_002
Revises: auth_001
Create Date: 2026-05-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "auth_002"
down_revision: Union[str, None] = "auth_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "authjs_users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("email_verified", sa.DateTime(timezone=True), nullable=True),
        sa.Column("image", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_authjs_users_email", "authjs_users", ["email"], unique=True)

    op.create_table(
        "authjs_verification_token",
        sa.Column("identifier", sa.Text(), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("expires", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("identifier", "token"),
    )


def downgrade() -> None:
    op.drop_table("authjs_verification_token")
    op.drop_index("ix_authjs_users_email", table_name="authjs_users")
    op.drop_table("authjs_users")
