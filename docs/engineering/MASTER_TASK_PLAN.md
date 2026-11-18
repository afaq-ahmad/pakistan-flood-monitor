# Master engineering task plan

Baseline: `58e735b` on `main`, 2026-11-17. This is the authoritative task checklist;
verify against code and history before claiming work. Status values: NOT_STARTED, IN_PROGRESS,
PARTIAL, BLOCKED, COMPLETE. A checkmark means that specific subtask has evidence; COMPLETE requires
all acceptance criteria and verification. Priorities reflect potential impact, not certified risk.

Objective: dependable, usable flood information with traceable science and human review. Scope:
canonical API, public/analyst interfaces, data, workflow, security, deployment and tests. Non-goals:
unauthorized warnings, fabricated observations, or claiming readiness without independent evidence.
ADR-001 and AGENTS.md govern runtime, simulation, publication, provenance and metric GIS.

## P0-001 — API-configured dashboard must fail closed on missing events
Priority: P0; Status: PARTIAL; owner: consolidated agent; starting commit: `58e735b`.
Dependencies: canonical publication boundary (PR #75). Files: `backend_service.py`, dashboard tests.
Evidence: `get_events` falls through to `data/flood_events.csv` on an empty 200 or API failure.
Impact: public dashboard can present local records after an outage or an empty published feed.
Acceptance: API-configured empty, invalid, and failed responses return no CSV events; valid data
continues mapping; failure has observable indication; deterministic offline tests pass.
- [x] Trace API response and local fallback path.
- [x] Reproduce empty and outage cases (three tests failed before the implementation commit in this PR).
- [x] Prevent API-configured fallback and verify valid response (the implementation commit in this PR, 8 focused tests).
- [x] Run offline regression and full suite (204 passed, 475 warnings).
- [ ] Validate Streamlit UI in a browser and assess local exposure/no-API paths (P0-003).

Evidence: `PYTHONPATH=. .../python -m pytest tests/test_dashboard_api_fail_closed.py -q` — 8 passed;
full offline suite — 204 passed. No browser screenshots; UI was not run in this environment.

## P0-002 — Prevent local review fallback after API failure
Priority: P0; Status: COMPLETE; dependency: P0-001; files: `backend_service.py`, `tests/test_dashboard_api_fail_closed.py`.
Evidence: `update_event_status` falls back to CSV after unsuccessful canonical API request.
Acceptance: API-configured failures cannot alter local event or audit files or report success.
- [x] Reproduce non-200 and network failure.
- [x] Fail closed; verify successful request, 403 and connection failure.
- [x] Evidence: the implementation commit in this PR; 8 focused tests and 204 full offline tests passed.

## P0-003 — Local-only dashboard data and exposure boundary
Priority: P0; Status: NOT_STARTED; files: `backend_service.py`, `streamlit_app.py`, `pages/`.
Evidence: without `API_BASE_URL`, `get_events` reads `data/flood_events.csv`; `get_exposure` reads
local exposure regardless of API; the public page uses these independently of API eligibility.
Trigger: no configured API, or API active while local exposures remain populated. Impact: potentially
misleading mixed or synthetic information. Acceptance: verify actual local data provenance and every
consumer; require explicit, visibly watermarked demo mode or fail closed, and never display unrelated
exposure as operational; test map/card/exposure consistency and unavailable states. Do not assume
local CSV records are live. Dependencies: mode/UI product contract and P0-001.
- [x] Identify no-API CSV and local exposure paths by code inspection.
- [ ] Reproduce operational/demo UI behavior and trace all callers.
- [ ] Implement safely labelled demo or unavailable behavior with browser-level coverage.

## P1-001 — Fenced worker recovery
Status: BLOCKED; files: `workflow/engine.py`, `workflow/repository.py`, migrations.
PR #76 added atomic claims; queued/running work can remain stuck after a crash. Recovery needs a
fenced ownership/lease contract, processor side-effect guarantees, migration and process-crash tests;
reclaiming a live worker is unsafe. Next: design and review ownership/fencing contract.
- [x] Identify existing atomic claims and crash limitation.
- [ ] Specify owner, fencing and idempotent side effects; approve design.
- [ ] Implement migration, recovery, stale-result rejection and crash/concurrency tests.

## P1-002 — Durable review, publication and audit state
Status: BLOCKED; files: `src/pakistan_flood_monitor/api/main.py`, models and migrations.
Review and audit state remains partly in memory; restart may lose it. Acceptance: transactional,
restart-safe review, authorization, audit and concurrency tests with migration/rollback. Requires
reviewed-product and persistence contract before implementation.
- [x] Identify in-memory state and restart limitation.
- [ ] Design approved durable contract and implement/test.

## P1-003 — Reviewed public products
Status: PARTIAL; dependencies: P1-002, DATA-001. PR #75 blocks raw views pending reviewed products.
- [x] Identify intentionally unavailable raw-run/advisory endpoints.
- [ ] Define reviewed-product provenance, authorization and public API/UI contracts.
- [ ] Implement and test availability, freshness and safe degradation.

## UI-001 — Public and analyst dashboard end-to-end audit
Status: NOT_STARTED; dependencies: P0-001, P0-002; files: `pages/`, `dashboard/`, `backend_service.py`.
Audit maps/cards, empty/outage states, demo watermark, districts, localization, mobile, field reports,
exports and status actions. Acceptance: evidence-backed inventory and integration tests; no synthetic
or unreviewed output represented as operational. Prototype UI is not an authoritative warning service.
- [ ] Trace every public and analyst data path, including standalone dashboard.
- [ ] Verify mode, freshness, authorization, privacy and error handling with UI tests.

## DATA-001 — Real environmental processing and validation
Status: BLOCKED; files: `src/pakistan_flood_monitor/data`, `pipeline`, services.
Operational pipeline is intentionally unavailable without required real observations. Sentinel, SAR,
optical, hydromet, DEM/HAND, forecasts, exposure, dam and backtesting require independent source,
provenance and scientific validation. No invented values or warning claims. Dependencies: source access,
accepted scientific decisions and validated datasets.
- [ ] Inventory each source, real/prototype/simulated state, units, freshness and validation.
- [ ] Obtain authoritative sources and independent validation; implement in separately reviewed steps.

## GIS-001 — Spatial and raster audit
Status: NOT_STARTED; dependencies: DATA-001; files: `geo/measurements.py`, raster processors.
Acceptance: evidence for CRS/units/nodata/alignment and golden geometries; document unresolved risks.
- [ ] Audit geodesic, reprojection, categorical masks and alignment.

## API-001 — Canonical/legacy and migrations
Status: PARTIAL; files: `src/pakistan_flood_monitor`, `src/app`, `alembic`.
ADR-001 selects canonical runtime; two migration histories are unreconciled. PR #79 added endpoints.
- [x] Record canonical runtime and migration split.
- [ ] Audit interfaces, consumers and safe migration plan with upgrade/rollback tests.

## SEC-001 — Security and privacy audit
Status: PARTIAL; dependencies: P0-001, P0-002; files: API, UI, exports and settings.
PR #74 rejected unsigned role tokens; PR #75 restricted publication. Confirm XSS, path, SSRF,
CSV injection, rate limits and sensitive data exposure with tests; do not assume prior fixes cover all.
- [x] Record prior authentication/publication changes.
- [ ] Verify remaining trust boundaries and document reproducible findings.

## OPS-001 — Deployment and operational verification
Status: BLOCKED; files: `Dockerfile`, `docker-compose.yml`, CI, migrations.
Offline CI exists; Docker, PostgreSQL, live provider and fresh deployment verification not established.
- [x] Identify offline CI and SQLite migration checks.
- [ ] Validate image, PostgreSQL migration and deployment with suitable infrastructure.

## QA-001 — Full independent audit and handoff
Status: IN_PROGRESS; owner: consolidated agent; baseline `58e735b`. Audit all workstreams above and
reconcile PRs #73–80 before claiming more work. Acceptance: exact commands and results; unresolved
work remains open and a reproducible session log exists. Do not interpret test pass as scientific validity.
- [x] Read agent contract, ADR-001, ledger, recent commits and open PRs.
- [ ] Complete deeper end-to-end audit and add only evidence-backed task IDs.
- [x] Run focused tests (8 passed) and complete offline suite (204 passed, 475 warnings).
- [ ] Verify Docker, PostgreSQL, live providers and UI when available.
- [ ] Record final commit, PR and next exact task in session log.


## Pakistan community features — research-backed backlog

Specifications and provisional value/feasibility matrix: [Pakistan roadmap](../product/PAKISTAN_FEATURE_ROADMAP.md). Prior P0/P1 safeguards remain prerequisites; no task is operationally complete solely from a prototype.

### PK-001 — My Area
Priority: P1; Status: PARTIAL; Dependencies: UI-001, P0-003, P1-003. Data: Validated administrative boundaries and area/corridor mapping.
- [ ] Audit district data and show no-data/unknown coverage; never infer property risk.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

- [ ] Audit district and corridor data and supported coverage.
- [ ] Validate district/tehsil and corridor associations.
- [ ] Show observations, official notices and history separately with timestamps.
- [ ] Test empty, unknown and demo states across map and cards.

### PK-002 — Official source hub
Priority: P1; Status: PARTIAL; Dependencies: P0-003. Data: Curated FFD and NDMA links; source permissions for any ingestion.
- [ ] Static attributed directory implemented; verify ongoing link maintenance and accessibility.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

- [x] Check FFD and NDMA public pages and implement static attributed links (2026-11-18).
- [x] Verify static HTTPS registry offline (9 focused tests; 205 full-suite tests passed).
- [ ] Inventory other official sources and permitted machine-readable access.
- [ ] Create a versioned registry with attribution and link maintenance.
- [ ] Show issue/acquisition times only when supported by actual source data.
- [ ] Test source failures, expiry, permissions and accessibility.

### PK-003 — Urdu and low-bandwidth access
Priority: P1; Status: PARTIAL; Dependencies: UI-001, P0-003. Data: Human-reviewed translations and accessibility research.
- [ ] Audit translations, mobile layout, text-only and print views.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

- [ ] Audit critical English/Urdu text and translation fallback.
- [ ] Design mobile, text-only, printable low-bandwidth views.
- [ ] Test accessibility and record regional-language needs.

### PK-004 — Community sharing cards
Priority: P1; Status: NOT_STARTED; Dependencies: P1-003, PK-003. Data: Authorized reviewed products and issue timestamps.
- [ ] Design source-attributed cards; test expiry and publication authorization.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

- [ ] Define source/area/issue-time/freshness schema.
- [ ] Restrict sharing to eligible reviewed content.
- [ ] Implement and test text and print formats with reviewed translations.

### PK-005 — Verified relief directory
Priority: P1/P2; Status: BLOCKED; Dependencies: P1-002, SEC-001. Data: Verified official contacts and maintained service status.
- [ ] Design verification, expiry and moderation; never infer active shelter availability.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

- [ ] Verify official directory sources and scope.
- [ ] Model verification time, expiry and service status.
- [ ] Add moderated corrections and privacy tests.

### PK-006 — Community reports
Priority: P2; Status: PARTIAL; Dependencies: P1-002, SEC-001. Data: Moderated field reports and privacy/retention policy.
- [ ] Audit existing field-report flow; distinguish reports from verified observations.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

- [ ] Audit field-report authorization and moderation.
- [ ] Design categories, evidence, deduplication and retention.
- [ ] Test sensitive-location and publication boundaries.

### PK-007 — Farmers and livestock
Priority: P2; Status: BLOCKED; Dependencies: DATA-001, GIS-001, PK-006. Data: Validated flood extents and licensed agricultural layers.
- [ ] Separate estimated exposure, reported losses and verified damage.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

- [ ] Inventory agricultural datasets and exposure methods.
- [ ] Validate spatial overlays and separate reported from verified damage.
- [ ] Test units, temporal alignment and unsupported compensation claims.

### PK-008 — River observation explorer
Priority: P2; Status: BLOCKED; Dependencies: DATA-001. Data: Licensed gauge data, units and timestamps.
- [ ] Validate official measurements, freshness and stage definitions.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

- [ ] Inventory gauge sources and permissions.
- [ ] Validate units, timestamps and stage definitions.
- [ ] Implement missing/stale states and source lineage tests.

### PK-009 — Partner and NGO information
Priority: P2; Status: PARTIAL; Dependencies: P1-002, SEC-001. Data: Authorization, audited exports and reviewed summaries.
- [ ] Audit partner mode; constrain access and sensitive data.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

- [ ] Audit partner-mode authorization and existing exports.
- [ ] Design reviewed summaries and sensitive-data minimization.
- [ ] Add authorization and audit tests.

### PK-010 — Historical and preparedness explorer
Priority: P3; Status: PARTIAL; Dependencies: DATA-001, GIS-001. Data: Dated licensed historical sources and approved preparedness guidance.
- [ ] Distinguish history from prediction; validate maps and legends.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

- [ ] Audit historical sources, dates and geometry.
- [ ] Distinguish history from forecasts and unknown coverage.
- [ ] Verify preparedness guidance and legend tests.

### PK-011 — Validated forecasting
Priority: P3; Status: BLOCKED; Dependencies: DATA-001. Data: Independent historical rainfall/gauge datasets and out-of-sample evaluation.
- [ ] Keep operational forecast disabled until independently validated.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

PK-002 initial slice: static, attributed FFD and NDMA source links only; no live feed or claims of active warnings. Link review date 2026-11-18. Browser/mobile and ongoing link verification remain pending.

- [ ] Audit model maturity and candidate datasets.
- [ ] Compare defensible baselines with out-of-sample validation.
- [ ] Test probabilistic calibration and preserve operational disablement.
