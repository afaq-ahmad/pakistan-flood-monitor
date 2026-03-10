from fastapi import FastAPI, HTTPException

from pakistan_flood_monitor.pipeline.runner import FloodMonitoringPipeline

app = FastAPI(title="Pakistan Flood Monitor API", version="0.2.0")
pipeline = FloodMonitoringPipeline()
latest_runs: dict[str, dict] = {}


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
