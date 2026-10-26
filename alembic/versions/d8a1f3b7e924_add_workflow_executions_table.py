"""add_workflow_executions_table

Revision ID: d8a1f3b7e924
Revises: c996258fd7c6
Create Date: 2026-10-27 02:55:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d8a1f3b7e924"
down_revision: Union[str, None] = "c996258fd7c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workflow_name", sa.String(length=100), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "created", "running", "paused_manual", "completed", "failed", "cancelled",
                name="workflowstatus",
            ),
            nullable=False,
        ),
        sa.Column("current_step_index", sa.Integer(), default=0),
        sa.Column("total_steps", sa.Integer(), default=0),
        sa.Column("step_results_json", sa.Text(), nullable=True),
        sa.Column("context_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wf_account_id", "workflow_executions", ["account_id"])
    op.create_index("ix_wf_job_id", "workflow_executions", ["job_id"])
    op.create_index("ix_wf_platform", "workflow_executions", ["platform"])
    op.create_index("ix_wf_status", "workflow_executions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_wf_status", table_name="workflow_executions")
    op.drop_index("ix_wf_platform", table_name="workflow_executions")
    op.drop_index("ix_wf_job_id", table_name="workflow_executions")
    op.drop_index("ix_wf_account_id", table_name="workflow_executions")
    op.drop_table("workflow_executions")
