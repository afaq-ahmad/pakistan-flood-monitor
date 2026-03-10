from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from pakistan_flood_monitor.config import settings
from pakistan_flood_monitor.pipeline.runner import FloodMonitoringPipeline

app = FastAPI(title="Pakistan Flood Monitor API", version="0.3.0")
pipeline = FloodMonitoringPipeline()
run_history: dict[str, list[dict[str, Any]]] = {}
event_store: dict[str, dict[str, Any]] = {}
review_audit_log: list[dict[str, Any]] = []
threshold_registry: list[dict[str, Any]] = []
model_registry: list[dict[str, Any]] = []


class ReviewEventRequest(BaseModel):
    action: str
    actor: str
    analyst_confidence: float | None = None
    notes: str = ""
    reviewed_geometry: dict[str, Any] | None = None


class ThresholdRegistrationRequest(BaseModel):
    threshold_name: str
    file_path: str
    version: str
    actor: str
    notes: str = ""


class ModelRegistrationRequest(BaseModel):
    model_id: str
    training_data_snapshot_version: str
    training_config_path: str
    evaluation_report_path: str
    actor: str
    notes: str = ""


def _corridor_run_history(aoi_name: str) -> list[dict[str, Any]]:
    return run_history.get(aoi_name, [])


def _latest_run(aoi_name: str) -> dict[str, Any] | None:
    history = _corridor_run_history(aoi_name)
    return history[-1] if history else None


def _event_record_from_run(report: dict[str, Any]) -> dict[str, Any]:
    review_event = report["published_outputs"]["review_queue_event"]
    detection = report["detections"][0]
    exposure = report["published_outputs"]["asset_exposure_report"]
    confidence_breakdown = {
        "flood_probability": detection["flood_probability"],
        "breach_risk": detection["breach_risk_score"],
        "flood_signal_weighted": round(detection["flood_probability"] * 0.6, 4),
        "breach_signal_weighted": round(detection["breach_risk_score"] * 0.4, 4),
        "final_confidence": detection["confidence_score"],
    }
    return {
        "event_id": review_event["event_id"],
        "run_id": report["run_id"],
        "aoi": review_event["aoi"],
        "event_class": review_event["event_class"],
        "status": review_event["decision"] or "pending_review",
        "queue_status": detection["review_status"],
        "machine_confidence": review_event["machine_confidence"],
        "analyst_confidence": review_event["analyst_confidence"],
        "confidence_bucket": _confidence_bucket(review_event["machine_confidence"]),
        "source_scenes": review_event["source_scenes"],
        "notes": review_event["notes"],
        "timestamps": {
            "detected_at": detection["timestamp"],
            "published_at": datetime.now(UTC).isoformat(),
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [67.0, 24.0],
                    [67.2, 24.0],
                    [67.2, 24.2],
                    [67.0, 24.2],
                    [67.0, 24.0],
                ]
            ],
        },
        "event_area_km2": detection["flood_area_km2"],
        "confidence_breakdown": confidence_breakdown,
        "exposure": exposure,
        "latest_event_summary": {
            "alert_level": detection["alert_level"],
            "summary": report["published_outputs"]["alert_feed_item"]["summary"],
        },
        "candidate_persistence_hours": round(max(detection["flood_probability"], 0.01) * 48, 2),
    }


def _record_run(report: dict[str, Any]) -> None:
    corridor = report["detections"][0]["aoi"]
    run_history.setdefault(corridor, []).append(report)
    event = _event_record_from_run(report)
    event_store[event["event_id"]] = event


def _all_events() -> list[dict[str, Any]]:
    return sorted(event_store.values(), key=lambda event: event["timestamps"]["detected_at"], reverse=True)


def _event_by_id(event_id: str) -> dict[str, Any] | None:
    return event_store.get(event_id)


def _confidence_bucket(score_percent: float) -> str:
    if score_percent >= 75:
        return "high"
    if score_percent >= 50:
        return "medium"
    return "low"



@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/run/{aoi_name}")
def run_pipeline(aoi_name: str):
    report = pipeline.run_daily(aoi_name).model_dump()
    _record_run(report)
    return report


@app.get("/publish/{aoi_name}")
def get_published_outputs(aoi_name: str):
    report = _latest_run(aoi_name)
    if not report:
        raise HTTPException(status_code=404, detail="No run found for AOI. Execute /run/{aoi_name} first.")

    return {
        "map_layers": {
            "flood_candidate_map": report["published_outputs"]["flood_candidate_map"],
            "confirmed_flood_extent": report["published_outputs"]["confirmed_flood_extent"],
            "breach_suspicion_layer": report["published_outputs"]["breach_suspicion_layer"],
        },
        "event_tables": report["detections"],
        "alert_summaries": report["published_outputs"]["alert_feed_item"],
        "api_outputs": report,
    }


@app.get("/alerts/feed")
def alert_feed():
    return [
        run["published_outputs"]["alert_feed_item"]
        for runs in run_history.values()
        for run in runs
        if run["detections"][0]["review_status"] == "analyst_validated"
    ]


@app.get("/corridors")
def corridors() -> list[dict]:
    response = []
    for corridor in settings.pilot_corridors:
        latest = _latest_run(corridor.name)
        detection = latest["detections"][0] if latest else None
        response.append(
            {
                "corridor_id": corridor.name,
                "district": corridor.district,
                "priority": corridor.priority,
                "active": True,
                "latest_operational_state": {
                    "run_id": latest["run_id"] if latest else None,
                    "alert_level": detection["alert_level"] if detection else "unknown",
                    "review_status": detection["review_status"] if detection else "no_runs",
                },
            }
        )
    return response


@app.get("/corridors/{aoi_name}/status")
def corridor_status(aoi_name: str) -> dict:
    report = _latest_run(aoi_name)
    if not report:
        raise HTTPException(status_code=404, detail="No status found for AOI.")
    detection = report["detections"][0]
    latest_event = _event_record_from_run(report)
    return {
        "corridor_id": aoi_name,
        "latest_hydromet_stress": {
            "rainfall_mm_72h": detection["indicators"].get("rainfall_mm_72h", 0.0),
            "glofas_return_period": detection["indicators"].get("glofas_return_period", 0.0),
            "trigger_reason": report["trigger_reason"],
        },
        "latest_scene_time": detection["timestamp"],
        "queue_status": detection["review_status"],
        "latest_event_summary": latest_event["latest_event_summary"],
    }


@app.get("/corridors/{aoi_name}/events")
def corridor_events(
    aoi_name: str,
    status: str | None = Query(default=None),
    confidence_bucket: str | None = Query(default=None),
) -> list[dict]:
    history = _corridor_run_history(aoi_name)
    if not history:
        raise HTTPException(status_code=404, detail="No events found for AOI.")

    records = [_event_record_from_run(report) for report in history]
    if status:
        records = [event for event in records if event["status"] == status]
    if confidence_bucket:
        records = [event for event in records if event["confidence_bucket"] == confidence_bucket]

    return [
        {
            "event_id": event["event_id"],
            "class": event["event_class"],
            "status": event["status"],
            "confidence_bucket": event["confidence_bucket"],
            "machine_confidence": event["machine_confidence"],
            "detected_at": event["timestamps"]["detected_at"],
        }
        for event in records
    ]


@app.get("/events/{event_id}")
def get_event(event_id: str) -> dict:
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    return {
        "event_id": event["event_id"],
        "class": event["event_class"],
        "status": event["status"],
        "geometry": event["geometry"],
        "source_scenes": event["source_scenes"],
        "confidence_breakdown": event["confidence_breakdown"],
        "notes": event["notes"],
        "timestamps": event["timestamps"],
    }


@app.get("/events/{event_id}/exposure")
def get_event_exposure(event_id: str) -> dict:
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    return {
        "event_id": event_id,
        "district": event["exposure"]["district"],
        "asset_summary": event["exposure"]["asset_class_exposure"],
    }


@app.get("/events/{event_id}/historical")
def get_event_historical(event_id: str) -> dict[str, Any]:
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    history = _corridor_run_history(event["aoi"])
    trend = [
        {
            "run_id": report["run_id"],
            "timestamp": report["detections"][0]["timestamp"],
            "event_area_km2": report["detections"][0]["flood_area_km2"],
            "candidate_persistence_hours": round(max(report["detections"][0]["flood_probability"], 0.01) * 48, 2),
        }
        for report in history
    ]
    return {"event_id": event_id, "event_area_trend": trend, "candidate_persistence_hours": event["candidate_persistence_hours"]}


@app.get("/events/{event_id}/confidence")
def get_event_confidence(event_id: str) -> dict[str, Any]:
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    return {"event_id": event_id, "confidence_breakdown": event["confidence_breakdown"]}


@app.get("/alerts/latest")
def latest_alerts() -> list[dict]:
    return [
        event["latest_event_summary"] | {"event_id": event["event_id"], "aoi": event["aoi"]}
        for event in _all_events()
        if event["status"] in {"accept", "published"}
    ]


@app.get("/breach-candidates")
def breach_candidates() -> list[dict]:
    items = []
    for event in _all_events():
        if event["event_class"] != "possible_breach":
            continue
        confidence = event["confidence_breakdown"]
        items.append(
            {
                "event_id": event["event_id"],
                "corridor_id": event["aoi"],
                "queue_status": event["queue_status"],
                "score_components": {
                    "breach_risk": confidence["breach_risk"],
                    "flood_probability": confidence["flood_probability"],
                    "final_confidence": confidence["final_confidence"],
                },
            }
        )
    return items


@app.post("/admin/reprocess-scene")
def admin_reprocess_scene(aoi_name: str) -> dict:
    report = pipeline.run_daily(aoi_name).model_dump()
    _record_run(report)
    return {
        "status": "reprocessed",
        "run_id": report["run_id"],
        "aoi": aoi_name,
        "history_depth": len(_corridor_run_history(aoi_name)),
    }


@app.post("/admin/review-event")
def admin_review_event(event_id: str, payload: ReviewEventRequest) -> dict:
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    old_status = event["status"]
    event["status"] = payload.action
    event["analyst_confidence"] = payload.analyst_confidence
    if payload.notes:
        event["notes"] = payload.notes
    if payload.reviewed_geometry:
        event["geometry"] = payload.reviewed_geometry

    review_audit_log.append(
        {
            "event_id": event_id,
            "actor": payload.actor,
            "action": payload.action,
            "changed_at": datetime.now(UTC).isoformat(),
            "old_status": old_status,
            "new_status": event["status"],
            "notes": payload.notes,
        }
    )
    return {"status": "review_updated", "event": event}


@app.get("/admin/review-audit")
def admin_review_audit() -> list[dict[str, Any]]:
    return review_audit_log


@app.post("/admin/register-threshold")
def register_threshold(payload: ThresholdRegistrationRequest) -> dict[str, Any]:
    record = payload.model_dump() | {"registered_at": datetime.now(UTC).isoformat()}
    threshold_registry.append(record)
    return {"status": "registered", "threshold": record}


@app.post("/admin/register-model")
def register_model(payload: ModelRegistrationRequest) -> dict[str, Any]:
    record = payload.model_dump() | {"registered_at": datetime.now(UTC).isoformat()}
    model_registry.append(record)
    return {"status": "registered", "model": record}
