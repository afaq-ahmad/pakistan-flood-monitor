# Master engineering task plan

Original baseline: `58e735b` on `main`, 2026-11-17. This is the authoritative task checklist;
verify against code and history before claiming work. Status values: NOT_STARTED, IN_PROGRESS,
PARTIAL, BLOCKED, COMPLETE. A checkmark means that specific subtask has evidence; COMPLETE requires
all acceptance criteria and verification. Priorities reflect potential impact, not certified risk.
Use the existing ID and the same record fields when editing a task. Record a workstream
or owner, dependencies, evidence and the exact next action. Keep closed subtasks for history.

Objective: dependable, usable flood information with traceable science and human review. Scope:
canonical API, public/analyst interfaces, data, workflow, security, deployment and tests. Non-goals:
unauthorized warnings, fabricated observations, or claiming readiness without independent evidence.
ADR-001 and AGENTS.md govern runtime, simulation, publication, provenance and metric GIS.

## Pending Work

Choose an authorized task below. Each link leads to the record that owns its
priority, current status, dependencies, acceptance and next action. Repeated
links are navigation to the same record. Confirm active PR ownership before
claiming work. Records without an active branch are unassigned until claimed
in the plan or [handoff](AGENT_SESSION_LOG.md). Priority ranges identify split
slices. Explicit P0 safety prerequisites take precedence.

| Area | Task records |
|---|---|
| Critical safety and security | [P0-001](#p0-001--api-configured-dashboard-must-fail-closed-on-missing-events), [SEC-001](#sec-001--security-and-privacy-audit) |
| Backend and API | [P1-001](#p1-001--fenced-worker-recovery), [P1-002](#p1-002--durable-review-publication-and-audit-state), [P1-003](#p1-003--reviewed-public-products), [API-001](#api-001--canonicallegacy-and-migrations) |
| Frontend and UX | [UI-001](#ui-001--public-and-analyst-dashboard-end-to-end-audit), [PK-001](#pk-001--my-area), [PK-003](#pk-003--urdu-and-low-bandwidth-access) |
| Scientific data, GIS and ML | [DATA-001](#data-001--real-environmental-processing-and-validation), [GIS-001](#gis-001--spatial-and-raster-audit), [PK-008](#pk-008--river-observation-explorer), [PK-011](#pk-011--validated-forecasting) |
| Product and community | [PK-002](#pk-002--official-source-hub), [PK-004](#pk-004--community-sharing-cards), [PK-005](#pk-005--verified-relief-directory), [PK-006](#pk-006--community-reports), [PK-007](#pk-007--farmers-and-livestock), [PK-009](#pk-009--partner-and-ngo-information), [PK-010](#pk-010--historical-and-preparedness-explorer) |
| Developer experience | [ENG-001](#eng-001--resumable-agent-github-workflow), [OPS-001](#ops-001--deployment-and-operational-verification) |
| Documentation | [ENG-001](#eng-001--resumable-agent-github-workflow) |
| QA and deployment | [QA-001](#qa-001--full-independent-audit-and-handoff), [OPS-001](#ops-001--deployment-and-operational-verification) |

Choose an offline failure-path slice under [DATA-001](#data-001--real-environmental-processing-and-validation), a deployment or packaging slice under [OPS-001](#ops-001--deployment-and-operational-verification), or continue the active docs checkpoint under [ENG-001](#eng-001--resumable-agent-github-workflow).
Completed dashboard safeguards [P0-002](#p0-002--prevent-local-review-fallback-after-api-failure) and [P0-003](#p0-003--local-only-dashboard-data-and-exposure-boundary) stay below with their evidence.

The execution baseline for this reconciliation is `8938d60` on main (353 offline tests). UX and FL identifiers refer to scenarios in the [UX matrix](../product/UI_UX_ACCEPTANCE_MATRIX.md) and [farmer/livestock QA matrix](../product/FARMER_LIVESTOCK_QA_MATRIX.md). Engineering IDs own the resulting actions.

## P0-001 — API-configured dashboard must fail closed on missing events

- **Priority** P0 · **Status** `PARTIAL` · **Workstream** Dashboard availability
- **Impact and requirement** A feed error can leave residents without reliable context. [Runtime safety](../adr/ADR-001-canonical-runtime.md)
- **Current behavior** The adapter returns no fixture events on a configured empty or failed feed and distinguishes unavailable from empty.
- **Code** [Dashboard adapter](../../backend_service.py), [1 🌍 Public Dashboard](../../pages/1_🌍_Public_Dashboard.py)
- **Dependencies and blockers** Canonical publication boundary in [PR #75](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/75). Browser evidence outstanding.
- **Acceptance** Empty, invalid and failed API responses stay free of CSV rows. Valid responses map and error states are visible in the browser.
- **Evidence** [PR #81](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/81) and [PR #85](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/85); tests/test_dashboard_api_fail_closed.py, tests/test_streamlit_public_pages.py.
- **Next action** Run the My Area browser empty and timeout cases with keyboard navigation.

- [x] Trace API response and local fallback path.
- [x] Reproduce empty and outage cases (three tests failed before commit `0c83302`).
- [x] Prevent API-configured fallback and verify valid response (commit `0c83302`, 8 focused tests).
- [x] Run offline regression and full suite (204 passed, 475 warnings).
- [x] Exercise no-API, empty, and outage behavior plus the published map/cards/exposure boundary in Streamlit AppTest (PR #85).
- [ ] Validate rendered pages and accessibility in a browser; Chromium startup was blocked in the audit environment.

## P0-002 — Prevent local review fallback after API failure

- **Priority** P0 · **Status** `COMPLETE` · **Workstream** Dashboard moderation
- **Impact and requirement** A canonical review failure must preserve local state. [Functionality audit](FUNCTIONALITY_GAP_AUDIT.md)
- **Current behavior** Review calls in API mode return failure without local updates. Local demo uses its explicit path.
- **Code** [Dashboard adapter update_event_status](../../backend_service.py)
- **Dependencies and blockers** P0-001. No unmet acceptance item for this slice.
- **Acceptance** API failure cannot change the local event or audit records or report success.
- **Evidence** [PR #81](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/81); tests/test_dashboard_api_fail_closed.py.
- **Next action** Keep the failure regression in the dashboard suite.

- [x] Reproduce non-200 and network failure.
- [x] Fail closed; verify successful request, 403 and connection failure.
- [x] Evidence: commit `0c83302`; 8 focused tests and 204 full offline tests passed.

## P0-003 — Local-only dashboard data and exposure boundary

- **Priority** P0 · **Status** `COMPLETE` · **Workstream** Dashboard demo boundary
- **Impact and requirement** Residents and partners need to separate demo exposures from observed products. [ADR-001](../adr/ADR-001-canonical-runtime.md)
- **Current behavior** No operational or API-backed local exposure. Standalone demo surfaces carry the simulation watermark.
- **Code** [Dashboard adapter](../../backend_service.py), [Streamlit entry point](../../streamlit_app.py), [Streamlit pages](../../pages)
- **Dependencies and blockers** P0-001 and explicit demo modes. No unmet acceptance item for this slice.
- **Acceptance** Watermark all demo outputs and suppress unrelated exposure in operational views.
- **Evidence** [PR #84](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/84); tests/test_p0003_exposure_boundary.py.
- **Next action** Retain the labelled demo and no-API operational regression when touching public views.

- [x] Identify no-API CSV and local exposure paths by code inspection.
- [x] Reproduce operational/demo UI behavior and trace all callers.
- [x] Implement safely labelled demo or unavailable behavior: `DEMO_WATERMARK` constant, `is_demo_mode`
  property, `exposure_data_source` tag; `get_exposure()` returns empty in API mode and operational
  no-API mode; public dashboard, analyst review, partner mode, and export center display watermark
  banners; partner advisory text prepends demo watermark; analyst review action buttons fail safe;
  settings UI reflects read-only configuration; 16 focused tests and 228 full offline tests pass.
- [x] Offline automated test coverage for demo watermark, exposure suppression, and API column parity.

## P1-001 — Fenced worker recovery

- **Priority** P1 · **Status** `BLOCKED` · **Workstream** Workflow recovery
- **Impact and requirement** Operators need a safe outcome after a process crash. [Persistence architecture](../architecture.md#workflow-retries-and-recovery)
- **Current behavior** Atomic claims and retries exist. A crash can strand queued or running work.
- **Code** [workflow](../../src/pakistan_flood_monitor/workflow), [Canonical migrations](../../alembic)
- **Dependencies and blockers** Accepted ownership, fencing and idempotency contract before implementation.
- **Acceptance** Restart recovery rejects stale results and duplicate side effects, with migration and concurrent-worker coverage.
- **Evidence** [PR #76](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/76); tests/test_workflow_concurrent_retry.py.
- **Next action** Specify lease expiry and stale-worker rejection, then agree on crash-test scenarios.

- [x] Identify existing atomic claims and crash limitation.
- [ ] Specify owner, fencing and idempotent side effects; approve design.
- [ ] Implement migration, recovery, stale-result rejection and crash/concurrency tests.

## P1-002 — Durable review, publication and audit state

- **Priority** P1 · **Status** `BLOCKED` · **Workstream** Review persistence
- **Impact and requirement** Analysts need review state and audit history retained across restarts. [Review flow](../architecture-user-and-review-flows.md#c-canonical-flood-event-lifecycle)
- **Current behavior** A draft can be written to SQL. Review transitions and audit remain partly process-local.
- **Code** [main.py](../../src/pakistan_flood_monitor/api/main.py), [Canonical migrations](../../alembic)
- **Dependencies and blockers** Durable identity, versioning and audit transaction contract before implementation.
- **Acceptance** Authorized transitions and their audit persist atomically and safely across retry, concurrency and rollback.
- **Evidence** [PR #86](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/86) and [PR #97](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/97); tests/test_canonical_review_queue.py verifies the current queue.
- **Next action** Specify event identity, review version and audit transaction, including duplicate and restart cases.

- [x] Identify in-memory state and restart limitation.
- [ ] Propose the durable event identity, review version and review/audit transaction contract.
- [ ] Define migration, restart, duplicate submission, concurrent transition and rollback acceptance tests.
- [ ] Implement and test the contract after review.

## P1-003 — Reviewed public products

- **Priority** P1 · **Status** `PARTIAL` · **Workstream** Reviewed publication
- **Impact and requirement** Residents need provenance and authority for shared results. [Publication contract](../api.md#publication-lineage)
- **Current behavior** Eligible events are available. Raw run/advisory views are guarded. Draft-time published_at does not establish actual publication time.
- **Code** [main.py](../../src/pakistan_flood_monitor/api/main.py), [publication_eligibility.py](../../src/pakistan_flood_monitor/services/publication_eligibility.py)
- **Dependencies and blockers** P1-002, DATA-001. Reviewed-product and source freshness contracts outstanding.
- **Acceptance** Authorize only eligible reviewed products and show unambiguous provenance, freshness and unavailable states.
- **Evidence** [PR #75](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/75) and [PR #97](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/97); tests/test_publication_lineage_boundary.py.
- **Next action** Specify publish-transition timestamps and public freshness, then outline review and authorization tests.

- [x] Identify intentionally unavailable raw-run/advisory endpoints.
- [ ] Define reviewed-product provenance, authorization and public API/UI contracts.
- [ ] Specify the publication timestamp contract. The API currently sets `published_at` when creating a draft. Define the actual publication timestamp, distinguish it from observation and evaluation time, and cover draft, publish, retract and public freshness behavior. See [verified ingestion semantics](../architecture-environmental-data.md).
- [ ] Implement and test availability, freshness and safe degradation.

## UI-001 — Public and analyst dashboard end-to-end audit

- **Priority** P1 · **Status** `PARTIAL` · **Workstream** Public and analyst UI
- **Impact and requirement** Residents and analysts need visible source limitations and reliable actions. [UX acceptance matrix](../product/UI_UX_ACCEPTANCE_MATRIX.md)
- **Current behavior** Grouped public navigation and a read-only canonical queue are merged. Prototype operator actions still have pending feedback checks.
- **Code** [Streamlit entry point](../../streamlit_app.py), [Streamlit pages](../../pages), [Dashboard](../../dashboard), [Dashboard adapter](../../backend_service.py)
- **Dependencies and blockers** P0-001, P0-002. Browser and assistive-technology evidence outstanding. P1-002 gates live mutations.
- **Acceptance** Verify navigation, publication, privacy, mode, freshness and failure states across component and browser checks.
- **Evidence** [PR #86](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/86), [PR #93](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/93), [PR #94](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/94); tests/test_streamlit_public_pages.py, tests/test_streamlit_analyst_queue.py.
- **Next action** Reproduce UX-A11 for Operations and Training, and record browser keyboard and reflow evidence when available.

- [x] Inventory public and analyst data paths, including standalone dashboard. See the [functionality gap audit](FUNCTIONALITY_GAP_AUDIT.md).
- [x] Verify public snapshot, mode, dashboard install, and demo export boundaries with offline tests.
- [x] Verify the standalone HTML prototype and feed are labelled in demo/test and refuse operational mode.
- [x] Verify the public/dashboard boundary work merged in [PR #85](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/85).
- [x] Reproduce the analyst discovery gap. The page filters a published-only API feed for drafts while using local audit CSV.
- [x] Specify the [authorized read-only queue](../api.md#analyst-review-workflow) and its process-local limits.
- [x] Test role enforcement, pagination, simulation labels, and public-feed isolation for the canonical queue. The focused queue, authentication, and public boundary suite passed 25 tests.
- [x] Wire a credential-scoped analyst viewer with distinct empty, access-denied, and unavailable states. Verified in Streamlit AppTest through the actual FastAPI route and offline failure cases.
- [x] Remove default attestations from the separate demo checklist and verify local/API isolation. The viewer, dashboard boundary and prior demo suite passed 35 focused tests.
- [x] Run the full offline suite (269 passed) and SQLite migration round-trip for PR #86.
- [ ] Define a durable review and audit contract before implementing live dashboard mutations (P1-002).
- [ ] Verify hosted CI and before/after browser render. GitHub runs on main and the implementation checkpoint returned zero jobs, and Chromium startup was blocked by local socket permissions.
- [ ] Verify browser presentation, keyboard access, and actual file download transfer.
- [ ] Verify mode, freshness, authorization, privacy and error handling with UI tests.
- [x] Audit Home, the 18 Streamlit pages, standalone dashboard and adapter. Record the [UX plan](../product/UI_UX_IMPROVEMENT_PLAN.md) and [acceptance matrix](../product/UI_UX_ACCEPTANCE_MATRIX.md).
- [x] Implement and verify UX-A01–03 on `ux/ui-001-public-home` ([PR #93](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/93)). Home has five native public links and one fail-closed published-event snapshot. AppTest verified destinations and feed states. Browser acceptance remains open.
- [x] Remove unauthenticated browser settings edits and configuration display. Verify the public journey and canonical access boundary under SEC-001.
- [ ] Improve Operations and Training action feedback in UI-001.
- [x] Register the existing pages in one native grouped menu ([PR #94](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/94)). Verify all 18 legacy route paths and the five public destinations in AppTest. Keep access checks in their existing handlers.
- [ ] Verify menu reflow, keyboard focus and browser history at 320, 360, 390, 768 and 1440 px. Track language and mobile acceptance under PK-003.
- [x] Refine Home's hierarchy and share availability guidance on Home and My Area. Verify absent source, empty feed, timeout and API error without fixture fallback. Display the existing stale status for demo processing and keep operational feed freshness unknown.

## DATA-001 — Real environmental processing and validation

- **Priority** P1 · **Status** `BLOCKED` · **Workstream** Environmental processing
- **Impact and requirement** Operators need traceable inputs and typed unavailable results. [ADR-001](../adr/ADR-001-canonical-runtime.md)
- **Current behavior** Required operational inputs are incomplete. The downstream guard has a confirmed missing exception import when extraction is stubbed.
- **Code** [runner.py](../../src/pakistan_flood_monitor/pipeline/runner.py), [data](../../src/pakistan_flood_monitor/data)
- **Dependencies and blockers** Real inputs require licensed sources, validated processing and independent evidence. Downstream failure hardening is eligible offline.
- **Acceptance** Evidence covers provider and processor failure, provenance, calibrated units and public eligibility before any operational result.
- **Evidence** [PR #97](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/97) and [PR #98](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/98); tests/test_operational_data_integrity.py covers upstream missing-data cases.
- **Next action** Exercise the downstream guard with an offline extraction fixture, restore typed failure and verify no candidate is published.

- [ ] Inventory each source, real/prototype/simulated state, units, freshness and validation.
- [ ] Restore the typed unavailable result at the downstream operational processor gate. A mocked extraction reaching `FloodHazardModule.run_daily` raises `NameError` for the missing `OperationalDataIntegrityError` import. Add a deterministic test for the degraded workflow result and structured 503. Keep publication blocked. This failure-path hardening can run offline while real provider work remains blocked.
- [ ] Obtain authoritative sources and independent validation; implement in separately reviewed steps.

## GIS-001 — Spatial and raster audit

- **Priority** P1 · **Status** `PARTIAL` · **Workstream** Spatial audit
- **Impact and requirement** Incorrect CRS, area or overlay alignment misstates potential exposure. [Geospatial contract](../architecture-environmental-data.md#meaning-freshness-and-provenance)
- **Current behavior** Canonical geodesic and projected measurement helpers have tests. Full raster and overlay audit remains open.
- **Code** [measurements.py](../../src/pakistan_flood_monitor/geo/measurements.py), [spatial.py](../../src/app/db/spatial.py)
- **Dependencies and blockers** DATA-001 for operational validation. Offline known-geometry audit is eligible.
- **Acceptance** Verify metric units, projection, nodata, alignment and boundaries with known fixtures and measured metadata.
- **Evidence** [PR #97](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/97); tests/test_geo_measurements.py. The helper baseline is evidence for this limited slice.
- **Next action** Inventory geometry and raster call sites and add evidence for nodata, reprojection and alignment.

- [ ] Audit geodesic, reprojection, categorical masks and alignment.

## API-001 — Canonical/legacy and migrations

- **Priority** P1 · **Status** `PARTIAL` · **Workstream** Canonical interfaces
- **Impact and requirement** Contributors need one supported entry point and a safe migration path. [ADR-001](../adr/ADR-001-canonical-runtime.md)
- **Current behavior** Canonical and legacy runtimes and independent migration heads are documented. Compatibility of remaining legacy callers is open.
- **Code** [Canonical package](../../src/pakistan_flood_monitor), [Legacy package](../../src/app), [Canonical migrations](../../alembic)
- **Dependencies and blockers** ADR-001 and route/consumer parity. Legacy migration choices require review.
- **Acceptance** Preserve public contracts and verify upgrade, rollback and caller parity in the chosen migration path.
- **Evidence** [PR #79](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/79) and [PR #97](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/97); tests/test_canonical_runtime_smoke.py.
- **Next action** Inventory remaining callers and migration paths before proposing compatibility or cleanup changes.

- [x] Record canonical runtime and migration split.
- [ ] Audit interfaces, consumers and safe migration plan with upgrade/rollback tests.

## SEC-001 — Security and privacy audit

- **Priority** P1 · **Status** `PARTIAL` · **Workstream** Security and privacy
- **Impact and requirement** Authorization and report confidentiality must survive UI and API changes. [API access contract](../api.md#authorization)
- **Current behavior** The canonical API checks roles and public eligibility. The settings web route is read-only and internal reports have receipt ownership tests.
- **Code** [main.py](../../src/pakistan_flood_monitor/api/main.py), [8 🔑 Settings](../../pages/8_🔑_Settings.py), [test_field_report_boundaries.py](../../tests/test_field_report_boundaries.py)
- **Dependencies and blockers** P0-001, P0-002; remaining export, upload and source trust paths require evidence.
- **Acceptance** Unauthorized calls fail safely and sensitive data stays out of responses, logs and exports.
- **Evidence** [PR #74](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/74), [PR #89](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/89), [PR #95](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/95).
- **Next action** Audit report and export data paths against the privacy contract, then record isolated negative tests.

- [x] Record prior authentication/publication changes.
- [ ] Verify remaining trust boundaries and document reproducible findings.
- [x] Verify PK-006 idempotent receipt ownership and sanitized conflict responses with synthetic canonical API records.

## OPS-001 — Deployment and operational verification

- **Priority** P1 · **Status** `BLOCKED` · **Workstream** Deployment verification
- **Impact and requirement** Maintainers need reproducible installs and confidence in database upgrades. [Deployment guide](../deployment.md)
- **Current behavior** Python 3.11 and 3.12 and local SQLite pass. Compose parses. Package metadata advertises 3.10, which fails the canonical import.
- **Code** [pyproject.toml](../../pyproject.toml), [Dockerfile](../../Dockerfile), [docker-compose.yml](../../docker-compose.yml), [Offline CI](../../.github/workflows/canonical-checks.yml)
- **Dependencies and blockers** Docker runtime, PostGIS and live provider verification need suitable infrastructure. Packaging can proceed separately.
- **Acceptance** Verify correct install constraints and a target deployment upgrade/rollback smoke with safe environment settings.
- **Evidence** [PR #98](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/98); [compatibility evidence](../testing.md#python-compatibility).
- **Next action** Reconcile Python metadata and tracked egg-info in a disposable checkout, with 3.10 rejection and fresh installs.

- [x] Identify offline CI and SQLite migration checks.
- [ ] Validate image, PostgreSQL migration and deployment with suitable infrastructure. Compose v2.40.3 parsed the configuration with dummy credentials.
- [x] Verify the Python runtime floor using 3.10, 3.11 and 3.12. Clean installs and the full offline suite passed on 3.11.18 and 3.12.14.
- [ ] Reconcile `requires-python` with the verified 3.11 floor and review tracked `src/pakistan_flood_monitor.egg-info/` files. In a disposable checkout, verify metadata, a fresh install and the rejection of the unsupported Python 3.10 runtime.

## QA-001 — Full independent audit and handoff

- **Priority** P1 · **Status** `IN_PROGRESS` · **Workstream** Independent QA
- **Impact and requirement** Maintainers need reproducible evidence across runtime and user journeys. [Functionality audit](FUNCTIONALITY_GAP_AUDIT.md)
- **Current behavior** Offline checks cover publication, browser components and reporting. Browser/device, production database and provider evidence remain open.
- **Code** [Test suite](../../tests), [Offline CI](../../.github/workflows/canonical-checks.yml)
- **Dependencies and blockers** Browser with usable startup, Docker/PostGIS and permitted provider access for those slices.
- **Acceptance** Dated fixtures, exact commands and reproducible outcomes for each tested surface. Domain validation needs independent evidence.
- **Evidence** [PR #85](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/85), [PR #89](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/89), [PR #95](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/95); [farmer and livestock QA](../product/FARMER_LIVESTOCK_QA_MATRIX.md).
- **Next action** Record a browser run for UX-A15 and FL-12 when available, preserving unverified acceptance separately.

- [x] Read agent contract, ADR-001, ledger, recent commits and open PRs.
- [x] Record baseline behavior by feature and runtime in the [functionality matrix](FUNCTIONALITY_GAP_AUDIT.md) (PR #85).
- [x] Run focused tests (8 passed) and complete offline suite (204 passed, 475 warnings).
- [ ] Verify Docker, PostgreSQL, live providers and UI when available.
- [x] Reconcile merged PR #88 and re-run the clean offline baseline at `cb70717` (278 passed).
- [x] Record the incremental [end-user acceptance matrix](../product/FARMER_LIVESTOCK_QA_MATRIX.md#independent-qa-follow-up) against current main without re-auditing closed workstreams.
- [x] Record PR #89, 293-test offline acceptance and handoff for this independent QA continuation.
- [ ] Complete hosted and browser verification and outstanding QA workstreams.

## Pakistan community features — research-backed backlog

### PK-001 — My Area

- **Priority** P1 · **Status** `PARTIAL` · **Workstream** My Area
- **Impact and requirement** Residents need known coverage and a way to select a supported corridor. [Feature specification](../product/PAKISTAN_FEATURE_ROADMAP.md#pk-001--my-area).
- **Current behavior** Configured pilot selector and published event association are merged. Unknown area and empty states remain explicit.
- **Code** [1 🌍 Public Dashboard](../../pages/1_🌍_Public_Dashboard.py), [Dashboard adapter](../../backend_service.py), [config.py](../../src/pakistan_flood_monitor/config.py)
- **Dependencies and blockers** UI-001, P0-003, P1-003; licensed local boundaries and browser verification outstanding.
- **Acceptance** Show configured corridors even on outage, keep unmapped events in all-events view and avoid parcel safety inference.
- **Evidence** [PR #87](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/87), [PR #88](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/88); tests/test_streamlit_public_pages.py.
- **Next action** Run mobile and keyboard cases, then validate candidate local aliases with partners.

- [x] Trace canonical names, public event fields and published-only data path (FL-01/01B/06).
- [x] Reproduce missing area context on empty response, 503 and timeout using AppTest.
- [x] Verify the [planning checkpoint](https://github.com/afaq-ahmad/pakistan-flood-monitor/commit/170a2608d8ac3effec415da1d432fd03816ad288) and open PR #87 before editing the public dashboard.
- [x] Add reference-list regressions before implementation. All five failed against the baseline.
- [x] Verify reference names and official navigation for an empty 200, 503, timeout, and API absence. Verify that an empty configured catalogue has an explicit state.
- [x] Verify demo/published filtering, fail-closed publication, and official navigation with 30 focused tests.
- [x] Run the full offline suite (274 passed, 475 warnings) and record delivery evidence.
- [x] Audit the six canonical pilot IDs against the five legacy CSV map lines and the event-side district labels. See [coverage evidence](../product/FARMER_LIVESTOCK_USER_JOURNEYS.md#my-area-coverage-and-selection).
- [x] Reproduce the missing corridor field and null-timestamp failure with four failing API/UI test cases before editing.
- [x] Verify allowlisted published-only projection, selected/no-match and unassigned all-events states, and empty, timeout, unavailable and unconfigured feeds.
- [x] Verify opt-in responsive map configuration, source navigation, separate timestamps, and demo district filtering with 34 focused API/UI tests.
- [x] Run the full offline suite (278 passed, 475 warnings) and publish the implementation checkpoint.
- [ ] Verify browser/mobile and keyboard behavior when a browser is available.
- [ ] Validate permitted district/tehsil/mouza IDs, aliases and coverage mapping with partners.
- [ ] Show reviewed observations, official notices and history separately, with source/issue times.

### PK-002 — Official source hub

- **Priority** P1 · **Status** `PARTIAL` · **Workstream** Source directory
- **Impact and requirement** Residents need issuer and scope before following an official link. [Feature specification](../product/PAKISTAN_FEATURE_ROADMAP.md#pk-002--official-source-hub).
- **Current behavior** The merged directory shows attributed FFD, NDMA and provincial links without live-bulletin ingestion.
- **Code** [official_sources.py](../../official_sources.py), [16 📚 Official Information](../../pages/16_📚_Official_Information.py)
- **Dependencies and blockers** P0-003. Source permissions and ongoing link/accessibility review before any ingestion.
- **Acceptance** Keep issuer, scope and review date visible; an unavailable link gives no current advisory status.
- **Evidence** [PR #82](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/82); tests/test_official_sources_directory.py.
- **Next action** Revalidate provincial destinations with a check date and timeout result.

- [x] Check FFD and NDMA public pages and implement static attributed links (2026-11-18).
- [x] Verify static HTTPS registry offline (9 focused tests; 205 full-suite tests passed).
- [ ] Inventory other official sources and permitted machine-readable access.
- [ ] Define version, ownership and link maintenance for the existing source registry.
- [ ] Show issue/acquisition times only when supported by actual source data.
- [ ] Test source failures, expiry, permissions and accessibility.
- [ ] Revalidate provincial source links and record check date, owner and timeout handling (FL-04).

### PK-003 — Urdu and low-bandwidth access

- **Priority** P1 · **Status** `PARTIAL` · **Workstream** Language and accessibility
- **Impact and requirement** Low-bandwidth and Urdu users need essential text, readable order and keyboard access. [Feature specification](../product/PAKISTAN_FEATURE_ROADMAP.md#pk-003--urdu-and-low-bandwidth-access).
- **Current behavior** Text-first guidance and print views exist. Translation readiness is documented. Urdu and browser acceptance are open.
- **Code** [Streamlit entry point](../../streamlit_app.py), [1 🌍 Public Dashboard](../../pages/1_🌍_Public_Dashboard.py), [17 🌾 Farmer Preparedness](../../pages/17_🌾_Farmer_Preparedness.py), [18 🐄 Livestock Preparedness](../../pages/18_🐄_Livestock_Preparedness.py)
- **Dependencies and blockers** UI-001, P0-003; qualified Urdu reviewers and real browsers/devices.
- **Acceptance** Verify reviewed Urdu/RTL, assistive technology, responsive text and readiness without tiles.
- **Evidence** [PR #94](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/94) and [PR #95](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/95); [UX evidence](../product/UI_UX_ACCEPTANCE_MATRIX.md).
- **Next action** Run UX-A15 and FL-12 at 360 px with assets blocked and record keyboard behavior.

- [ ] Audit translations, mobile layout, text-only and print views.
- [x] Inventory English public copy and existing Urdu fields. Document language selection, fallback, units, review and RTL requirements in the UX plan.
- [ ] Add reviewed Urdu strings and verify screen-reader language switching.
- [ ] Design mobile, text-only, printable low-bandwidth views.
- [ ] Test accessibility and record regional-language needs.
- [ ] Test 360 px reflow, reviewed Urdu/RTL, keyboard order and essentials without tiles (FL-06/12).

### PK-004 — Community sharing cards

- **Priority** P1 · **Status** `NOT_STARTED` · **Workstream** Community sharing
- **Impact and requirement** Forwarded text needs an issuer, expiry and clear review status. [Feature specification](../product/PAKISTAN_FEATURE_ROADMAP.md#pk-004--community-sharing-cards).
- **Current behavior** Demo partner text and notification stubs exist. They provide no verified sharing or delivery.
- **Code** [alert_templates.py](../../src/pakistan_flood_monitor/services/alert_templates.py), [notifications.py](../../src/pakistan_flood_monitor/services/notifications.py), [4 🤝 Partner Mode](../../pages/4_🤝_Partner_Mode.py)
- **Dependencies and blockers** P1-003, PK-003; authorized reviewed material and issue/expiry data.
- **Acceptance** Keep source, area, status and expiry intact through copying or exporting, with demo labels where appropriate.
- **Evidence** [PR #97](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/97) documents the boundary. See tests/test_notifications.py for the stub contract.
- **Next action** Specify fields and the expiration and publication policy for forwarded text.

- [ ] Design source-attributed cards; test expiry and publication authorization.
- [ ] Define source/area/issue-time/freshness schema.
- [ ] Restrict sharing to eligible reviewed content.
- [ ] Implement and test text and print formats with reviewed translations.
- [ ] Test issuer, issue/expiry, scope, confidence and demo label through copy/export; validate real provider acceptance (FL-07/11).

### PK-005 — Verified relief directory

- **Priority** P1/P2 · **Status** `BLOCKED` · **Workstream** Relief directory
- **Impact and requirement** Farmers and residents need clearly verified relief and veterinary contact information. [Feature specification](../product/PAKISTAN_FEATURE_ROADMAP.md#pk-005--verified-relief-directory).
- **Current behavior** Preparedness pages link to official resources. Maintained operational service status is unavailable.
- **Code** [16 📚 Official Information](../../pages/16_📚_Official_Information.py), [18 🐄 Livestock Preparedness](../../pages/18_🐄_Livestock_Preparedness.py), [official_sources.py](../../official_sources.py)
- **Dependencies and blockers** P1-002, SEC-001 and verified service ownership, scope and expiry.
- **Acceptance** Only verified, attributed and current records can claim service availability. Test expired and unverified states.
- **Evidence** [PR #95](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/95) covers veterinary link attribution. FL-04 records directory gaps.
- **Next action** Identify official service owners and verify permitted reuse and maintenance cadence.

- [ ] Design verification, expiry and moderation; never infer active shelter availability.
- [ ] Verify official directory sources and scope.
- [ ] Model verification time, expiry and service status.
- [ ] Add moderated corrections and privacy tests.
- [ ] Design verified animal shelter, water, fodder and veterinary resource records with expiry and provider ownership (FL-04).

### PK-006 — Community reports

- **Priority** P2 · **Status** `PARTIAL` · **Workstream** Community reporting
- **Impact and requirement** Residents need consent and a durable private receipt before believing a report was sent. [Feature specification](../product/PAKISTAN_FEATURE_ROADMAP.md#pk-006--community-reports).
- **Current behavior** The demo supplies a preview without saving. The canonical role-restricted API uses process-local report state.
- **Code** [3 📱 Field Reports](../../pages/3_📱_Field_Reports.py), [Dashboard adapter](../../backend_service.py), [main.py](../../src/pakistan_flood_monitor/api/main.py)
- **Dependencies and blockers** P1-002, SEC-001; durable storage, consent, privacy and retention approval for resident intake.
- **Acceptance** Verify no mutation in demo preview and enforce privacy, durability, abuse handling and authorization in operational intake.
- **Evidence** [PR #89](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/89), [PR #92](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/92); tests/test_field_report_boundaries.py.
- **Next action** Draft the private acknowledgement, retention and idempotency contract ahead of any implementation.

- [x] FL-05 follow-up verified in PR #92 (29 focused and 336 full-suite tests passed), originally claimed on `fix/pk-006-report-receipts` from `90062a0`. Replace the unbacked demo receipt with a private practice preview. Check empty fixtures, missing coverage, repeated previews, mode separation and an unchanged moderation queue. Real intake retains P1-002 and SEC-001 dependencies.
- [ ] Audit existing field-report flow; distinguish reports from verified observations.
- [ ] Audit field-report authorization and moderation.
- [ ] Design categories, evidence, deduplication and retention.
- [ ] Test sensitive-location and publication boundaries.
- [x] Reproduce FL-05 page 3 loading local report metrics/actions in API mode and giving no visible error when an AppTest moderation write is declined.
- [x] Reproduce 13 failing FL-05 regression cases before application edits.
- [x] Verify no report CSV reads/writes in operational and API-backed modes, explicit unavailable state and labelled demo moderation.
- [x] Verify stale and failed writes preserve demo CSV and return a failure. Verify every button's failure message and acknowledged success across AppTest rerun.
- [x] Verify an idempotent same-identity, same-event receipt, sanitized conflicts, concurrent same-process retry linkage, and unchanged authorization and IDs. The related suite passed 64 tests.
- [x] Run full offline suite and verify SQLite upgrade/downgrade/re-upgrade, compile and tracked-data isolation (293 passed, 475 warnings).
- [ ] Verify Field Reports and My Area at 360 px with keyboard/screen-reader and visual contrast checks.
- [ ] Design resident consent, categories, receipt and private evidence checks for future intake (FL-05).
- [ ] Define a private acknowledgement and retry/idempotency contract with minimal coarse-area fields, moderation states and retention rules. Exercise unauthorized, duplicate/spam and write-failure cases before enabling operational intake. Verify durable storage and explicit consent for any onward integration.

### PK-007 — Farmers and livestock

- **Priority** P2 · **Status** `BLOCKED` · **Workstream** Agricultural exposure
- **Impact and requirement** Farm households need estimated exposure, reports and verified loss kept distinct. [Feature specification](../product/PAKISTAN_FEATURE_ROADMAP.md#pk-007--farmers-and-livestock).
- **Current behavior** Agricultural report categories and prerequisite specification are present. Parcel-level exposure remains blocked.
- **Code** [report_categories.py](../../src/pakistan_flood_monitor/models/report_categories.py), [exposure.py](../../src/pakistan_flood_monitor/core/exposure.py)
- **Dependencies and blockers** DATA-001, GIS-001, PK-006; licensed field boundaries, consent and validated inundation.
- **Acceptance** Verify spatial and time alignment, units, uncertainty and authorization by data product.
- **Evidence** [PR #90](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/90); tests/test_report_categories.py and [exposure specification](../product/AGRICULTURAL_EXPOSURE_SPECIFICATION.md).
- **Next action** Inventory candidate datasets, licensing and aggregation before designing overlays.

- [ ] Separate estimated exposure, reported losses and verified damage.
- [x] Define agricultural report categories with metadata, privacy flags and consent requirements. See `src/pakistan_flood_monitor/models/report_categories.py` and 12 offline tests.
- [x] Document the agricultural exposure specification and 9 prerequisites in `docs/product/AGRICULTURAL_EXPOSURE_SPECIFICATION.md`. All prerequisites remain BLOCKED.
- [ ] Inventory agricultural datasets and exposure methods.
- [ ] Validate spatial overlays and separate reported from verified damage.
- [ ] Test units, temporal alignment and unsupported compensation claims.
- [ ] Specify crop-stage, storage, irrigation and livestock data separately; validate methods, licensing and unknown-versus-zero semantics (FL-03/04).
- [ ] Require licensed field boundaries, informed consent and access control, validated flood extents, CRS/projection and spatial/temporal alignment. Compare baseline and new inundation, quantify crop and model uncertainty, and keep estimated exposure separate from verified loss. Property-level exposure remains BLOCKED.

### PK-008 — River observation explorer

- **Priority** P2 · **Status** `BLOCKED` · **Workstream** River observations
- **Impact and requirement** Users need measured stage and freshness for supported locations. [Feature specification](../product/PAKISTAN_FEATURE_ROADMAP.md#pk-008--river-observation-explorer).
- **Current behavior** Research hydromet views and source references exist. Canonical validated gauge observations are not available.
- **Code** [10 🌧️ NASA Hydromet](../../pages/10_🌧️_NASA_Hydromet.py), [nasa_service.py](../../nasa_service.py), [feature_generation.py](../../src/pakistan_flood_monitor/pipeline/feature_generation.py)
- **Dependencies and blockers** DATA-001; licensed, calibrated gauge data, timestamps and stage definitions.
- **Acceptance** Verify observation source, units, valid stage and missing/stale states before public display.
- **Evidence** [PR #91](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/91) covers prototype failure messaging; [provider boundary](../architecture-environmental-data.md#research-and-integration-boundaries).
- **Next action** Inventory gauge datasets and permissions for pilot corridors.

- [ ] Validate official measurements, freshness and stage definitions.
- [ ] Inventory gauge sources and permissions.
- [ ] Validate units, timestamps and stage definitions.
- [ ] Implement missing/stale states and source lineage tests.

### PK-009 — Partner and NGO information

- **Priority** P2 · **Status** `PARTIAL` · **Workstream** Partner exports
- **Impact and requirement** Partners need authorized reviewed summaries that protect sensitive information. [Feature specification](../product/PAKISTAN_FEATURE_ROADMAP.md#pk-009--partner-and-ngo-information).
- **Current behavior** Standalone demo export is labelled. Reviewed public export and operational advisory composition are pending.
- **Code** [4 🤝 Partner Mode](../../pages/4_🤝_Partner_Mode.py), [5 📤 Export Center](../../pages/5_📤_Export_Center.py), [main.py](../../src/pakistan_flood_monitor/api/main.py)
- **Dependencies and blockers** P1-002, P1-003, SEC-001; role and redaction policy needed.
- **Acceptance** Export only permitted fields and preserve source and expiry. Verify role boundaries and audit.
- **Evidence** [PR #85](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/85), [PR #97](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/97); tests/test_streamlit_demo_export.py.
- **Next action** Review current advisory text for issuer, expiry, scope and redaction with an offline payload fixture.

- [ ] Audit partner mode; constrain access and sensitive data.
- [ ] Audit partner-mode authorization and existing exports.
- [ ] Design reviewed summaries and sensitive-data minimization.
- [ ] Add authorization and audit tests.
- [ ] Review Partner advisory payload, remove unsupported authorizations and verify plaintext source/expiry and redaction (FL-07/13).

### PK-010 — Historical and preparedness explorer

- **Priority** P3 · **Status** `PARTIAL` · **Workstream** Preparedness and history
- **Impact and requirement** Farmers and livestock keepers need sourced practical material and unambiguous historical dates. [Feature specification](../product/PAKISTAN_FEATURE_ROADMAP.md#pk-010--historical-and-preparedness-explorer).
- **Current behavior** English guides with checklists and print views merged. Historical map provenance and reviewed Urdu remain open.
- **Code** [12 🗺️ Historical Flood Map](../../pages/12_🗺️_Historical_Flood_Map.py), [17 🌾 Farmer Preparedness](../../pages/17_🌾_Farmer_Preparedness.py), [18 🐄 Livestock Preparedness](../../pages/18_🐄_Livestock_Preparedness.py), [historical_flood_regions.json](../../data/historical_flood_regions.json)
- **Dependencies and blockers** DATA-001, GIS-001 for history; qualified translation review under PK-003.
- **Acceptance** Keep history separate from forecast and verify attributed, accessible, text-first preparedness guidance.
- **Evidence** [PR #90](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/90), [PR #95](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/95); tests/test_public_preparedness_journeys.py.
- **Next action** Audit historical outline sources, dates and licensing; verify additional guide content against published guidance.

- [ ] Distinguish history from prediction; validate maps and legends.
- [ ] Audit historical sources, dates and geometry.
- [ ] Distinguish history from forecasts and unknown coverage.
- [ ] Verify preparedness guidance and legend tests.
- [ ] Check provenance and permissions of bundled historical flood outlines; distinguish approximate outlines from verified training evidence (FL-03).
- [x] Add Farmer Preparedness page (`pages/17_🌾_Farmer_Preparedness.py`) with sourced English guidance for crops, grain/seed, equipment, chemicals, records and recovery. Text-first, no maps or live feed dependency. 8 offline tests pass.
- [x] Add Livestock Preparedness page (`pages/18_🐄_Livestock_Preparedness.py`) with sourced English guidance for animal water/fodder, identification, welfare, veterinary links and recovery. Service availability treated as unknown. 9 offline tests pass.
- [x] Add visible stage checklists, sourced topic details, and a text-first print view to Farmer Preparedness.
- [x] Apply the stage and print pattern to Livestock Preparedness. Replace the untraceable fixed fodder duration and unsupported treatment details. Add attributed provincial veterinary contact sources.
- [x] Verify all six public journeys with offline component and API tests. Document source labels, request counts, browser gaps and Urdu readiness. See [PR #95](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/95).
- [ ] Verify and attribute additional government or humanitarian guidance for remaining agricultural topics.
- [ ] Verify and attribute guidance for additional species-specific livestock needs. Treat service availability as unknown unless the provider verifies it (PK-005).
- [ ] Review Urdu translations with a qualified human reviewer before publication. Keep preparedness content separate from model outputs, evacuation routes or operational notices.

### PK-011 — Validated forecasting

- **Priority** P3 · **Status** `BLOCKED` · **Workstream** Forecast validation
- **Impact and requirement** An unvalidated model must not be presented as actionable guidance. [Feature specification](../product/PAKISTAN_FEATURE_ROADMAP.md#pk-011--validated-forecasting).
- **Current behavior** Operational forecast and dam pages fail closed. Demo separates simulated research from official advice.
- **Code** [13 🔮 Flood Forecasting](../../pages/13_🔮_Flood_Forecasting.py), [15 🏗️ Dam Flood Risk](../../pages/15_🏗️_Dam_Flood_Risk.py), [forecast_service.py](../../src/pakistan_flood_monitor/services/forecast_service.py)
- **Dependencies and blockers** DATA-001; independent hindcast, gauge datasets and calibration evidence.
- **Acceptance** Preserve disabled operational views and prove calibration, provenance and failure semantics before exposure.
- **Evidence** [PR #91](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/91); tests/test_safety_gates_and_community_reporting.py.
- **Next action** Inventory datasets and compare defensible baselines with an out-of-sample design.

- [ ] Keep operational forecast disabled until independently validated.
- [x] Treat FL-08 as P0 presentation risk. Gated prototype forecast (`pages/13`) and dam analysis (`pages/15`) in operational mode. Removed evacuation wording and uncalibrated alarmist alerts. 6 offline tests pass in `tests/test_safety_gates_and_community_reporting.py`.
- [ ] Audit model maturity and candidate datasets.
- [ ] Compare defensible baselines with out-of-sample validation.
- [ ] Test probabilistic calibration and preserve operational disablement.

## ENG-001 — Resumable agent GitHub workflow

- **Priority** P2 · **Status** `PARTIAL` · **Workstream** Agent and documentation workflow
- **Impact and requirement** Contributors need one recoverable task, evidenced checkpoints and working links. [Agent contract](../../AGENTS.md)
- **Current behavior** Root contract, Git helpers, vault navigation and runtime diagrams are merged. Current slice is on `docs/backlog-verification` from `8938d60`.
- **Code** [Root contract](../../AGENTS.md), [Documentation](../../docs), [Agent checkpoint script](../../scripts/agent_checkpoint.sh), [documentation checker](../../scripts/check_docs.py), [Offline CI](../../.github/workflows/canonical-checks.yml)
- **Dependencies and blockers** Current GitHub integration and hosted CI work. Authenticated gh and GitHub/Obsidian visual previews require suitable access.
- **Acceptance** IDs and statuses are unique and verifiable. Startup, diff check, CI, remote ref and handoff give an agent enough information to resume.
- **Evidence** [PR #83](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/83), [PR #96](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/96), [PR #97](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/97), [PR #98](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/98); tests/test_agent_git_workflow.py and [hosted verification](https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44355477233).
- **Next action** Verify the rendered Pending Work entry and diagrams in GitHub and Obsidian, then record evidence for maintainer review of [PR #99](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/99).

- [x] Open a draft PR after initial workflow documentation checkpoint.
- [x] Implement and exercise preflight, checkpoint and recovery helpers with isolated local remotes (7 tests).
- [x] Verify hosted PR and CI behavior with the authorized integration. PR #98 passed the hosted offline suite.
- [ ] Verify authenticated GitHub CLI behavior when a CLI session is available.
- [ ] Complete any remaining acceptance scenarios and request human review; keep PR draft until then.
- [x] Inventory the 33 baseline Markdown files and add the [vault index](../INDEX.md) and [documentation guide](../DOCUMENTATION_GUIDE.md) on `docs/obsidian-knowledge-base` from `77dc8b7`.
- [x] Correct onboarding, architecture, persistence, API and status discrepancies. Preserve historical reports and accepted decisions. See [the discrepancy audit](DOCUMENTATION_INVENTORY.md) and [PR #96](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/96).
- [ ] Open the vault in Obsidian and preview the index and all six architecture Mermaid diagrams in GitHub and Obsidian. Record rendering and cross-vault navigation evidence.
- [x] Verify canonical imports and the SQLite workflow on Python 3.11. Package metadata follow-up is in [OPS-001](#ops-001--deployment-and-operational-verification).
- [x] Document verified entry points, SQL boundaries and the canonical environmental processing path on `docs/verified-runtime-architecture` from `bbf988e`.
- [x] Trace public reads, review, field reports and agent recovery. Verify six Mermaid diagrams at the grammar level, compare 26 route/method pairs with canonical OpenAPI, and verify all 25 event-state pairs and four aliases. See [PR #97](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/97).
- [x] Consolidate the root startup, scope and safety rules, align branch and ownership steps, and publish the [engineering standards](ENGINEERING_STANDARDS.md). The 11 focused contract and Git helper tests passed.
- [x] Verify the development commands and compatibility evidence, fix the existing CI expression scope and document a staged quality baseline. See [PR #98](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/98).
- [x] Reconcile all authoritative task records against merged PRs and verification evidence. Add direct Pending Work navigation.
- [x] Verify the offline documentation baseline and failure cases. Integrate the check into the existing workflow and record its scope in [testing](../testing.md#documentation-checks) and the handoff.
