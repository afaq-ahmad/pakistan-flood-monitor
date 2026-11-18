# Pakistan Flood Monitor UI and UX improvement plan

## Executive assessment

On 18 November 2026, main at `39dd0e4` includes PRs #85–92. The public event
boundary, private read-only analyst queue, area lookup, English preparedness
guides, research gates and report practice preview are in place. Home still
starts with the event count and provides one direct link, to Official Information.
People who want to check a corridor or protect crops or animals must discover the
relevant page in an 18-page sidebar.

Keep the existing routes. Start with task-based links on Home and treat the event
feed as secondary information. Some specialist pages display fixture or prototype
results in operational mode. Their presentation and authorization boundaries need
independent review before any broader navigation change promotes those pages.

## Audience and information architecture

| Audience | First question | Proposed entry |
|---|---|---|
| Resident on a basic phone | Is information published for my area, and where can I check official bulletins? | Home → My Area or Official Information |
| Farmer or agricultural worker | What preparations apply to my crops, grain, pumps and records? | Home → Farmer Safety |
| Livestock owner | What can I prepare for my animals, and where can I seek verified veterinary information? | Home → Livestock Safety |
| Community volunteer | Where can I find information to share, or report a local problem? | Official Information → issuer; Community Reporting → practice or explicit unavailability |
| Analyst | What evidence is available and which candidates can I review? | Research and Analysis → source-specific tools; Operations and Administration → Analyst Review |
| Authorized administrator | Can I see what ran or change a setting, and where is the audit trail? | Operations and Administration → confirmed status and authorized actions |

Today Streamlit derives a flat sidebar from numbered files. Home links only to
Official Information, and several public pages link to the same directory. The
separate HTML dashboard has its own prototype routes and data. The proposed public
sequence is Home, My Area, Farmer Safety, Livestock Safety, Official Information
and Community Reporting. Research and Analysis groups history and scientific
tools. Operations and Administration groups review, partner sharing, exports,
training administration, run controls and settings. These groupings are navigation
labels. Authorization remains enforced at the service or write boundary.

Use native `st.page_link` for the first slice. It works with the current `pages/`
registry and preserves direct URLs. Evaluate grouped `st.navigation` and
`st.Page` only after testing minimum Streamlit support, AppTest, direct URL
compatibility, back navigation and protected actions. Once a process executes
`st.navigation`, Streamlit uses that registry in place of the filesystem sidebar.
Review the [Streamlit navigation guide](https://docs.streamlit.io/develop/concepts/multipage-apps/overview).

## Screen audit

The audit opened Home and all 18 numbered pages in AppTest using operational
mode with no canonical URL, stubbed rainfall failure and an empty STAC result.
The table distinguishes inspected code and companion tests from exercised
actions. It covers a runtime sample, with live providers, browser presentation
and authorized mutations outside the sample. The baseline full offline suite
passed 336 tests. All screens primarily display English. Selected event copy
also exposes an Urdu field, with translation accuracy and RTL behavior pending.
Mobile and accessibility notes describe layout risks to verify.

| Screen and audience | Entry and traced interaction | Hierarchy, states, data and follow-up |
|---|---|---|
| Home · everyone | Root. Open with no API; see unavailable and one official link. | Event metric drives hierarchy when available. Canonical published snapshot or labelled fixtures. Lead with public tasks, then explain empty and unavailable states. UI-001. |
| 1 Public Dashboard · resident | Sidebar → My Area → corridor → matched publications → optional map. Existing tests exercise empty and failed API. | Reference coverage and official link survive outage. Feed freshness is unavailable when unsupported. Cards, exposure and map come after text. Check linked, unlinked and unsupported areas, map legend and mobile reflow. PK-001, PK-003. |
| 2 Analyst Review · analyst | Sidebar → credential → request queue → filter and paginate. Unconfigured API showed unavailable. | Authorized read-only canonical queue, separate demo CSV controls and audit. Dense tables and evidence need keyboard and narrow-screen checks. Mutations and durable history depend on P1-002. UI-001. |
| 3 Field Reports · resident/analyst | Sidebar → demo practice → category, corridor, date → preview. Operational AppTest showed unavailable. | PR #92 preserved. Structured practice issues no receipt. Demo moderation displays fixture metadata separately. Make practice discoverable without suggesting that real intake exists. PK-006. |
| 4 Partner Mode · volunteer/partner | Sidebar → select event → download advisory text. Unconfigured API showed unavailable. | Code composes a brief from a sparse public feed or demo fixture, without a reviewed-product issuer and expiry contract. Review eligibility before promoting links. Text-first sharing needs source metadata. PK-004, PK-009. |
| 5 Export Center · researcher/partner | Sidebar → demo event → generate → download GeoJSON point and manifest. Operational path showed unavailable. | Existing mode guard and provenance tests. Actual browser file transfer and retry behavior still need acceptance. P1-003, UI-001. |
| 6 ML Training · developer | Sidebar → Trigger Retraining. AppTest showed “pipeline triggered”; handler prints a command. | Local registry, fixed drift/benchmark copy and simulated actions appear beside actual metrics. Label reference commands and examples; provide results only from an identified run. Wide comparison tables need review. UI-001. |
| 7 Operations · operator | Sidebar → Trigger Daily Pipeline. AppTest showed “Pipeline triggered”; handler prints a command. | Freshness and runs read local fixtures. Hardcoded incident ages imply current status. Run and snapshot affordances need clear command-reference labels or authorized real actions. UI-001, OPS-001. |
| 8 Settings · administrator | Sidebar → thresholds/weights → Save. Controls rendered. Traced handlers to local YAML writes; did not click. | Config file labels are visible, with no page/backend mode or role check on these save paths in the inspected code. Verify access and constrain writes before redesigning operator navigation. Credential/environment sections show instructions. SEC-001, UI-001. |
| 9 Satellite Viewer · researcher | Sidebar → select sensor/corridor → search → inspect scene. Empty fixture produced success with 0 results. | Direct STAC query and scene timestamps, with map and dense tables. Catalog failure can collapse into an empty result. Separate provider failure, no matches and actual scene evidence. DATA-001, UI-001. |
| 10 NASA Hydromet · researcher | Sidebar → rainfall auto-load → risk scores or imagery tabs. Stubbed failures showed an error for six corridors. | PR #91 failure counts hold. Provider queries run on open by default. Distinguish dated rainfall from the composite prototype score. Keep heavy requests and tables below source and availability. DATA-001, PK-008. |
| 11 ML Water Detection · researcher | Sidebar → download images → select local image → run clustering. Actions rendered on open. | Direct provider/local storage path and image-scale percentage. Label detection as an experimental image result and show image acquisition and coverage. Verify write boundary, map alternatives and failure states. DATA-001, GIS-001, UI-001. |
| 12 Historical Flood Map · farmer/researcher | Sidebar → choose dated event → read approximate extent and map. Disclaimer rendered. | PR #91 removes ground-truth terminology. Bundled reference JSON needs provenance and licensing checks. Provide readable coverage context without tiles. PK-010, GIS-001. |
| 13 Flood Forecasting · researcher | Sidebar → operational unavailability; demo → corridor → optional prototype forecast. | Operational gate verified. Demo labels and official route remain. Forecast dates, predicted levels and model limits must stay visible beside results. External inputs and hindcast validation pending. PK-011. |
| 14 Advanced ML SAR · researcher | Sidebar → run SAR and terrain steps → run inference. Entry exposed controls; traced prerequisite/error branches. | Missing dependencies are reported. Prototype processing and simulated rainfall need explicit output provenance and a mode check. Preserve charts with text equivalents. UI-001, DATA-001. |
| 15 Dam Flood Risk · researcher | Sidebar → operational unavailability; demo → choose corridor → inspect local proxy and history. | PR #91 gate verified. Preserve research labels; validate proxy measurand, time and uncertainty separately from storage or warning claims. PK-011, DATA-001. |
| 16 Official Information · everyone | Home/page link → choose agency → follow published source. Registry rendered independently of event API. | Source scope and review date provided. Check destination reachability separately and keep names readable without imagery. PK-002, PK-003. |
| 17 Farmer Preparedness · farmer | Sidebar → before/during/after sections → named source. Guidance rendered without provider queries. | Stages already exist. Improve scan time with short checklists and source-adjacent attribution after checking existing statements. Print and reviewed Urdu remain open. PK-010, PK-003. |
| 18 Livestock Preparedness · animal owner | Sidebar → before/during/after sections → named source. Guidance rendered without provider queries. | Stages and species guidance exist. Verify quantitative claims against each cited source. Keep service availability distinct from contact links. PK-010, PK-005, PK-003. |
| Standalone `dashboard/` · developer demo | `dashboard_app.py` → HTML → Leaflet and `/api/events` → map/summary. Existing TestClient covers mode guard. | Separate sample feed, external fonts/icons/tiles and placeholder panels. Chart/map browser behavior depends on assets. Retain explicit prototype identity and avoid positioning it as the public Home. UI-001. |
| `backend_service.py` · UI adapter | Home and My Area → one published-only view of `/public/events`, or CSV in explicit local demo/test. Analyst uses a distinct internal queue. | No failover to demo after API error. Local methods also expose config, run or model files to prototype pages. Audit each caller's mode, source timestamp and permissions independently. UI-001, SEC-001. |

## Visual and interaction system

Use Streamlit headings, body text, explicit widget labels and native links.
Use one reading column for essentials and reserve wider layouts for maps or
specialist tables that need space. Place descriptive text before optional maps
and use whitespace and section headings to support scanning. Write dates with
their meaning and timezone, and show units next to quantities. Use the existing
theme for the first slice. Preserve visible focus and use text alongside colour.

| Status text | Meaning |
|---|---|
| Available | Named source returned usable information. Represent freshness separately. |
| No published events | The publication feed returned no eligible entries. Local conditions may still be unknown. |
| Unavailable | The source, service or required input could not be used. Keep alternate links accessible. |
| Stale / Degraded | Explain the quality or freshness rule when the backend supplies that evidence. |
| Simulated | Display the established watermark beside fixture or prototype values. |
| Under review / Published | Show the actual workflow status. Neither label establishes an official emergency warning. |

Reuse the demo watermark, source directory and public-feed adapter. Use native
widgets for the first slice. Extract common source/availability and stage
checklist components only when at least two callers share vocabulary and
behavior. Keep operator action feedback tied to an acknowledged outcome.

**Home wireframe in reading order:** Title → short description and limitations →
My Area → Official Information → Farmer Safety → Livestock Safety → Community
Reporting → published-event summary. Use a single vertical list. Keep the demo
watermark before the event count or any other fixture value.

**My Area wireframe:** Coverage explanation → corridor selector → official
sources → published entries or an explicit empty/unavailable state → optional
map. Retain the verified corridor scope and preserve unassigned events.

## Accessibility, language and verification

Target [WCAG 2.2 AA](https://www.w3.org/TR/WCAG22/) and track evidence per
page. Verify mobile at 360 px and reflow at 320 CSS px, enlarged text, keyboard
order and visible focus, link purpose, screen-reader names and status
announcements, text alternatives, and contrast in light and dark themes. Check
slow service and blocked tile requests. For Urdu, use a qualified reviewer
and test Urdu script rendering and RTL reading order, including mixed units,
numbers, dates, links and names. Preserve reviewed English when approved Urdu
copy is unavailable. Automated component tests verify labels and order.
Browser rendering, assistive technology and user comprehension require
separate checks. Local Chromium failed before rendering with socket permission
denied. No screenshots or browser acceptance evidence are available.

## Priorities and milestones

| Order | Work and acceptance | Dependency or blocker |
|---|---|---|
| 1 | UI-001 Home. Show five plain-language links in the body before information that depends on the feed. Validate routes in AppTest, preserve watermark, keep links after 200-empty, timeout, 503 and no configuration, and restrict Home to one canonical request per run with the existing timeout. | Existing registry and public adapter. |
| 2 | UI-001 / SEC-001 specialist controls. Verify the Settings authorization boundary with a temporary config and role fixtures. Address unbacked Operations and Training acknowledgements in separate slices. | Explicit read/write and run permissions. Navigation does not grant authorization. |
| 3 | PK-001 / PK-003 verify the Home-to-area path on a narrow browser, with keyboard and map assets blocked. Add direct return paths and check no event is interpreted as known safety. | Browser environment. District/tehsil mapping requires validated boundaries. |
| 4 | PK-010 / PK-003 improve scanning and print layouts for the two existing guides. Verify source support for quantities and preserve attribution. | Human approval for Urdu and any new preparedness claims. |
| 5 | UI-001 evaluate grouped sidebar, specialist labels and deep links. Preserve stable routes and authorization. | Specialist mode/access audit and browser compatibility. |
| 6 | PK-006 define the private receipt lifecycle. Walk through coarse area and category, informed consent, durable write, private acknowledgement, authorized moderation and private status lookup. Design for write failure, retries and retention/deletion. | P1-002 and SEC-001. Resident identity and retention policy require review. |

Scientific readiness, official publication, relief availability, and service or
hazard validation remain governed by existing roadmap dependencies. Use the
[acceptance matrix](UI_UX_ACCEPTANCE_MATRIX.md) for journeys and the
[master plan](../engineering/MASTER_TASK_PLAN.md) for task ownership.
