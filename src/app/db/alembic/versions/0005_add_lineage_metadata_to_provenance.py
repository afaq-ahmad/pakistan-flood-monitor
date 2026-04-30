"""Add lineage metadata json to provenance-backed entities."""

from alembic import op
import sqlalchemy as sa


revision = "0005_add_lineage_metadata_to_provenance"
down_revision = "0004_runtime_state_persistence"
branch_labels = None
depends_on = None

_TABLES = [
    "flood_candidates",
    "breach_candidates",
    "flood_events",
    "breach_reviews",
    "exposure_results",
    "alert_log",
]


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(table, sa.Column("lineage_metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    for table in _TABLES:
        op.drop_column(table, "lineage_metadata")
