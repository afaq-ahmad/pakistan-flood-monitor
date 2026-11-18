# Farmer and livestock QA matrix

Baseline `d24fa22` on 18 November 2026. **CONFIRMED** means a behavior reproduced or directly
traceable through code. **SUSPECTED** means a plausible issue with an unresolved dependency.
**INTENTIONAL** means a verified restriction. **NOT YET VERIFIED** marks unexecuted scenarios.
Severity reflects potential user harm. Implementation status and dependencies remain in the
[master plan](../engineering/MASTER_TASK_PLAN.md). Persona letters refer to the [user journeys](FARMER_LIVESTOCK_USER_JOURNEYS.md).

| ID | Persona | Workflow | Preconditions | Steps | Expected | Observed | Evidence | Severity | Test coverage | Finding status | Task |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FL-01 | A, D | Locate an area with no published event | Canonical public events returns 200 and an empty list | Open Public Dashboard, find Chenab reference, then look for a village or official source | Reference labels and official sources available; explicit lack of village coverage and no safety inference | Empty response stops the page before My Area. The official link is visible. The configured corridor catalogue still has six entries. | AppTest with an empty 200; canonical `GET /public/corridors`; public page after `st.stop()` | P1 | Four AppTest feed-state regressions plus empty catalogue; baseline failed, fixed branch passed | CONFIRMED | PK-001 |
| FL-01B | A, C | Find district, tehsil or mouza | Published API records or unsupported area | Inspect canonical response and UI filter choices | Only validated area IDs match; unknown locality remains unknown | `list_public_events` omits district, tehsil and corridor fields; UI builds districts solely from the snapshot | Code trace in `api/main.py` and `backend_service.py` | P1 | Existing Demo district fixture; canonical mapping negative cases pending | CONFIRMED | PK-001 |
| FL-02 | A, D, F | Understand event state and freshness | Empty 200, API 503, timeout, or draft fixture | Open public page and verify feed status, source access and publication boundary | Empty means no published events; failed means unavailable; no draft escapes | Public view distinguishes empty from outage, and marks live freshness unavailable | AppTest 200, 503 and `httpx.ReadTimeout`; publication gate tests | P1 | Existing Streamlit/publication tests | INTENTIONAL | P0-001, P1-003 |
| FL-03 | A, F | Check crops, stored grain and history | Configured API; open Historical Flood Map | Inspect impact panel and compare dated history against one farm | Unknown exposure rather than zero; historical map clearly identified with evidence limits | Operational dashboard suppresses local exposure. Historical map now carries contextual outline disclaimer and demo watermark; ground-truth claims removed. | AppTest history; `get_exposure`, public page and JSON source trace; `test_safety_gates_and_community_reporting.py` | P1 | Prior exposure tests; disclaimer regression passed | RESOLVED | PK-007, PK-010 |
| FL-04 | B, C | Find animal, fodder, water or veterinary assistance | Official Information page; no partner confirmations | Open links and look for a verified in-area listing with a check time | Generic source access works; any service availability needs provider and verification time | Static FFD/NDMA links render; no species-specific guidance or verified service roster. Punjab PDMA direct fetch timed out. | AppTest page 16 and `official_sources.py`; historical sources in journeys | P1 | Official source tests; provider and field validation pending | CONFIRMED | PK-002, PK-005, PK-007 |
| FL-05 | C, B, F | Submit a loss or access report and receive acknowledgement | Public visitor, then API-mode Streamlit | Look for intake, submit unauthenticated request, inspect moderation boundary | Private acknowledgement and moderation with consent; no automatic verified observation | No public submit form; internal route returns 401 without credentials. Moderation page still reads local records in API mode and approve feedback ignores the return value. Canonical records live in process memory. | AppTest page 3; TestClient; `moderate_report` and `field_reports` trace | P1 | Anonymous 401 reproduced; isolated moderation failure, persistence and redaction tests pending | CONFIRMED | PK-006, SEC-001, P1-002 |
| FL-06 | D | Slow or intermittent connection | Application is already loaded; provider sockets disabled | Open Official Information, return to public page, simulate feed timeout | Essential links and plain text load independently of maps; offline cold load handled honestly | Official Information rendered with sockets disabled. Feed timeout returns unavailable and stops before district selector. Cold load and external links need connectivity. | AppTest with pytest-socket and mocked timeout | P1 | Offline application logic exercised; browser bandwidth/accessibility pending | CONFIRMED | PK-001, PK-003 |
| FL-07 | E, F | Receive or forward an advisory | Explicit local demo with sample event | Use Partner Mode and inspect text sent to download | Area, issuer, issue/expiry and limits survive forwarding; demo marked | Download payload contains demo marker and updated line. It lacks explicit expiry and verified issuer. | Captured `st.download_button` payload; canonical reviewed-product guard in `api/main.py` | P1 | Baseline AppTest payload; copy/print and authorization tests pending | CONFIRMED | PK-004, PK-009, P1-003 |
| FL-08 | A, B | Interpret model or dam result | Prototype code available, missing dam imagery; forecast dependencies optional | Call dam proxy with absent imagery and deterministic noise; inspect forecast alert path with nonvalidated weights | Missing input unavailable; prototypes visibly simulated; official evacuation terminology reserved | Pages 13 & 15 now fail closed in operational mode, display DEMO_WATERMARK in demo mode, and evacuation language is replaced with simulated research notices. | AppTest operational fail-closed and demo alert regressions in `tests/test_safety_gates_and_community_reporting.py` | P0 | 6 focused tests pass; evacuation directives removed | RESOLVED | PK-011, DATA-001 |
| FL-09 | A, F | Check rainfall and satellite evidence during provider failure | DNS/network blocked | Open NASA Hydromet with auto-load and inspect statuses; trace STAC and water detection | Failures summarized as failures; maps and scene metadata distinguished from impact | NASA Hydromet now tracks failed corridors and reports errors instead of unconditional success. | AppTest error fixture test in `tests/test_safety_gates_and_community_reporting.py` | P1 | Focused failure-count test passed | RESOLVED | DATA-001, UI-001 |
| FL-10 | F | Review a candidate across restarts | Role credential; process-local API | Discover draft, verify public isolation, clear process/restart fixture | Queue is private; a future durable review preserves event identity, concurrent updates and audit | Existing role-protected queue intentionally process-local. No live review controls on the Streamlit page. | PR #86 and canonical queue tests | P1 | Existing offline role and pipeline tests; restart persistence pending | INTENTIONAL | UI-001, P1-002 |
| FL-11 | E | Receive notification and verify delivery | Stub provider configured with test fixture | Inspect returned receipt and provider calls | Only confirmed external acceptance can imply delivery; expiry and consent tracked | Stubs construct receipt IDs without network transport. Prototype receipts do not confirm delivery. | `services/notifications.py` send methods | P1 | Provider stub tests; sandbox-provider attestation and consent pending | CONFIRMED | PK-004, SEC-001 |
| FL-12 | D, E | Read in Urdu, mobile, or without tiles | Low-end Android, 360 px, throttled data, or screen reader | Navigate official links, public dashboard and saved text | Readable order, no forced horizontal scroll, reviewed Urdu/RTL, useful text without tiles | Dashboard map requests fixed width; actual reflow, browser accessibility and comprehension are unknown | Source inspection; headless Chromium unavailable in prior run | P2 | AppTest structure only; browser and field tests pending | NOT YET VERIFIED | PK-003 |
| FL-13 | C, F | Export agricultural evidence | Operational API or explicit local demo | Open Export Centre, obtain demo file if enabled | Operational export only from reviewed material; demo independently marked | API export intentionally unavailable. Local GeoJSON and manifest are labelled demo. | PR #85 export tests and page 5 | P1 | Existing tests cover labels and download payload; operational export pending | INTENTIONAL | P1-003, PK-009 |

## Reproduction notes

Run offline with `APP_MODE=test`. Use `AppTest.from_file("streamlit_app.py").switch_page(...).run()`
and set `backend_service.API_BASE_URL` to a fixture URL for API-mode cases. Stub `httpx.get`
to return `httpx.Response(200, json={"events": []})`, a 503, or a `ReadTimeout`.
For the dam test, return no thumbnail, set random noise to zero and stub the history writer.
For Field Reports, select operational mode with an API configured and inspect the local report
metrics without submitting anything. Use `TestClient` for the unauthorized internal report route.
No real resident information, provider credentials, or delivery calls are needed. No emergency
routing, herd advice, treatment, or claims decisions are part of the software tests.

## Implemented slice and validation

The [documentation-only checkpoint](https://github.com/afaq-ahmad/pakistan-flood-monitor/commit/170a2608d8ac3effec415da1d432fd03816ad288)
preceded UI edits in draft PR #87. PK-001's reference list addressed the catalogue portion of FL-01
and FL-06. It is independent of the published event feed and avoids map rendering on the tested
empty or unavailable paths. FL-01B's district, tehsil and mouza mapping remains open.

- `APP_MODE=test .venv/bin/python -m pytest --disable-socket --allow-unix-socket tests/test_streamlit_public_pages.py -k reference -q --tb=short`
  failed five times on the baseline, as expected. The five cases passed in the 30-test focused suite after the edit.
- `APP_MODE=test .venv/bin/python -m pytest --disable-socket --allow-unix-socket tests/ -q --tb=short`
  passed 274 tests with 475 warnings. Compilation, tracked-data isolation, link checks and whitespace checks passed.
- Chromium could not create a local socket. Mobile rendering, browser keyboard checks, screenshots and a
  fully offline first load remain unverified. Hosted Actions on main and the implementation checkpoint
  failed with zero jobs. No scientific source, authorization or output contract changed.

## My Area selector follow-up

Baseline `6f35e9e` preserved the text references from PR #87. Draft PR #88 adds selection at
configured corridor resolution. FL-01 and FL-06 now have offline selector and official-navigation
coverage for empty 200, 503, timeout and unconfigured feeds. The named selection reports no linked
events when there is no match. FL-01B remains open for administrative mapping.

- The new API/UI subset initially failed four cases. Three showed the missing public corridor field
  and the fourth showed that nullable timestamps could suppress the entire snapshot.
- The real FastAPI-to-AppTest integration now preserves unassigned published records in the all-events
  view, shows unavailable time/exposure, and filters a selected corridor without surfacing drafts.
  The map is opt-in and requests container width. Browser/mobile and keyboard checks remain open.
- The related dashboard, publication and official source suites passed 34 tests. The full offline
  suite passed 278 tests with 475 warnings. SQLite downgrade/re-upgrade, compilation, tracked-data
  isolation and whitespace checks passed.

## Independent QA follow-up

Baseline `cb70717` includes merged PR #88. The complete network-disabled baseline passed
278 tests with 475 warnings. The matrix below reuses the existing FL IDs. **PASS** refers to
the stated fixture contract. **FAIL** means a reproduced or directly confirmed defect.
**BLOCKED** identifies an unavailable prerequisite or feature. **UNVERIFIED** marks a missing
test environment or evidence gap.

| Journey | Result at baseline | Current evidence and remaining boundary |
|---|---|---|
| Select an area with no events (FL-01/06) | PASS | AppTest preserves configured corridor and official-source navigation on empty 200, timeout, 503 and unconfigured feed. A disconnected browser first load remains unverified. |
| Select an area with a published event (FL-01B/02) | PASS at corridor resolution | Canonical FastAPI-to-Streamlit test uses published, unassigned, draft and ineligible fixtures. Administrative locality and property associations remain BLOCKED by boundary validation. |
| See coverage and official sources (FL-01/04) | PASS for the link directory | Configured corridor scope and unavailable district/tehsil/village/farm coverage are labelled. AppTest verifies navigation and the local source registry. External reachability was outside the offline run. |
| Understand freshness and missing observations (FL-02/09) | PASS for the public feed, FAIL for a prototype | Public page separates unavailable freshness, event timestamps and empty versus failed feed. Operational data-integrity tests check no-data and provider failure. The existing NASA auto-load success count can include failed attempts (FL-09). Provider expiry through every UI and wrong-unit payload rejection remain UNVERIFIED. |
| View agricultural information (FL-03) | BLOCKED for validated farm-level answers | AppTest verifies unavailable operational exposure. Demo crop/exposure values and approximate historical outlines do not establish verified farm loss. English preparedness content needs verified attribution. |
| View livestock information (FL-04/08) | BLOCKED for livestock services | The static directory works. Species-specific content and verified service availability remain missing. Missing-imagery dam output and unvalidated forecast language remain open under FL-08. Missing optional forecast dependency was injected in AppTest and disabled the run control. |
| Submit a community report (FL-05) | BLOCKED for residents | Existing canonical tests cover authorized intake, coordinate validation, same-identity retry and event linkage. The application has no resident consent/submission workflow or restart-safe store. |
| Follow moderation (FL-05/10) | FAIL for page 3, PASS for the covered API roles | At baseline, API-configured page 3 displayed four local metrics and moderation controls. A declined demo update produced zero visible errors. Canonical tests verify unauthorized moderation, audit entries and transitions. P1-002 still owns durable review and concurrent modification. |
| Export or share eligible information (FL-07/11/13) | PASS for demo export, BLOCKED for operational export | Demo GeoJSON/manifest tests verify provenance and invalid coordinates. Canonical operational publication remains guarded. Demo Partner text and stub notification receipts do not establish a reviewed product, delivery, freshness or expiry. |
| Recover from service failure (FL-06/09) | PASS for public feed and analyst fixture paths | Socket-disabled tests cover timeout/503, incomplete event envelope, anonymous/forbidden roles, and retry semantics. Explicit snapshot export/restore tests do not prove automatic report recovery. Database failure for report persistence remains UNVERIFIED because that store is absent. |

### FL-05 — verified baseline and selected changes

| Finding | Reproduction and code | Expected result and impact | Severity / confidence | Acceptance test and state |
|---|---|---|---|---|
| Mode boundary | Set operational mode and an API fixture URL, then open page 3. `pages/3_📱_Field_Reports.py` calls `DataService.get_field_reports()`, which loads CSV in every mode. | The page reports unavailable and the helper neither reads nor changes local reports in operational/API mode. This prevents accidental disclosure and a misleading parallel queue. | P1 / High, reproduced | PASS in draft PR #89 across API-configured demo and both operational configurations. No local reads or writes. |
| False completion | In local demo, inject a declined moderation result and click Approve. UI unconditionally proceeds to success/rerun and the user receives no lasting error. Direct CSV write also propagates filesystem failures. | Failed, missing or stale actions show a clear error. After an acknowledged save, reread and show the new demo moderation state. Preserve old bytes when a save fails. Approval does not certify an observation. | P1 / High for declined action, reproduced. Injected write failure also reproduced. | PASS in draft PR #89 for each declined action, malformed/empty CSV, saved state, stale state and an interrupted write. |
| Idempotency ownership | Canonical `ingest_field_report` derives the receipt from a client ID. It currently returns an existing report without checking its stored event and server-selected submitting identity. | Same authorized identity and event can replay. A conflicting receipt returns a generic conflict without the prior payload. This protects precise locations, notes and evidence from unintended disclosure. | P1 / High, confirmed by failing synthetic API regressions. | PASS in draft PR #89 for event/principal conflicts and same-scope replays, including concurrent retries in one process. |

### Evidence limits

The offline checks exercised API and component behavior, including missing district/AOI, null timestamps,
invalid export coordinates, empty/malformed responses and no fixture fallback. The supported SQLite
migration test, workflow concurrency fixtures and explicit snapshot recovery are separate from durable
field reporting. Cross-process concurrency, browser map tile failure, contrast, real keyboard/screen-reader
navigation, 360 px reflow, Urdu/RTL reading order, live-provider timing and field comprehension remain open.
Chromium startup failed before a page could render. Existing Markdown and CSV paths were reviewed for
this slice, without a general XSS, CSV-injection or secret-exposure certification.

### Independent QA resolution and verification

[Draft PR #89](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/89) changes the FL-05
moderation row from FAIL to PASS for the tested unavailable/demo boundaries. The resident-intake
row remains BLOCKED. Streamlit demo writes only to its local fixture through temporary-file
replacement, with explicit acknowledged success or failure. The canonical path separately validates
an authorized intake, stores a process-local record, applies allowed moderation transitions and
audits them. The existing publication gate still controls what reaches the public view. Durable
private reporting, independently verified observations, and live moderation remain prerequisites.

- `APP_MODE=test .venv/bin/python -m pytest --disable-socket --allow-unix-socket tests/test_field_report_boundaries.py -q --tb=no`
  produced 13 failures and one pass before the edit. The final regression file contains 15 cases.
- The focused Field Reports, API, analyst and publication suite passed 64 tests. It verified
  401/403 denial, 409 conflicts without stored report content, a 400 stale moderation action,
  a same-scope replay retaining its ID, and one linked record after concurrent process-local retries.
- `APP_MODE=test .venv/bin/python -m pytest --disable-socket --allow-unix-socket tests/ -q --tb=short`
  passed 293 tests with 475 warnings. SQLite reached `b4d9d93f2a10` after downgrade/re-upgrade.
  Compilation, changed-file whitespace, local links and tracked-data checks passed.
- [Main](https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44278515915) and the
  [implementation checkpoint](https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44280556574)
  reported hosted failure with zero jobs. Local browser startup failed on socket permissions.
- Next QA case: add offline AppTest for PK-011 / FL-08 that injects a functioning optional forecast
  provider, opens the prototype in operational mode, and checks that unavailable is shown before
  any provider call or alert-style output. Review the presentation guard against ADR-001 separately.
  Existing scientific forecast and dam validation remain open.

### FL-05 · demo acknowledgement follow-up

| Journey and reproduction on main at `90062a0` | Expected | Actual and cause | Impact / confidence | Acceptance |
|---|---|---|---|---|
| In standalone demo open Field Reports, enter a fictional note, consent, submit, then inspect the queue. | A real receipt identifies a saved submission. A rehearsal identifies itself before and after the action. | Page 3 calculates a hash and displays “Report received” and “Pending Moderation”. No write or queue insertion occurs. The existing acceptance test checks those strings alone. | P1 / confirmed by handler inspection and the passing baseline test. A visitor can mistake the screen for acknowledgement of a loss report. | Render a labelled preview, verify selected category/area/date, unchanged queue/file and repeat behavior. |
| Open the demo with no moderation CSV or no configured corridors. | Practice remains usable independently of fixture rows and selectable areas come from configuration. | An early stop hides the form when rows are missing. A hardcoded fallback supplies two areas when coverage is empty. | P2 / confirmed by control flow. | Exercise both empty states and the operational/API boundary in AppTest. |

Operational reporting remains blocked on private durable intake and policy. This
slice owns the presentation contract only.
