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
Actor IDs in privileged payloads are constrained by role prefix:

- admin tokens -> `actor` must start with `admin-`
- analyst tokens -> `actor` must start with `analyst-`

This prevents actor spoofing in audit logs.

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
