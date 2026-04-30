# Canonical Runtime API Contract

## Canonical stack
Use **`pakistan_flood_monitor.api.main:app`** as the runtime API for operational monitoring.

- Canonical internal base path: `/internal/*`
- Canonical public base path: `/public/*`
- Legacy/demo stack: `app.api.main:app` is retained for feature prototyping and dashboard UX experiments only.

## Authentication and session strategy
Internal APIs require bearer tokens:

- `FLOOD_MONITOR_ADMIN_TOKEN` for admin operations
- `FLOOD_MONITOR_ANALYST_TOKEN` for analyst operations

### Rotation strategy
1. Keep two valid token slots in deployment secrets (`current` and `next`).
2. Deploy app with both tokens accepted via a secret manager template rollout.
3. Switch clients to `next` token.
4. Remove old token in the following deployment.
5. Rotate at least every 30 days or immediately after incident response.

### Actor attribution control
Privileged actor identity is **server-derived** from the authenticated token principal.

- Client-supplied `actor` fields are accepted for backward compatibility but ignored.
- Audit records persist `principal_id` from authenticated claims/context only.
- `actor` in audit payloads mirrors `principal_id` for compatibility with legacy consumers.

## Abuse controls
Internal API has configurable rate limiting middleware:

- `FLOOD_MONITOR_RATE_LIMIT_REQUESTS` (default `60`)
- `FLOOD_MONITOR_RATE_LIMIT_WINDOW_SECONDS` (default `60`)

Exceeding the policy returns `429` with a `Retry-After` header.


## Failure response examples

### 401 Unauthorized
```http
GET /internal/run/Indus-Lower
Authorization: Bearer invalid-token
```
```json
{"detail": "Unauthorized"}
```
Troubleshooting: verify token value and secret injection for `FLOOD_MONITOR_ADMIN_TOKEN`/`FLOOD_MONITOR_ANALYST_TOKEN`.

### 403 Forbidden
```http
POST /internal/admin/register-threshold
Authorization: Bearer <analyst-token>
```
```json
{"detail": "Forbidden"}
```
Troubleshooting: endpoint requires admin principal.

### 404 Not Found
```http
GET /public/events/evt-does-not-exist
```
```json
{"detail": "Event not found."}
```
Troubleshooting: verify event ID from `/public/corridors/{corridor_id}/events`.

### 429 Too Many Requests
```json
{"detail": "Rate limit exceeded"}
```
Troubleshooting: respect `Retry-After` header and tune `FLOOD_MONITOR_RATE_LIMIT_*` settings for environment capacity.

### 500 Internal Server Error
```json
{"detail": "Internal server error"}
```
Troubleshooting: check API logs, PostGIS connectivity, and restore from latest state export if runtime state is inconsistent.


## Canonical scene-derived feature contract
- `FloodMonitoringPipeline.run_daily` computes `DetectionFeatures` from fetched Sentinel-1 scene assets (if available) and deterministic hashed fallbacks when rasters are unavailable.
- Per-run deterministic snapshot is written to `.cache/feature_snapshots/{aoi}/{run_id}.json`.
- Snapshot schema fields: `run_id`, `aoi_name`, `processing_version`, `threshold_version`, `source_scene_ids`, `parameters`, `thresholds`, `derived_features`.
- Lineage requirements: snapshot stores processing and threshold versions plus source scene IDs for reproducibility and replay.
- Reproducibility guarantee: for identical scene IDs/assets and support-layer references, derived features are stable across replays.


## Lineage metadata contract
- Event responses now include `lineage` with STAC-like fields: `schema`, `run_id`, `source_scene_ids`, `source_scenes[]`, `processing_version`, `threshold_version`, `thresholds`, `model`, `generated_at`.
- Run responses include top-level `run_lineage` with the same structure plus `aoi`.
- `source_scenes[]` include `scene_id`, `sensor`, `acquired_at`, and `assets` (href + roles).
- Troubleshooting missing lineage: verify scene discovery provided `scene_id` and acquisition date, and SAR preprocessing populated scene assets before `run_daily`.


## Analyst approval lifecycle

Lifecycle states are strictly ordered:
`draft -> review -> approved -> published -> retracted`.

`POST /internal/admin/review-event` now enforces only the next allowed state.
Invalid transitions return `400` with:
- `error: invalid_lifecycle_transition`
- `current_state`
- `requested_state`
- `allowed_transitions`

Each transition appends an `approval_trace` entry on the event payload:
- `principal_id`
- `timestamp`
- `previous_state`
- `new_state`
- `reason`
- `comment`

Example publish request (must already be in `approved`):
```json
{
  "action": "published",
  "notes": "QA passed and ready for public release",
  "label_metadata": {"label_type": "flood_extent"},
  "mapping_rules": {"certainty_class": "high"}
}
```

## Public limitations and intended-use contract
All public-facing alert endpoints include a `limitations` object with:
- `href`: canonical link to limitations statement (`/public/limitations`)
- `rel`: link relation (`limitations`)
- `title`: short human-readable label

The limitations statement endpoint (`GET /public/limitations`) provides:
- confidence and uncertainty notes
- intended-use boundaries
- warning limitations (false positives, misses, latency)
- non-replacement notice for official emergency instructions

Public endpoints required to include the `limitations` reference:
- `/public/publish/{aoi_name}`
- `/public/alerts/feed`
- `/public/corridors`
- `/public/corridors/{aoi_name}/status`
- `/public/corridors/{aoi_name}/events`
- `/public/events/{event_id}`
- `/public/events/{event_id}/exposure`
- `/public/events/{event_id}/historical`
- `/public/events/{event_id}/confidence`
- `/public/historical-events`
- `/public/historical-events/{event_id}`
- `/public/alerts/latest`
