# Pakistan River Flood Monitoring and Breach Detection System

Satellite-driven framework for near-real-time flood detection, river breach early warning, flood extent mapping, and exposure analysis across Pakistan.

## What this project includes
- **Startup-focused MVP architecture** across monitoring, analytics, and delivery.
- **Pilot-corridor-first operations** to control cost and latency.
- **Rule-based phase-1 engine** with pathways to ML and deep-learning upgrades.
- **FastAPI service** for triggering and serving flood analysis outputs with confidence and review status.

## Data ecosystem
### Primary EO sources
- Sentinel-1 SAR (all-weather flood detection)
- Sentinel-2 optical imagery (water indices and boundary refinement)
- Landsat 8/9 (historical context)
- HLS (higher temporal optical harmonization)

### Supporting layers
- IMERG rainfall
- GloFAS river forecasts
- Copernicus DEM
- JRC Global Surface Water

## Repository structure
- `src/pakistan_flood_monitor/data/` dataset connectors and metadata models
- `src/pakistan_flood_monitor/core/` preprocessing, flood detection, exposure analytics
- `src/pakistan_flood_monitor/pipeline/` event-driven daily orchestration
- `src/pakistan_flood_monitor/services/` alerts and trigger logic
- `src/pakistan_flood_monitor/api/` FastAPI endpoints
- `configs/` alert thresholds and operational settings
- `docs/` architecture and startup implementation blueprint
- `scripts/` local command-line runners

## Alert levels
- **Watch**: rainfall or forecast signals indicate potential flooding.
- **Warning**: satellite anomalies indicate active water expansion.
- **Critical**: confirmed flooding and/or probable embankment breach.

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn pakistan_flood_monitor.api.main:app --reload
```

Run the sample pipeline:
```bash
python scripts/run_daily.py
```

## API endpoints
- `GET /health` → service heartbeat
- `GET /run/{aoi_name}` → run daily flood workflow for a configured pilot AOI and return detection/exposure report

## Methodology summary
1. Detect event triggers (rainfall / forecast / anomaly) to avoid wasteful processing.
2. Download and preprocess SAR/optical data for pilot corridors.
3. Build baseline behavior and detect anomalies.
4. Fuse SAR + optical + hydro-meteorological indicators.
5. Generate flood masks and area statistics.
6. Estimate exposed population and infrastructure.
7. Trigger alert levels with confidence scores and review status.

## ML roadmap
- **Phase 1**: rule-based thresholds (implemented scaffold)
- **Phase 2**: RandomForest/XGBoost/LightGBM classifiers
- **Phase 3**: U-Net/U-Net++/DeepLabV3+ segmentation

## Planning docs
- `docs/startup_implementation_plan.md` (expanded startup and operating model)
- `docs/architecture.md` (technical architecture summary)

## Deployment target
Containerized microservices with PostGIS, object storage, REST APIs, orchestration (Prefect/Airflow), and optional GPU training services.
