from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DashboardEventCard(BaseModel):
    event_id: str
    corridor_id: str
    event_type: str
    confidence: float
    status: str
    detected_at: datetime


class DashboardViewResponse(BaseModel):
    corridor_id: str
    generated_at: datetime
    active_events: int
    published_events: int
    average_confidence: float
    recent_events: list[DashboardEventCard]


class ReviewLayerToggles(BaseModel):
    previous_sar: bool = True
    current_sar: bool = True
    anomaly_mask: bool = True
    flood_candidate_polygons: bool = True
    embankments: bool = True
    seasonal_permanent_water: bool = True
    districts: bool = True
    optical_support: bool = False


class ReviewContextLinks(BaseModel):
    before_sar: str
    after_sar: str
    anomaly_mask: str
    flood_candidates: str
    embankments: str
    seasonal_permanent_water: str
    districts: str
    optical_support: str | None = None


class ReviewActionControls(BaseModel):
    accept_reject: bool = True
    class_selection: list[str] = Field(default_factory=lambda: ["flood", "breach", "ponding", "artifact"])
    note_entry: bool = True
    confidence_adjustment: dict[str, float] = Field(default_factory=lambda: {"min": 0.0, "max": 1.0, "step": 0.05})
    publish_action: bool = True


class ReviewFilterState(BaseModel):
    corridor: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    event_class: str | None = None
    review_status: str | None = None
    breach_suspicion_min: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_band: str | None = None


class ReviewQueueItem(BaseModel):
    candidate_id: str
    corridor_id: str
    district: str
    detected_at: datetime
    review_status: str
    event_class: str
    confidence: float
    confidence_band: str
    breach_suspicion: float
    analyst_confidence: float | None = None
    context_links: ReviewContextLinks


class ReviewDashboardResponse(BaseModel):
    generated_at: datetime
    layer_toggles: ReviewLayerToggles
    action_controls: ReviewActionControls
    applied_filters: ReviewFilterState
    queue_size: int
    queue: list[ReviewQueueItem]


class SnapshotRequest(BaseModel):
    event_ids: list[str] | None = None


class SnapshotRecord(BaseModel):
    event_id: str
    corridor_id: str
    generated_at: datetime
    snapshot_path: str
    snapshot_url: str
    width: int = Field(default=512)
    height: int = Field(default=512)
