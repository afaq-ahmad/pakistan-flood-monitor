from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProvenanceMixin:
    source_scene_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    processing_run_id: Mapped[int | None] = mapped_column(ForeignKey("scene_processing_runs.id"), nullable=True)
    code_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    threshold_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    review_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    reviewer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AOICorridor(Base):
    __tablename__ = "aoi_corridors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    corridor_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    pilot_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    responsible_analyst: Mapped[str | None] = mapped_column(String(255), nullable=True)
    geom: Mapped[str] = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)

    __table_args__ = (
        Index("ix_aoi_corridors_corridor_id", "corridor_id"),
        Index("ix_aoi_corridors_geom", "geom", postgresql_using="gist"),
    )


class RiverReach(Base):
    __tablename__ = "river_reaches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    corridor_id: Mapped[int] = mapped_column(ForeignKey("aoi_corridors.id"), nullable=False)
    reach_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    geom: Mapped[str] = mapped_column(Geometry("MULTILINESTRING", srid=4326), nullable=False)

    __table_args__ = (
        Index("ix_river_reaches_corridor_id", "corridor_id"),
        Index("ix_river_reaches_geom", "geom", postgresql_using="gist"),
    )


class Embankment(Base):
    __tablename__ = "embankments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    corridor_id: Mapped[int] = mapped_column(ForeignKey("aoi_corridors.id"), nullable=False)
    embankment_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    geom: Mapped[str] = mapped_column(Geometry("MULTILINESTRING", srid=4326), nullable=False)

    __table_args__ = (
        Index("ix_embankments_corridor_id", "corridor_id"),
        Index("ix_embankments_geom", "geom", postgresql_using="gist"),
    )


class SatelliteScene(Base):
    __tablename__ = "satellite_scenes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    corridor_id: Mapped[int] = mapped_column(ForeignKey("aoi_corridors.id"), nullable=False)
    sensor: Mapped[str] = mapped_column(String(100), nullable=False)
    scene_id: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    acquisition_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    orbit_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    intersection_area_sqkm: Mapped[float] = mapped_column(Float, default=0.0)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="discovered", nullable=False)

    __table_args__ = (
        Index("ix_satellite_scenes_corridor_id", "corridor_id"),
        Index("ix_satellite_scenes_acquisition_time", "acquisition_time"),
        Index("ix_satellite_scenes_status", "status"),
    )


class SceneProcessingRun(Base):
    __tablename__ = "scene_processing_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_type: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    corridor_id: Mapped[int] = mapped_column(ForeignKey("aoi_corridors.id"), nullable=False)
    scene_id: Mapped[int] = mapped_column(ForeignKey("satellite_scenes.id"), nullable=False)
    code_version: Mapped[str] = mapped_column(String(100), nullable=False)
    config_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    output_locations: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_scene_processing_runs_status", "status"),)




class TaskQueueRecord(Base):
    __tablename__ = "task_queue"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_type: Mapped[str] = mapped_column(String(80), nullable=False)
    corridor_id: Mapped[int] = mapped_column(ForeignKey("aoi_corridors.id"), nullable=False)
    scene_id: Mapped[int | None] = mapped_column(ForeignKey("satellite_scenes.id"), nullable=True)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rank_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)
    run_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_task_queue_status", "status"),
        Index("ix_task_queue_corridor_priority", "corridor_id", "priority_score"),
        Index("ix_task_queue_run_hash", "run_hash"),
    )


class FloodCandidate(Base, ProvenanceMixin):
    __tablename__ = "flood_candidates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    corridor_id: Mapped[int] = mapped_column(ForeignKey("aoi_corridors.id"), nullable=False)
    scene_id: Mapped[int] = mapped_column(ForeignKey("satellite_scenes.id"), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_band: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="new", nullable=False)
    geom: Mapped[str] = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)

    __table_args__ = (
        Index("ix_flood_candidates_geom", "geom", postgresql_using="gist"),
        Index("ix_flood_candidates_corridor_id", "corridor_id"),
        Index("ix_flood_candidates_status", "status"),
    )


class BreachCandidate(Base, ProvenanceMixin):
    __tablename__ = "breach_candidates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    corridor_id: Mapped[int] = mapped_column(ForeignKey("aoi_corridors.id"), nullable=False)
    scene_id: Mapped[int] = mapped_column(ForeignKey("satellite_scenes.id"), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_band: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="new", nullable=False)
    geom: Mapped[str] = mapped_column(Geometry("POINT", srid=4326), nullable=False)

    __table_args__ = (
        Index("ix_breach_candidates_geom", "geom", postgresql_using="gist"),
        Index("ix_breach_candidates_corridor_id", "corridor_id"),
        Index("ix_breach_candidates_status", "status"),
    )


class FloodEvent(Base, ProvenanceMixin):
    __tablename__ = "flood_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    corridor_id: Mapped[int] = mapped_column(ForeignKey("aoi_corridors.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), default="flood", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_band: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    geom: Mapped[str] = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)

    __table_args__ = (
        Index("ix_flood_events_geom", "geom", postgresql_using="gist"),
        Index("ix_flood_events_corridor_id", "corridor_id"),
        Index("ix_flood_events_status", "status"),
        Index("ix_flood_events_type_confidence_band", "event_type", "confidence_band"),
    )


class BreachReview(Base, ProvenanceMixin):
    __tablename__ = "breach_reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    breach_candidate_id: Mapped[int] = mapped_column(ForeignKey("breach_candidates.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExposureResult(Base, ProvenanceMixin):
    __tablename__ = "exposure_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    flood_event_id: Mapped[int] = mapped_column(ForeignKey("flood_events.id"), nullable=False)
    results: Mapped[dict] = mapped_column(JSON, default=dict)


class AlertLog(Base, ProvenanceMixin):
    __tablename__ = "alert_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    flood_event_id: Mapped[int] = mapped_column(ForeignKey("flood_events.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(50), nullable=False)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    model_type: Mapped[str] = mapped_column(String(100), nullable=False)
    training_snapshot_version: Mapped[str] = mapped_column(String(150), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    deployment_status: Mapped[str] = mapped_column(String(50), nullable=False, default="candidate")
    rollback_parent_model_id: Mapped[str | None] = mapped_column(String(150), nullable=True)
    model_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_model_versions_type_status", "model_type", "deployment_status"),
        Index("ix_model_versions_snapshot", "training_snapshot_version"),
    )


class ThresholdVersion(Base):
    __tablename__ = "threshold_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    threshold_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    threshold_values: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    linked_model_id: Mapped[str | None] = mapped_column(String(150), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_threshold_versions_name_version", "threshold_name", "version", unique=True),
    )


class RetrainingDecisionLog(Base):
    __tablename__ = "retraining_decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[str] = mapped_column(String(150), nullable=False)
    should_retrain: Mapped[bool] = mapped_column(Boolean, nullable=False)
    trigger_reasons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    signal_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ValidationSample(Base):
    __tablename__ = "validation_samples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("flood_events.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
