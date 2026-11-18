# Implementation status

Last verified for this follow-up: **2026-11-18**, against `main` at `6f35e9e` and the My Area selector changes in draft PR #88. Read this file with root
[`AGENTS.md`](../../AGENTS.md) and applicable [ADRs](../adr/README.md) before every task. Verify stale
claims against code and Git history; update this ledger in each consolidated-prompt PR.

## Current contract

| Item | Repository state |
|---|---|
| Canonical package | `src/pakistan_flood_monitor/` |
| Supported API runtime | `pakistan_flood_monitor.api.main:app` |
| Legacy migration source | `src/app/`; deprecated API entrypoint warns of removal after 2026-12-31 |
| Runtime modes | `test`, `demo`, `operational` via `APP_MODE`; default is `demo`; mode is persisted in canonical run metadata |
| Accepted ADRs | [ADR-001: canonical runtime and operational data integrity](../adr/ADR-001-canonical-runtime.md) |
| Package version | `0.1.0` in `pyproject.toml` |
| Canonical DB migration head | Root Alembic chain: `b4d9d93f2a10` (durable canonical pipeline tasks) |
| Legacy DB migration head | `src/app/db/alembic`: `0005_add_lineage_metadata_to_provenance` |
| CI | `.github/workflows/canonical-checks.yml` runs the full offline suite and SQLite migration round-trip on this branch |

The two Alembic histories are not reconciled. The root chain imports canonical package metadata; the
legacy chain belongs to `src/app`. A later migration task must not create another chain or silently
choose between them.

## Consolidated prompt ledger

`COMPLETE` means merged acceptance evidence exists; it does not by itself mean production maturity.

| Prompt | State | Evidence / scope |
|---|---|---|
| 00 | COMPLETE | Repository operating contract merged in [PR #69](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/69); ledger and ADR policy added by the current Prompt 00 follow-up PR |
| 01 | COMPLETE | [PR #68](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/68) merged the first observation-state contract and [PR #71](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/71) merged canonical API/CLI/worker wiring, explicit demo-only helpers, typed availability, publication eligibility, and durable run/task persistence. |
| 02 | COMPLETE | Metric GIS and provenance contracts merged in [PR #72](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/72); operational maturity remains partial. |
| 03 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 04 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 05 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 06 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 07 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 08 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 09 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 10 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 11 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 12 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 13 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 14 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 15 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |

## Current limitations and deprecated work

- Operational execution fails closed because real required IMERG, GloFAS, optical, floodplain,
  flood-extent, and exposure-overlay processors are not all implemented. This structured unavailable
  response is a safety behavior, not an operational capability.
- Advanced SAR remains simulated, optical water detection uses RGB proxies, forecast LSTM weights are
  untrained, and dam surface extent is only a fill proxy. None is validated for warning authority.
- The canonical runner and API no longer import `app.*`; `src/app` remains a deprecated compatibility
  source for prototype routes, analyst tooling, and workflow shims. Its separate Alembic history is
  still unreconciled and must not receive new canonical runtime features.
- Canonical pipeline runs and dependency-aware tasks persist with signature-based idempotency and
  retry counts. Event, review, audit, and dashboard state remain partly in memory; full restart-safe
  API-state migration is still outstanding. Queued or running work cannot safely recover automatically
  after a crash without ownership and fencing. Some raw public views return 503 pending reviewed products.
- Availability now represents `AVAILABLE`, `NO_DATA`, `UNAVAILABLE`, `DEGRADED`, `STALE`, and
  `PARTIAL` with a reason code, evaluation time, and optional freshness rule. Real source adapters
  must populate these fields rather than relying on default values.
- Code, routes, dashboards, or tests existing in the tree do not establish operational readiness.

## Known P0/P1 defects

Severity reflects current evidence, not an exhaustive safety assessment.

| Priority | Defect / risk | Evidence and disposition |
|---|---|---|
| P0 | None formally triaged | Do not interpret this as evidence of operational safety or readiness |
| P1 | Worker crash recovery is not implemented | Queued/running work cannot be safely reclaimed without ownership, fencing, and operator recovery. |
| P1 | Full dependency reproducibility and operational integration are unverified | Dependencies remain loosely constrained; hosted CI, Docker, PostgreSQL, and live providers require validation. |
| P1 | Runtime and migration split-brain remains | Canonical and legacy packages plus two independent Alembic histories require incremental reconciliation |
| P1 | Canonical durable task migration must be applied before operational use | Root Alembic head is `b4d9d93f2a10`; demo/test may initialize local tables, but operational deployments must use Alembic |

## Test and validation status

Baseline verified before this documentation change:

- `python -m pytest tests/ -q --tb=short` — **blocked** in the base environment: `No module named pytest`.
- After `uv sync --all-extras` and locally adding `pytest`: `.venv/bin/python -m pytest tests/ -q
  --tb=short` — **136 passed, 24 failed, 569 warnings**.
- Prompt 00 focused contract and local-link validation: `.venv/bin/python -m pytest
  tests/test_agent_operating_contract.py -q` — **4 passed**.
- Prompt 00 post-change full run: `.venv/bin/python -m pytest tests/ -q --tb=no` — **138 passed,
  24 failed, 569 warnings**; the same 24 pre-existing failure set remains.
- No repository documentation-lint command or CI workflow is configured.

Focused checks on the unmerged canonical-runtime workstream:

- `python -m compileall -q src/pakistan_flood_monitor src/app/pipelines src/app/workers scripts alembic/versions tests/test_workflow_foundation.py` — **passed**.
- Canonical configuration loaded with `APP_MODE=test` and `APP_MODE=demo` — **passed**.
- Canonical `DataCatalog` in `APP_MODE=operational` returned a typed `UNAVAILABLE` observation for a provider outage and typed `NO_DATA` for an empty provider response — **passed**; neither observation contained a value or synthetic lineage.
- Root migration modules were syntax-parsed — **passed**.
- `tests/test_workflow_foundation.py` — **not run** because this workspace has no virtual environment and its available base runtime lacks `pytest`, `SQLAlchemy`, and raster dependencies. The new `dev` extra supplies `pytest`; no broad dependency install or full-suite run was performed for this workstream.

Focused checks on the unmerged metric-GIS contracts workstream:

- `PYTHONPATH=src uv run --no-project --with 'shapely>=2.0' --with 'pyproj>=3.6' --with 'pytest>=8.0' --with 'pydantic>=2.6' python -m pytest tests/test_geo_measurements.py tests/test_lineage_schema.py -q` — **4 passed**. Pakistan-latitude geometry assertions confirm plausible km/km² values; the two existing Pydantic `schema`-field warnings remain.
- `python -m compileall -q src/pakistan_flood_monitor/geo src/pakistan_flood_monitor/models src/pakistan_flood_monitor/pipeline/runner.py src/app/services src/app/db/spatial.py` — **passed**.
- Static call-site check confirms scene ingestion, exposure, preprocessing, and corridor buffer services import `pakistan_flood_monitor.geo.measurements`; no raw Shapely metric calculation remains outside the helper implementation.

## Next recommended prompt

Prioritize fenced worker crash recovery, restart-safe event/review persistence, and independently
validated real-data ingestion and reviewed products. These are not completed by the offline test fixes.

## Independent audit follow-up (2026-11-17; historical baseline)

The following findings describe the earlier audit baseline; see the later follow-ups for merged fixes.

At main `6f486ca`, API import failed because the canonical task model used an unimported
`Index`. This branch repairs the import, preserves `DEGRADED` input in integrity summaries,
including the operational required-input gate, and records invalid processor results as failed
runs and tasks. These fixes do not establish operational readiness.

Critical unresolved security: the API accepts unsigned `v1` role/principal payloads as bearer
credentials. Operational publication lineage also accepts an `AVAILABLE` mapping without source,
time, status, or units. The public latest-run output and advisory endpoints bypass the reviewed-event
publication path. These require urgent contract and authorization decisions before exposure. Durable
workflow recovery and concurrency remain incomplete; no CI workflows are present. README's
"Production-ready" dashboard label is not supported by the accepted ADR or this audit.

- Focused isolated SQLite check: `DATABASE_URL=sqlite:////tmp/flood_audit_tests_1.db .venv/bin/python -m pytest tests/test_operational_data_integrity.py tests/test_integrity_summary_regression.py tests/test_workflow_foundation.py tests/test_canonical_runtime_smoke.py -q --tb=short` — 12 passed.
- `python -m pytest tests/ -q --tb=no` initially could not collect 14 modules, including the missing `Index`; after the fix and installing Pillow separately, a full run produced failures and was interrupted while still running. The suite writes tracked storage and is not reliably isolated/offline. Full results remain unverified.
- Docker image and PostgreSQL migration were not exercised; Docker was unavailable.

## Publication and authentication audit follow-up (2026-11-17; historical baseline)

The public-route and CI observations in this section predate PRs #75 and #77.

This work removes forgeable unsigned identity tokens from the canonical API and requires complete
per-observation metadata at the publication gate outside test mode. Configured role secrets remain
supported. Existing unsigned-token clients must migrate to configured secrets; role-based audit IDs
are not individual identities. Metadata validation does not verify source authenticity or freshness.
The public latest-run and advisory paths still bypass reviewed-product gating; workflow restart and
concurrent retry ownership, CI, isolated offline tests, and operational data processing remain open.

## Workflow concurrency follow-up (2026-11-17)

Atomic database claims prevent a retry from resetting a queued or running execution, and concurrent
retries of a terminal run cannot both claim it while active. Retried processors receive the original
persisted run ID. Duplicate active API requests return HTTP 409 with the run ID. This does not recover
crashed workers: queued/running runs remain stuck until a separately designed, fenced recovery
mechanism exists. PostgreSQL concurrency and real worker crashes remain unverified.

Focused workflow/security check: `DATABASE_URL=sqlite:////tmp/workflow_claim_final.db
/workspace/scratch/b87b53edb69f/repo/.venv/bin/python -m pytest tests/test_workflow_concurrent_retry.py
tests/test_workflow_foundation.py tests/test_operational_data_integrity.py tests/test_canonical_runtime_smoke.py
tests/test_authentication_boundary.py tests/test_publication_lineage_boundary.py -q --tb=short` — 22 passed.

## Consolidated reliability follow-up (2026-11-17)

- Reused in-memory runs preserve analyst review and do not duplicate history. A changed report for the
  same event/run returns HTTP 409; full restart-safe review persistence remains unimplemented.
- Runtime declares Pillow; CI runs the complete test suite with network sockets disabled and verifies
  that tracked data/storage remain unchanged. Tests force a temporary SQLite DB and test mode, and
  isolate prototype dam history and PDF output.
- Baseline at `65aa6d4`: 164 passed, 25 failed under an offline SQLite run. With this branch, a fresh
  Python 3.12 install and offline full run passed **190 tests** (475 warnings); a three-run concurrent
  subset passed 13 tests each run. SQLite Alembic upgrade/downgrade/upgrade passed.
- Docker, PostgreSQL, hosted Actions and live providers were not tested. Full dependency locking,
  fenced crash recovery, durable reviewed state, currently disabled raw public routes and operational
  EO products remain open. Synthetic historical replay is not accuracy validation.

## Comprehensive functionality-gap remediation (2026-11-17; PR #79)

- **API Layer**: Added `POST /internal/run/{aoi_name}`, `GET /internal/runs`, route alias `POST /internal/field-reports/{report_id}/moderate`, and body/query parameter duality for `POST /internal/admin/review-event`. Added `db.rollback()` in exception handlers before `db.close()`.
- **Configuration**: Expanded `Settings.pilot_corridors` from 3 to all 6 monitored river corridors in `DataCatalog.CORRIDOR_BBOXES`.
- **UI / Dashboard**: Streamlit `backend_service.py` now maps `district`, `event_class`, `confidence_band`, and `breach_suspicion`. Public dashboard (`pages/1_🌍_Public_Dashboard.py`) filters summary stats, alert cards, and exposure tables when a district is selected. Added UI fallback for optional ML packages (`torch`, `openmeteo-requests`). Fixed DOM element lookups in standalone dashboard (`dashboard/app.js` and `dashboard/index.html`).
- **Services & ML**: Added missing `import numpy as np`, guarded optional `torch` imports with a pure-NumPy Otsu thresholding fallback in `advanced_ml_service.py`, and added offline test bypass and timeouts for `_fetch_dam_thumbnail` in `dam_service.py`.
- **Historical Backtesting**: Replaced tautological assertions in `tests/test_backtesting.py` with meaningful scenario-rainfall risk tests.
- **Verification**: `python -m pytest tests/ -q` — **196 passed, 0 failed**. Full compilation check across canonical packages passed.

## Persistent plan and dashboard audit (2026-11-17)

The authoritative work tracker and session handoff are `MASTER_TASK_PLAN.md` and
`AGENT_SESSION_LOG.md`. API-configured event reads no longer fall back to local CSV on empty/error;
API review failures do not write local state (the implementation commit in this PR). Full offline suite: 204 passed, 475 warnings.
Local-only CSV, local exposure, live scientific data, restart-safe review and fenced recovery remain
open; see P0-003 and P1/DATA tasks. Streamlit browser verification, Docker and PostgreSQL not run.

## Pakistan community research follow-up (2026-11-18)

Pakistan-specific needs research and feature specifications are linked from the master plan. PK-002
provides a static FFD/NDMA link page only, with no live warning feed. P0-003 and operational data,
durable review and fenced recovery remain open. PDMA helpline verification timed out; no number is
published. Browser/mobile validation and live provider licensing remain unverified.

## Agent GitHub workflow (2026-11-18; PR #83, PARTIAL)

A checkpoint-first guide, mandatory AGENTS.md pointer, and intentionally invoked Bash helpers
support small commits, fast-forward recovery and remote SHA verification. Seven isolated temporary
Git repository tests passed. Shell syntax and Python test compilation passed; ShellCheck was not
installed. Direct GitHub CLI authentication was unavailable, so the connector created remote
checkpoints; actual GitHub CLI authentication, live push failure, hosted CI and full tests against
current main were not verified. The existing CI was evaluated and left unchanged. Secret screening
is heuristic and requires human/agent review. No application or scientific behavior was changed.
Continue ENG-001 validation before human review; other backlog statuses remain unchanged.

## Public dashboard and functionality audit (2026-11-18, PR #85)

- [Functionality matrix](FUNCTIONALITY_GAP_AUDIT.md) records entry points and gaps across the
  canonical API, dashboard pages, standalone UI, workers, GIS, and deployment.
- UI-001 remains PARTIAL. This branch fixes public event boundaries, dashboard dependencies,
  standalone demo labelling, and local-demo export format and provenance. Browser verification,
  authenticated analyst discovery, partner sharing and reviewed live products remain open.
- Baseline 228 passed. Branch 245 passed, 475 warnings with network sockets disabled. SQLite
  migration round-trip to `b4d9d93f2a10`, compile, workflow YAML and tracked-data checks passed.
- Hosted Actions failed before creating jobs on both baseline and implementation checkpoint.
  Chromium startup was blocked by local socket permissions. Docker, PostgreSQL, external
  providers and scientific validation were outside the verified environment.
- Next UI-001 action is to specify the private queue and audit contract alongside durable review
  (P1-002). Keep P1-003 reviewed publication and operational GIS export open.

## Analyst queue continuation (2026-11-18, PR #86)

- PR #85 merged as `5f700f6`. UI-001 remains PARTIAL. The canonical API now offers a bounded,
  role-protected read-only queue with simulation labels and a minimized response. Its scope is
  the current API process. The Streamlit viewer uses an explicitly entered session credential
  and avoids local audit and fixture reads in API mode. The local demo's review checklist starts
  unchecked.
- The queue, authentication, and publication regression group passed 25 tests. The Streamlit
  and demo regression group passed 35 tests. The full offline suite passed 269 tests with
  475 warnings. SQLite upgrade/downgrade/upgrade, compilation, diff and tracked-data checks passed.
- Chromium startup was blocked by local socket permissions. The
  [main baseline](https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44254312814)
  and [implementation checkpoint](https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44256032041)
  reported failure with zero hosted jobs. Docker and PostgreSQL were unavailable locally.
- Next, propose the P1-002 durable event identity and the review/audit transaction,
  including a review version check, restart behavior, migration, and rollback criteria.
  Keep live dashboard transitions and public products pending contract review.

## Farmer and community audit (18 November 2026)

Base `d24fa22` includes the merged read-only analyst queue from PR #86. The
[persona walkthrough](../product/FARMER_LIVESTOCK_USER_JOURNEYS.md) and
[QA matrix](../product/FARMER_LIVESTOCK_QA_MATRIX.md) record deterministic evidence and
remaining evidence needs. In draft PR #87, PK-001 renders the canonical reference names
and official-source link on empty, errored, timed-out, and unconfigured feeds. Five new
regressions failed before the edit and passed after it. The focused suite passed 30 tests
and the full offline suite passed 274 tests with 475 warnings. The change adds no migration
or publisher behavior. Browser/mobile acceptance remains pending.

The [main workflow](https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44266515268)
and [implementation checkpoint workflow](https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44267412433)
reported failure with zero jobs. Chromium startup failed on local socket permissions.
FL-08's prototype forecast and dam presentation, report protection, reviewed products and
validated farm-level exposure remain open. The next scoped change is the operational
forecast page guard under PK-011, exercised with injected prototype responses.

## PK-001 corridor selector continuation

PR #87 is merged. Draft PR #88 adds a configured-ID selector in the published event view.
It keeps unknown associations in the all-events view, distinguishes missing measurements
and timestamps, and avoids loading the map until requested. No validated district, tehsil,
village or farm coverage is available from the audited data.

All 34 focused tests and 278 full offline tests passed. The SQLite chain round-tripped to
`b4d9d93f2a10`. The [main run](https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44274735400)
and [selector checkpoint](https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44276177058)
reported failure with zero jobs. Chromium startup failed on socket permissions. The draft
retains mobile, browser and keyboard checks. Future farmer and livestock content requires
verified, attributed English guidance and human-reviewed Urdu under PK-010. Reports and
property exposure retain the PK-006 and PK-007 prerequisites.
