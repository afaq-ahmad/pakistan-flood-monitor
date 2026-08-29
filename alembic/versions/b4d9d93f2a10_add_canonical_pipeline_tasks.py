"""Add durable canonical pipeline task state.

Revision ID: b4d9d93f2a10
Revises: f46f1d9e187b
Create Date: 2026-08-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4d9d93f2a10"
down_revision: Union[str, Sequence[str], None] = "f46f1d9e187b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pipeline_tasks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("task_name", sa.String(), nullable=False),
        sa.Column("task_order", sa.Integer(), nullable=False),
        sa.Column("run_signature", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("input_metadata", sa.JSON(), nullable=False),
        sa.Column("result_metadata", sa.JSON(), nullable=False),
        sa.Column("data_availability", sa.String(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_signature", "task_name", name="uq_pipeline_tasks_signature_name"),
    )
    op.create_index("ix_pipeline_tasks_run_id", "pipeline_tasks", ["run_id"], unique=False)
    op.create_index("ix_pipeline_tasks_run_signature", "pipeline_tasks", ["run_signature"], unique=False)
    op.create_index("ix_pipeline_tasks_status", "pipeline_tasks", ["status"], unique=False)
    op.create_index("ix_pipeline_tasks_run_order", "pipeline_tasks", ["run_id", "task_order"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pipeline_tasks_run_order", table_name="pipeline_tasks")
    op.drop_index("ix_pipeline_tasks_status", table_name="pipeline_tasks")
    op.drop_index("ix_pipeline_tasks_run_signature", table_name="pipeline_tasks")
    op.drop_index("ix_pipeline_tasks_run_id", table_name="pipeline_tasks")
    op.drop_table("pipeline_tasks")
