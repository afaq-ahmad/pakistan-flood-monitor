# Pakistan River Flood Monitoring and Breach Detection System

Satellite-driven framework for near-real-time flood detection, river breach early warning, flood extent mapping, and exposure analysis across Pakistan.

## What this project includes
- **Operational architecture** across ingestion, preprocessing, analytics, and delivery.
- **Python package scaffold** for flood detection and alerting workflows.
- **Rule-based phase-1 engine** with pathways to ML and deep-learning upgrades.
- **FastAPI service** for triggering and serving flood analysis outputs.

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
- `src/pakistan_flood_monitor/pipeline/` end-to-end daily orchestration
- `src/pakistan_flood_monitor/services/` alert-level classification logic
- `src/pakistan_flood_monitor/api/` FastAPI endpoints
- `configs/` alert thresholds and operational settings
- `docs/` architecture and delivery blueprint
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
- `GET /run/{aoi_name}` → run a daily flood workflow for an AOI and return detection/exposure report

## Methodology summary
1. Download and preprocess SAR/optical data.
2. Build baseline behavior and detect anomalies.
3. Fuse SAR + optical + hydro-meteorological indicators.
4. Generate flood masks and area statistics.
5. Estimate exposed population and infrastructure.
6. Trigger alert levels based on confidence and breach risk.

## ML roadmap
- **Phase 1**: rule-based thresholds (implemented scaffold)
- **Phase 2**: RandomForest/XGBoost/LightGBM classifiers
- **Phase 3**: U-Net/U-Net++/DeepLabV3+ segmentation

## Deployment target
Containerized microservices with PostGIS, object storage, REST APIs, orchestration (Prefect/Airflow), and optional GPU training services.
