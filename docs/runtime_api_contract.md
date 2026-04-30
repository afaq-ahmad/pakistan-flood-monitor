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
