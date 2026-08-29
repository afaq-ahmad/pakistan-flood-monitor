from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, JSON, Text, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    
    id = Column(String, primary_key=True, index=True)
    corridor_aoi = Column(String, index=True)
    status = Column(String, default="completed")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    run_metadata = Column(JSON, default=dict)
    
    events = relationship("FloodEvent", back_populates="pipeline_run")
    assessments = relationship("RiskAssessment", back_populates="pipeline_run")
    tasks = relationship("PipelineTask", back_populates="pipeline_run", cascade="all, delete-orphan")


class PipelineTask(Base):
    """Durable task state for the canonical workflow engine.

    ``PipelineRun`` remains the root record to preserve compatibility with
    existing API/event persistence.  Task signatures enforce idempotency for a
    workflow's meaningful inputs without introducing another runtime schema.
    """

    __tablename__ = "pipeline_tasks"

    id = Column(String, primary_key=True)
    run_id = Column(String, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    task_name = Column(String, nullable=False)
    task_order = Column(Integer, nullable=False)
    run_signature = Column(String(128), nullable=False, index=True)
    status = Column(String, nullable=False, default="queued", index=True)
    dependencies = Column(JSON, default=list, nullable=False)
    attempt_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    input_metadata = Column(JSON, default=dict, nullable=False)
    result_metadata = Column(JSON, default=dict, nullable=False)
    data_availability = Column(String, nullable=True)
    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    pipeline_run = relationship("PipelineRun", back_populates="tasks")

    __table_args__ = (
        UniqueConstraint("run_signature", "task_name", name="uq_pipeline_tasks_signature_name"),
        Index("ix_pipeline_tasks_run_order", "run_id", "task_order"),
    )

class FloodEvent(Base):
    __tablename__ = "flood_events"
    
    id = Column(String, primary_key=True, index=True)
    run_id = Column(String, ForeignKey("pipeline_runs.id"))
    corridor_aoi = Column(String, index=True)
    event_class = Column(String)
    status = Column(String, default="draft")  # draft, review, approved, published, retracted
    queue_status = Column(String, default="pending")
    machine_confidence = Column(Float)
    analyst_confidence = Column(Float, nullable=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    # Store geometry as GeoJSON to support both PostgreSQL and SQLite
    geometry_geojson = Column(JSON, default=dict)
    event_area_km2 = Column(Float)
    notes = Column(String, default="")
    
    pipeline_run = relationship("PipelineRun", back_populates="events")
    reviews = relationship("AnalystReview", back_populates="event")
    alerts = relationship("Alert", back_populates="event")

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    
    id = Column(String, primary_key=True, index=True)
    run_id = Column(String, ForeignKey("pipeline_runs.id"))
    corridor_aoi = Column(String, index=True)
    risk_score = Column(Float)
    severity_score = Column(Float)
    exposure_score = Column(Float)
    confidence_score = Column(Float)
    assessment_data = Column(JSON, default=dict)  # Composite inputs and explainability
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    pipeline_run = relationship("PipelineRun", back_populates="assessments")

class AnalystReview(Base):
    __tablename__ = "analyst_reviews"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, ForeignKey("flood_events.id"))
    actor = Column(String)
    action = Column(String)
    notes = Column(String, default="")
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    event = relationship("FloodEvent", back_populates="reviews")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chain = Column(String, index=True)
    action = Column(String)
    principal_id = Column(String)
    resource_type = Column(String)
    resource_id = Column(String)
    details = Column(JSON, default=dict)
    previous_hash = Column(String)
    entry_hash = Column(String, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(String, primary_key=True, index=True)
    event_id = Column(String, ForeignKey("flood_events.id"))
    alert_level = Column(String)
    message = Column(String)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    
    event = relationship("FloodEvent", back_populates="alerts")

class ModelRegistry(Base):
    __tablename__ = "model_registry"
    
    id = Column(String, primary_key=True, index=True)
    model_type = Column(String)
    status = Column(String)  # candidate, active, retired
    training_data_version = Column(String)
    validation_metrics = Column(JSON, default=dict)
    notes = Column(String, default="")
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
