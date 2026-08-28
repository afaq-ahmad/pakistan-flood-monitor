from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from pakistan_flood_monitor.config import AppMode
from pakistan_flood_monitor.models.observations import (
    ObservationStatus,
    ScientificObservation,
    SourceAvailabilityStatus,
)


class AlertLevel(str, Enum):
    watch = "watch"
    warning = "warning"
    critical = "critical"


class ReviewStatus(str, Enum):
    machine_only = "machine_only"
    analyst_review_required = "analyst_review_required"
    analyst_validated = "analyst_validated"


class BreachCategory(str, Enum):
    likely_overflow = "likely_overflow"
    likely_embankment_failure = "likely_embankment_failure"
    uncertain_anomaly = "uncertain_anomaly"


class EventClass(str, Enum):
    flood = "flood"
    likely_overflow = "likely_overflow"
    possible_breach = "possible_breach"
    uncertain = "uncertain"
    false_positive = "false_positive"


class EventDecision(str, Enum):
    accept = "accept"
    modify = "modify"
    reject = "reject"


class AOI(BaseModel):
    name: str
    district: str
    geometry_wkt: str


class LineageSceneAsset(BaseModel):
    href: str
    roles: List[str] = Field(default_factory=list)


class SourceSceneLineage(BaseModel):
    scene_id: str
    sensor: str
    acquired_at: datetime
    assets: Dict[str, LineageSceneAsset] = Field(default_factory=dict)
    observation_status: ObservationStatus = ObservationStatus.OBSERVED
    availability_status: SourceAvailabilityStatus = SourceAvailabilityStatus.AVAILABLE
    synthetic: bool = False
    source_uri: str | None = None


class EventLineage(BaseModel):
    schema: str = "stac-lineage-event/v1"
    run_id: str
    source_scene_ids: List[str] = Field(default_factory=list)
    source_scenes: List[SourceSceneLineage] = Field(default_factory=list)
    processing_version: str
    threshold_version: str
    thresholds: Dict[str, float] = Field(default_factory=dict)
    model: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime
    observations: Dict[str, ScientificObservation] = Field(default_factory=dict)
    contains_synthetic: bool = False
    data_availability: SourceAvailabilityStatus = SourceAvailabilityStatus.AVAILABLE
    product_label: ObservationStatus = ObservationStatus.OBSERVED
    watermark: str | None = None


class RunLineage(BaseModel):
    schema: str = "stac-lineage-run/v1"
    run_id: str
    aoi: str
    source_scene_ids: List[str] = Field(default_factory=list)
    source_scenes: List[SourceSceneLineage] = Field(default_factory=list)
    processing_version: str
    threshold_version: str
    thresholds: Dict[str, float] = Field(default_factory=dict)
    model: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime
    observations: Dict[str, ScientificObservation] = Field(default_factory=dict)
    contains_synthetic: bool = False
    data_availability: SourceAvailabilityStatus = SourceAvailabilityStatus.AVAILABLE
    product_label: ObservationStatus = ObservationStatus.OBSERVED
    watermark: str | None = None


class FloodDetectionResult(BaseModel):
    aoi: str
    timestamp: datetime
    flood_probability: float
    flood_area_km2: float
    breach_risk_score: float
    alert_level: AlertLevel
    confidence_score: float
    review_status: ReviewStatus
    indicators: Dict[str, float]
    probabilistic_forecast: Dict[str, Any] = Field(default_factory=dict)
    observation_statuses: Dict[str, ObservationStatus] = Field(default_factory=dict)
    data_availability: SourceAvailabilityStatus = SourceAvailabilityStatus.AVAILABLE
    product_label: ObservationStatus = ObservationStatus.OBSERVED


class FloodCandidateMap(BaseModel):
    aoi: str
    run_id: str
    polygon_ids: List[str]


class ConfirmedFloodExtent(BaseModel):
    aoi: str
    run_id: str
    review_status: ReviewStatus
    approved_polygon_ids: List[str]


class BreachSuspicionLayer(BaseModel):
    aoi: str
    run_id: str
    candidate_id: str
    category: BreachCategory
    confidence_score: float


class ExposureStats(BaseModel):
    affected_population: int
    affected_cropland_km2: float
    affected_roads_km: float
    affected_schools: int
    affected_hospitals: int


class AssetExposureReport(BaseModel):
    aoi: str
    district: str
    asset_class_exposure: Dict[str, float]


class AlertSummary(BaseModel):
    alert_id: str
    aoi: str
    alert_level: AlertLevel
    confidence_score: float
    summary: str
    product_label: ObservationStatus = ObservationStatus.OBSERVED
    data_availability: SourceAvailabilityStatus = SourceAvailabilityStatus.AVAILABLE
    watermark: str | None = None


class ModelVersion(BaseModel):
    model_id: str
    training_data_snapshot_version: str
    training_config_path: str
    threshold_file_path: str
    evaluation_report_path: str
    reproducible_training_script: str
    rollback_model_id: str | None = None


class ReviewQueueEvent(BaseModel):
    event_id: str
    run_id: str
    aoi: str
    event_class: EventClass
    machine_confidence: float
    analyst_confidence: float | None = None
    decision: EventDecision | None = None
    notes: str = ""
    source_scenes: List[str] = Field(default_factory=list)
    lineage: EventLineage | None = None


class HistoricalEventRecord(BaseModel):
    event_id: str
    aoi: str
    peak_date: datetime
    flood_area_km2: float
    label_quality_tier: int


class MVPOutputs(BaseModel):
    flood_candidate_map: FloodCandidateMap
    confirmed_flood_extent: ConfirmedFloodExtent
    breach_suspicion_layer: BreachSuspicionLayer
    asset_exposure_report: AssetExposureReport
    alert_feed_item: AlertSummary
    model_version: ModelVersion
    review_queue_event: ReviewQueueEvent
    historical_event_dashboard: List[HistoricalEventRecord]


class ProcessingReport(BaseModel):
    run_id: str
    source_sensors: List[str]
    detections: List[FloodDetectionResult]
    exposure: Dict[str, ExposureStats]
    trigger_reason: str
    published_outputs: MVPOutputs
    run_lineage: RunLineage
    app_mode: AppMode = AppMode.DEMO
    data_availability: SourceAvailabilityStatus = SourceAvailabilityStatus.AVAILABLE
    product_label: ObservationStatus = ObservationStatus.OBSERVED
    contains_synthetic: bool = False
    watermark: str | None = None
    observations: Dict[str, ScientificObservation] = Field(default_factory=dict)
