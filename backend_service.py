"""
Pakistan Flood Monitor — CSV-backed data service layer.
Provides all data operations for the Streamlit dashboard,
reading from local CSV files instead of PostgreSQL/PostGIS.
"""
from __future__ import annotations

import os
import json
import math
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

import pandas as pd
import yaml
import httpx
from shapely.errors import ShapelyError
from shapely.geometry import shape

from pakistan_flood_monitor.config import AppMode
from pakistan_flood_monitor.models.review_queue import (
    REVIEW_QUEUE_PAGE_SIZE,
    SIMULATION_WATERMARK,
    ReviewQueuePage,
    ReviewQueueStatus,
)

DATA_DIR = Path("data")
CONFIG_DIR = Path("config/thresholds")
REPORTS_DIR = Path("reports")
STORAGE_DIR = Path("storage")
API_BASE_URL = os.getenv("API_BASE_URL")

# ADR-001 / AGENTS.md: exactly three runtime modes.
# When APP_MODE is "demo" or "test" and no API_BASE_URL is configured, local CSV
# data is acknowledged as synthetic/demo and must carry a visible watermark.
# In "operational" mode without API_BASE_URL the system must fail closed.
_APP_MODE = os.getenv("APP_MODE", AppMode.DEMO.value).strip().lower()
DEMO_WATERMARK = f"⚠️ {SIMULATION_WATERMARK}"

EVENT_COLUMNS = [
    "event_id", "corridor_id", "status", "severity", "confidence",
    "population_exposed", "updated_at", "published_at", "detected_at",
    "latitude", "longitude", "district", "tehsil", "event_class",
    "confidence_band", "breach_suspicion", "source_scenes",
    "affected_area_sqkm", "roads_exposed_km", "health_facilities_exposed",
    "schools_exposed", "cropland_exposed_sqkm", "what_changed",
    "what_this_means_en", "what_this_means_ur", "limitations",
]


def _event_coordinates(geometry: dict | None) -> tuple[float | None, float | None]:
    """Choose a display point from GeoJSON WGS84 coordinates (longitude, latitude)."""
    if not geometry:
        return None, None
    try:
        geom = shape(geometry)
        if geom.is_empty:
            return None, None
        marker = geom.representative_point()
        lon, lat = marker.x, marker.y
    except (ShapelyError, KeyError, AttributeError, TypeError, ValueError):
        return None, None
    if math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90:
        return lat, lon
    return None, None


class ReviewQueueUnavailable(RuntimeError):
    """User-facing failure to retrieve the canonical analyst queue."""


class DataService:
    """Singleton-style CSV data backend for the dashboard."""

    def __init__(self):
        self._cache: dict[str, pd.DataFrame] = {}
        self.event_api_error: str | None = None
        # Exposure data source tag: "api", "local_csv", or "unavailable"
        self.exposure_data_source: str = "unavailable"

    @property
    def has_api(self) -> bool:
        return bool(API_BASE_URL)

    @property
    def is_demo_mode(self) -> bool:
        """True when running without a live API in demo or test APP_MODE.

        In demo/test mode local CSV data is acknowledged as synthetic.
        In operational mode without API_BASE_URL the system should fail closed;
        callers must check this and show the appropriate unavailability state.
        """
        return not self.has_api and _APP_MODE in ("demo", "test")

    def _load(self, name: str) -> pd.DataFrame:
        path = DATA_DIR / f"{name}.csv"
        if path.exists():
            return pd.read_csv(path)
        return pd.DataFrame()

    # ── Corridors ────────────────────────────────────────
    def get_corridors(self) -> pd.DataFrame:
        return self._load("corridors")

    def get_corridor(self, corridor_id: str) -> dict | None:
        df = self.get_corridors()
        row = df[df["corridor_id"] == corridor_id]
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    # ── Flood Events ─────────────────────────────────────
    def get_events(self) -> pd.DataFrame:
        self.event_api_error = None
        if API_BASE_URL:
            try:
                response = httpx.get(f"{API_BASE_URL}/public/events", timeout=2.0)
                if response.status_code == 200:
                    payload = response.json()
                    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
                        raise ValueError("invalid event response")
                    events = payload["events"]
                    if events:
                        # Map API dicts to CSV-like DataFrame
                        rows = []
                        for e in events:
                            latitude, longitude = _event_coordinates(e.get("geometry"))
                            timestamps = e.get("timestamps")
                            if timestamps is None:
                                timestamps = {}
                            rows.append({
                                "event_id": e.get("event_id"),
                                "corridor_id": e.get("corridor_id", e.get("aoi")),
                                "status": e.get("status"),
                                "severity": e.get("latest_event_summary", {}).get("alert_level", "low"),
                                "confidence": e.get("machine_confidence"),
                                "population_exposed": e.get("exposure", {}).get("asset_class_exposure", {}).get("population", 0),
                                "updated_at": timestamps.get("published_at") or timestamps.get("detected_at"),
                                "published_at": timestamps.get("published_at"),
                                "detected_at": timestamps.get("detected_at"),
                                "latitude": latitude,
                                "longitude": longitude,
                                "district": e.get("district"),
                                "tehsil": e.get("tehsil", ""),
                                "event_class": e.get("event_class", "flood_event"),
                                "confidence_band": e.get("confidence_band", "medium"),
                                "breach_suspicion": e.get("breach_suspicion", False),
                                "source_scenes": e.get("source_scenes", ""),
                                "affected_area_sqkm": e.get("affected_area_sqkm", 0),
                                "roads_exposed_km": e.get("exposure", {}).get("asset_class_exposure", {}).get("roads_km", 0),
                                "health_facilities_exposed": e.get("exposure", {}).get("asset_class_exposure", {}).get("health_facilities", 0),
                                "schools_exposed": e.get("exposure", {}).get("asset_class_exposure", {}).get("schools", 0),
                                "cropland_exposed_sqkm": e.get("exposure", {}).get("asset_class_exposure", {}).get("cropland_sqkm", 0),
                                "what_changed": e.get("what_changed", ""),
                                "what_this_means_en": e.get("what_this_means_en", ""),
                                "what_this_means_ur": e.get("what_this_means_ur", ""),
                                "limitations": e.get("limitations", ""),
                            })
                        return pd.DataFrame(rows, columns=EVENT_COLUMNS)
                else:
                    self.event_api_error = "Event service returned an error."
            except (httpx.HTTPError, ValueError, TypeError, AttributeError, IndexError, KeyError):
                self.event_api_error = "Event service unavailable or returned invalid data."
            if self.event_api_error:
                print(self.event_api_error)
            # An empty response, HTTP error, or malformed payload is not a reason
            # to present unrelated local data as published API results.
            return pd.DataFrame(columns=EVENT_COLUMNS)
        if self.is_demo_mode:
            return self._load("flood_events")
        self.event_api_error = "No event API is configured."
        return pd.DataFrame(columns=EVENT_COLUMNS)

    def get_event(self, event_id: str) -> dict | None:
        df = self.get_events()
        if df.empty:
            return None
        row = df[df["event_id"] == event_id]
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    def get_events_by_status(self, statuses: list[str]) -> pd.DataFrame:
        df = self.get_events()
        if df.empty:
            return df
        return df[df["status"].isin(statuses)]

    def get_events_by_corridor(self, corridor_id: str) -> pd.DataFrame:
        df = self.get_events()
        if df.empty:
            return df
        return df[df["corridor_id"] == corridor_id]

    def get_public_events(self) -> pd.DataFrame:
        """Only published events visible to the public."""
        return self.get_events_by_status(["published"])

    def get_review_queue(self) -> pd.DataFrame:
        """Local demo events awaiting review."""
        if not self.is_demo_mode:
            return pd.DataFrame(columns=EVENT_COLUMNS)
        return self.get_events_by_status(["draft", "queued", "review", "active", "approved"])

    def fetch_review_queue(
        self,
        token: str,
        *,
        offset: int = 0,
        status: ReviewQueueStatus | None = None,
    ) -> ReviewQueuePage:
        if not self.has_api or not token:
            raise ReviewQueueUnavailable("An API endpoint and review credential are required.")
        if not token.isascii() or not token.isprintable() or any(char.isspace() for char in token):
            raise ReviewQueueUnavailable("Enter a valid bearer credential without spaces.")

        params: dict[str, int | str] = {"offset": offset, "limit": REVIEW_QUEUE_PAGE_SIZE}
        if status is not None:
            params["status"] = status
        try:
            response = httpx.get(
                f"{API_BASE_URL.rstrip('/')}/internal/review-queue",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=2.0,
            )
        except httpx.HTTPError:
            raise ReviewQueueUnavailable("The analyst queue is unavailable. Try again shortly.") from None

        if response.status_code in (401, 403):
            raise ReviewQueueUnavailable("The API rejected this review credential.")
        if response.status_code == 429:
            raise ReviewQueueUnavailable("The analyst queue is rate limited. Try again shortly.")
        if response.status_code != 200:
            raise ReviewQueueUnavailable("The analyst queue is unavailable. Try again shortly.")
        try:
            return ReviewQueuePage.model_validate(response.json())
        except ValueError:
            raise ReviewQueueUnavailable("The analyst queue returned an invalid response.") from None

    def update_event_status(self, event_id: str, new_status: str, actor: str, notes: str = ""):
        """Update event status and write audit record."""
        if API_BASE_URL:
            try:
                admin_token = os.getenv("FLOOD_MONITOR_ADMIN_TOKEN", "mock-token")
                headers = {"Authorization": f"Bearer {admin_token}"}
                payload = {"action": new_status, "actor": actor, "notes": notes, "event_id": event_id}
                response = httpx.post(
                    f"{API_BASE_URL}/internal/admin/review-event",
                    params={"event_id": event_id},
                    json=payload,
                    headers=headers,
                    timeout=2.0,
                )
                if response.status_code == 200:
                    return True
            except httpx.HTTPError:
                print("Review API unavailable; no local update was made.")
            return False

        df = self.get_events()
        if df.empty:
            return False
        idx = df.index[df["event_id"] == event_id]
        if len(idx) == 0:
            return False
        old_status = df.loc[idx[0], "status"]
        df.loc[idx[0], "status"] = new_status
        df.loc[idx[0], "updated_at"] = datetime.now(timezone.utc).isoformat()
        if new_status == "published" and pd.isna(df.loc[idx[0], "published_at"]):
            df.loc[idx[0], "published_at"] = datetime.now(timezone.utc).isoformat()
        
        csv_path = DATA_DIR / "flood_events.csv"
        if csv_path.exists():
            df.to_csv(csv_path, index=False)

        # Write audit record
        self._append_audit(event_id, actor, new_status.replace("published", "publish_alert").replace("approved", "accept"),
                           old_status, new_status, notes)
        return True

    # ── Exposure / Impact ────────────────────────────────
    def get_exposure(self) -> pd.DataFrame:
        """Return exposure data with provenance tracking.

        Provenance rules (ADR-001 / P0-003):
        - API mode: local exposure CSV must NOT be shown alongside API events —
          the two datasets are unrelated and mixing them silently creates false
          provenance. Return empty until an exposure API endpoint is available.
        - Demo/test mode (no API_BASE_URL): local CSV is synthetic; callers
          MUST display DEMO_WATERMARK before showing this data.
        - Operational mode without API: fail closed — return empty.
        Sets ``self.exposure_data_source`` for callers to inspect.
        """
        if API_BASE_URL:
            # Local exposure CSV was not produced by the current API feed.
            # Return empty to prevent mixed provenance; a future API exposure
            # endpoint can be wired here when available.
            self.exposure_data_source = "unavailable"
            return pd.DataFrame()
        if not self.is_demo_mode:
            # Operational mode must fail closed without real data.
            self.exposure_data_source = "unavailable"
            return pd.DataFrame()
        # demo or test mode: local CSV is acknowledged as synthetic.
        df = self._load("exposure_results")
        self.exposure_data_source = "local_csv" if not df.empty else "unavailable"
        return df

    def get_exposure_for_event(self, event_id: str) -> pd.DataFrame:
        df = self.get_exposure()
        if df.empty:
            return df
        return df[df["event_id"] == event_id]

    # ── Field Reports ────────────────────────────────────
    def get_field_reports(self) -> pd.DataFrame:
        if not self.is_demo_mode:
            return pd.DataFrame()
        try:
            reports = self._load("field_reports")
        except (OSError, UnicodeError, pd.errors.EmptyDataError, pd.errors.ParserError):
            return pd.DataFrame()

        required = {"report_id", "event_id", "reporter_channel", "status", "moderation_tags"}
        return reports if required.issubset(reports.columns) else pd.DataFrame()

    def get_reports_for_event(self, event_id: str) -> pd.DataFrame:
        df = self.get_field_reports()
        if df.empty:
            return df
        return df[df["event_id"] == event_id]

    def moderate_report(self, report_id: str, new_status: str, reason: str = "") -> bool:
        if new_status not in {"approved", "rejected", "flagged_spam"}:
            return False
        df = self.get_field_reports()
        if df.empty:
            return False
        matching = df.index[df["report_id"] == report_id]
        if len(matching) != 1 or df.at[matching[0], "status"] not in {"submitted", "needs_more_info"}:
            return False

        row = matching[0]
        df.at[row, "status"] = new_status
        if "trusted" not in df:
            df["trusted"] = False
        if "moderation_reason" not in df:
            df["moderation_reason"] = ""
        df["moderation_reason"] = df["moderation_reason"].astype("string")
        df.at[row, "trusted"] = new_status == "approved"
        df.at[row, "moderation_reason"] = reason
        path = DATA_DIR / "field_reports.csv"
        pending = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False) as handle:
                pending = Path(handle.name)
                df.to_csv(handle, index=False)
            pending.replace(path)
        except OSError:
            if pending is not None:
                try:
                    pending.unlink(missing_ok=True)
                except OSError:
                    pass
            return False
        return True

    def field_report_summary(self, event_id: str) -> dict:
        reports = self.get_reports_for_event(event_id)
        if reports.empty:
            return {"total": 0, "trusted": 0, "unmoderated": 0, "conflicting": 0, "spam": 0}
        return {
            "total": len(reports),
            "trusted": int(reports["trusted"].sum()) if "trusted" in reports.columns else 0,
            "unmoderated": len(reports[reports["status"] == "submitted"]),
            "conflicting": len(reports[reports["moderation_tags"].fillna("").str.contains("conflicting")]),
            "spam": len(reports[reports["status"] == "flagged_spam"]),
        }

    # ── Notification Audit ───────────────────────────────
    def get_notifications(self) -> pd.DataFrame:
        return self._load("notification_audit")

    def get_notifications_for_event(self, event_id: str) -> pd.DataFrame:
        df = self.get_notifications()
        if df.empty:
            return df
        return df[df["event_id"] == event_id]

    # ── Audit Log ────────────────────────────────────────
    def get_audit_log(self) -> pd.DataFrame:
        return self._load("audit_log") if self.is_demo_mode else pd.DataFrame()

    def _append_audit(self, event_id: str, actor: str, action: str,
                      old_status: str, new_status: str, notes: str):
        log_path = DATA_DIR / "audit_log.csv"
        df = self._load("audit_log")
        new_id = f"AUD-{len(df) + 1:03d}"
        new_row = pd.DataFrame([{
            "record_id": new_id,
            "candidate_id": event_id,
            "actor": actor,
            "action": action,
            "old_status": old_status,
            "new_status": new_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": notes,
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(log_path, index=False)

    # ── Pipeline Runs ────────────────────────────────────
    def get_pipeline_runs(self) -> pd.DataFrame:
        return self._load("pipeline_runs")

    def get_latest_run(self, pipeline_name: str = None) -> dict | None:
        df = self.get_pipeline_runs()
        if df.empty:
            return None
        if pipeline_name:
            df = df[df["pipeline_name"] == pipeline_name]
        if df.empty:
            return None
        df = df.sort_values("started_at", ascending=False)
        return df.iloc[0].to_dict()

    def freshness_status(self) -> dict:
        """Compute data freshness SLA status per dashboard_freshness_lineage.md."""
        if not self.is_demo_mode:
            return {"status": "unknown", "message": "Event feed freshness is unavailable.", "age_minutes": None}
        latest = self.get_latest_run("daily_monitoring")
        if latest is None:
            return {"status": "unknown", "message": "No pipeline runs found", "age_minutes": None}
        try:
            if latest.get("status") == "completed" and pd.notna(latest.get("completed_at")):
                completed = pd.Timestamp(latest["completed_at"])
                if completed.tzinfo is None:
                    completed = completed.tz_localize("UTC")
            else:
                completed = None
        except Exception:
            completed = None
        if completed is None:
            return {"status": "unknown", "message": "Latest run has no completion time", "age_minutes": None}
        now = pd.Timestamp.now(tz="UTC")
        age = (now - completed).total_seconds() / 60.0
        if age < 0:
            return {"status": "unknown", "message": "Run completion time is in the future.", "age_minutes": None}
        if age <= 30:
            status = "fresh"
        elif age <= 60:
            status = "watch"
        else:
            status = "stale"
        return {
            "status": status,
            "message": f"Last completed {int(age)} minutes ago",
            "age_minutes": round(age, 1),
            "last_completed": str(completed),
            "target_minutes": 30,
            "stale_after_minutes": 60,
        }

    # ── Model Registry ───────────────────────────────────
    def get_model_registry(self) -> pd.DataFrame:
        return self._load("model_registry")

    def get_deployed_models(self) -> pd.DataFrame:
        df = self.get_model_registry()
        if df.empty:
            return df
        return df[df["status"] == "deployed"]

    # ── Thresholds & Config ──────────────────────────────
    def get_flood_thresholds(self) -> dict:
        path = CONFIG_DIR / "flood_thresholds.yaml"
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f)
        return {}

    def get_breach_weights(self) -> dict:
        path = CONFIG_DIR / "breach_weights.yaml"
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f)
        return {}

    def save_flood_thresholds(self, data: dict):
        path = CONFIG_DIR / "flood_thresholds.yaml"
        with open(path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False)

    def save_breach_weights(self, data: dict):
        path = CONFIG_DIR / "breach_weights.yaml"
        with open(path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False)

    # ── Export Center ────────────────────────────────────
    def generate_export(self, event_id: str, fmt: str) -> dict:
        """Write a labelled GeoJSON point and its manifest for a local demo event."""
        if not self.is_demo_mode:
            return {"error": "GIS export is unavailable for API-backed or operational events."}
        if fmt != "geojson":
            return {"error": "Only GeoJSON demo point export is available."}
        event = self.get_event(event_id)
        if event is None:
            return {"error": f"Event {event_id} not found."}

        try:
            lon, lat = float(event["longitude"]), float(event["latitude"])
        except (KeyError, TypeError, ValueError):
            return {"error": "Event coordinates are unavailable."}
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            return {"error": "Event coordinates are outside valid WGS84 bounds."}

        export_id = f"exp-{uuid4().hex}"
        export_dir = Path(".cache/exports") / export_id
        output_path = export_dir / "event.geojson"
        manifest_path = export_dir / "manifest.json"

        labels = {"product_label": "SIMULATED", "demo_watermark": DEMO_WATERMARK}
        geojson = {
            "type": "FeatureCollection",
            **labels,
            "features": [{
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {"event_id": event_id, **labels},
            }],
        }
        output = json.dumps(geojson, indent=2, ensure_ascii=False).encode("utf-8")
        manifest = {
            "schema": "pakistan-flood-monitor/export-manifest/v1",
            "export_id": export_id,
            "event_id": event_id,
            "format": fmt,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **labels,
            "lineage": {
                "source_type": "local_demo_fixture",
                "dataset": str(DATA_DIR / "flood_events.csv"),
            },
            "geometry": "GeoJSON point in WGS84 longitude/latitude order",
            "outputs": [{"path": output_path.name, "size_bytes": len(output)}],
        }
        try:
            export_dir.mkdir(parents=True)
            output_path.write_bytes(output)
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            return {"error": "Unable to write the demo export."}

        return {
            "export_id": export_id,
            "output_path": str(output_path),
            "manifest_path": str(manifest_path),
            "format": fmt,
            "demo_watermark": DEMO_WATERMARK,
        }

    # ── Release Checklist ────────────────────────────────
    def get_release_checklist(self) -> list[dict]:
        """Return prototype release checklist items.

        WARNING: All "pass" statuses below are hardcoded prototype placeholders
        and do NOT represent verified operational state. No claim of readiness
        should be made from this list without independent verification.
        """
        return [
            {"category": "Pre-release", "item": "Canonical runtime command validated", "status": "pass"},
            {"category": "Pre-release", "item": "No deprecated prototype entrypoint in deployment", "status": "pass"},
            {"category": "Pre-release", "item": "Alembic migration state current", "status": "skip"},
            {"category": "Pre-release", "item": "Runtime config validation completed", "status": "pass"},
            {"category": "Pre-release", "item": "/health returns OK", "status": "pass"},
            {"category": "Pre-release", "item": "Monitoring metrics reachable", "status": "pass"},
            {"category": "Pre-release", "item": "Backup snapshot exported", "status": "warning"},
            {"category": "Security", "item": "Admin/analyst tokens rotated", "status": "pass"},
            {"category": "Security", "item": "Actor-prefix checks verified", "status": "pass"},
            {"category": "Security", "item": "Audit integrity verified", "status": "pass"},
            {"category": "Security", "item": "Rate limit thresholds configured", "status": "pass"},
            {"category": "Validation", "item": "Known-event benchmark validation run", "status": "pass"},
            {"category": "Validation", "item": "Monthly false-positive trend reviewed", "status": "warning"},
            {"category": "Validation", "item": "End-to-end contract test passes", "status": "pass"},
            {"category": "Validation", "item": "Resilience tests pass", "status": "pass"},
        ]

    # ── Scenario Replay ──────────────────────────────────
    def get_scenarios(self) -> list[dict]:
        scenario_dir = DATA_DIR / "demo" / "scenario_replay"
        scenarios = []
        if scenario_dir.exists():
            for f in scenario_dir.glob("*.json"):
                with open(f) as fh:
                    scenarios.append(json.load(fh))
        return scenarios

    # ── Statistics Helpers ────────────────────────────────
    def summary_stats(self, district: str = None) -> dict:
        events = self.get_events()
        if district and not events.empty and "district" in events.columns:
            events = events[events["district"] == district]
        if events.empty:
            return {
                "total_events": 0,
                "active_events": 0,
                "critical_zones": 0,
                "total_population": 0,
                "avg_confidence": 0.0,
                "corridors_monitored": 0,
                "pending_review": 0,
            }
        return {
            "total_events": len(events),
            "active_events": len(events[events["status"].isin(["active", "published"])]),
            "critical_zones": len(events[events["severity"] == "critical"]),
            "total_population": int(events["population_exposed"].sum()) if "population_exposed" in events.columns else 0,
            "avg_confidence": round(events["confidence"].mean(), 2) if "confidence" in events.columns and not events["confidence"].isna().all() else 0.0,
            "corridors_monitored": events["corridor_id"].nunique() if "corridor_id" in events.columns else 0,
            "pending_review": len(events[events["status"].isin(["draft", "queued", "review"])]),
        }


# Singleton
data_service = DataService()
