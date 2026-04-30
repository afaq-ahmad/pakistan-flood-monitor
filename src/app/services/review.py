from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

ReviewDecision = Literal["accepted", "rejected", "needs_revision", "published"]

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"accepted", "rejected", "needs_revision"},
    "needs_revision": {"accepted", "rejected"},
    "accepted": {"published", "needs_revision"},
    "published": set(),
    "rejected": set(),
}


@dataclass(slots=True)
class ReviewCandidate:
    candidate_id: str
    candidate_type: Literal["flood", "breach"]
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
    optical_support_url: str | None
    baseline_overlay_url: str
    confidence_breakdown: dict[str, float]
    exposure_summary: dict[str, float]
    source_scene_references: list[str]
    system_notes: str


@dataclass(slots=True)
class ReviewGeometryState:
    original_machine_geometry: dict
    analyst_edited_geometry: dict | None = None
    final_published_geometry: dict | None = None


@dataclass(slots=True)
class ReviewAuditRecord:
    candidate_id: str
    actor: str
    changed_at: datetime
    old_status: str
    new_status: str
    old_geometry_ref: str | None
    new_geometry_ref: str | None
    notes: str | None = None


@dataclass(slots=True)
class ReviewPacket:
    rank: int
    review_score: float
    candidate: ReviewCandidate


@dataclass(slots=True)
class ReviewItemState:
    candidate: ReviewCandidate
    status: str = "queued"
    candidate_class: str = "flood"
    analyst_confidence: float | None = None
    notes: list[str] = field(default_factory=list)
    assigned_analyst: str | None = None
    geometry: ReviewGeometryState | None = None


class AnalystReviewService:
    def __init__(self) -> None:
        self._items: dict[str, ReviewItemState] = {}
        self._audit_log: list[ReviewAuditRecord] = []

    @staticmethod
    def _compute_review_score(candidate: ReviewCandidate, now: datetime) -> float:
        recency_hours = max((now - candidate.detected_at).total_seconds() / 3600.0, 0.0)
        recency_score = max(0.0, 1.0 - min(recency_hours / 72.0, 1.0))

        return (
            candidate.operational_severity * 0.30
            + min(candidate.corridor_priority / 5.0, 1.0) * 0.20
            + candidate.exposure_significance * 0.20
            + candidate.breach_suspicion * 0.15
            + recency_score * 0.15
        )

    def generate_review_queue(
        self,
        candidates: list[ReviewCandidate],
        now: datetime | None = None,
    ) -> list[ReviewPacket]:
        """Select medium/high confidence candidates, rank them, and create review packets."""
        reference_now = now or datetime.now(UTC)
        selected = [candidate for candidate in candidates if candidate.confidence >= 0.5]

        packets: list[tuple[ReviewCandidate, float]] = [
            (candidate, self._compute_review_score(candidate, reference_now)) for candidate in selected
        ]
        packets.sort(key=lambda row: row[1], reverse=True)

        output: list[ReviewPacket] = []
        for index, (candidate, score) in enumerate(packets, start=1):
            if candidate.candidate_id not in self._items:
                self._items[candidate.candidate_id] = ReviewItemState(
                    candidate=candidate,
                    candidate_class=candidate.candidate_type,
                    geometry=ReviewGeometryState(original_machine_geometry={"source": "machine-output"}),
                )
            output.append(ReviewPacket(rank=index, review_score=score, candidate=candidate))
        return output

    @staticmethod
    def _confidence_band(confidence: float) -> str:
        if confidence < 0.5:
            return "low"
        if confidence < 0.75:
            return "medium"
        return "high"

    def list_queue(
        self,
        *,
        corridor_id: str | None = None,
        candidate_class: str | None = None,
        review_status: str | None = None,
        detected_after: datetime | None = None,
        detected_before: datetime | None = None,
        breach_suspicion_min: float | None = None,
        confidence_band: str | None = None,
    ) -> list[ReviewItemState]:
        items = [item for item in self._items.values() if item.status in {"queued", "accepted", "needs_revision"}]
        if corridor_id is not None:
            items = [item for item in items if item.candidate.corridor_id == corridor_id]
        if candidate_class is not None:
            items = [item for item in items if item.candidate_class == candidate_class]
        if review_status is not None:
            items = [item for item in items if item.status == review_status]
        if detected_after is not None:
            items = [item for item in items if item.candidate.detected_at >= detected_after]
        if detected_before is not None:
            items = [item for item in items if item.candidate.detected_at <= detected_before]
        if breach_suspicion_min is not None:
            items = [item for item in items if item.candidate.breach_suspicion >= breach_suspicion_min]
        if confidence_band is not None:
            normalized_band = confidence_band.lower()
            items = [item for item in items if self._confidence_band(item.candidate.confidence) == normalized_band]
        return items

    def get(self, candidate_id: str) -> ReviewItemState:
        if candidate_id not in self._items:
            raise KeyError(f"Unknown candidate_id: {candidate_id}")
        return self._items[candidate_id]

    def _record_audit(
        self,
        *,
        candidate_id: str,
        actor: str,
        old_status: str,
        new_status: str,
        old_geometry_ref: str | None,
        new_geometry_ref: str | None,
        notes: str | None,
    ) -> None:
        self._audit_log.append(
            ReviewAuditRecord(
                candidate_id=candidate_id,
                actor=actor,
                changed_at=datetime.now(UTC),
                old_status=old_status,
                new_status=new_status,
                old_geometry_ref=old_geometry_ref,
                new_geometry_ref=new_geometry_ref,
                notes=notes,
            )
        )

    def apply_action(
        self,
        *,
        candidate_id: str,
        action: str,
        actor: str,
        notes: str | None = None,
        geometry: dict | None = None,
        candidate_class: str | None = None,
        analyst_confidence: float | None = None,
    ) -> ReviewItemState:
        item = self.get(candidate_id)
        old_status = item.status
        old_geometry_ref = _geometry_ref(item.geometry.analyst_edited_geometry if item.geometry else None)

        if notes:
            item.notes.append(notes)

        if candidate_class:
            item.candidate_class = candidate_class

        if analyst_confidence is not None:
            item.analyst_confidence = max(0.0, min(1.0, analyst_confidence))

        if geometry is not None and item.geometry is not None:
            item.geometry.analyst_edited_geometry = geometry

        status_change: str | None = None
        if action == "accept":
            status_change = "accepted"
        elif action == "reject":
            status_change = "rejected"
        elif action == "request_changes":
            status_change = "needs_revision"
        elif action == "publish_alert":
            status_change = "published"
            if item.geometry is not None:
                item.geometry.final_published_geometry = item.geometry.analyst_edited_geometry or item.geometry.original_machine_geometry
        elif action in {"edit_geometry", "change_class", "add_notes", "assign_confidence"}:
            pass
        else:
            raise ValueError(f"Unsupported review action: {action}")

        if status_change is not None:
            allowed_next = ALLOWED_TRANSITIONS.get(old_status, set())
            if status_change not in allowed_next:
                raise ValueError(
                    f"Invalid lifecycle transition from '{old_status}' to '{status_change}'. Allowed: {sorted(allowed_next)}"
                )
            item.status = status_change

        new_geometry = None
        if item.geometry is not None:
            new_geometry = item.geometry.final_published_geometry or item.geometry.analyst_edited_geometry
        self._record_audit(
            candidate_id=item.candidate.candidate_id,
            actor=actor,
            old_status=old_status,
            new_status=item.status,
            old_geometry_ref=old_geometry_ref,
            new_geometry_ref=_geometry_ref(new_geometry),
            notes=notes,
        )
        return item

    def audit_records(self) -> list[ReviewAuditRecord]:
        return self._audit_log.copy()


def _geometry_ref(geometry: dict | None) -> str | None:
    if geometry is None:
        return None
    return f"geometry:{abs(hash(str(geometry))) % 10_000_000}"


review_service = AnalystReviewService()
