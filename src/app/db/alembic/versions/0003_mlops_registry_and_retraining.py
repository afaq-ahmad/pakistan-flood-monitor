"""Add MLOps model/threshold registries and retraining decision log.

Revision ID: 0003_mlops_registry_and_retraining
Revises: 0002_task_queue_orchestration
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_mlops_registry_and_retraining"
down_revision = "0002_task_queue_orchestration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("model_id", sa.String(150), nullable=False, unique=True),
        sa.Column("model_type", sa.String(100), nullable=False),
        sa.Column("training_snapshot_version", sa.String(150), nullable=False),
        sa.Column("metrics", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("deployment_status", sa.String(50), nullable=False, server_default="candidate"),
        sa.Column("rollback_parent_model_id", sa.String(150), nullable=True),
        sa.Column("metadata", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_model_versions_type_status", "model_versions", ["model_type", "deployment_status"])
    op.create_index("ix_model_versions_snapshot", "model_versions", ["training_snapshot_version"])

    op.create_table(
        "threshold_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("threshold_name", sa.String(100), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("threshold_values", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("linked_model_id", sa.String(150), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index(
        "ix_threshold_versions_name_version",
        "threshold_versions",
        ["threshold_name", "version"],
        unique=True,
    )

    op.create_table(
        "retraining_decisions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("model_id", sa.String(150), nullable=False),
        sa.Column("should_retrain", sa.Boolean, nullable=False),
        sa.Column("trigger_reasons", sa.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("signal_snapshot", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("retraining_decisions")
    op.drop_table("threshold_versions")
    op.drop_table("model_versions")
