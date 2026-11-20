"""Customer number and contract refs on organizations for sales-led onboarding.

Revision ID: customer_onboard_001
Revises: company_profile_001
Create Date: 2026-11-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "customer_onboard_001"
down_revision: Union[str, None] = "company_profile_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("customer_number", sa.String(64), nullable=True))
    op.create_index(
        "ix_organizations_customer_number",
        "organizations",
        ["customer_number"],
        unique=True,
    )
    op.add_column("organizations", sa.Column("contract_ref", sa.String(128), nullable=True))
    op.add_column("organizations", sa.Column("contract_signed_on", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "contract_signed_on")
    op.drop_column("organizations", "contract_ref")
    op.drop_index("ix_organizations_customer_number", table_name="organizations")
    op.drop_column("organizations", "customer_number")
