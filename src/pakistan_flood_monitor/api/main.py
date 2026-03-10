from fastapi import FastAPI

from pakistan_flood_monitor.pipeline.runner import FloodMonitoringPipeline

app = FastAPI(title="Pakistan Flood Monitor API", version="0.1.0")
pipeline = FloodMonitoringPipeline()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/run/{aoi_name}")
def run_pipeline(aoi_name: str):
    return pipeline.run_daily(aoi_name).model_dump()
