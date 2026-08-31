"""Add optimistic locking version column to clinical_handoffs

Revision ID: 0024_handoff_concurrency_version
Revises: 0023_multi_tenant_clinical_isolation_and_outbox
Create Date: 2026-08-31 12:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0024_handoff_concurrency_version"
down_revision: Union[str, None] = "0023_multi_tenant_clinical_isolation_and_outbox"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add optimistic locking version column to clinical_handoffs with default 1
    op.add_column("clinical_handoffs", sa.Column("version", sa.Integer(), server_default="1", nullable=False))


def downgrade() -> None:
    op.drop_column("clinical_handoffs", "version")
