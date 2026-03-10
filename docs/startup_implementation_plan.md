# Startup Implementation Plan (Operational MVP)

## System framing
Build the MVP as a three-layer pipeline:
- **Monitoring layer** for discovery and ingestion of Sentinel-1, optical support imagery, rainfall, forecast, DEM, and static masks.
- **Analytics layer** for flood anomalies, breach suspicion, confidence scoring, and exposure summaries.
- **Delivery layer** for reviewed event persistence, API services, dashboard/map outputs, and alert-ready products.

Implementation must remain modular (not one monolithic script), with modules focused on:
1. metadata/data fetching,
2. raster/vector preprocessing,
3. detection computation,
4. review/publication state management,
5. API and map-service output exposure.

## Engineering sequence
1. AOI/corridor and metadata schema
2. Scene discovery service (metadata-first, deduplicated)
3. Raw/prepared/derived/published storage layout
4. Daily processing job runner (idempotent)
5. Event and review tables
6. Narrow operational API
7. Lightweight dashboard/map publishing
8. Logging/monitoring + failure notifications
9. Scaling upgrades only when needed

## Ingestion architecture
- Event-driven corridor-aware ingestion, not bulk crawling.
- Jobs:
  - scene discovery (Sentinel/Landsat/HLS intersection + dedupe)
  - hydromet fetch (IMERG/GloFAS summaries)
  - reference layer sync (DEM/GSW/boundaries/exposure)
  - task planner (prioritize high-trigger corridors)

## Storage design
- **Raw**: immutable source data
- **Prepared**: clipped/reprojected/normalized COGs
- **Derived**: masks, vectors, confidence layers, stats
- **Published**: analyst-approved and API-ready assets

Preferred formats: COG, GeoParquet, PostGIS, JSON/GeoJSON only for delivery.

## Workflow states
`queued`, `running`, `success`, `failed`, `skipped`, `stale`, `manual_retry_requested`.

## Reliability minimums
Monitor discovery success, download failures, processing latency, AOIs processed, events created, false-alert suppressions, API uptime, disk usage, and queue backlog.

## Security minimums
- Admin authentication
- Tokenized API access
- Secret encryption
- Audit logs for reviewed alerts
- Public vs internal endpoint separation

## ML roadmap discipline
- **Phase A:** rules-first benchmark (implemented first)
- **Phase B:** classical ML candidate ranking
- **Phase C:** segmentation only after label maturity and measurable ROI

## Label quality strategy
Use tiered labels:
- Tier 1 analyst verified
- Tier 2 corroborated
- Tier 3 weak
- Tier 4 auto provisional

Evaluate with event-based and geography-aware splits to avoid leakage.

## Model serving strategy
### MVP and early pilot
- Do not build a separate model serving platform.
- Run inference inside the batch processing pipeline and store outputs.
- Real-time ML inference endpoints are not required in early phases.

### Later split (only if demand grows)
- offline training
- batch inference
- review queue
- API delivery

## Minimal MLOps controls
- model registry table (`model_versions`)
- training data snapshot version tracked in metadata
- training config file (`configs/training_config.yaml`)
- threshold file (`configs/alert_thresholds.yaml`)
- evaluation report archive (`reports/evaluation/`)
- reproducible training script (`scripts/train_candidate_ranker.py`)
- rollback path via previous `model_id`

### Retraining triggers
Retrain only when false alarms materially rise, label diversity improves, or new sensors/features are added.
Do not retrain on a fixed schedule by default.

## Deep learning readiness checklist
Move to segmentation only when all are true:
- dozens of high-quality event labels are available
- flood boundary labels are consistent
- GPU access is available for training
- there is measurable need for better shape extraction
- deployment complexity remains acceptable

### Low-cost compute strategy
- CPU for feature engineering and rule-based inference
- rented/temporary GPU for training bursts only
- avoid dedicated always-on GPU servers until justified

## GIS analyst mandate and QA
The GIS analyst role is mission-critical and owns:
- baseline geospatial products (AOI boundaries, centerlines/channels, embankments, protected-side zones, seasonal and permanent water masks, admin overlays, exposure layers)
- event review queue decisions (accept/modify/reject + event class + confidence + notes)
- labeling SOP maintenance to prevent inter-analyst drift
- cartographic output templates for corridor, district, event comparison, and exposure products
- QA checklist for topology, overlap checks, units, timestamp correctness, and source-scene linkage

## Hydrologist advisory scope (part-time)
When available, a hydrologist should support:
- reach-specific threshold calibration
- plausibility scoring and interpretation
- separation of overflow vs possible breach vs backwater/ponding artifacts
- periodic advisor review instead of mandatory full-time staffing

## Consolidated daily workflow
1. Ingest IMERG and GloFAS summaries.
2. Rank corridors by hydromet stress.
3. Discover new Sentinel-1 scenes for ranked corridors.
4. Download and preprocess relevant scenes.
5. Run SAR anomaly detection vs baseline.
6. Generate flood candidate objects.
7. Enrich candidates with terrain, water history, embankments, and hydromet features.
8. Score flood and breach candidates.
9. Push medium/high-confidence candidates to analyst review queue.
10. Publish reviewed events.
11. Compute exposure overlays.
12. Update API/dashboard outputs.
13. Archive outputs, model metadata, and metrics.


## Step 17 implementation details (rules stable -> ML ranking)
17.1 is implemented as a feature-snapshot workflow for reproducible classical ML ranking training:
- **17.1.1 Feature tables:** each candidate feature row stores SAR, optical support, terrain, hydromet, baseline-context, and (for breach candidates) breach-specific geometric features.
- **17.1.2 Frozen snapshots:** training references immutable snapshot folders with a manifest and separated flood/breach feature tables.
- **17.1.3 Label linkage:** each row carries review outcome, final class, and label quality tier so filters can enforce label quality constraints for training.

This preserves the roadmap order: rules-first operations remain primary, classical ML ranking is trained from frozen feature tables, and deep learning remains deferred until the readiness checklist is met.

17.2 is now implemented as **classical ML candidate ranking** before any deep-learning expansion:
- **17.2.1 Ranking targets:** three independent ranking models are trained for flood candidate confidence, breach candidate confidence, and false-positive suppression.
- **17.2.2 Rules baseline retained:** rule-based confidence scores remain first-class benchmark signals (`rules_flood_confidence`, `rules_breach_confidence`) and are tracked against ML validation metrics.
- **17.2.3 Candidate-object training:** training runs consume candidate-level snapshot tables (not full-scene imagery), preserving lower compute cost and stronger explainability.
- **17.2.4 Model metadata registry:** each training run registers training snapshot ID, feature-set version, hyperparameters, validation metrics, and deployment threshold.
