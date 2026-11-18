# UI and UX acceptance matrix

Baseline main `39dd0e4` on 18 November 2026. Scenario IDs identify test
cases. Task ownership remains in the
[master plan](../engineering/MASTER_TASK_PLAN.md). `Observed` refers to a
local AppTest run or cited regression. `Traced` refers to the call path only.
Prototype actions were tested without real providers or configuration writes.

| Scenario | Persona and entry | Actions | Expected | Baseline actual | Failure condition | Evidence and code | Severity | Status / task |
|---|---|---|---|---|---|---|---|---|
| UX-A01 | New visitor · Home | Open root → read first heading → locate and open My Area, Farmer Safety, Livestock Safety, Official Information and Community Reporting | All five routes visible in main content, with scope explained before event status | One direct link, to Official Information. Other routes require the sidebar. | Missing/wrong route, unexplained scope or specialist actions in public content | Observed Home AppTest and `streamlit_app.py`. Destination render check planned. | P1 | FAIL / UI-001 |
| UX-A02 | Phone user · Home | Open with healthy empty feed → read message → choose My Area; repeat with 503, timeout and no API | Distinct empty/unavailable text, unchanged orientation and links, single timed API call when configured | Empty/fail messages exist. Only official directory has a body link. | Navigation lost during failure, empty used as safety claim, fixture fallback or repeated fetch | Home source and `tests/test_streamlit_public_pages.py`; new Home fixtures planned. | P1 | PARTIAL / UI-001 |
| UX-A03 | Demo visitor · Home | Open standalone demo → read watermark → inspect summary → click Community Reporting | Watermark before figures, count of published fixtures only, demo practice clearly identified | Watermark and published count pass existing test. No direct reporting link. | Unmarked figures, draft counted or practice called submission | Observed regression `test_demo_home_shows_only_published_fixtures`; page 3 tests. | P1 | PARTIAL / UI-001, PK-006 |
| UX-A04 | Farmer · My Area | Open dashboard → choose configured corridor → inspect published card → toggle map; repeat with empty and failed feed | Clear counts and unknown state, coverage and officials accessible without tiles | Selector and official link remain on tested outages. Area map is opt-in. | Unsupported locality presented as covered, unrelated event surfaced or missing time shown as current | Observed existing public page tests; page 1 and backend adapter. | P1 | PASS for corridor fixtures / PK-001 |
| UX-A05 | Farm worker · Farmer Safety | Open guide → find equipment and stored grain → read recovery → open cited guidance → print | Find stages and sources quickly; complete print view | Stage headings and sources render. Scan time and print unverified. | Hidden section, truncated print or unsupported instruction | Observed AppTest and `tests/test_preparedness_pages.py`; page 17. | P2 | PARTIAL / PK-010, PK-003 |
| UX-A06 | Herd owner · Livestock Safety | Open guide → find identification and fodder → locate veterinary directory → read recovery | Topics and source traceable; service availability stays unknown | Sections render. Quantitative source review and phone comprehension pending. | Unsupported quantities or unconfirmed service listing shown as available | Observed AppTest; page 18 and preparedness tests. | P1 | PARTIAL / PK-010, PK-005 |
| UX-A07 | Volunteer · Official Information | Open directory during feed outage → identify issuer and scope → open agency link | Directory independent of feed, visible review date, official destination | Directory renders. External browser reachability outside fixture run. | Hidden links, inaccurate attribution or unavailable destination | Observed AppTest and `tests/test_official_sources_directory.py`; page 16. | P1 | PASS for directory / PK-002 |
| UX-A08 | Resident · Community Reporting | Open demo → expand practice → select example → confirm → preview; switch to operational | Demo explicitly states nothing was submitted. Operational shows unavailable. | PR #92 text and mode gate verified. | Receipt or moderation status shown for preview; operational submission control appears | Observed existing field-report and community-report tests; page 3. | P1 | PASS for demo boundary / PK-006 |
| UX-A09 | Resident · future intake | Start report → consent → send → save private receipt → retry after restart → check moderation | Acknowledgement after durable commit; private status access | No operational resident intake; identity, retention and transaction contract open. | Data exposed, receipt without committed record, duplicate or lost retry | Traced page 3 and canonical `api/main.py`; field report boundary tests. | P1 | BLOCKED / PK-006, P1-002, SEC-001 |
| UX-A10 | Analyst · Analyst Review | Open without credential → try authorized reviewer → filter and paginate → retry failed API | Server enforces role; read-only items and explicit error/empty status | Existing test fixtures pass. Durable review and browser table access pending. | Unauthorized rows, fake queue on outage or unintended mutation | Observed existing `tests/test_streamlit_analyst_queue.py`; page 2. | P1 | PASS for read-only path / UI-001, P1-002 |
| UX-A11 | Operator · Training / Operations | Open page 6 → Trigger Retraining; open page 7 → Trigger Daily Pipeline | Command reference clearly labelled or authorized job ID confirms actual enqueue | Both controls display triggered text and a command, with no dispatch call. | Success or triggered copy without confirmed execution | Observed click in AppTest and handlers in pages 6 and 7. | P1 | FAIL / UI-001, OPS-001 |
| UX-A12 | Admin · Settings | Open page 8 → inspect local config form → verify permitted and denied writes with temp config | Protected changes and truthful persistence outcome | Form renders. Save path leads to local YAML; role enforcement and write outcomes still need isolated test. | Unauthorized write or misleading save confirmation | Observed entry, traced `save_flood_thresholds` and `save_breach_weights`. | P1 | TRACED / SEC-001, UI-001 |
| UX-A13 | Researcher · Satellite Viewer / Hydromet | Search with no STAC results → open rainfall with provider failure → inspect statuses | Empty search distinct from unavailable. Rainfall failures identified individually. | STAC showed success with zero scenes. Hydromet showed six failed requests. | Provider error interpreted as zero observations or successful retrieval | Observed AppTest with providers stubbed; pages 9 and 10. | P2 | PARTIAL / UI-001, DATA-001 |
| UX-A14 | Resident · Forecast / Dam | Open pages 13 and 15 in operational mode → look for actionable outputs → use official link | Operational gate before prototype results, official route available | Both gates rendered. Demo boundary has existing AppTests. | Operational output from an unvalidated model or proxy | Observed AppTest; safety gate tests. | P1 | PASS for mode gates / PK-011 |
| UX-A15 | Low-bandwidth or assistive-tech user · Home → My Area | Resize to 360 and 320 CSS px → Tab and activate links → block map assets → read status with screen reader → repeat with Urdu when approved | No loss of essential content or actions; accessible names/focus/reflow/contrast; reviewed RTL | Component logic runs. Chromium startup failed before rendering. Human-reviewed Urdu pending. | Clipped content, invisible focus, unreadable status or wrong reading order | Chromium socket error and AppTest only. Screenshots pending. | P1 | UNVERIFIED / UI-001, PK-003 |

## Homepage checkpoint in PR #93

| Scenario | Actual after change | Evidence and status |
|---|---|---|
| UX-A01 | Home gives the coverage and emergency-information context before the five public routes. Streamlit resolves native links to the current pages, and each destination renders in AppTest. | PASS in component tests. Browser clicks and focus remain part of UX-A15. |
| UX-A02 | Navigation precedes publication status with empty, 503, timeout, published and unconfigured feeds. The configured request uses the existing two-second timeout, once per run. An empty feed explicitly leaves conditions unknown. | PASS for fixture states. `test_home_keeps_public_links_when_event_feed_changes` and the unconfigured operational test. |
| UX-A03 | The existing watermark precedes the standalone demo count. Demo and authorized-publication filters retain their established behavior. The Community Reporting entry explains that real submission is unavailable. | PASS for the tested publication and mode boundaries. Existing page 3 regressions continue to pass. |

The selection of homepage cases failed seven times before the change, with one
existing non-Home case passing. All 18 tests in
`tests/test_streamlit_public_pages.py` and all 341 offline tests passed after
the change. No browser screenshots were captured because Chromium failed
before rendering. Keyboard, focus, contrast, reflow, assistive technology and
Urdu acceptance remain open.

## Homepage and grouped navigation follow-up in PR #94

| Cases | Verified at the component level |
|---|---|
| UX-A01 and UX-A02 | One native top menu groups public, research and operations routes. Home and all 18 existing pages retain their paths. All destinations rendered in an offline AppTest smoke run. Home shows availability first, then area, farm, livestock and official information links. |
| UX-A02 to UX-A04 | Home and My Area use the same wording for a missing publication source, a failed service, empty results and demo data. The stale notice describes demo processing only. A successful feed may still have unknown update timing. |
| UX-A03 and UX-A10 | No local fixture fallback or research provider load during initial operational Home rendering. The single canonical request retains its two-second timeout. The analyst and reports boundary suites passed. |
| UX-A15 | Reading order and native link labels verified in AppTest. Chromium could not open its startup socket, so screenshots, navigation overflow, keyboard focus, touch size, contrast and reflow at 320, 360, 390, 768 and 1440 px remain unverified. |

Verification used Streamlit 1.67.0. The dashboard dependency requires 1.46 or
later to support native top navigation. The full offline suite passed 345 tests.

## Preparedness and public-journey follow-up in PR #95

The steps below are the browser journey. The offline suite resolves each
native link target and calls Streamlit's route switch in the same AppTest
session. AppTest can change selectors, checkboxes and buttons. It cannot
physically click links, open a collapsed detail panel or measure layout.

| Journey and tracking | Exact steps | Result and evidence |
|---|---|---|
| A · UX-A05, PK-010 | Open Home → Prepare my farm → read Before flooding → open Crops, equipment and chemicals → turn on Show all details for printing → View official flood information → choose the FFD bulletin. | The pump and storage checklist appears inline. The detail topic and extension reference are present. The print toggle renders the topic as a heading, with sources. The official page identifies FFD and its destination, link review date and need to check bulletin issue time and area. Component PASS. |
| B · UX-A06, PK-010 | Open Home → Prepare my livestock → read Before flooding → open Feed and water before flooding → turn on Show all details for printing → find Veterinary Information and Official Resources → locate the Sindh and Punjab contact links → View official flood information. | Feed, water, identification and shelter appear in order. LEGS and provincial sources are linked. The page explains that service availability is unknown. The fixed fodder duration and wound-treatment instruction are absent. Component PASS. |
| C · UX-A04, PK-001 | Open Home with a 200 response containing an empty list → Open My Area → select Chenab-Middle → read the result → View official flood information. | Clear message says there are no linked publications and local conditions may still be unknown. No event figure or map is rendered. FFD and NDMA links retain the source directory review date. Component PASS. |
| D · UX-A02, PK-003 | Open Home with a simulated timeout → Open My Area → select Chenab-Middle → read the unavailable message → View official flood information. | Failed requests remain distinct from empty results. No fixture fallback, map or count. The official directory renders after the failure. Three two-second-timeout requests were issued across Home, initial area and selector change, with zero on the official page. Component PASS. |
| E · UX-A08, PK-006 | Open standalone demo Home → Community Reporting → Practice a community report (demo) → choose Fodder or clean water need and Chenab-Middle → acknowledge → Preview example. Repeat in operational mode. | The preview explicitly says nothing was submitted, and the isolated data directory stays empty. Operational mode shows resident intake unavailable without a practice action. Component PASS. |
| F · UX-A10 and UX-A12, UI-001 and SEC-001 | Open operational Home → inspect public links → navigate directly to Analyst Review without a credential → navigate to Settings → verify anonymous canonical review queue and state export responses. | Analyst Review displays a credential prompt without requesting a queue. Settings exposes neither editable controls nor server configuration. Temporary configuration remains unchanged. Canonical review and admin state export return 401. Component and API PASS for these interfaces. |

Five journey cases initially failed. Four found identical link names on the
official directory, which would appear with identical names in a screen reader's links list. The fifth found settings controls that could edit server files without an
authenticated web operator. PR #95 gives FFD and NDMA distinct action labels and
replaces hosted settings controls with server-side configuration guidance.

### Low-bandwidth and accessibility evidence

Both guides use a centered single column, plain checklist text before optional
details, a consistent heading order and a labelled print checkbox. The external
references are navigation links. The guide routes and print reruns perform zero
event/provider requests or fixture reads in the isolated checks. In five local
AppTest samples per guide, median initial component times were 68.0 ms (farm)
and 69.2 ms (livestock). Median print reruns were 6.6 ms for each. These measure
local component execution. Device, tile throttling, Internet, print and assistive
technology performance remain unverified.

Home and My Area still use one canonical event request per run when configured.
Changing the corridor re-runs that request and keeps the selected corridor.
The map remains optional and the directory loads independently of the feed.
There is no offline cold-load guarantee for a browser that cannot reach the app.

Chromium startup failed on a denied socket before rendering. Browser screenshots
and actual Android print pagination, focus/activation, zoom, target sizes,
contrast and screen-reader announcements remain unverified. UX-A15 needs a
browser-enabled run at 320, 360, 390, 768 and 1440 px. A links-list and expanded
details check should include the names, focus and source dates.
