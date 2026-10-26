"""spec_compliance_enums_and_job_idempotency

Revision ID: e1a2b3c4d5e6
Revises: d8a1f3b7e924
Create Date: 2026-10-27 04:00:00.000000

Adds missing AccountStatus/ProviderStatus enum values per master spec,
and adds idempotency_key column to jobs table.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e1a2b3c4d5e6"
down_revision: str | None = "d8a1f3b7e924"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SQLite doesn't support ALTER TYPE, so enum changes are handled at the
    # application level (SQLAlchemy stores enum values as VARCHAR for SQLite).
    # For PostgreSQL deployments, you'd ALTER TYPE here.

    # Add idempotency_key to jobs
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.add_column(
            sa.Column("idempotency_key", sa.String(length=64), nullable=True)
        )
        batch_op.create_index("ix_jobs_idempotency_key", ["idempotency_key"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_index("ix_jobs_idempotency_key")
        batch_op.drop_column("idempotency_key")
