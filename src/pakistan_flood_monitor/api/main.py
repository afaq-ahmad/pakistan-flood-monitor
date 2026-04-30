from __future__ import annotations

import base64
from datetime import UTC, datetime
import hashlib
import json
import os
from threading import Lock
import time
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.services.observability import metrics_registry

from pakistan_flood_monitor.config import settings
from pakistan_flood_monitor.pipeline.runner import FloodMonitoringPipeline
from pakistan_flood_monitor.services.gis_qa import publication_gate
from pakistan_flood_monitor.services.alert_templates import render_alert_template

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
state_lock = Lock()

public_router = APIRouter(prefix="/public", tags=["public"])
internal_router = APIRouter(prefix="/internal", tags=["internal"])
security_scheme = HTTPBearer(auto_error=False)


class RateLimiter:
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: dict[tuple[str, str], list[float]] = {}

    def allow(self, identity: str, path: str, limit: int, window_seconds: int) -> bool:
        if limit <= 0:
            return True
        now = time.time()
        window_start = now - window_seconds
        key = (identity, path)
        with self._lock:
            current = [stamp for stamp in self._requests.get(key, []) if stamp >= window_start]
            if len(current) >= limit:
                self._requests[key] = current
                return False
            current.append(now)
            self._requests[key] = current
            return True

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


rate_limiter = RateLimiter()

LIMITATIONS_PATH = "/public/limitations"
LIMITATIONS_STATEMENT = {
    "title": "Pakistan Flood Monitor limitations and intended use",
    "intended_use": "Supports situational awareness and analyst triage for potential flooding and embankment anomalies.",
    "confidence_and_uncertainty": "Confidence scores are model-derived estimates from SAR, hydromet, and rule-based signals and can be wrong, delayed, or incomplete.",
    "warning_limitations": "Alerts may miss events, include false positives, and can lag real-world conditions due to data latency and quality constraints.",
    "non_replacement_notice": "Do not use this system as a replacement for official emergency warnings, evacuation orders, or instructions from government authorities and disaster-management agencies.",
}
LIMITATIONS_STATEMENT_UR = {
    "title": "پاکستان فلڈ مانیٹر کی حدود اور مجوزہ استعمال",
    "intended_use": "ممکنہ سیلاب اور پشتے کی بے قاعدگی کی صورتحال میں آگاہی اور تجزیہ کار کی معاونت کے لیے۔",
    "confidence_and_uncertainty": "اعتماد کے اسکور SAR، ہائیڈرو میٹ، اور قواعدی اشاروں پر مبنی تخمینے ہیں اور غلط، تاخیر زدہ، یا نامکمل ہو سکتے ہیں۔",
    "warning_limitations": "الرٹس بعض واقعات کو نہیں پکڑ سکتے، غلط مثبت دے سکتے ہیں، اور ڈیٹا تاخیر یا معیار کی وجہ سے زمینی حالات سے پیچھے ہو سکتے ہیں۔",
    "non_replacement_notice": "اس نظام کو سرکاری ہنگامی انتباہات، انخلا کے احکامات، یا حکومتی ہدایات کے متبادل کے طور پر استعمال نہ کریں۔",
}

def _limitations_link() -> dict[str, str]:
    return {"href": LIMITATIONS_PATH, "rel": "limitations", "title": LIMITATIONS_STATEMENT["title"]}


def _attach_limitations(payload: dict[str, Any]) -> dict[str, Any]:
    existing = payload.get("limitations")
    if isinstance(existing, dict):
        link = _limitations_link()
        return payload | {"limitations": existing | link | {"link": link}}
    return payload | {"limitations": _limitations_link()}


def _apply_language(payload: dict[str, Any], language: str) -> dict[str, Any]:
    if language not in {"en", "ur"}:
        raise HTTPException(status_code=400, detail="language must be one of en|ur")
    localized = payload.get("localized", {})
    if language == "ur":
        payload = payload | {
            "language": "ur",
            "dir": "rtl",
            "a11y": (payload.get("a11y") or {}) | {"direction": "rtl", "language": ["en", "ur"]},
        }
        if isinstance(localized, dict):
            if isinstance(localized.get("disclaimer"), dict):
                payload["public_disclaimer"] = localized["disclaimer"].get("ur", payload.get("public_disclaimer"))
            if isinstance(localized.get("limitations_summary"), dict):
                payload.setdefault("limitations", {})["summary"] = localized["limitations_summary"].get("ur", payload.get("limitations", {}).get("summary"))
            if isinstance(localized.get("recommended_actions"), dict):
                payload["recommended_actions"] = localized["recommended_actions"].get("ur", payload.get("recommended_actions"))
        return payload
    return payload | {"language": "en", "dir": "ltr"}


LIFECYCLE_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"review"},
    "review": {"approved"},
    "approved": {"published"},
    "published": {"retracted"},
    "retracted": set(),
}


def _normalize_lifecycle_action(action: str) -> str:
    normalized = action.strip().lower()
    aliases = {
        "accept": "approved",
        "accepted": "approved",
        "publish": "published",
        "reject": "retracted",
    }
    return aliases.get(normalized, normalized)


def _validate_lifecycle_transition(current_state: str, requested_state: str) -> None:
    allowed = LIFECYCLE_TRANSITIONS.get(current_state, set())
    if requested_state not in allowed:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_lifecycle_transition",
                "current_state": current_state,
                "requested_state": requested_state,
                "allowed_transitions": sorted(allowed),
            },
        )


def _canonicalize(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _build_audit_entry(*, chain_name: str, action: str, principal_id: str, resource_type: str, resource_id: str, details: dict[str, Any] | None = None, previous_hash: str = "GENESIS") -> dict[str, Any]:
    timestamp = datetime.now(UTC).isoformat()
    payload = {
        "chain": chain_name,
        "action": action,
        "principal_id": principal_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {},
        "timestamp": timestamp,
        "previous_hash": previous_hash,
    }
    payload_hash = hashlib.sha256(_canonicalize(payload).encode("utf-8")).hexdigest()
    return payload | {"entry_hash": payload_hash, "actor": principal_id}


def _append_audit_entry(log: list[dict[str, Any]], entry: dict[str, Any]) -> None:
    log.append(entry)


def _verify_audit_chain(log: list[dict[str, Any]], chain_name: str) -> tuple[bool, str | None]:
    previous_hash = "GENESIS"
    for idx, row in enumerate(log):
        payload = {
            "chain": row.get("chain", chain_name),
            "action": row.get("action"),
            "principal_id": row.get("principal_id"),
            "resource_type": row.get("resource_type"),
            "resource_id": row.get("resource_id"),
            "details": row.get("details", {}),
            "timestamp": row.get("timestamp") or row.get("changed_at"),
            "previous_hash": row.get("previous_hash", previous_hash),
        }
        expected = hashlib.sha256(_canonicalize(payload).encode("utf-8")).hexdigest()
        if row.get("entry_hash") != expected:
            return False, f"{chain_name}[{idx}] hash mismatch"
        if payload["previous_hash"] != previous_hash:
            return False, f"{chain_name}[{idx}] previous_hash mismatch"
        previous_hash = expected
    return True, None


class ReviewEventRequest(BaseModel):
    action: str
    actor: str | None = Field(default=None, deprecated=True)
    analyst_confidence: float | None = None
    notes: str = ""
    reviewed_geometry: dict[str, Any] | None = None
    label_metadata: dict[str, Any] | None = None
    mapping_rules: dict[str, Any] | None = None


class ThresholdRegistrationRequest(BaseModel):
    threshold_name: str
    file_path: str
    version: str
    threshold_values: dict[str, float] = Field(default_factory=dict)
    linked_model_id: str | None = None
    actor: str | None = Field(default=None, deprecated=True)
    notes: str = ""




class RetrainingTriggerRequest(BaseModel):
    model_id: str
    label_quality_gain: float
    drift_score: float
    feature_schema_changed: bool = False
    actor: str | None = Field(default=None, deprecated=True)
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
    actor: str | None = Field(default=None, deprecated=True)
    notes: str = ""


class RiskSummaryRow(BaseModel):
    province: str
    district: str
    tehsil: str
    event_count: int
    risk_score: float
    exposure_score: float
    severity_score: float
    confidence_score: float
    latest_event_id: str | None = None
    latest_event_status: str | None = None
    latest_review_status: str | None = None


def _corridor_run_history(aoi_name: str) -> list[dict[str, Any]]:
    return run_history.get(aoi_name, [])


def _latest_run(aoi_name: str) -> dict[str, Any] | None:
    history = _corridor_run_history(aoi_name)
    return history[-1] if history else None


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _simple_pdf(lines: list[str]) -> bytes:
    content = "BT /F1 11 Tf 40 800 Td " + " T* ".join(f"({_pdf_escape(line)}) Tj" for line in lines) + " ET"
    stream = content.encode("latin-1", errors="replace")
    objs = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n",
        f"4 0 obj << /Length {len(stream)} >> stream\n".encode() + stream + b"\nendstream endobj\n",
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode())
    pdf.extend(f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(pdf)


def _latest_reviewed_or_approved_event() -> dict[str, Any] | None:
    candidates = [evt for evt in event_store.values() if evt.get("status") in {"review", "approved", "published"}]
    if not candidates:
        return None
    return sorted(candidates, key=lambda e: e.get("timestamps", {}).get("detected_at", ""))[-1]


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
        "status": "draft",
        "queue_status": detection["review_status"],
        "machine_confidence": review_event["machine_confidence"],
        "analyst_confidence": review_event["analyst_confidence"],
        "confidence_bucket": _confidence_bucket(review_event["machine_confidence"]),
        "source_scenes": review_event["source_scenes"],
        "lineage": review_event.get("lineage"),
        "district_overlays": [review_event["aoi"]],
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
        "approval_trace": [],
    }


def _record_run(report: dict[str, Any]) -> None:
    corridor = report["detections"][0]["aoi"]
    with state_lock:
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


def _admin_breakdown_for_event(event: dict[str, Any]) -> list[dict[str, str]]:
    overlays = event.get("admin_overlays")
    if isinstance(overlays, list) and overlays:
        return [item for item in overlays if isinstance(item, dict)]
    aoi = str(event.get("aoi", "unknown"))
    return [{"province": aoi, "district": aoi, "tehsil": f"{aoi}-central"}]


def _summarize_risk_rows(
    *,
    level: str,
    province: str | None = None,
    district: str | None = None,
    only_reviewed: bool = True,
) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str], dict[str, Any]] = {}
    for event in _all_events():
        if only_reviewed and event.get("status") not in {"approved", "published"}:
            continue
        for admin in _admin_breakdown_for_event(event):
            admin_province = admin.get("province", "unknown")
            admin_district = admin.get("district", "unknown")
            admin_tehsil = admin.get("tehsil", "unknown")
            if province and admin_province != province:
                continue
            if district and admin_district != district:
                continue
            key = (admin_province, admin_district, admin_tehsil)
            row = buckets.setdefault(
                key,
                {
                    "province": admin_province,
                    "district": admin_district,
                    "tehsil": admin_tehsil,
                    "event_count": 0,
                    "risk_score": 0.0,
                    "exposure_score": 0.0,
                    "severity_score": 0.0,
                    "confidence_score": 0.0,
                    "latest_event_id": None,
                    "latest_event_status": None,
                    "latest_review_status": None,
                    "_latest_detected_at": "",
                },
            )
            exposure = event.get("exposure", {}).get("asset_class_exposure", {})
            exposure_score = float(exposure.get("population", 0.0)) + float(exposure.get("roads_km", 0.0)) * 20.0
            confidence = float(event.get("machine_confidence", 0.0))
            severity = float(event.get("event_area_km2", 0.0))
            risk = round((confidence * 0.5) + (min(severity / 25.0, 1.0) * 0.3) + (min(exposure_score / 100000.0, 1.0) * 0.2), 4)
            row["event_count"] += 1
            row["risk_score"] += risk
            row["exposure_score"] += exposure_score
            row["severity_score"] += severity
            row["confidence_score"] += confidence
            detected_at = str(event.get("timestamps", {}).get("detected_at", ""))
            if detected_at >= row["_latest_detected_at"]:
                row["_latest_detected_at"] = detected_at
                row["latest_event_id"] = event.get("event_id")
                row["latest_event_status"] = event.get("status")
                row["latest_review_status"] = event.get("queue_status")
    rows = list(buckets.values())
    for row in rows:
        count = max(1, row["event_count"])
        row["risk_score"] = round(row["risk_score"] / count, 4)
        row["exposure_score"] = round(row["exposure_score"] / count, 2)
        row["severity_score"] = round(row["severity_score"] / count, 3)
        row["confidence_score"] = round(row["confidence_score"] / count, 4)
        row.pop("_latest_detected_at", None)
    if level == "district":
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            key = (row["province"], row["district"])
            agg = grouped.setdefault(key, row | {"tehsil": "ALL_TEHSILS"})
            if agg is not row:
                agg["event_count"] += row["event_count"]
                agg["risk_score"] = round((agg["risk_score"] + row["risk_score"]) / 2, 4)
                agg["exposure_score"] += row["exposure_score"]
                agg["severity_score"] += row["severity_score"]
                agg["confidence_score"] = round((agg["confidence_score"] + row["confidence_score"]) / 2, 4)
        rows = list(grouped.values())
    if level == "province":
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            agg = grouped.setdefault(
                row["province"],
                row | {"district": "ALL_DISTRICTS", "tehsil": "ALL_TEHSILS"},
            )
            if agg is not row:
                agg["event_count"] += row["event_count"]
                agg["risk_score"] = round((agg["risk_score"] + row["risk_score"]) / 2, 4)
                agg["exposure_score"] += row["exposure_score"]
                agg["severity_score"] += row["severity_score"]
                agg["confidence_score"] = round((agg["confidence_score"] + row["confidence_score"]) / 2, 4)
        rows = list(grouped.values())
    return rows


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
        records = [r for r in records if r.status in {"approved", "published"}]
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


def _audit_privileged_action(*, principal_id: str, action: str, resource_type: str, resource_id: str, details: dict[str, Any] | None = None) -> None:
    previous_hash = privileged_audit_log[-1]["entry_hash"] if privileged_audit_log else "GENESIS"
    entry = _build_audit_entry(
        chain_name="privileged",
        action=action,
        principal_id=principal_id,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        previous_hash=previous_hash,
    )
    _append_audit_entry(privileged_audit_log, entry)


def _resolve_role(token: str) -> str | None:
    admin_token = os.getenv("FLOOD_MONITOR_ADMIN_TOKEN")
    analyst_token = os.getenv("FLOOD_MONITOR_ANALYST_TOKEN")
    reviewer_token = os.getenv("FLOOD_MONITOR_REVIEWER_TOKEN")
    service_token = os.getenv("FLOOD_MONITOR_SERVICE_TOKEN")
    if admin_token and token == admin_token:
        return "admin"
    if analyst_token and token == analyst_token:
        return "analyst"
    if reviewer_token and token == reviewer_token:
        return "reviewer"
    if service_token and token == service_token:
        return "service"
    return None


def _principal_id_for_role(role: str) -> str:
    return f"{role}-principal"


def _parse_structured_token(token: str) -> dict[str, Any] | None:
    if not token.startswith("v1."):
        return None
    payload_token = token.split(".", 1)[1]
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_token + "=" * (-len(payload_token) % 4))
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")
    return payload


def _resolve_principal(token: str) -> tuple[str, str]:
    structured = _parse_structured_token(token)
    if structured:
        role = structured.get("role")
        principal_id = structured.get("principal_id")
        exp = structured.get("exp")
        if not isinstance(role, str) or not isinstance(principal_id, str) or not isinstance(exp, str):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")
        try:
            expiry = datetime.fromisoformat(exp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token") from exc
        if expiry <= datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        return role, principal_id

    role = _resolve_role(token)
    if role is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return role, _principal_id_for_role(role)


def _runtime_state_snapshot() -> dict[str, Any]:
    with state_lock:
        return {
            "run_history": run_history,
            "event_store": event_store,
            "historical_event_library": historical_event_library,
            "review_audit_log": review_audit_log,
            "threshold_registry": threshold_registry,
            "model_registry": model_registry,
            "retraining_decisions": retraining_decisions,
            "privileged_audit_log": privileged_audit_log,
        }


def _restore_runtime_state(payload: dict[str, Any]) -> None:
    with state_lock:
        run_history.clear()
        run_history.update(payload.get("run_history", {}))
        event_store.clear()
        event_store.update(payload.get("event_store", {}))
        historical_event_library.clear()
        historical_event_library.update(payload.get("historical_event_library", {}))
        review_audit_log.clear()
        review_audit_log.extend(payload.get("review_audit_log", []))
        threshold_registry.clear()
        threshold_registry.extend(payload.get("threshold_registry", []))
        model_registry.clear()
        model_registry.extend(payload.get("model_registry", []))
        retraining_decisions.clear()
        retraining_decisions.extend(payload.get("retraining_decisions", []))
        privileged_audit_log.clear()
        privileged_audit_log.extend(payload.get("privileged_audit_log", []))


@app.middleware("http")
async def enforce_rate_limit(request: Request, call_next):
    if not request.url.path.startswith("/internal"):
        return await call_next(request)

    limit = int(os.getenv("FLOOD_MONITOR_RATE_LIMIT_REQUESTS", "60"))
    window_seconds = int(os.getenv("FLOOD_MONITOR_RATE_LIMIT_WINDOW_SECONDS", "60"))
    identity = request.headers.get("Authorization", request.client.host if request.client else "anonymous")
    if not rate_limiter.allow(identity=identity, path=request.url.path, limit=limit, window_seconds=window_seconds):
        return PlainTextResponse(
            "Rate limit exceeded for internal API. Retry later.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(window_seconds)},
        )
    return await call_next(request)


def _require_role(*allowed_roles: str):
    def _verify_token(credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme)) -> dict[str, str]:
        if credentials is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
        role, principal_id = _resolve_principal(credentials.credentials)
        if role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")
        return {"role": role, "principal_id": principal_id}

    return _verify_token


def _ensure_published_event(event: dict[str, Any]) -> None:
    if event["status"] != "published":
        raise HTTPException(status_code=404, detail="Event not found.")



@app.get("/health")
def health() -> dict[str, str | float]:
    metrics_registry.set_gauge("ops.api_uptime", 1.0)
    return {"status": "ok", "api_uptime": 1.0}


@public_router.get("/limitations")
def public_limitations() -> dict[str, Any]:
    return {
        "path": LIMITATIONS_PATH,
        "statement": LIMITATIONS_STATEMENT,
    }


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

    return _attach_limitations({
        "map_layers": {
            "flood_candidate_map": report["published_outputs"]["flood_candidate_map"],
            "confirmed_flood_extent": report["published_outputs"]["confirmed_flood_extent"],
            "breach_suspicion_layer": report["published_outputs"]["breach_suspicion_layer"],
        },
        "event_tables": report["detections"],
        "alert_summaries": report["published_outputs"]["alert_feed_item"],
        "api_outputs": report,
    })


@public_router.get("/advisories/{aoi_name}/mobile")
def mobile_advisory(
    aoi_name: str,
    low_bandwidth: bool = Query(default=False),
    language: str = Query(default="en"),
) -> dict[str, Any]:
    report = _latest_run(aoi_name)
    if not report:
        raise HTTPException(status_code=404, detail="No run found for AOI.")

    detection = report["detections"][0]
    advisory = {
        "aoi": aoi_name,
        "run_id": report["run_id"],
        "generated_at": detection["timestamp"],
        "headline": f"{detection['alert_level'].upper()} flood advisory for {aoi_name}",
        "summary": {
            "alert_level": detection["alert_level"],
            "confidence": detection["confidence_score"],
            "confidence_bucket": _confidence_bucket(detection["confidence_score"]),
            "review_status": detection["review_status"],
        },
        "actions": [
            "Monitor official district and provincial disaster-management updates.",
            "Avoid crossing flooded roads and low bridges.",
            "Prepare household emergency supplies and communication plans.",
        ],
        "map": {
            "core_layers": ["confirmed_flood_extent", "breach_suspicion_layer"],
            "bbox": detection.get("geometry_bbox", [67.5, 24.5, 74.2, 34.0]),
        },
        "a11y": {
            "min_text_size_px": 16,
            "high_contrast": True,
            "language": ["en", "ur"],
            "keyboard_navigation_required": True,
        },
        "localized": {
            "headline": {
                "en": f"{detection['alert_level'].upper()} flood advisory for {aoi_name}",
                "ur": f"{aoi_name} کے لیے {detection['alert_level']} سیلابی ہدایت",
            },
            "actions": {
                "en": [
                    "Monitor official district and provincial disaster-management updates.",
                    "Avoid crossing flooded roads and low bridges.",
                    "Prepare household emergency supplies and communication plans.",
                ],
                "ur": [
                    "ضلعی اور صوبائی ڈیزاسٹر مینجمنٹ کی سرکاری ہدایات پر نظر رکھیں۔",
                    "زیرِ آب سڑکوں اور نچلے پلوں سے گزرنے سے گریز کریں۔",
                    "گھریلو ہنگامی سامان اور رابطہ منصوبہ تیار رکھیں۔",
                ],
            },
        },
    }
    if low_bandwidth:
        advisory["map"] = advisory["map"] | {"core_layers": ["confirmed_flood_extent"], "static_tiles_only": True}
        advisory["payload_target_kb"] = 500
        advisory["payload_estimate_kb"] = 145
        advisory["network_profile"] = "2g_slow"
    else:
        advisory["payload_estimate_kb"] = 320
        advisory["network_profile"] = "3g"

    advisory = _attach_limitations(advisory)
    advisory = _apply_language(advisory, language)
    if advisory.get("language") == "ur":
        advisory["headline"] = advisory["localized"]["headline"]["ur"]
        advisory["actions"] = advisory["localized"]["actions"]["ur"]
    return advisory


@public_router.get("/alerts/feed")
def alert_feed(variant: str = Query(default="public_safe"), language: str = Query(default="en")):
    return [_attach_limitations(
        _apply_language(render_alert_template(event=_event_record_from_run(run), variant=variant), language))
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
    return [_attach_limitations(item) for item in response]


@public_router.get("/corridors/{aoi_name}/status")
def corridor_status(aoi_name: str) -> dict:
    report = _latest_run(aoi_name)
    if not report:
        raise HTTPException(status_code=404, detail="No status found for AOI.")
    detection = report["detections"][0]
    latest_event = _event_record_from_run(report)
    return _attach_limitations({
        "corridor_id": aoi_name,
        "latest_hydromet_stress": {
            "rainfall_mm_72h": detection["indicators"].get("rainfall_mm_72h", 0.0),
            "glofas_return_period": detection["indicators"].get("glofas_return_period", 0.0),
            "trigger_reason": report["trigger_reason"],
        },
        "latest_scene_time": detection["timestamp"],
        "queue_status": detection["review_status"],
        "latest_event_summary": latest_event["latest_event_summary"],
    })


@public_router.get("/corridors/{aoi_name}/events")
def corridor_events(
    aoi_name: str,
    status: str | None = Query(default=None),
    confidence_bucket: str | None = Query(default=None),
) -> list[dict]:
    history = _corridor_run_history(aoi_name)
    if not history:
        raise HTTPException(status_code=404, detail="No events found for AOI.")

    records = [event for event in _all_events() if event["aoi"] == aoi_name]
    records = [event for event in records if event["status"] == "published"]
    if status:
        records = [event for event in records if event["status"] == status]
    if confidence_bucket:
        records = [event for event in records if event["confidence_bucket"] == confidence_bucket]

    return [_attach_limitations({
            "event_id": event["event_id"],
            "class": event["event_class"],
            "status": event["status"],
            "confidence_bucket": event["confidence_bucket"],
            "machine_confidence": event["machine_confidence"],
            "detected_at": event["timestamps"]["detected_at"],
        })
        for event in records
    ]


@public_router.get("/events/{event_id}")
def get_event(event_id: str) -> dict:
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    _ensure_published_event(event)
    return _attach_limitations({
        "event_id": event["event_id"],
        "class": event["event_class"],
        "status": event["status"],
        "geometry": event["geometry"],
        "source_scenes": event["source_scenes"],
        "lineage": event.get("lineage"),
        "confidence_breakdown": event["confidence_breakdown"],
        "notes": event["notes"],
        "timestamps": event["timestamps"],
    })


@public_router.get("/events/{event_id}/exposure")
def get_event_exposure(event_id: str) -> dict:
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    _ensure_published_event(event)
    return _attach_limitations({
        "event_id": event_id,
        "district": event["exposure"]["district"],
        "asset_summary": event["exposure"]["asset_class_exposure"],
    })


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
    return _attach_limitations({"event_id": event_id, "event_area_trend": trend, "candidate_persistence_hours": event["candidate_persistence_hours"]})


@public_router.get("/historical-events")
def list_historical_events(corridor_reach: str | None = Query(default=None)) -> list[dict[str, Any]]:
    records = [HistoricalEventRecord.model_validate(item) for item in historical_event_library.values()]
    if corridor_reach:
        records = [record for record in records if record.catalog.corridor_reach == corridor_reach]
    return [_attach_limitations({
            "event_id": record.event_id,
            "event_name": record.catalog.event_name,
            "corridor_reach": record.catalog.corridor_reach,
            "peak_date": record.catalog.peak_date,
            "label_quality_score": record.catalog.label_quality_score,
            "status": record.status,
        })
        for record in records
    ]


@public_router.get("/historical-events/{event_id}")
def get_historical_event(event_id: str) -> dict[str, Any]:
    record = historical_event_library.get(event_id)
    if not record:
        raise HTTPException(status_code=404, detail="Historical event not found.")
    parsed = HistoricalEventRecord.model_validate(record)
    return _attach_limitations(parsed.model_dump())


@public_router.get("/events/{event_id}/confidence")
def get_event_confidence(event_id: str) -> dict[str, Any]:
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    _ensure_published_event(event)
    return _attach_limitations({"event_id": event_id, "confidence_breakdown": event["confidence_breakdown"]})


@public_router.get("/alerts/latest")
def latest_alerts(variant: str = Query(default="public_safe"), language: str = Query(default="en")) -> list[dict]:
    return [_attach_limitations(_apply_language(render_alert_template(event=event, variant=variant), language))
        for event in _all_events()
        if event["status"] == "published"
    ]


@internal_router.get("/alerts/templates", dependencies=[Depends(_require_role("admin", "analyst", "reviewer"))])
def internal_alert_templates(event_id: str, variant: str = Query(default="official_internal")) -> dict[str, Any]:
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    return render_alert_template(event=event, variant=variant)


@public_router.get("/risk-summary/{level}")
def risk_summary(
    level: str,
    province: str | None = None,
    district: str | None = None,
    sort_by: str = Query(default="risk_score"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    min_risk: float | None = Query(default=None, ge=0.0, le=1.0),
    min_exposure: float | None = Query(default=None, ge=0.0),
    min_severity: float | None = Query(default=None, ge=0.0),
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
) -> dict[str, Any]:
    if level not in {"tehsil", "district", "province"}:
        raise HTTPException(status_code=400, detail="level must be one of tehsil|district|province")
    allowed_sort = {"risk_score", "exposure_score", "severity_score", "confidence_score", "province", "district", "tehsil", "event_count"}
    if sort_by not in allowed_sort:
        raise HTTPException(status_code=400, detail={"error": "invalid_sort_by", "allowed": sorted(allowed_sort)})
    rows = _summarize_risk_rows(level=level, province=province, district=district, only_reviewed=True)
    if min_risk is not None:
        rows = [row for row in rows if row["risk_score"] >= min_risk]
    if min_exposure is not None:
        rows = [row for row in rows if row["exposure_score"] >= min_exposure]
    if min_severity is not None:
        rows = [row for row in rows if row["severity_score"] >= min_severity]
    if min_confidence is not None:
        rows = [row for row in rows if row["confidence_score"] >= min_confidence]
    rows = sorted(rows, key=lambda row: row[sort_by], reverse=(order == "desc"))
    return {
        "level": level,
        "filters": {"province": province, "district": district, "min_risk": min_risk, "min_exposure": min_exposure, "min_severity": min_severity, "min_confidence": min_confidence},
        "sort": {"sort_by": sort_by, "order": order},
        "count": len(rows),
        "results": rows,
        "baseline_dataset_requirements": {
            "district_tehsil_boundaries": "Required (properties: province, district, tehsil).",
            "event_admin_overlay_join": "Required for mapping reviewed/approved events to district/tehsil.",
            "exposure_baseline_layers": "Required for exposure score comparability.",
        },
    }


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
@internal_router.post("/admin/reprocess-scene")
def admin_reprocess_scene(aoi_name: str, auth_context: dict[str, str] = Depends(_require_role("admin"))) -> dict:
    report = pipeline.run_daily(aoi_name).model_dump()
    _record_run(report)
    _audit_privileged_action(principal_id=auth_context["principal_id"], action="reprocess", resource_type="corridor", resource_id=aoi_name)
    return {
        "status": "reprocessed",
        "run_id": report["run_id"],
        "aoi": aoi_name,
        "history_depth": len(_corridor_run_history(aoi_name)),
    }


@internal_router.post("/admin/review-event")
def admin_review_event(event_id: str, payload: ReviewEventRequest, auth_context: dict[str, str] = Depends(_require_role("admin", "analyst", "reviewer"))) -> dict:
    principal_id = auth_context["principal_id"]
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    old_status = event["status"]
    requested_state = _normalize_lifecycle_action(payload.action)
    _validate_lifecycle_transition(old_status, requested_state)
    event["status"] = requested_state
    event["analyst_confidence"] = payload.analyst_confidence
    if payload.notes:
        event["notes"] = payload.notes
    if payload.reviewed_geometry:
        event["geometry"] = payload.reviewed_geometry
    if payload.label_metadata:
        event["label_metadata"] = payload.label_metadata
    if payload.mapping_rules:
        event["mapping_rules"] = payload.mapping_rules

    if payload.reviewed_geometry and (not payload.label_metadata or not payload.mapping_rules):
        raise HTTPException(
            status_code=400,
            detail="reviewed_geometry requires both label_metadata and mapping_rules.",
        )

    qa_result = publication_gate(event)
    if requested_state == "published" and not qa_result.passed:
        raise HTTPException(status_code=400, detail={"qa_failed": qa_result.errors})
    if qa_result.normalized_geometry:
        event["geometry"] = qa_result.normalized_geometry

    _upsert_historical_event_from_event(event)
    historical_record = HistoricalEventRecord.model_validate(historical_event_library[event_id])
    historical_record.catalog.label_quality_score = max(historical_record.catalog.label_quality_score, 0.85)
    if payload.reviewed_geometry:
        historical_record.assets.reviewed_polygons = [f"published/{event['aoi']}/{event_id}/reviewed_extent.geojson"]
    if payload.notes:
        historical_record.assets.analyst_notes.append(payload.notes)
    historical_record.updated_at = datetime.now(UTC).isoformat()
    historical_event_library[event_id] = historical_record.model_dump()

    review_previous_hash = review_audit_log[-1]["entry_hash"] if review_audit_log else "GENESIS"
    review_entry = _build_audit_entry(
        chain_name="review",
        action=requested_state,
        principal_id=principal_id,
        resource_type="event",
        resource_id=event_id,
        details={
            "old_status": old_status,
            "new_status": event["status"],
            "notes": payload.notes,
            "qa_passed": qa_result.passed,
            "qa_errors": qa_result.errors,
        },
        previous_hash=review_previous_hash,
    )
    review_entry["event_id"] = event_id
    review_entry["changed_at"] = review_entry["timestamp"]
    review_entry["old_status"] = old_status
    review_entry["new_status"] = event["status"]
    review_entry["notes"] = payload.notes
    review_entry["qa_passed"] = qa_result.passed
    review_entry["qa_errors"] = qa_result.errors
    _append_audit_entry(review_audit_log, review_entry)
    _audit_privileged_action(
        principal_id=principal_id,
        action="review",
        resource_type="event",
        resource_id=event_id,
        details={"old_status": old_status, "new_status": event["status"]},
    )
    trace_entry = {
        "principal_id": principal_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "previous_state": old_status,
        "new_state": event["status"],
        "reason": payload.notes or None,
        "comment": payload.notes or None,
    }
    event.setdefault("approval_trace", []).append(trace_entry)
    if requested_state in {"approved", "published"}:
        metrics_registry.increment("product.alerts_confirmed")
        metrics_registry.increment("product.analyst_hours_saved_proxy", 0.75)
    if requested_state in {"retracted"}:
        metrics_registry.increment("product.false_alarms")
    return {"status": "review_updated", "event": event, "qa": {"passed": qa_result.passed, "errors": qa_result.errors}}


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


@internal_router.post("/admin/sitrep/export", dependencies=[Depends(_require_role("admin", "analyst", "reviewer"))])
def admin_export_sitrep() -> FileResponse:
    event = _latest_reviewed_or_approved_event()
    if not event:
        raise HTTPException(status_code=404, detail="No reviewed/approved/published event available for SitRep export.")
    exposure = event.get("exposure", {})
    asset_summary = exposure.get("asset_summary", {})
    district_rows = event.get("admin_overlays") or [{"district": d, "tehsil": "ALL_TEHSILS"} for d in event.get("district_overlays", [])]
    confidence = event.get("confidence_breakdown", {})
    lines = [
        "Pakistan Flood Monitor - Situation Report (SitRep)",
        f"Event ID: {event['event_id']} | AOI: {event['aoi']} | Status: {event['status']}",
        f"Detected: {event['timestamps']['detected_at']} | Generated: {datetime.now(UTC).isoformat()}",
        "Section: Event Summary",
        event.get("latest_event_summary", {}).get("summary", "No summary available."),
        "Section: District/Tehsil Priorities",
    ]
    for idx, row in enumerate(district_rows, start=1):
        lines.append(f"{idx}. {row.get('district', 'Unknown')} / {row.get('tehsil', 'ALL_TEHSILS')}")
    lines.extend(
        [
            "Section: Recommended Actions",
            "1) Activate district control room and verify high-risk settlements.",
            "2) Pre-position rescue boats, shelter kits, and medical teams.",
            "3) Notify tehsil administrators and union council focal points.",
            "Section: Exposure/Risk Summary",
            f"Population exposed: {asset_summary.get('estimated_people_exposed', 'n/a')}",
            f"Cropland exposed ha: {asset_summary.get('estimated_cropland_exposed_ha', 'n/a')}",
            f"Critical facilities exposed: {asset_summary.get('critical_facilities_exposed', 'n/a')}",
            f"Confidence final: {confidence.get('final_confidence', 'n/a')}",
            "Section: Confidence and Limitations",
            LIMITATIONS_STATEMENT["confidence_and_uncertainty"],
            LIMITATIONS_STATEMENT["warning_limitations"],
            LIMITATIONS_STATEMENT["non_replacement_notice"],
            "Section: Contacts",
            "PDMA Provincial Control Room: +92-21-99204452",
            "District Emergency Officer: [to be filled by operator]",
            "Rescue 1122: 1122",
        ]
    )
    output_dir = os.path.join("reports", "sitrep")
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"sitrep_{event['event_id']}.pdf")
    with open(out_path, "wb") as f:
        f.write(_simple_pdf(lines))
    return FileResponse(out_path, filename=os.path.basename(out_path), media_type="application/pdf")


@internal_router.post("/admin/register-threshold")
def register_threshold(payload: ThresholdRegistrationRequest, auth_context: dict[str, str] = Depends(_require_role("admin"))) -> dict[str, Any]:
    principal_id = auth_context["principal_id"]
    record = payload.model_dump(exclude={"actor"}) | {"actor": principal_id, "registered_at": datetime.now(UTC).isoformat()}
    threshold_registry.append(record)
    _audit_privileged_action(
        principal_id=principal_id,
        action="threshold_change",
        resource_type="threshold",
        resource_id=payload.threshold_name,
        details={"version": payload.version, "file_path": payload.file_path},
    )
    return {"status": "registered", "threshold": record}


@internal_router.post("/admin/register-model")
def register_model(payload: ModelRegistrationRequest, auth_context: dict[str, str] = Depends(_require_role("admin"))) -> dict[str, Any]:
    principal_id = auth_context["principal_id"]
    record = payload.model_dump(exclude={"actor"}) | {"actor": principal_id, "registered_at": datetime.now(UTC).isoformat()}
    model_registry.append(record)
    _audit_privileged_action(
        principal_id=principal_id,
        action="publish",
        resource_type="model",
        resource_id=payload.model_id,
        details={"training_data_snapshot_version": payload.training_data_snapshot_version},
    )
    return {"status": "registered", "model": record}




@internal_router.post("/admin/evaluate-retraining")
def evaluate_retraining(payload: RetrainingTriggerRequest, auth_context: dict[str, str] = Depends(_require_role("admin"))) -> dict[str, Any]:
    principal_id = auth_context["principal_id"]
    decision = _evaluate_retraining_trigger(payload)
    record = payload.model_dump(exclude={"actor"}) | {"actor": principal_id} | decision | {"evaluated_at": datetime.now(UTC).isoformat()}
    retraining_decisions.append(record)
    _audit_privileged_action(
        principal_id=principal_id,
        action="retraining_evaluated",
        resource_type="model",
        resource_id=payload.model_id,
        details=decision,
    )
    return {"status": "evaluated", "decision": record}

@internal_router.get("/admin/privileged-audit", dependencies=[Depends(_require_role("admin"))])
def privileged_audit() -> list[dict[str, Any]]:
    return privileged_audit_log


@internal_router.get("/monitoring/metrics/prometheus", dependencies=[Depends(_require_role("admin", "analyst"))])
def monitoring_metrics_prometheus() -> PlainTextResponse:
    snapshot = metrics_registry.snapshot()
    lines: list[str] = []
    for key, value in snapshot.counters.items():
        metric = key.replace(".", "_") + "_total"
        lines.append(f"# TYPE {metric} counter")
        lines.append(f"{metric} {value}")
    for key, value in snapshot.gauges.items():
        metric = key.replace(".", "_")
        lines.append(f"# TYPE {metric} gauge")
        lines.append(f"{metric} {value}")
    for key, summary in snapshot.latencies_ms.items():
        metric = key.replace(".", "_")
        lines.append(f"# TYPE {metric}_avg_ms gauge")
        lines.append(f"{metric}_avg_ms {summary.get('avg_ms', 0.0)}")
        lines.append(f"# TYPE {metric}_p95_ms gauge")
        lines.append(f"{metric}_p95_ms {summary.get('p95_ms', 0.0)}")
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@internal_router.get("/admin/state/export", dependencies=[Depends(_require_role("admin"))])
def export_runtime_state() -> dict[str, Any]:
    return {"exported_at": datetime.now(UTC).isoformat(), "state": _runtime_state_snapshot()}


@internal_router.post("/admin/state/restore", dependencies=[Depends(_require_role("admin"))])
def restore_runtime_state(payload: dict[str, Any], auth_context: dict[str, str] = Depends(_require_role("admin"))) -> dict[str, Any]:
    principal_id = auth_context["principal_id"]
    state = payload.get("state", {})
    _restore_runtime_state(state)
    _audit_privileged_action(
        principal_id=principal_id,
        action="restore_attempt",
        resource_type="runtime_state",
        resource_id="global",
        details={"requested_keys": sorted(state.keys())},
    )
    _audit_privileged_action(
        principal_id=principal_id,
        action="restore_completed",
        resource_type="runtime_state",
        resource_id="global",
        details={"events": len(event_store), "audit_records": len(review_audit_log)},
    )
    return {
        "status": "restored",
        "corridors": len(run_history),
        "events": len(event_store),
        "audit_records": len(review_audit_log),
    }


@internal_router.get("/admin/audit/verify", dependencies=[Depends(_require_role("admin"))])
def verify_audit_integrity() -> dict[str, Any]:
    review_ok, review_error = _verify_audit_chain(review_audit_log, "review")
    privileged_ok, privileged_error = _verify_audit_chain(privileged_audit_log, "privileged")
    if not review_ok or not privileged_ok:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "failed",
                "review": review_error,
                "privileged": privileged_error,
            },
        )
    return {"status": "ok", "review_entries": len(review_audit_log), "privileged_entries": len(privileged_audit_log)}


app.include_router(public_router)
app.include_router(internal_router)
