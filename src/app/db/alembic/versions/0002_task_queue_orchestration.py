"""Add orchestration task queue table.

Revision ID: 0002_task_queue_orchestration
Revises: 0001_initial_schema
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_task_queue_orchestration"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_queue",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("task_type", sa.String(80), nullable=False),
        sa.Column("corridor_id", sa.Integer, sa.ForeignKey("aoi_corridors.id"), nullable=False),
        sa.Column("scene_id", sa.Integer, sa.ForeignKey("satellite_scenes.id"), nullable=True),
        sa.Column("priority_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("rank_reason", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("run_hash", sa.String(128), nullable=True),
        sa.Column("payload", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_task_queue_status", "task_queue", ["status"])
    op.create_index("ix_task_queue_corridor_priority", "task_queue", ["corridor_id", "priority_score"])
    op.create_index("ix_task_queue_run_hash", "task_queue", ["run_hash"])


def downgrade() -> None:
    op.drop_table("task_queue")
