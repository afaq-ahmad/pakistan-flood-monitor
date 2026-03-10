# Pakistan River Flood Monitoring and Breach Detection System

Satellite-driven MVP for daily corridor flood monitoring, flood anomaly mapping, breach suspicion flagging, exposure estimation, and alert publishing.

## What we are building
The system is implemented as a coordinated pipeline with three concrete layers:

1. **Monitoring layer**
   - discovers and ingests Sentinel-1, optical support imagery, rainfall, forecast, DEM, and static masks.
2. **Analytics layer**
   - computes flood anomalies, breach suspicion, confidence scoring, and exposure summaries.
3. **Delivery layer**
   - stores reviewed events, serves APIs, powers dashboard/map outputs, and emits alert-ready products.

In implementation terms, this repository is intentionally modular rather than a single script. Python modules are organized to do five things well:
- fetch metadata and data,
- preprocess rasters and vectors,
- compute detections,
- manage review and publication state,
- expose outputs through APIs and map services.

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
- `src/app/config/` typed settings, environment loading, and threshold-file loading
- `src/app/db/` SQLAlchemy session setup, spatial helpers, and Alembic migration scaffolding
- `src/app/models/` ORM tables for AOIs, ingestion state, candidates, events, reviews, and provenance
- `src/app/schemas/` API contracts separated from ORM models
- `src/app/services/` reusable domain logic components
- `src/app/pipelines/` runnable workflow entrypoints for each monitoring stage
- `src/app/api/` FastAPI application and domain routers (monitoring, events, analytics, admin, health)
- `src/app/workers/` background worker entrypoints (cron/Prefect wrappers)
- `src/app/utils/` pure utility helpers
- `config/thresholds/` runtime YAML threshold and weighting files
- `tests/`, `infra/`, `docs/`, and `data_contracts/` for validation, deployment, design, and schema contracts
- `docs/storage_layout.md` storage conventions, naming policy, formats, and run manifests

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.api.main:app --reload
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
