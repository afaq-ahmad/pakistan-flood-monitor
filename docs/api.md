# API contract

The canonical service is `pakistan_flood_monitor.api.main:app`. For startup
see [local setup](setup.md). Use `/docs` or `/openapi.json` on a running
instance to discover full routes, parameters and schemas. This page explains
the lifecycle, availability and access boundaries that the generated schema
cannot fully describe.

Canonical workflow runs and tasks are durable. `/internal/runs` and several
review, report, audit and public views rely on process-local state. Use
`/internal/workflow-runs/{run_id}` for the persisted workflow and see
[runtime architecture](architecture.md) for storage boundaries.

## Authorization

Public routes allow reads without a bearer credential. Internal routes require
a configured role secret in `Authorization: Bearer <token>`. The environment
variables and route permissions are described in [configuration](configuration.md)
and below. Missing or unrecognized credentials return 401. A recognized role
without route permission returns 403. The internal rate limiter can return 429
with a `Retry-After` header.

The server resolves audit identities to role principals. A shared role secret
does not identify a person or provide individual token expiry. Unsigned
asserted identities are rejected. Keep internal routes and analyst access in
a trusted deployment.

## Core endpoints

### Public routes

| Route | Behavior |
|---|---|
| `GET /health` | Service health and runtime mode. Service reachability gives no evidence of local flood conditions. |
| `GET /public/limitations` | Public limitations statement. |
| `GET /public/corridors` | Six configured pilot corridor references. Outside test mode, its state is unknown and no run is attached. The catalogue's `active` flag is not live monitoring status. |
| `GET /public/events` | Eligible published snapshot with nullable configured `corridor_id`. Events without a configured association remain in the all-events view. The draft timestamp named `published_at` is not the time of the publish transition. See [timestamp and provenance limits](architecture-environmental-data.md#meaning-freshness-and-provenance). |
| `GET /public/corridors/{aoi_name}/events` | Eligible records for that corridor, optionally filtered by status or confidence bucket. Returns 404 if no corridor run history exists. |
| `GET /public/events/{event_id}` | Eligible event detail or 404. |
| `GET /public/alerts/feed` | Public-safe renderings derived from eligible events. |
| `GET /public/risk-summary/{level}` | Aggregates eligible public events. See the [risk-summary contract](https://github.com/afaq-ahmad/pakistan-flood-monitor/blob/main/data_contracts/README.md). |
| `GET /public/publish/{aoi_name}`, `GET /public/advisories/{aoi_name}/mobile`, `GET /public/corridors/{aoi_name}/status` | Raw run-derived views return 503 outside test mode pending reviewed-product publication. |

### Internal Routes (`/internal`)

#### Operational Runs
- `POST /internal/run/{aoi_name}`: Runs the canonical workflow (admin).
  The existing GET alias has the same permission and starts work too.
- `GET /internal/runs`: Lists this process's run summaries (admin, analyst).
- `GET /internal/workflow-runs/{run_id}`: Reads persisted workflow and task state (admin).

#### Analyst Review Workflow
- `GET /internal/review-queue` lists the current API process's review candidates for
  admin, analyst, and reviewer roles. The items are ordered by descending recorded detection
  time, then event ID. Optional `status` filters to `draft`, `review`, or `approved`;
  `limit` is 1–100 (default 25), and `offset` is nonnegative (default 0).
  The response contains `app_mode`, `items`, and `next_offset` (null at the end).
  Rows contain the event ID, corridor, class, lifecycle state, recorded detection time,
  `machine_confidence_pct` on a 0–100 scale when known, and product label and watermark when
  available. Canonical historic naive UTC detection times are serialized with a UTC offset.
  Missing metadata stays unavailable. Demo/test and identified synthetic records carry
  a simulation marker. Unknown lineage does not establish an operational observation.
  The response sets `Cache-Control: no-store`. The queue is a read-only, process-local
  snapshot. It is subject to change between pages
  and can be incomplete after restart or across workers.
- The API-connected Streamlit viewer uses a role credential supplied in that browser session.
  Use it from a trusted internal deployment. It has read-only triage controls and displays
  a distinct access-denied or unavailable state. Live transitions and audit remain available
  through the existing role-protected API. A durable review and audit contract is tracked in P1-002. See [canonical lifecycle and failures](architecture-user-and-review-flows.md#c-canonical-flood-event-lifecycle).
- `POST /internal/admin/review-event`: Admin, analyst and reviewer roles can
  submit allowed lifecycle transitions. Publication requires the publication gate.
- `POST /internal/reports/field`: Internal intake into process-local report state for admin, analyst and reviewer. A
  duplicate receipt returns `accepted_duplicate` only for the same authenticated role principal
  and event. Conflicting reuse returns HTTP 409 without the existing payload. Report IDs retain
  their current format. Shared role credentials do not establish distinct reporter identities.
- `POST /internal/field-reports/{report_id}/moderate`: Moderates an internal report (admin, analyst).

#### Settings & Configurations
- `POST /internal/admin/register-threshold`: Records threshold version metadata (admin).
- `GET /internal/monitoring/metrics`: JSON metrics (admin, analyst).
- `GET /internal/monitoring/metrics/prometheus`: Prometheus text metrics (admin, analyst).
- `GET /internal/admin/state/export` and `POST /internal/admin/state/restore`: Explicit runtime snapshots (admin).

### Publication lineage

Outside test mode, the publication gate rejects missing or malformed observation lineage. Each
required observation must include its matching name, a finite value, units, status, availability,
source URI, timezone-aware source timestamp, processing version, and quality status. Available,
non-synthetic metadata is necessary but does not by itself establish that a source is authentic,
current, scientifically validated, or authorized for public warning. Existing producers with incomplete
lineage must populate these fields before publication. The separate latest-run and mobile-advisory
routes still need a reviewed-product publication design and must not be relied on for operational use.

### Concurrent workflow requests

A workflow execution claims its persisted run before processing. A duplicate request observes the
existing run; `GET /internal/run/{aoi_name}` returns HTTP 409 with `workflow_in_progress`, its run ID and
status while the existing run is queued or running. Explicit retry claims only a terminal run, and
uses its original persisted run ID. A queued or running run left after a crash cannot be reclaimed
automatically: safe recovery requires worker ownership/fencing and an operator procedure, which are
not implemented. Do not reset an active worker's state directly.
A failed or degraded run without a successful report returns HTTP 503 with `workflow_not_successful`;
a stale report from an earlier attempt is not returned as a successful result.

### Reused runs and analyst review

Repeating an identical completed run does not recreate its in-memory event or erase analyst review
state. If a retry produces a different report for an existing event and run ID, the API returns
HTTP 409 `existing_event_report_conflict` rather than pairing new machine results with the earlier
review. Reusing an event ID for a different run returns 409 `existing_event_run_conflict`. A distinct reviewed-product identity is still needed for changed results. Review state is not
yet fully durable across process restarts.
