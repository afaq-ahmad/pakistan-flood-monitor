# Startup Implementation Plan (Operational MVP)

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
