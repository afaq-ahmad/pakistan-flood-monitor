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
