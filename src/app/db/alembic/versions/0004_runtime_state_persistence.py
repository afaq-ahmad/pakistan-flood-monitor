"""Persist runtime runs/reviews/audit state.

Revision ID: 0004_runtime_state_persistence
Revises: 0003_mlops_registry_and_retraining
Create Date: 2026-04-30
"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision = "0004_runtime_state_persistence"
down_revision = "0003_mlops_registry_and_retraining"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_run_states",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("run_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("outputs", sa.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("state_payload", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_runtime_run_states_run_hash", "runtime_run_states", ["run_hash"], unique=True)

    op.create_table(
        "runtime_review_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("candidate_id", sa.String(150), nullable=False, unique=True),
        sa.Column("candidate_payload", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("candidate_class", sa.String(50), nullable=False, server_default="flood"),
        sa.Column("analyst_confidence", sa.Float, nullable=True),
        sa.Column("notes", sa.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("assigned_analyst", sa.String(255), nullable=True),
        sa.Column("original_machine_geometry", Geometry("GEOMETRY", srid=4326), nullable=False),
        sa.Column("analyst_edited_geometry", Geometry("GEOMETRY", srid=4326), nullable=True),
        sa.Column("final_published_geometry", Geometry("GEOMETRY", srid=4326), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_runtime_review_items_candidate_id", "runtime_review_items", ["candidate_id"], unique=True)
    op.create_index("ix_runtime_review_items_original_geom", "runtime_review_items", ["original_machine_geometry"], postgresql_using="gist")

    op.create_table(
        "runtime_review_audit",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("candidate_id", sa.String(150), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("changed_at", sa.DateTime, nullable=False),
        sa.Column("old_status", sa.String(50), nullable=False),
        sa.Column("new_status", sa.String(50), nullable=False),
        sa.Column("old_geometry_ref", sa.String(128), nullable=True),
        sa.Column("new_geometry_ref", sa.String(128), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("runtime_review_audit")
    op.drop_table("runtime_review_items")
    op.drop_table("runtime_run_states")
