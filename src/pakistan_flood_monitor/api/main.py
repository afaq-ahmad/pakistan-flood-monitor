from __future__ import annotations

from datetime import UTC, datetime
import os
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.services.observability import metrics_registry

from pakistan_flood_monitor.config import settings
from pakistan_flood_monitor.pipeline.runner import FloodMonitoringPipeline

app = FastAPI(title="Pakistan Flood Monitor API", version="0.3.0")
pipeline = FloodMonitoringPipeline()
run_history: dict[str, list[dict[str, Any]]] = {}
event_store: dict[str, dict[str, Any]] = {}
historical_event_library: dict[str, dict[str, Any]] = {}
review_audit_log: list[dict[str, Any]] = []
threshold_registry: list[dict[str, Any]] = []
model_registry: list[dict[str, Any]] = []
retraining_decisions: list[dict[str, Any]] = []
privileged_audit_log: list[dict[str, Any]] = []

public_router = APIRouter(prefix="/public", tags=["public"])
internal_router = APIRouter(prefix="/internal", tags=["internal"])
security_scheme = HTTPBearer(auto_error=False)


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
    threshold_values: dict[str, float] = Field(default_factory=dict)
    linked_model_id: str | None = None
    actor: str
    notes: str = ""




class RetrainingTriggerRequest(BaseModel):
    model_id: str
    label_quality_gain: float
    drift_score: float
    feature_schema_changed: bool = False
    actor: str
    notes: str = ""


class HistoricalDateRange(BaseModel):
    start: datetime
    end: datetime


class HistoricalEventCatalogRecord(BaseModel):
    event_name: str
    corridor_reach: str
    date_range: HistoricalDateRange
    peak_date: datetime
    source_scenes: list[str] = Field(default_factory=list)
    rainfall_context: dict[str, float | str] = Field(default_factory=dict)
    forecast_context: dict[str, float | str] = Field(default_factory=dict)
    known_embankment_notes: str = ""
    label_quality_score: float = Field(default=0.4, ge=0.0, le=1.0)


class HistoricalEventAssets(BaseModel):
    reviewed_polygons: list[str] = Field(default_factory=list)
    source_rasters: list[str] = Field(default_factory=list)
    screenshots: list[str] = Field(default_factory=list)
    analyst_notes: list[str] = Field(default_factory=list)
    partner_references: list[str] = Field(default_factory=list)


class HistoricalEventRecord(BaseModel):
    event_id: str
    run_id: str
    catalog: HistoricalEventCatalogRecord
    assets: HistoricalEventAssets
    status: str
    created_at: str
    updated_at: str


def _evaluate_retraining_trigger(payload: RetrainingTriggerRequest) -> dict[str, Any]:
    reasons: list[str] = []
    if payload.label_quality_gain >= 0.1:
        reasons.append("label_quality_improved")
    if payload.drift_score >= 0.2:
        reasons.append("data_drift_detected")
    if payload.feature_schema_changed:
        reasons.append("sensor_or_feature_changed")
    return {"should_retrain": bool(reasons), "reasons": reasons}

class ModelRegistrationRequest(BaseModel):
    model_id: str
    model_type: str
    training_data_snapshot_version: str
    training_config_path: str
    evaluation_report_path: str
    validation_metrics: dict[str, float] = Field(default_factory=dict)
    deployment_status: str = "candidate"
    rollback_parent_model_id: str | None = None
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
    _upsert_historical_event_from_event(event)
    metrics_registry.increment("pipeline.alerts_published")
    metrics_registry.set_gauge("ops.queue_backlog", float(sum(len(v) for v in run_history.values())))


def _all_events() -> list[dict[str, Any]]:
    return sorted(event_store.values(), key=lambda event: event["timestamps"]["detected_at"], reverse=True)


def _event_by_id(event_id: str) -> dict[str, Any] | None:
    return event_store.get(event_id)


def _upsert_historical_event_from_event(event: dict[str, Any]) -> None:
    existing = historical_event_library.get(event["event_id"])
    detected_at = event["timestamps"]["detected_at"]
    now_iso = datetime.now(UTC).isoformat()
    rainfall = event["confidence_breakdown"]["flood_probability"]
    forecast = event["confidence_breakdown"]["breach_risk"]

    if existing is None:
        event_record = HistoricalEventRecord(
            event_id=event["event_id"],
            run_id=event["run_id"],
            status=event["status"],
            created_at=now_iso,
            updated_at=now_iso,
            catalog=HistoricalEventCatalogRecord(
                event_name=f"{event['aoi']} {event['event_class']} event",
                corridor_reach=event["aoi"],
                date_range=HistoricalDateRange(start=detected_at, end=detected_at),
                peak_date=detected_at,
                source_scenes=event["source_scenes"],
                rainfall_context={"rainfall_signal": rainfall},
                forecast_context={"forecast_signal": forecast},
                known_embankment_notes="No embankment notes captured yet.",
                label_quality_score=0.4,
            ),
            assets=HistoricalEventAssets(
                reviewed_polygons=[],
                source_rasters=[f"derived/{event['aoi']}/{event['run_id']}/flood_mask.tif"],
                screenshots=[],
                analyst_notes=[event.get("notes", "")],
                partner_references=[],
            ),
        )
    else:
        event_record = HistoricalEventRecord.model_validate(existing)
        event_record.status = event["status"]
        event_record.updated_at = now_iso
        event_record.catalog.source_scenes = event["source_scenes"]
        event_record.assets.source_rasters = [f"derived/{event['aoi']}/{event['run_id']}/flood_mask.tif"]
        if event.get("notes"):
            event_record.assets.analyst_notes.append(event["notes"])

    historical_event_library[event["event_id"]] = event_record.model_dump()


def _training_export_package(*, min_label_quality: float, include_pending: bool) -> dict[str, Any]:
    records = [HistoricalEventRecord.model_validate(item) for item in historical_event_library.values()]
    if not include_pending:
        records = [r for r in records if r.status in {"accept", "published"}]
    records = [r for r in records if r.catalog.label_quality_score >= min_label_quality]

    return {
        "manifest": {
            "generated_at": datetime.now(UTC).isoformat(),
            "record_count": len(records),
            "min_label_quality": min_label_quality,
            "include_pending": include_pending,
            "schema_version": "historical-event-library-v1",
        },
        "events": [
            {
                "event_id": record.event_id,
                "event_name": record.catalog.event_name,
                "corridor_reach": record.catalog.corridor_reach,
                "date_range": record.catalog.date_range.model_dump(),
                "peak_date": record.catalog.peak_date,
                "source_scenes": record.catalog.source_scenes,
                "rainfall_context": record.catalog.rainfall_context,
                "forecast_context": record.catalog.forecast_context,
                "known_embankment_notes": record.catalog.known_embankment_notes,
                "label_quality_score": record.catalog.label_quality_score,
                "reviewed_polygons": record.assets.reviewed_polygons,
                "source_rasters": record.assets.source_rasters,
                "screenshots": record.assets.screenshots,
                "analyst_notes": record.assets.analyst_notes,
                "partner_references": record.assets.partner_references,
                "status": record.status,
            }
            for record in records
        ],
    }


def _confidence_bucket(score_percent: float) -> str:
    if score_percent >= 75:
        return "high"
    if score_percent >= 50:
        return "medium"
    return "low"


def _audit_privileged_action(*, actor: str, action: str, resource_type: str, resource_id: str, details: dict[str, Any] | None = None) -> None:
    privileged_audit_log.append(
        {
            "actor": actor,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "details": details or {},
        }
    )


def _resolve_role(token: str) -> str | None:
    admin_token = os.getenv("FLOOD_MONITOR_ADMIN_TOKEN")
    analyst_token = os.getenv("FLOOD_MONITOR_ANALYST_TOKEN")
    if admin_token and token == admin_token:
        return "admin"
    if analyst_token and token == analyst_token:
        return "analyst"
    return None


def _require_role(*allowed_roles: str):
    def _verify_token(credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme)) -> str:
        if credentials is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

        role = _resolve_role(credentials.credentials)
        if role is None or role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")
        return role

    return _verify_token


def _ensure_published_event(event: dict[str, Any]) -> None:
    if event["status"] not in {"accept", "published"}:
        raise HTTPException(status_code=404, detail="Event not found.")



@app.get("/health")
def health() -> dict[str, str | float]:
    metrics_registry.set_gauge("ops.api_uptime", 1.0)
    return {"status": "ok", "api_uptime": 1.0}


@internal_router.get("/run/{aoi_name}", dependencies=[Depends(_require_role("admin"))])
def run_pipeline(aoi_name: str):
    report = pipeline.run_daily(aoi_name).model_dump()
    _record_run(report)
    return report


@public_router.get("/publish/{aoi_name}")
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


@public_router.get("/alerts/feed")
def alert_feed():
    return [
        run["published_outputs"]["alert_feed_item"]
        for runs in run_history.values()
        for run in runs
        if run["detections"][0]["review_status"] == "analyst_validated"
    ]


@public_router.get("/corridors")
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


@public_router.get("/corridors/{aoi_name}/status")
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


@public_router.get("/corridors/{aoi_name}/events")
def corridor_events(
    aoi_name: str,
    status: str | None = Query(default=None),
    confidence_bucket: str | None = Query(default=None),
) -> list[dict]:
    history = _corridor_run_history(aoi_name)
    if not history:
        raise HTTPException(status_code=404, detail="No events found for AOI.")

    records = [_event_record_from_run(report) for report in history]
    records = [event for event in records if event["status"] in {"accept", "published"}]
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


@public_router.get("/events/{event_id}")
def get_event(event_id: str) -> dict:
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    _ensure_published_event(event)
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


@public_router.get("/events/{event_id}/exposure")
def get_event_exposure(event_id: str) -> dict:
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    _ensure_published_event(event)
    return {
        "event_id": event_id,
        "district": event["exposure"]["district"],
        "asset_summary": event["exposure"]["asset_class_exposure"],
    }


@public_router.get("/events/{event_id}/historical")
def get_event_historical(event_id: str) -> dict[str, Any]:
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    _ensure_published_event(event)

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


@public_router.get("/historical-events")
def list_historical_events(corridor_reach: str | None = Query(default=None)) -> list[dict[str, Any]]:
    records = [HistoricalEventRecord.model_validate(item) for item in historical_event_library.values()]
    if corridor_reach:
        records = [record for record in records if record.catalog.corridor_reach == corridor_reach]
    return [
        {
            "event_id": record.event_id,
            "event_name": record.catalog.event_name,
            "corridor_reach": record.catalog.corridor_reach,
            "peak_date": record.catalog.peak_date,
            "label_quality_score": record.catalog.label_quality_score,
            "status": record.status,
        }
        for record in records
    ]


@public_router.get("/historical-events/{event_id}")
def get_historical_event(event_id: str) -> dict[str, Any]:
    record = historical_event_library.get(event_id)
    if not record:
        raise HTTPException(status_code=404, detail="Historical event not found.")
    parsed = HistoricalEventRecord.model_validate(record)
    return parsed.model_dump()


@public_router.get("/events/{event_id}/confidence")
def get_event_confidence(event_id: str) -> dict[str, Any]:
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    _ensure_published_event(event)
    return {"event_id": event_id, "confidence_breakdown": event["confidence_breakdown"]}


@public_router.get("/alerts/latest")
def latest_alerts() -> list[dict]:
    return [
        event["latest_event_summary"] | {"event_id": event["event_id"], "aoi": event["aoi"]}
        for event in _all_events()
        if event["status"] in {"accept", "published"}
    ]


@internal_router.get("/breach-candidates", dependencies=[Depends(_require_role("admin", "analyst"))])
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




@internal_router.get("/monitoring/metrics", dependencies=[Depends(_require_role("admin", "analyst"))])
def monitoring_metrics() -> dict[str, Any]:
    snapshot = metrics_registry.snapshot()
    return {
        "pipeline_metrics": {
            "discovery_count": snapshot.counters.get("pipeline.discovery_count", 0.0),
            "download_failures": snapshot.counters.get("pipeline.download_failures", 0.0),
            "aois_processed": snapshot.counters.get("pipeline.aois_processed", 0.0),
            "candidates_created": snapshot.counters.get("pipeline.candidates_created", 0.0),
            "alerts_published": snapshot.counters.get("pipeline.alerts_published", 0.0),
            "processing_latency": snapshot.latencies_ms.get("pipeline.processing_latency_ms", {}),
        },
        "ops_metrics": {
            "disk_usage": {
                "total_bytes": snapshot.gauges.get("ops.disk.total_bytes", 0.0),
                "used_bytes": snapshot.gauges.get("ops.disk.used_bytes", 0.0),
                "free_bytes": snapshot.gauges.get("ops.disk.free_bytes", 0.0),
            },
            "queue_backlog": snapshot.gauges.get("ops.queue_backlog", 0.0),
            "api_uptime": snapshot.gauges.get("ops.api_uptime", 0.0),
            "response_latency": snapshot.latencies_ms.get("ops.response_latency_ms", {}),
            "stale_job_count": snapshot.gauges.get("ops.stale_job_count", 0.0),
        },
        "product_metrics": {
            "alerts_produced": snapshot.counters.get("product.alerts_produced", 0.0),
            "alerts_confirmed": snapshot.counters.get("product.alerts_confirmed", 0.0),
            "false_alarms": snapshot.counters.get("product.false_alarms", 0.0),
            "scene_to_alert_delay": snapshot.latencies_ms.get("product.scene_to_alert_delay_ms", {}),
            "analyst_hours_saved_proxy": snapshot.counters.get("product.analyst_hours_saved_proxy", 0.0),
            "exposure_outputs_delivered": snapshot.counters.get("product.exposure_outputs_delivered", 0.0),
        },
    }
@internal_router.post("/admin/reprocess-scene", dependencies=[Depends(_require_role("admin"))])
def admin_reprocess_scene(aoi_name: str) -> dict:
    report = pipeline.run_daily(aoi_name).model_dump()
    _record_run(report)
    _audit_privileged_action(actor="system-admin", action="reprocess", resource_type="corridor", resource_id=aoi_name)
    return {
        "status": "reprocessed",
        "run_id": report["run_id"],
        "aoi": aoi_name,
        "history_depth": len(_corridor_run_history(aoi_name)),
    }


@internal_router.post("/admin/review-event", dependencies=[Depends(_require_role("admin", "analyst"))])
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

    _upsert_historical_event_from_event(event)
    historical_record = HistoricalEventRecord.model_validate(historical_event_library[event_id])
    historical_record.catalog.label_quality_score = max(historical_record.catalog.label_quality_score, 0.85)
    if payload.reviewed_geometry:
        historical_record.assets.reviewed_polygons = [f"published/{event['aoi']}/{event_id}/reviewed_extent.geojson"]
    if payload.notes:
        historical_record.assets.analyst_notes.append(payload.notes)
    historical_record.updated_at = datetime.now(UTC).isoformat()
    historical_event_library[event_id] = historical_record.model_dump()

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
    _audit_privileged_action(
        actor=payload.actor,
        action="review",
        resource_type="event",
        resource_id=event_id,
        details={"old_status": old_status, "new_status": event["status"]},
    )
    if payload.action in {"accept", "published"}:
        metrics_registry.increment("product.alerts_confirmed")
        metrics_registry.increment("product.analyst_hours_saved_proxy", 0.75)
    if payload.action in {"reject", "false_alarm"}:
        metrics_registry.increment("product.false_alarms")
    return {"status": "review_updated", "event": event}


@internal_router.get("/admin/review-audit", dependencies=[Depends(_require_role("admin", "analyst"))])
def admin_review_audit() -> list[dict[str, Any]]:
    return review_audit_log


@internal_router.get("/admin/historical-events", dependencies=[Depends(_require_role("admin", "analyst"))])
def admin_list_historical_events() -> list[dict[str, Any]]:
    return [HistoricalEventRecord.model_validate(item).model_dump() for item in historical_event_library.values()]


@internal_router.get("/admin/historical-events/export", dependencies=[Depends(_require_role("admin", "analyst"))])
def admin_export_historical_events(
    min_label_quality: float = Query(default=0.8, ge=0.0, le=1.0),
    include_pending: bool = Query(default=False),
) -> dict[str, Any]:
    return _training_export_package(min_label_quality=min_label_quality, include_pending=include_pending)


@internal_router.get("/admin/historical-events/{event_id}", dependencies=[Depends(_require_role("admin", "analyst"))])
def admin_get_historical_event(event_id: str) -> dict[str, Any]:
    record = historical_event_library.get(event_id)
    if not record:
        raise HTTPException(status_code=404, detail="Historical event not found.")
    return HistoricalEventRecord.model_validate(record).model_dump()


@internal_router.post("/admin/register-threshold", dependencies=[Depends(_require_role("admin"))])
def register_threshold(payload: ThresholdRegistrationRequest) -> dict[str, Any]:
    record = payload.model_dump() | {"registered_at": datetime.now(UTC).isoformat()}
    threshold_registry.append(record)
    _audit_privileged_action(
        actor=payload.actor,
        action="threshold_change",
        resource_type="threshold",
        resource_id=payload.threshold_name,
        details={"version": payload.version, "file_path": payload.file_path},
    )
    return {"status": "registered", "threshold": record}


@internal_router.post("/admin/register-model", dependencies=[Depends(_require_role("admin"))])
def register_model(payload: ModelRegistrationRequest) -> dict[str, Any]:
    record = payload.model_dump() | {"registered_at": datetime.now(UTC).isoformat()}
    model_registry.append(record)
    _audit_privileged_action(
        actor=payload.actor,
        action="publish",
        resource_type="model",
        resource_id=payload.model_id,
        details={"training_data_snapshot_version": payload.training_data_snapshot_version},
    )
    return {"status": "registered", "model": record}




@internal_router.post("/admin/evaluate-retraining", dependencies=[Depends(_require_role("admin"))])
def evaluate_retraining(payload: RetrainingTriggerRequest) -> dict[str, Any]:
    decision = _evaluate_retraining_trigger(payload)
    record = payload.model_dump() | decision | {"evaluated_at": datetime.now(UTC).isoformat()}
    retraining_decisions.append(record)
    _audit_privileged_action(
        actor=payload.actor,
        action="retraining_evaluated",
        resource_type="model",
        resource_id=payload.model_id,
        details=decision,
    )
    return {"status": "evaluated", "decision": record}

@internal_router.get("/admin/privileged-audit", dependencies=[Depends(_require_role("admin"))])
def privileged_audit() -> list[dict[str, Any]]:
    return privileged_audit_log


app.include_router(public_router)
app.include_router(internal_router)
