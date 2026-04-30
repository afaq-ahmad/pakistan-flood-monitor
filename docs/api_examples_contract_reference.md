# API Examples and Contract Reference Pack

This pack provides validated request/response examples for core runtime endpoints in `pakistan_flood_monitor.api.main:app`.

## Versioning policy and compatibility

- Current API version is **`0.3.0`** (OpenAPI `info.version`).
- Base paths are versionless and stable by audience:
  - Internal: `/internal/*`
  - Public: `/public/*`
- **Compatibility expectation**:
  - Additive response fields MAY be introduced in minor releases.
  - Existing response fields and types are backwards compatible within `0.x` unless explicitly announced in release notes.
  - Breaking changes require a documented migration note in `docs/runtime_api_contract.md` and coordinated consumer rollout.
- Structured bearer token format is versioned (`v1.<base64url-json>`); token claim requirements are contract-bound and validated.

## Success examples

### 1) Run workflow kickoff (internal)

`GET /internal/run/{aoi_name}` with admin token.

```json
{
  "status": "run_completed",
  "published_outputs": {
    "review_queue_event": {
      "event_id": "evt-indus-lower-2026-...",
      "status": "draft"
    }
  },
  "run_lineage": {
    "schema": "lineage/v1",
    "processing_version": "sar-preprocess-v1",
    "source_scene_ids": ["scene-..."]
  }
}
```

### 2) Corridor event listing (public)

`GET /public/corridors/{corridor_id}/events`

```json
[
  {
    "event_id": "evt-indus-lower-2026-...",
    "corridor_id": "Indus-Lower",
    "status": "published",
    "limitations": {
      "href": "/public/limitations",
      "rel": "limitations",
      "title": "Pakistan Flood Monitor limitations and intended use"
    }
  }
]
```

### 3) Event confidence view (public)

`GET /public/events/{event_id}/confidence`

```json
{
  "event_id": "evt-indus-lower-2026-...",
  "confidence_breakdown": {
    "overall": 0.8,
    "signals": {
      "sar": 0.82,
      "hydromet": 0.76
    }
  },
  "limitations": {
    "href": "/public/limitations",
    "rel": "limitations",
    "title": "Pakistan Flood Monitor limitations and intended use"
  }
}
```

## Failure examples

### 401 Unauthorized (auth)

```http
GET /internal/run/Indus-Lower
Authorization: Bearer invalid-token
```

```json
{"detail": "Unauthorized"}
```

### 422 Validation error (request/path validation)

```http
GET /public/events/
```

```json
{
  "detail": [
    {
      "loc": ["path", "event_id"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

### 404 Not Found (resource lookup)

```http
GET /public/events/evt-does-not-exist
```

```json
{"detail": "Event not found."}
```

### 429 Too Many Requests (rate limit)

```json
{"detail": "Rate limit exceeded"}
```

Includes `Retry-After` header.

### 500 Internal Server Error (unexpected runtime fault)

```json
{"detail": "Internal server error"}
```

Troubleshooting: verify service dependencies (storage/database), inspect server logs, and retry once transient faults are resolved.

## Common integrator workflow

1. Trigger run: `GET /internal/run/{aoi_name}` (authenticated).
2. Review/publish lifecycle via `POST /internal/admin/review-event`.
3. Read published signals from `/public/corridors/{corridor_id}/events` and `/public/events/{event_id}`.
4. Render confidence/exposure context via `/public/events/{event_id}/confidence` and `/public/events/{event_id}/exposure`.

## Troubleshooting notes

- `401`: token missing/invalid/expired; verify token secrets and structured claim `exp`.
- `403`: principal role is outside authorization matrix for requested endpoint.
- `404`: stale or mistyped IDs; re-discover IDs from corridor/event list endpoints.
- `429`: client exceeded environment rate policy; implement backoff and honor `Retry-After`.
- `5xx`: retry with jitter and alert operators if persistent.

## Validation source

Canonical examples are stored in `tests/fixtures/api_contract_examples.json` and validated in `tests/test_api_contract_examples.py` against live endpoint behavior and OpenAPI response schemas.
