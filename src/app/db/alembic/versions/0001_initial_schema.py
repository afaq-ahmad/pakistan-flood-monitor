"""Initial monitoring schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aoi_corridors",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("corridor_id", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("pilot_status", sa.String(100), nullable=True),
        sa.Column("responsible_analyst", sa.String(255), nullable=True),
        sa.Column("geom", Geometry("MULTIPOLYGON", srid=4326), nullable=False),
    )
    op.create_index("ix_aoi_corridors_corridor_id", "aoi_corridors", ["corridor_id"])
    op.create_index("ix_aoi_corridors_geom", "aoi_corridors", ["geom"], postgresql_using="gist")

    op.create_table(
        "satellite_scenes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("corridor_id", sa.Integer, sa.ForeignKey("aoi_corridors.id"), nullable=False),
        sa.Column("sensor", sa.String(100), nullable=False),
        sa.Column("scene_id", sa.String(150), unique=True, nullable=False),
        sa.Column("acquisition_time", sa.DateTime, nullable=False),
        sa.Column("orbit_metadata", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("intersection_area_sqkm", sa.Float, nullable=False, server_default="0"),
        sa.Column("storage_uri", sa.Text, nullable=False),
        sa.Column("discovered_at", sa.DateTime, nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
    )
    op.create_index("ix_satellite_scenes_corridor_id", "satellite_scenes", ["corridor_id"])
    op.create_index("ix_satellite_scenes_acquisition_time", "satellite_scenes", ["acquisition_time"])
    op.create_index("ix_satellite_scenes_status", "satellite_scenes", ["status"])


def downgrade() -> None:
    op.drop_table("satellite_scenes")
    op.drop_table("aoi_corridors")
