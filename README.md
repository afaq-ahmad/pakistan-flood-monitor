# Pakistan River Flood Monitoring and Breach Detection System

Satellite-driven MVP for daily corridor flood monitoring, flood anomaly mapping, breach suspicion flagging, exposure estimation, and alert publishing.

## MVP capabilities
- Monitor selected river corridors daily.
- Pull Sentinel-1 corridor scenes plus IMERG and GloFAS indicators.
- Compare new observations against historical baseline context.
- Generate flood candidate polygons and breach suspicion candidates.
- Estimate district/asset exposure.
- Publish map layers, event tables, alert summaries, and API outputs.

## MVP outputs
1. Flood candidate map
2. Confirmed flood extent (after analyst review)
3. Breach suspicion layer
4. Asset exposure report
5. Alert feed with confidence score
6. Historical event dashboard snapshot

## Out of scope for MVP
No national wall-to-wall daily runs, no public mobile app, no hydrodynamic simulation stack, no social media streaming, no enterprise IAM multi-tenancy, and no Kubernetes unless scaling bottlenecks are proven.


## Operational strategy guardrails
- MVP inference is batch-first inside the pipeline; no separate model serving platform.
- Real-time ML inference endpoints are intentionally deferred.
- Minimal MLOps artifacts are tracked (model metadata, data snapshot version, config, thresholds, evaluation archive, reproducible training script, rollback reference).
- Segmentation/deep learning is gated by label quality, GPU availability, clear business need, and acceptable deployment complexity.
- GIS analyst review is mission-critical for event acceptance, event-class labeling, and QA confidence.

## Repository structure
- `src/pakistan_flood_monitor/data/` dataset connectors and metadata
- `src/pakistan_flood_monitor/core/` detection and exposure logic
- `src/pakistan_flood_monitor/pipeline/` daily orchestration
- `src/pakistan_flood_monitor/services/` trigger and alert scoring services
- `src/pakistan_flood_monitor/api/` FastAPI endpoints
- `docs/` architecture and implementation plan

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn pakistan_flood_monitor.api.main:app --reload
```

Run a sample daily pipeline:
```bash
python scripts/run_daily.py
```

## API endpoints
- `GET /health`
- `GET /corridors`
- `GET /corridors/{id}/status`
- `GET /corridors/{id}/events`
- `GET /events/{id}`
- `GET /events/{id}/exposure`
- `GET /alerts/latest`
- `GET /breach-candidates`
- `POST /admin/reprocess-scene`
- `POST /admin/review-event`
- `GET /run/{aoi_name}`
- `GET /publish/{aoi_name}`
- `GET /alerts/feed`

## Deployment stance
Use a simple low-cost setup first (single VM or two-node split) with Python + PostGIS + FastAPI + cron/Prefect OSS + Docker.
