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
- [x] Exercise no-API, empty, and outage behavior plus the published map/cards/exposure boundary in Streamlit AppTest (PR #85).
- [ ] Validate rendered pages and accessibility in a browser; Chromium startup was blocked in the audit environment.

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
Priority: P0; Status: COMPLETE; files: `backend_service.py`, `streamlit_app.py`, `pages/`, `tests/test_p0003_exposure_boundary.py`.
Evidence: without `API_BASE_URL`, `get_events` reads `data/flood_events.csv`; `get_exposure` reads
local exposure regardless of API; the public page uses these independently of API eligibility.
Trigger: no configured API, or API active while local exposures remain populated. Impact: potentially
misleading mixed or synthetic information. Acceptance: verify actual local data provenance and every
consumer; require explicit, visibly watermarked demo mode or fail closed, and never display unrelated
exposure as operational; test map/card/exposure consistency and unavailable states. Do not assume
local CSV records are live. Dependencies: mode/UI product contract and P0-001.
- [x] Identify no-API CSV and local exposure paths by code inspection.
- [x] Reproduce operational/demo UI behavior and trace all callers.
- [x] Implement safely labelled demo or unavailable behavior: `DEMO_WATERMARK` constant, `is_demo_mode`
  property, `exposure_data_source` tag; `get_exposure()` returns empty in API mode and operational
  no-API mode; public dashboard, analyst review, partner mode, and export center display watermark
  banners; partner advisory text prepends demo watermark; analyst review action buttons fail safe;
  settings UI reflects read-only configuration; 16 focused tests and 228 full offline tests pass.
- [x] Offline automated test coverage for demo watermark, exposure suppression, and API column parity.

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
- [ ] Propose the durable event identity, review version and review/audit transaction contract.
- [ ] Define migration, restart, duplicate submission, concurrent transition and rollback acceptance tests.
- [ ] Implement and test the contract after review.

## P1-003 — Reviewed public products
Status: PARTIAL; dependencies: P1-002, DATA-001. PR #75 blocks raw views pending reviewed products.
- [x] Identify intentionally unavailable raw-run/advisory endpoints.
- [ ] Define reviewed-product provenance, authorization and public API/UI contracts.
- [ ] Implement and test availability, freshness and safe degradation.

## UI-001 — Public and analyst dashboard end-to-end audit
Status: PARTIAL; read-only analyst slice in [PR #86](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/86); baseline: `5f700f6`; dependencies: P0-001, P0-002; files: `pages/`, `dashboard/`, `backend_service.py`.
Audit maps/cards, empty/outage states, demo watermark, districts, localization, mobile, field reports,
exports and status actions. Acceptance: evidence-backed inventory and integration tests; no synthetic
or unreviewed output represented as operational. Prototype UI is not an authoritative warning service.
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
- [x] Document comprehensive UI/UX improvement plan and persona acceptance matrix (`docs/product/UI_UX_IMPROVEMENT_PLAN.md`, `docs/product/UI_UX_ACCEPTANCE_MATRIX.md`).
- [ ] Implement audience-centered homepage navigation hub and sidebar organization (`streamlit_app.py`).
- [ ] Harmonize demo watermarks, limitations, and official info links across specialist modules.

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
- [x] Verify PK-006 idempotent receipt ownership and sanitized conflict responses with synthetic canonical API records.

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
- [x] Record baseline behavior by feature and runtime in the [functionality matrix](FUNCTIONALITY_GAP_AUDIT.md) (PR #85).
- [x] Run focused tests (8 passed) and complete offline suite (204 passed, 475 warnings).
- [ ] Verify Docker, PostgreSQL, live providers and UI when available.
- [x] Reconcile merged PR #88 and re-run the clean offline baseline at `cb70717` (278 passed).
- [x] Record the incremental [end-user acceptance matrix](../product/FARMER_LIVESTOCK_QA_MATRIX.md#independent-qa-follow-up) against current main without re-auditing closed workstreams.
- [x] Record draft PR #89, 293-test offline acceptance and handoff for this independent QA continuation.
- [ ] Complete hosted and browser verification and outstanding QA workstreams.


## Pakistan community features — research-backed backlog

Specifications and provisional value/feasibility matrix: [Pakistan roadmap](../product/PAKISTAN_FEATURE_ROADMAP.md). Reproducible farmer, livestock and community findings are in the [QA matrix](../product/FARMER_LIVESTOCK_QA_MATRIX.md). Prior P0/P1 safeguards remain prerequisites; no task is operationally complete solely from a prototype.

### PK-001 — My Area
Priority: P1; Status: PARTIAL. The corridor selector slice is in [draft PR #88](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/88). The reference catalogue merged in
[PR #87](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/87). Current baseline `6f35e9e`.
Workstream branch `feat/pk-001-my-area-corridor`.
Dependencies for validated local coverage: UI-001, P0-003, P1-003, and validated administrative boundaries.
Reference catalogue dependencies: the existing canonical pilot corridor settings.
Files: `pages/1_🌍_Public_Dashboard.py`, `src/pakistan_flood_monitor/config.py`,
`backend_service.py`, `src/pakistan_flood_monitor/api/main.py`, and public dashboard/publication tests.

**Problem and scope.** The merged reference list survives an empty response. The interactive
district filter still depends on event rows, and the canonical public collection omits the
recorded corridor association. Use configured pilot corridor IDs as the selectable resolution.
Expose a nullable corridor ID on eligible published records when the stored value matches the
canonical catalogue. Use exact ID matching in a single published snapshot. The separate
district filter remains labelled demo-only.

**Acceptance and tests.** The corridor selector and Official Information link appear before any
feed stop. Verified states include empty, error, timeout, unconfigured, unknown association,
selected corridor with no match, and a published match. Unassociated events stay available in
the all-events view. A result count measures records only. Keep missing measurements unavailable,
show publication and detection dates separately when supplied, and avoid area/safety inference.
Use the map container's width and render text without needing map tiles. Verify keyboard and
mobile behavior with a real browser where available.

- [x] Trace canonical names, public event fields and published-only data path (FL-01/01B/06).
- [x] Reproduce missing area context on empty response, 503 and timeout using AppTest.
- [x] Verify the [planning checkpoint](https://github.com/afaq-ahmad/pakistan-flood-monitor/commit/170a2608d8ac3effec415da1d432fd03816ad288) and open draft PR #87 before editing the public dashboard.
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

**Blockers.** Authoritative local coverage, aliases, and scientific freshness are pending. The
reference and selector slices passed offline. Chromium startup was blocked and hosted workflows on main and the selector checkpoint returned zero jobs. Browser and mobile acceptance remain open.

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
- [ ] Revalidate provincial source links and record check date, owner and timeout handling (FL-04).


### PK-003 — Urdu and low-bandwidth access
Priority: P1; Status: PARTIAL; Dependencies: UI-001, P0-003. Data: Human-reviewed translations and accessibility research.
- [ ] Audit translations, mobile layout, text-only and print views.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

- [ ] Audit critical English/Urdu text and translation fallback.
- [ ] Design mobile, text-only, printable low-bandwidth views.
- [ ] Test accessibility and record regional-language needs.
- [ ] Test 360 px reflow, reviewed Urdu/RTL, keyboard order and essentials without tiles (FL-06/12).


### PK-004 — Community sharing cards
Priority: P1; Status: NOT_STARTED; Dependencies: P1-003, PK-003. Data: Authorized reviewed products and issue timestamps.
- [ ] Design source-attributed cards; test expiry and publication authorization.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

- [ ] Define source/area/issue-time/freshness schema.
- [ ] Restrict sharing to eligible reviewed content.
- [ ] Implement and test text and print formats with reviewed translations.
- [ ] Test issuer, issue/expiry, scope, confidence and demo label through copy/export; validate real provider acceptance (FL-07/11).


### PK-005 — Verified relief directory
Priority: P1/P2; Status: BLOCKED; Dependencies: P1-002, SEC-001. Data: Verified official contacts and maintained service status.
- [ ] Design verification, expiry and moderation; never infer active shelter availability.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

- [ ] Verify official directory sources and scope.
- [ ] Model verification time, expiry and service status.
- [ ] Add moderated corrections and privacy tests.
- [ ] Design verified animal shelter, water, fodder and veterinary resource records with expiry and provider ownership (FL-04).


### PK-006 — Community reports

- [x] FL-05 follow-up verified in draft PR #92 (29 focused and 336 full-suite tests passed), originally claimed on `fix/pk-006-report-receipts` from `90062a0`. Replace the unbacked demo receipt with a private practice preview. Check empty fixtures, missing coverage, repeated previews, mode separation and an unchanged moderation queue. Real intake retains P1-002 and SEC-001 dependencies.
Priority: P2; Status: PARTIAL. The FL-05 boundary and failure-feedback slice passed offline in
[draft PR #89](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/89), based on `cb70717`. Dependencies for operational intake: P1-002, SEC-001,
a durable report store and privacy/retention policy. This containment slice uses the existing
demo boundary and canonical role checks.
- [ ] Audit existing field-report flow; distinguish reports from verified observations.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

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
Priority: P2; Status: BLOCKED; Dependencies: DATA-001, GIS-001, PK-006. Data: Validated flood extents and licensed agricultural layers.
- [ ] Separate estimated exposure, reported losses and verified damage.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

- [x] Define agricultural report categories with metadata, privacy flags and consent requirements. See `src/pakistan_flood_monitor/models/report_categories.py` and 12 offline tests.
- [x] Document the agricultural exposure specification and 9 prerequisites in `docs/product/AGRICULTURAL_EXPOSURE_SPECIFICATION.md`. All prerequisites remain BLOCKED.
- [ ] Inventory agricultural datasets and exposure methods.
- [ ] Validate spatial overlays and separate reported from verified damage.
- [ ] Test units, temporal alignment and unsupported compensation claims.
- [ ] Specify crop-stage, storage, irrigation and livestock data separately; validate methods, licensing and unknown-versus-zero semantics (FL-03/04).
- [ ] Require licensed field boundaries, informed consent and access control, validated flood extents, CRS/projection and spatial/temporal alignment. Compare baseline and new inundation, quantify crop and model uncertainty, and keep estimated exposure separate from verified loss. Property-level exposure remains BLOCKED.


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
- [ ] Review Partner advisory payload, remove unsupported authorizations and verify plaintext source/expiry and redaction (FL-07/13).


### PK-010 — Historical and preparedness explorer
Priority: P3; Status: PARTIAL; Dependencies: DATA-001, GIS-001. Data: Dated licensed historical sources and approved preparedness guidance.
- [ ] Distinguish history from prediction; validate maps and legends.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

- [ ] Audit historical sources, dates and geometry.
- [ ] Distinguish history from forecasts and unknown coverage.
- [ ] Verify preparedness guidance and legend tests.
- [ ] Check provenance and permissions of bundled historical flood outlines; distinguish approximate outlines from verified training evidence (FL-03).
- [x] Add Farmer Preparedness page (`pages/17_🌾_Farmer_Preparedness.py`) with sourced English guidance for crops, grain/seed, equipment, chemicals, records and recovery. Text-first, no maps or live feed dependency. 8 offline tests pass.
- [x] Add Livestock Preparedness page (`pages/18_🐄_Livestock_Preparedness.py`) with sourced English guidance for animal water/fodder, identification, welfare, veterinary links and recovery. Service availability treated as unknown. 9 offline tests pass.
- [ ] Verify and attribute additional government or humanitarian guidance for remaining agricultural topics.
- [ ] Verify and attribute guidance for additional species-specific livestock needs. Treat service availability as unknown unless the provider verifies it (PK-005).
- [ ] Review Urdu translations with a qualified human reviewer before publication. Keep preparedness content separate from model outputs, evacuation routes or operational notices.


### PK-011 — Validated forecasting
Priority: P3; Status: BLOCKED; Dependencies: DATA-001. Data: Independent historical rainfall/gauge datasets and out-of-sample evaluation.
- [ ] Keep operational forecast disabled until independently validated.
- [ ] Validate safety, attribution, accessibility, required data and acceptance tests.

PK-002 initial slice: static, attributed FFD and NDMA source links only; no live feed or claims of active warnings. Link review date 2026-11-18. Browser/mobile and ongoing link verification remain pending.

- [x] Treat FL-08 as P0 presentation risk. Gated prototype forecast (`pages/13`) and dam analysis (`pages/15`) in operational mode. Removed evacuation wording and uncalibrated alarmist alerts. 6 offline tests pass in `tests/test_safety_gates_and_community_reporting.py`.
- [ ] Audit model maturity and candidate datasets.
- [ ] Compare defensible baselines with out-of-sample validation.
- [ ] Test probabilistic calibration and preserve operational disablement.


## ENG-001 — Resumable agent GitHub workflow
Priority: engineering reliability; Status: PARTIAL; owner: PR #83 integration agent.
Base: `21450751d7b24e389cee8cbf9336d04bc8223e7c`; branch: `engineering/resumable-agent-workflow`.
Acceptance: startup instructions, safe checkpoint/recovery helpers, isolated failure-path tests,
one draft PR, verified remote checkpoints, and factual handoff. Existing flood backlog is unchanged.
- [x] Open a draft PR after initial workflow documentation checkpoint.
- [x] Implement and exercise preflight, checkpoint and recovery helpers with isolated local remotes (7 tests).
- [ ] Verify real GitHub CLI authentication, hosted PR/CI behavior, and full suite on current main.
- [ ] Complete any remaining acceptance scenarios and request human review; keep PR draft until then.
