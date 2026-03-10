from fastapi import FastAPI, HTTPException

from pakistan_flood_monitor.config import settings
from pakistan_flood_monitor.pipeline.runner import FloodMonitoringPipeline

app = FastAPI(title="Pakistan Flood Monitor API", version="0.3.0")
pipeline = FloodMonitoringPipeline()
latest_runs: dict[str, dict] = {}


def _all_events() -> list[dict]:
    return [run["published_outputs"]["review_queue_event"] for run in latest_runs.values()]


def _event_by_id(event_id: str) -> dict | None:
    return next((event for event in _all_events() if event["event_id"] == event_id), None)



@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/run/{aoi_name}")
def run_pipeline(aoi_name: str):
    report = pipeline.run_daily(aoi_name).model_dump()
    latest_runs[aoi_name] = report
    return report


@app.get("/publish/{aoi_name}")
def get_published_outputs(aoi_name: str):
    report = latest_runs.get(aoi_name)
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
    return [run["published_outputs"]["alert_feed_item"] for run in latest_runs.values()]


@app.get("/corridors")
def corridors() -> list[dict]:
    return [corridor.model_dump() for corridor in settings.pilot_corridors]


@app.get("/corridors/{aoi_name}/status")
def corridor_status(aoi_name: str) -> dict:
    report = latest_runs.get(aoi_name)
    if not report:
        raise HTTPException(status_code=404, detail="No status found for AOI.")
    return {
        "aoi": aoi_name,
        "last_run_id": report["run_id"],
        "trigger_reason": report["trigger_reason"],
        "last_alert_level": report["published_outputs"]["alert_feed_item"]["alert_level"],
    }


@app.get("/corridors/{aoi_name}/events")
def corridor_events(aoi_name: str) -> list[dict]:
    report = latest_runs.get(aoi_name)
    if not report:
        raise HTTPException(status_code=404, detail="No events found for AOI.")
    return [report["published_outputs"]["review_queue_event"]]


@app.get("/events/{event_id}")
def get_event(event_id: str) -> dict:
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    return event


@app.get("/events/{event_id}/exposure")
def get_event_exposure(event_id: str) -> dict:
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    run = latest_runs.get(event["aoi"])
    return {"aoi": event["aoi"], "exposure": run["exposure"][event["aoi"]]}


@app.get("/alerts/latest")
def latest_alerts() -> list[dict]:
    return [run["published_outputs"]["alert_feed_item"] for run in latest_runs.values()]


@app.get("/breach-candidates")
def breach_candidates() -> list[dict]:
    return [run["published_outputs"]["breach_suspicion_layer"] for run in latest_runs.values()]


@app.post("/admin/reprocess-scene")
def admin_reprocess_scene(aoi_name: str) -> dict:
    report = pipeline.run_daily(aoi_name).model_dump()
    latest_runs[aoi_name] = report
    return {"status": "reprocessed", "run_id": report["run_id"], "aoi": aoi_name}


@app.post("/admin/review-event")
def admin_review_event(event_id: str, decision: str, analyst_confidence: float, notes: str = "") -> dict:
    event = _event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    event["decision"] = decision
    event["analyst_confidence"] = analyst_confidence
    event["notes"] = notes or event["notes"]
    return {"status": "review_updated", "event": event}
