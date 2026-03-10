# Release Readiness Audit — pakistan-flood-monitor

Date: 2026-03-10
Auditor stance: independent, skeptical, evidence-based

## A. Executive summary

- **Overall health:** Functional MVP prototype with passing tests, but substantial production-readiness gaps.
- **Release readiness:** **Not ready for release** (for real operational deployment).
- **Main risks:**
  1. Data and state are primarily in-memory for the user-facing API path (loss on restart, no durability).
  2. Dashboard and analytics payloads are partly hardcoded/demo data, reducing trustworthiness.
  3. Security model is minimal token-check RBAC with no user identity binding for actor attribution.
  4. Contract/documentation mismatch and duplicate API stacks (`app.api` vs `pakistan_flood_monitor.api`) create integration ambiguity.
- **Main missing areas:** persistence integration, hardened authn/authz, robust observability + operational controls, and stronger requirement-to-implementation traceability.
- **Confidence level:** **Medium-high** (full test run + targeted code inspection); lower confidence on live infrastructure behavior because no deployed environment was audited.

## B. Completion verification

| Module / feature area | Claimed complete? | Actually complete | Evidence | Gaps found |
|---|---|---|---|---|
| Daily monitoring pipeline (trigger + detection + scoring + outputs) | Yes | **Partial** | Runner executes end-to-end and returns structured report outputs. | Uses fixed/mock feature values and synthetic event geometry in API records; not wired to persistent storage. |
| Public/internal API endpoints | Yes | **Partial** | Endpoints exist and tests pass for key flows. | Two API stacks with different behavior; primary functional API keeps mutable global state in memory. |
| Analyst review + QA gate | Yes | **Partial** | Review endpoint enforces geometry + SOP on publish action. | Actor identity is client-supplied string; no binding to authenticated principal in audit records. |
| Dashboard/reporting/map APIs | Yes | **Partial** | Dashboard endpoints and snapshot generation exist. | Event data source is pre-seeded static list in service constructor, not authoritative pipeline/event store. |
| Security controls | Yes (minimums in plan) | **Partial** | Token-based role checks on internal endpoints. | No stronger auth/session model, no rate limiting, and actor spoofing risk in audit trail. |
| Database + migrations | Yes (schema scaffolding) | **Partial** | SQLAlchemy models + Alembic migrations exist. | Operational API flow does not use DB for core run/event/review state. |
| Testing | Yes | **Partial** | 55 tests pass. | Test environment initially failed due missing `httpx`; coverage is strong for happy-path API behavior but weak on persistence, recovery, and abuse/security scenarios. |

## C. Findings log

### 1) In-memory operational state for core API data (durability/integration gap)
- Severity: **High**
- Category: integration / reliability
- Impacted modules: `src/pakistan_flood_monitor/api/main.py`
- Status: **Confirmed issue**
- Description: The primary API stores run history, events, review audits, model/threshold registry data in module-level Python dictionaries/lists.
- Why it matters: State is lost on process restart, non-shared across workers/replicas, and unsafe for production consistency.
- Evidence: `run_history`, `event_store`, `historical_event_library`, etc. are globals and all endpoint state reads/writes reference them directly.
- Repro reasoning: Restart app => all runtime state disappears; run multiple app instances => divergent state.
- Recommended fix: Move these stores to Postgres/PostGIS-backed repositories with transactionally safe writes and idempotent keys.
- Release blocker: **Yes**

### 2) Dashboard event layer is demo/static data, not authoritative operational data
- Severity: **High**
- Category: dashboard / correctness
- Impacted modules: `src/app/services/dashboard.py`, `src/app/api/routers/analytics.py`
- Status: **Confirmed issue**
- Description: `DashboardService` seeds a hardcoded `_events` list in `__init__` and dashboard/map APIs read from it.
- Why it matters: Business users can make decisions from stale/demo data unrelated to actual reviewed flood events.
- Evidence: Static event definitions are instantiated at service startup; analytics routes call `dashboard_service.*` directly.
- Recommended fix: Source dashboard metrics/layers from reviewed event tables + temporal filters, with explicit data freshness metadata.
- Release blocker: **Yes** for decision-support release.

### 3) Audit actor spoofing risk (identity not bound to token principal)
- Severity: **High**
- Category: security
- Impacted modules: `src/pakistan_flood_monitor/api/main.py`
- Status: **Confirmed issue**
- Description: Internal endpoints validate role by bearer token, but privileged audit entries use `payload.actor` (request body) without binding it to the authenticated identity.
- Why it matters: Any caller with a valid token can impersonate another analyst/admin in the audit log.
- Evidence: `_require_role` returns role only; `admin_review_event` and registry endpoints append audit entries using untrusted `payload.actor`.
- Recommended fix: Derive actor from authenticated token claims; reject/ignore client-supplied actor for privileged actions.
- Release blocker: **Yes**

### 4) Dependency specification gap: test/runtime dependency missing from project manifest
- Severity: **Medium**
- Category: maintainability / testing
- Impacted files: `pyproject.toml`
- Status: **Confirmed issue**
- Description: Test collection fails in clean environments due missing `httpx` required by FastAPI test client.
- Why it matters: CI and reproducibility are fragile; teams can report “complete” while basic checks fail in fresh environments.
- Evidence: Initial `pytest -q` failed with `RuntimeError: starlette.testclient requires httpx` until manual install.
- Recommended fix: Add `httpx` to test/dev dependencies (or core deps if intentionally required broadly), and pin CI env from lockfile.
- Release blocker: **No** (but should be fixed before formal release gate).

### 5) Duplicate API surfaces with inconsistent maturity creates integration ambiguity
- Severity: **Medium**
- Category: integration / maintainability
- Impacted modules: `src/app/api/main.py`, `src/app/api/routers/*.py`, `src/pakistan_flood_monitor/api/main.py`
- Status: **Likely issue**
- Description: Repository contains two API stacks: one minimal (`app.api`) and one richer operational mock (`pakistan_flood_monitor.api`).
- Why it matters: Teams/infrastructure may deploy wrong entrypoint, leading to missing endpoints or different behavior.
- Evidence: `app.api.main` registers sparse routers; `pakistan_flood_monitor.api.main` contains the full endpoint set and business logic.
- Recommended fix: Choose one canonical API module, deprecate/remove the other, and document the deployment entrypoint explicitly.
- Release blocker: **Likely yes** for coordinated multi-team release.

### 6) Time handling uses deprecated naive UTC calls in critical path
- Severity: **Low**
- Category: correctness / maintainability
- Impacted modules: `src/pakistan_flood_monitor/pipeline/runner.py`
- Status: **Confirmed issue**
- Description: `datetime.utcnow()` is used repeatedly for timestamps and durations; tests emit deprecation warnings.
- Why it matters: Encourages naive datetime handling and future compatibility issues.
- Evidence: pytest warnings point to multiple `datetime.utcnow()` calls in runner.
- Recommended fix: Replace with timezone-aware `datetime.now(UTC)` and enforce timezone-normalized schema boundaries.
- Release blocker: **No** (but fix soon).

## D. Missing coverage

- **Tests:**
  - No resilience tests for process restart/state recovery.
  - No multi-worker consistency tests (concurrent writes/read-after-write across instances).
  - Limited negative/abuse auth tests (token misuse, actor spoofing assertions).
- **Validation:**
  - No evidence of end-to-end data contract checks from ingestion through dashboard outputs using realistic datasets.
- **Security:**
  - No rate limiting / abuse controls surfaced in API.
  - No secret-rotation/session strategy documented for bearer tokens.
- **Documentation:**
  - Canonical runtime API path unclear due dual stacks.
  - No explicit runbook for backup/restore and disaster recovery of operational state.
- **Monitoring/ops:**
  - Metrics registry is in-process memory only; no exporter/alert rules integration shown.
- **Dashboard/reporting:**
  - No data freshness SLA or source-of-truth lineage shown for dashboard payloads.
- **Deployment readiness:**
  - No hard release checklist tying migration state, config validation, health checks, and rollback steps.

## E. Dashboard and visualization trust review

Dashboards reviewed:
- `/analytics/summary`
- `/analytics/dashboard/views/{corridor_id}`
- `/analytics/dashboard/review`
- `/analytics/map/events`
- `/analytics/map/corridors`
- `/analytics/snapshots/*`

Assessment:
- **Trustworthiness:** **Low-to-medium** for production decisions.
- **Main mismatches:** Dashboard service is seeded with hardcoded events and geometry, rather than authoritative reviewed event persistence.
- **UX/visual clarity concerns:** Snapshot generation works technically, but visual artifact provenance is not linked to confirmed event lineage/version.
- **Decision risk:** Users may trust map layers/summary counts that do not reflect actual operational event state.

## F. Final verdict

## **Not ready for release**

Reasoning:
1. Core operational state durability/integration is not production-safe (in-memory global state).
2. Dashboard/reporting trust is undermined by static/demo event sources.
3. Security/audit design allows actor spoofing in privileged audit trails.
4. Delivery architecture remains split across two API stacks with unclear canonical deployment target.

Before release, the minimum required work is:
- consolidate to one API stack,
- persist all critical state in DB,
- bind audit actor to authenticated identity,
- wire dashboards to authoritative reviewed-event data,
- add restart/concurrency/security regression tests,
- fix dependency and datetime hygiene issues.
