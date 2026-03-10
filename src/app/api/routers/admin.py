from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.pipelines import publish_events_pipeline
from app.schemas.review import ReviewActionRequest, ReviewCandidateInput
from app.services.review import ReviewCandidate, review_service

router = APIRouter()


@router.post("/publish")
def publish_events() -> dict[str, str]:
    return {"run": publish_events_pipeline()}


@router.post("/review/queue")
def generate_review_queue(candidates: list[ReviewCandidateInput]) -> list[dict]:
    packets = review_service.generate_review_queue([ReviewCandidate(**candidate.model_dump()) for candidate in candidates])
    return [
        {
            "rank": packet.rank,
            "review_score": packet.review_score,
            "candidate_id": packet.candidate.candidate_id,
            "candidate_type": packet.candidate.candidate_type,
            "district": packet.candidate.district,
            "links": {
                "before_sar": packet.candidate.before_sar_url,
                "after_sar": packet.candidate.after_sar_url,
                "optical_support": packet.candidate.optical_support_url,
                "baseline_overlay": packet.candidate.baseline_overlay_url,
            },
            "confidence_breakdown": packet.candidate.confidence_breakdown,
            "exposure_summary": packet.candidate.exposure_summary,
            "source_scene_references": packet.candidate.source_scene_references,
            "system_notes": packet.candidate.system_notes,
        }
        for packet in packets
    ]


@router.get("/review/queue")
def list_review_queue() -> list[dict]:
    return [
        {
            "candidate_id": item.candidate.candidate_id,
            "status": item.status,
            "class": item.candidate_class,
            "analyst_confidence": item.analyst_confidence,
            "notes": item.notes,
            "geometry": {
                "original_machine_geometry": item.geometry.original_machine_geometry if item.geometry else None,
                "analyst_edited_geometry": item.geometry.analyst_edited_geometry if item.geometry else None,
                "final_published_geometry": item.geometry.final_published_geometry if item.geometry else None,
            },
        }
        for item in review_service.list_queue()
    ]


@router.post("/review/{candidate_id}/actions")
def review_action(candidate_id: str, payload: ReviewActionRequest) -> dict:
    try:
        item = review_service.apply_action(
            candidate_id=candidate_id,
            action=payload.action,
            actor=payload.actor,
            notes=payload.notes,
            geometry=payload.geometry,
            candidate_class=payload.candidate_class,
            analyst_confidence=payload.analyst_confidence,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "candidate_id": item.candidate.candidate_id,
        "status": item.status,
        "class": item.candidate_class,
        "analyst_confidence": item.analyst_confidence,
        "notes": item.notes,
    }


@router.get("/review/audit")
def review_audit() -> list[dict]:
    return [
        {
            "candidate_id": record.candidate_id,
            "actor": record.actor,
            "changed_at": record.changed_at.isoformat(),
            "old_status": record.old_status,
            "new_status": record.new_status,
            "old_geometry_ref": record.old_geometry_ref,
            "new_geometry_ref": record.new_geometry_ref,
            "notes": record.notes,
        }
        for record in review_service.audit_records()
    ]
