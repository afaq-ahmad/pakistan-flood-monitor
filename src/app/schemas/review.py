from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ReviewActionRequest(BaseModel):
    action: str
    actor: str
    notes: str | None = None
    geometry: dict | None = None
    candidate_class: str | None = Field(default=None, alias="class")
    analyst_confidence: float | None = None


class ReviewCandidateInput(BaseModel):
    candidate_id: str
    candidate_type: str
    corridor_id: str
    district: str
    detected_at: datetime
    confidence: float
    operational_severity: float
    corridor_priority: int
    exposure_significance: float
    breach_suspicion: float
    before_sar_url: str
    after_sar_url: str
    optical_support_url: str | None = None
    baseline_overlay_url: str
    confidence_breakdown: dict[str, float]
    exposure_summary: dict[str, float]
    source_scene_references: list[str]
    system_notes: str
