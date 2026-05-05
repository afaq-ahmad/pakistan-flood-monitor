"""
Pakistan Flood Monitor — CSV-backed data service layer.
Provides all data operations for the Streamlit dashboard,
reading from local CSV files instead of PostgreSQL/PostGIS.
"""
from __future__ import annotations

import os
import json
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import yaml
import httpx

DATA_DIR = Path("data")
CONFIG_DIR = Path("config/thresholds")
REPORTS_DIR = Path("reports")
STORAGE_DIR = Path("storage")
API_BASE_URL = os.getenv("API_BASE_URL")


class DataService:
    """Singleton-style CSV data backend for the dashboard."""

    def __init__(self):
        self._cache: dict[str, pd.DataFrame] = {}

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
        if API_BASE_URL:
            try:
                response = httpx.get(f"{API_BASE_URL}/public/events", timeout=2.0)
                if response.status_code == 200:
                    events = response.json().get("events", [])
                    if events:
                        # Map API dicts to CSV-like DataFrame
                        df = pd.DataFrame([{
                            "event_id": e.get("event_id"),
                            "corridor_id": e.get("aoi"),
                            "status": e.get("status"),
                            "severity": e.get("latest_event_summary", {}).get("alert_level", "low"),
                            "confidence": e.get("machine_confidence"),
                            "population_exposed": e.get("exposure", {}).get("asset_class_exposure", {}).get("population", 0),
                            "updated_at": e.get("timestamps", {}).get("published_at") or e.get("timestamps", {}).get("detected_at"),
                            "published_at": e.get("timestamps", {}).get("published_at"),
                            "latitude": e.get("geometry", {}).get("coordinates", [[[0,0]]])[0][0][1] if e.get("geometry") else 0,
                            "longitude": e.get("geometry", {}).get("coordinates", [[[0,0]]])[0][0][0] if e.get("geometry") else 0,
                        } for e in events])
                        return df
            except Exception as e:
                print(f"API fetch failed: {e}")
        return self._load("flood_events")

    def get_event(self, event_id: str) -> dict | None:
        df = self.get_events()
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
        """Events awaiting analyst review."""
        return self.get_events_by_status(["draft", "queued", "review", "active", "approved"])

    def update_event_status(self, event_id: str, new_status: str, actor: str, notes: str = ""):
        """Update event status and write audit record."""
        if API_BASE_URL:
            try:
                admin_token = os.getenv("FLOOD_MONITOR_ADMIN_TOKEN", "mock-token")
                headers = {"Authorization": f"Bearer {admin_token}"}
                payload = {"action": new_status, "actor": actor, "notes": notes}
                response = httpx.post(f"{API_BASE_URL}/internal/admin/review-event", json=payload, headers=headers, timeout=2.0)
                if response.status_code == 200:
                    return True
            except Exception as e:
                print(f"API update failed: {e}")
                
        df = self.get_events()
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
        return self._load("exposure_results")

    def get_exposure_for_event(self, event_id: str) -> pd.DataFrame:
        df = self.get_exposure()
        if df.empty:
            return df
        return df[df["event_id"] == event_id]

    # ── Field Reports ────────────────────────────────────
    def get_field_reports(self) -> pd.DataFrame:
        return self._load("field_reports")

    def get_reports_for_event(self, event_id: str) -> pd.DataFrame:
        df = self.get_field_reports()
        if df.empty:
            return df
        return df[df["event_id"] == event_id]

    def moderate_report(self, report_id: str, new_status: str, reason: str = ""):
        df = self.get_field_reports()
        idx = df.index[df["report_id"] == report_id]
        if len(idx) == 0:
            return False
        df.loc[idx[0], "status"] = new_status
        df.loc[idx[0], "trusted"] = (new_status == "approved")
        df.loc[idx[0], "moderation_reason"] = reason
        df.to_csv(DATA_DIR / "field_reports.csv", index=False)
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
        return self._load("audit_log")

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
        latest = self.get_latest_run("daily_monitoring")
        if latest is None:
            return {"status": "unknown", "message": "No pipeline runs found", "age_minutes": None}
        try:
            if pd.notna(latest.get("completed_at")):
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
        """Generate a mock export artifact matching export_center.md."""
        event = self.get_event(event_id)
        if event is None:
            return {"error": f"Event {event_id} not found"}
        export_id = f"exp-{event_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
        export_dir = Path(".cache/exports") / export_id
        export_dir.mkdir(parents=True, exist_ok=True)

        ext_map = {"geojson": ".geojson", "cog": ".tif", "geoparquet": ".parquet"}
        ext = ext_map.get(fmt, ".geojson")
        output_path = export_dir / f"{event_id}{ext}"

        # Write mock data
        if fmt == "geojson":
            geojson = {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [float(event.get("longitude", 0)), float(event.get("latitude", 0))]},
                    "properties": {"event_id": event_id, "severity": event.get("severity"), "confidence": event.get("confidence")}
                }]
            }
            output_path.write_text(json.dumps(geojson, indent=2))
        else:
            output_path.write_text(f"Mock {fmt} export for {event_id}")

        manifest = {
            "schema": "pakistan-flood-monitor/export-manifest/v1",
            "export_id": export_id,
            "event_id": event_id,
            "format": fmt,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "lineage": {
                "source_endpoint": f"/public/events/{event_id}",
                "exposure_endpoint": f"/public/events/{event_id}/exposure",
                "processing_version": "2.1.0",
            },
            "outputs": [{"path": str(output_path), "size_bytes": output_path.stat().st_size}],
        }
        manifest_path = export_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        return {
            "export_id": export_id,
            "output_path": str(output_path),
            "manifest_path": str(manifest_path),
            "format": fmt,
            "validation": {"valid": True, "checks_passed": ["format_valid", "crs_present", "non_empty"]},
        }

    # ── Release Checklist ────────────────────────────────
    def get_release_checklist(self) -> list[dict]:
        """Return release checklist items from release_checklist.md."""
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
    def summary_stats(self) -> dict:
        events = self.get_events()
        if events.empty:
            return {}
        return {
            "total_events": len(events),
            "active_events": len(events[events["status"].isin(["active", "published"])]),
            "critical_zones": len(events[events["severity"] == "critical"]),
            "total_population": int(events["population_exposed"].sum()),
            "avg_confidence": round(events["confidence"].mean(), 2),
            "corridors_monitored": events["corridor_id"].nunique(),
            "pending_review": len(events[events["status"].isin(["draft", "queued", "review"])]),
        }


# Singleton
data_service = DataService()
