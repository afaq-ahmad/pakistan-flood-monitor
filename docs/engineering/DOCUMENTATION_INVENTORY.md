---
title: Documentation Inventory and Evidence Audit
doc_type: reference
status: baseline
owner: engineering
verified_at: 2026-11-18
---

# Documentation inventory and evidence audit

This inventory covers all 33 tracked Markdown files at main `77dc8b7`, after
[PR #95](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/95).
Every row records the topic, audience, evidence owner or source, related code
or contracts, task IDs and disposition. Verification on 18 November 2026 was
a repository review. It does not revalidate old research, every historical
claim, external services, or the accepted decisions themselves. The revision
table records the last Git edit before the audit, independently of this
verification date. See the [documentation homepage](../INDEX.md).

## File inventory

| ID | File at baseline | Diátaxis type and audience | Purpose and primary topic | Evidence owner, implementation and tasks | Finding and disposition |
|---|---|---|---|---|---|
| D01 | [`.github/pull_request_template.md`](https://github.com/afaq-ahmad/pakistan-flood-monitor/blob/77dc8b7fd1e545c4284de54afc11dc8760b64456/.github/pull_request_template.md) | Reference · maintainers | PR evidence fields | AGENTS.md, agent workflow; ENG-001 | Retain. GitHub template uses section headings and comments by design. |
| D02 | [`AGENTS.md`](https://github.com/afaq-ahmad/pakistan-flood-monitor/blob/77dc8b7fd1e545c4284de54afc11dc8760b64456/AGENTS.md) | Reference · coding agents | Repository operating contract | Accepted ADR, tests and CLI/API; ENG-001, DATA-001, GIS-001 | Retain authoritative. Link from the vault and repository README. |
| D03 | [`PROJECT_PROGRESS_AND_IMPLEMENTATION_REPORT.md`](https://github.com/afaq-ahmad/pakistan-flood-monitor/blob/77dc8b7fd1e545c4284de54afc11dc8760b64456/PROJECT_PROGRESS_AND_IMPLEMENTATION_REPORT.md) | Explanation · maintainers, architects | Prototype progress and research choices | Git history, implementation ledger; UI-001, DATA-001, PK-011 | Label historical. Its 15-page count and operational capability claims predate current safety boundaries. |
| D04 | [`README.md`](https://github.com/afaq-ahmad/pakistan-flood-monitor/blob/77dc8b7fd1e545c4284de54afc11dc8760b64456/README.md) | Explanation · newcomers | Project orientation and onboarding links | Streamlit registry, canonical API, setup; UI-001, OPS-001 | Make a short repository entry point. Old diagram, 15-page count, Active corridor labels and installed commands need correction. |
| D05 | [`data_contracts/README.md`](https://github.com/afaq-ahmad/pakistan-flood-monitor/blob/77dc8b7fd1e545c4284de54afc11dc8760b64456/data_contracts/README.md) | Reference · API integrators, QA | Risk summary contract | api/main.py and publication contract tests; API-001, P1-003 | Retain with current mode and route limitations verified. Linked from API and index. |
| D06 | [`docs/adr/ADR-001-canonical-runtime.md`](../adr/ADR-001-canonical-runtime.md) | Explanation · architects, coding agents | Accepted runtime and integrity decision | ADR approval and Git history; API-001, DATA-001 | Retain immutable. Current implementation evidence belongs in the ledger. |
| D07 | [`docs/adr/ADR-TEMPLATE.md`](../adr/ADR-TEMPLATE.md) | Reference · ADR authors | Decision record format | ADR policy and Git history; ENG-001 | Retain as template. No live claims. |
| D08 | [`docs/adr/README.md`](../adr/README.md) | Reference · architects | Decision index and policy | ADR-001 and ADR template; API-001, ENG-001 | Retain. Link to the documentation guide and index. |
| D09 | [`docs/api.md`](../api.md) | Reference · developers, QA | HTTP routes, roles and publication | api/main.py, OpenAPI, API regressions; API-001, SEC-001, P1-003 | Correct storage semantics, roles and public/publication limitations. Routes omitted from prose are discoverable via OpenAPI. |
| D10 | [`docs/architecture.md`](../architecture.md) | Explanation · architects | Runtime and data flow | Entrypoints, workflow repository, ADR-001; API-001, P1-001, P1-002 | Replace provider-first diagram with actual entrypoints and persistence boundaries. |
| D11 | [`docs/configuration.md`](../configuration.md) | Reference · operators | Environment and thresholds | config.py, .env.example, docker-compose.yml, config/thresholds; OPS-001, SEC-001 | Correct DATABASE_DSN, dotenv precedence and YAML interpretation. |
| D12 | [`docs/contributing.md`](../contributing.md) | How-to · contributors | Landing an owned change | AGENTS.md, Git workflow and PR template; ENG-001 | Centralize setup and test references. Correct Python guidance. |
| D13 | [`docs/deployment.md`](../deployment.md) | How-to · operators | Run a local demonstration stack | Dockerfile, Compose, root Alembic; OPS-001, P1-002 | Replace speculative production recommendation with traced local topology and explicit validation limits. |
| D14 | [`docs/development.md`](../development.md) | How-to · developers | Add and test changes | streamlit_app.py, canonical package, tests; UI-001, ENG-001 | Replace automatic file routing and file-only persistence guidance. |
| D15 | [`docs/engineering/AGENT_GITHUB_WORKFLOW.md`](AGENT_GITHUB_WORKFLOW.md) | How-to · coding agents | Start, checkpoint or resume work | Git helpers and workflow tests; ENG-001 | Retain workflow authority. No duplication in the index. |
| D16 | [`docs/engineering/AGENT_SESSION_LOG.md`](AGENT_SESSION_LOG.md) | Reference · agents | Chronological session handoffs | Git history and per-session evidence; ENG-001 and historical task IDs | Keep append-only. Draft PR links describe their state at that checkpoint. |
| D17 | [`docs/engineering/FUNCTIONALITY_GAP_AUDIT.md`](FUNCTIONALITY_GAP_AUDIT.md) | Reference · maintainers, QA | Observed baseline gaps and responses | PRs #85–89, AppTest and audit fixtures; UI-001, QA-001 | Retain as evidence with explicit cutoff. Current state belongs in the plan and ledger. |
| D18 | [`docs/engineering/IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md) | Reference · maintainers, architects | Evidence ledger and maturity | Merged changes, test results, ADRs; ENG-001, API-001, DATA-001 | Retain. Keep historical test and prompt sections clearly dated. |
| D19 | [`docs/engineering/MASTER_TASK_PLAN.md`](MASTER_TASK_PLAN.md) | Reference · all contributors | Task IDs and current state | Merged evidence and acceptance; all task IDs | Retain as sole task tracker. Label baseline evidence and link to the ledger. |
| D20 | [`docs/engineering/REMAINING_WORK.md`](REMAINING_WORK.md) | Reference · agents, maintainers | PR #92 checkpoint and dependencies | PR #92 and master plan; PK-006, P1-002, SEC-001 | Keep path and evidence. Relabel dated snapshot and replace parallel pending table with master-plan pointer. |
| D21 | [`docs/overview.md`](../overview.md) | Explanation · users, contributors | What the system provides and scope | Public streamlit routes, source directory and ledger; PK-001, PK-010, PK-011 | Replace live-map and early-warning implications, retain research goals with limitations. |
| D22 | [`docs/product/AGRICULTURAL_EXPOSURE_SPECIFICATION.md`](../product/AGRICULTURAL_EXPOSURE_SPECIFICATION.md) | Reference · product, GIS, QA | Prerequisites for field exposure | GIS and data contracts, publication and consent rules; PK-007, DATA-001, GIS-001 | Retain as blocked design. Does not establish implementation or field evidence. |
| D23 | [`docs/product/FARMER_LIVESTOCK_QA_MATRIX.md`](../product/FARMER_LIVESTOCK_QA_MATRIX.md) | Reference · product, QA | Field scenarios and prior evidence | AppTests and linked PRs; PK-001, PK-006, PK-010, QA-001 | Retain dated scenario history and link current UI acceptance matrix. |
| D24 | [`docs/product/FARMER_LIVESTOCK_USER_JOURNEYS.md`](../product/FARMER_LIVESTOCK_USER_JOURNEYS.md) | Explanation · product, QA | Rural personas and source-informed journeys | Published sources and QA scenario evidence; PK-001, PK-006, PK-007, PK-010 | Retain simulated personas and historical walkthroughs. Avoid treating them as participant validation. |
| D25 | [`docs/product/PAKISTAN_FEATURE_ROADMAP.md`](../product/PAKISTAN_FEATURE_ROADMAP.md) | Reference · product, maintainers | Feature specifications and product dependencies | PK task acceptance and product research; PK-001–PK-011 | Keep requirements authoritative. Task execution and current status belong in the master plan. |
| D26 | [`docs/product/PAKISTAN_USER_NEEDS_AND_EVIDENCE.md`](../product/PAKISTAN_USER_NEEDS_AND_EVIDENCE.md) | Explanation · product, researchers | Public needs and government source context | Dated source research; PK-001–PK-011 | Retain research snapshot. Independently recheck time-sensitive links and service claims before reuse. |
| D27 | [`docs/product/UI_UX_ACCEPTANCE_MATRIX.md`](../product/UI_UX_ACCEPTANCE_MATRIX.md) | Reference · QA, product | UX scenarios and verification status | Streamlit and API fixtures; UI-001, PK-003, PK-010 | Retain explicit baseline and later checkpoints. Browser and assistive evidence remains open. |
| D28 | [`docs/product/UI_UX_IMPROVEMENT_PLAN.md`](../product/UI_UX_IMPROVEMENT_PLAN.md) | Explanation · product, frontend | Design proposals, audits and Urdu readiness | Public routes, tests and source review; UI-001, PK-003, PK-010 | Retain proposal and historical audit. Separate later merged behavior from initial baseline. |
| D29 | [`docs/setup.md`](../setup.md) | Tutorial · new developers | First local run | pyproject.toml, .env.example, API and dashboard entrypoints; OPS-001 | Make sole installation and quickstart recipe. Python version and required provider credentials need correction. |
| D30 | [`docs/testing.md`](../testing.md) | How-to · developers, QA | Offline checks and evidence limits | canonical-checks.yml, tests, root Alembic; QA-001, OPS-001 | Use canonical offline command. Keep replay diagnostics distinct from true historical validation. |
| D31 | [`docs/troubleshooting.md`](../troubleshooting.md) | How-to · developers, operators | Recover from setup and runtime failures | backend_service.py, workflow repository, role checks; OPS-001, API-001, SEC-001 | Correct synthetic fallback, authentication and restart advice. |
| D32 | [`infra/README.md`](https://github.com/afaq-ahmad/pakistan-flood-monitor/blob/77dc8b7fd1e545c4284de54afc11dc8760b64456/infra/README.md) | Reference · operators | Placeholder for deployment assets | Dockerfile and docker-compose.yml at root; OPS-001 | Point to current deployment instructions and record that the directory is a placeholder. |
| D33 | [`reports/evaluation/rules_v1.md`](https://github.com/afaq-ahmad/pakistan-flood-monitor/blob/77dc8b7fd1e545c4284de54afc11dc8760b64456/reports/evaluation/rules_v1.md) | Reference · researchers, QA | Historical rule-evaluation record | Evaluation artifacts and model registry contract; DATA-001, PK-011 | Keep evidence as historical. Thresholds and retraining triggers do not certify current performance. |

## Baseline link graph and latest revisions

Incoming links are links from tracked Markdown in this repository. Outgoing
local paths refer to the same IDs, including fragments where present. External
targets are listed separately and retain the baseline URLs. This graph is an
inventory of links as written, independent of live URL reachability or the
positions of links added by this workstream.

| ID | Last edited at baseline | Incoming local links | Outgoing local links | External targets |
|---|---|---|---|---|
| D01 | 2026-08-29 `8ac89a9` | — | — | — |
| D02 | 2026-11-18 `47b7781` | D12, D18 | `D06`, `D07`, `D15`, `D18` | — |
| D03 | 2026-05-05 `95ef3cc` | — | — | — |
| D04 | 2026-11-17 `d115316` | — | `D09`, `D10`, `D11`, `D12`, `D13`, `D14`, `D21`, `D29`, `D30`, `D31`, `LICENSE` | 1 |
| D05 | 2026-04-30 `a254cf1` | — | — | — |
| D06 | 2026-08-28 `26d800c` | D02, D08, D10, D18 | — | — |
| D07 | 2026-08-29 `d02acc8` | D02, D08 | — | — |
| D08 | 2026-08-29 `d02acc8` | D12, D18 | `D06`, `D07` | — |
| D09 | 2026-11-18 `80ee8aa` | D04, D19 | — | — |
| D10 | 2026-08-28 `26d800c` | D04 | `D06` | — |
| D11 | 2026-08-28 `26d800c` | D04 | — | — |
| D12 | 2026-08-29 `d02acc8` | D04 | `D02`, `D08`, `D18`, `D29` | — |
| D13 | 2026-08-28 `26d800c` | D04 | — | — |
| D14 | 2026-11-18 `dda09b3` | D04 | `D30` | — |
| D15 | 2026-11-18 `0e71b9c` | D02 | — | 3 |
| D16 | 2026-11-18 `eadb511` | — | `D17` | 10 |
| D17 | 2026-11-18 `ba221c0` | D16, D18, D19 | `D23#independent-qa-follow-up`, `D23`, `D24` | 2 |
| D18 | 2026-11-18 `eadb511` | D02, D12 | `D02`, `D06`, `D08`, `D17`, `D23`, `D24`, `D27` | 13 |
| D19 | 2026-11-18 `eadb511` | D20, D23, D24, D25, D27, D28 | `D09#analyst-review-workflow`, `D17`, `D23#independent-qa-follow-up`, `D23`, `D24#my-area-coverage-and-selection`, `D25`, `D27`, `D28` | 9 |
| D20 | 2026-11-18 `388ceaf` | — | `D19`, `D23` | — |
| D21 | 2026-08-28 `26d800c` | D04 | — | — |
| D22 | 2026-11-18 `fe40e36` | — | — | — |
| D23 | 2026-11-18 `388ceaf` | D17, D18, D19, D20, D24, D25 | `D19`, `D24` | 4 |
| D24 | 2026-11-18 `ecdbda3` | D17, D18, D19, D23, D25 | `D19`, `D23`, `D25` | 8 |
| D25 | 2026-11-18 `2c232c2` | D19, D24 | `D19`, `D23`, `D24`, `D26` | — |
| D26 | 2026-11-18 `47443d7` | D25 | — | 8 |
| D27 | 2026-11-18 `eadb511` | D18, D19, D28 | `D19` | — |
| D28 | 2026-11-18 `eadb511` | D19 | `D19`, `D27` | 2 |
| D29 | 2026-11-18 `8b2ba96` | D04, D12 | — | 1 |
| D30 | 2026-11-17 `d115316` | D04, D14 | — | — |
| D31 | 2026-05-05 `95ef3cc` | D04 | — | — |
| D32 | 2026-03-10 `0458037` | — | — | — |
| D33 | 2026-03-10 `3fc984f` | — | — | — |

### External targets at the baseline

- D04 · `https://urs.earthdata.nasa.gov/users/new`
- D15 · `https://developers.openai.com/cookbook/articles/codex_exec_plans`, `https://docs.github.com/en/get-started/using-github/github-flow`, `https://docs.github.com/en/pull-requests/reference/pull-requests`
- D16 · `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/83`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/85`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/86`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/87`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/88`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/89`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/92`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/93`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/94`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/95`
- D17 · `https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44252001189`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44253138615`
- D18 · `https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44254312814`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44256032041`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44266515268`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44267412433`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44274735400`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44276177058`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/68`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/69`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/71`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/72`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/93`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/94`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/95`
- D19 · `https://github.com/afaq-ahmad/pakistan-flood-monitor/commit/170a2608d8ac3effec415da1d432fd03816ad288`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/85`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/86`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/87`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/88`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/89`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/93`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/94`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/95`
- D23 · `https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44278515915`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44280556574`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/commit/170a2608d8ac3effec415da1d432fd03816ad288`, `https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/89`
- D24 · `https://ffd.pmd.gov.pk/`, `https://pdma.punjab.gov.pk/`, `https://www.dawn.com/news/1939265`, `https://www.dawn.com/news/1945551`, `https://www.fao.org/geospatial/news/news-detail/fao-releases-geospatial-flood-impact-assessment-for-pakistan--2025/en`, `https://www.fao.org/giews/countrybrief/country.jsp?code=PAK&lang=en`, `https://www.ifrc.org/emergency/pakistan-monsoon-floods-2025`, `https://www.worldbank.org/en/news/feature/2026/09/03/preparing-better-for-monsoons-lessons-from-the-2025-flash-floods-in-pakistan`
- D26 · `https://ffd.weather.gov.pk/flood-ews`, `https://pitb.gov.pk/pfdms`, `https://www.dawn.com/news/1939265/crisis-in-the-making-complaints-of-missing-facilities-emerge-from-punjabs-flood-hit-areas`, `https://www.dawn.com/news/1941317/residents-share-their-losses-during-ravi-flooding`, `https://www.dawn.com/news/1945132/punjab-floods-small-farmers-contractors-face-ruin`, `https://www.ifrc.org/emergency/pakistan-monsoon-floods-2025`, `https://www.ndma.gov.pk/sitreps?cat_id=3`, `https://www.worldbank.org/en/news/feature/2026/09/03/preparing-better-for-monsoons-lessons-from-the-2025-flash-floods-in-pakistan`
- D28 · `https://docs.streamlit.io/develop/concepts/multipage-apps/overview`, `https://www.w3.org/TR/WCAG22/`
- D29 · `https://urs.earthdata.nasa.gov/users/new`

## Discrepancies and resolution

| Area | Baseline statement | Evidence at `77dc8b7` | Resolution on this branch |
|---|---|---|---|
| Dashboard count and routing | README and development guide said 15 pages. Development said adding a file automatically registers a page. | `streamlit_app.py` registers Home and 18 files using `st.navigation`. PR #94 and public-page tests verify existing paths. | README and development describe the registered menu. The earlier progress report is labelled historical. |
| Architecture and actual entry points | The README and architecture diagrams foregrounded research helpers as a single backend and depicted in-memory or CSV storage as the runtime. | `Dockerfile`, Compose, package scripts and the dashboard adapter point to canonical FastAPI, CLI and workflow entry points. Research pages have their own helpers. | The architecture diagram traces public reads, standalone fixtures, workflow SQL and process-local review state. |
| Active monitoring and warnings | README marked corridors Active or Watch, and overview promised live maps and early warning. | `Settings.pilot_corridors` and `/public/corridors` expose six configured references. Outside test, no current observation/run is attached. Public checks return eligible events or an empty feed. | Describe a pilot catalogue and situational-awareness prototype. Explain that an empty feed gives no evidence of safety. |
| Forecasting and ML | Overview and old milestone report described a running early-warning system, ready SAR and live forecast capabilities. | PR #91 gates forecast and dam outputs outside standalone demo/test. Forecast weights are untrained, SAR is simulated, dam extent is a proxy, and replay tests use scenario data. | Overview and testing separate research from operational evidence. Historical progress claims remain visible with a cutoff notice. |
| Canonical and legacy code | Older structure showed a canonical `core/` tree and prescribed direct extension from Streamlit. | ADR-001, package scripts, `src/app` and `src/pakistan_flood_monitor` identify separate runtimes. The canonical runner has its own workflow. | Link to the accepted ADR and state what extension path the project supports. |
| Persistence and migrations | API and deployment implied all run state is in memory. Troubleshooting said PostgreSQL was future work. | Root Alembic head `b4d9d93f2a10`, workflow repository, Compose PostGIS service and a separate-process `run-status` prove distinct storage layers. Role-protected snapshots cover process-local state explicitly. | Deployment and API separate durable runs/tasks, in-memory product state, and root versus legacy migrations. Docker/PostGIS execution remains unverified. |
| Python versions | Setup and contribution guides allowed 3.10. Package metadata does too. | `datetime.UTC` imports require 3.11 or later. Docker declares 3.11, CI declares 3.12, and Python 3.12.14 passed 353 tests locally. [Python 3.11 change notes](https://docs.python.org/3.11/whatsnew/3.11.html#datetime). | Recommend 3.12 and document the actual import floor. Verify 3.11 and adjust metadata in a separately reviewed task. |
| API routes and roles | API called corridor events active, JSON metrics Prometheus-compatible and threshold registration a weight update. Data contracts allowed approved rows. | `api/main.py` and OpenAPI distinguish eligible publication, route roles, JSON/text metrics and threshold registry records. Local checks returned 401 and 403 at the relevant boundaries. | Correct endpoint descriptions and public risk-summary eligibility. Explain 503 for guarded raw products outside test mode. |
| Recent delivery | Ledger described #92–95 as draft or in-review checkpoints. | Main merge history through #95 and offline tests verify the preparation, navigation, practice and available-data boundaries. | Add a verified current snapshot. Keep the earlier dated checkpoint wording and PR records. |
| Milestones and older diagnostics | Progress report called the 15-page dashboard complete. Existing QA rows include early failures. | Current code, tests and dated handoffs show later fixes and remaining browser/scientific gaps. | Keep the historical report and QA history, with a current entry point and clear dated evidence. |
| Task authority | Remaining Work duplicated pending tasks and described the old receipt as implemented. Product specs included status labels. | PR #92 removed the unbacked receipt. The master plan owns live state. The roadmap owns requirements. | Preserve the #92 evidence and direct remaining work to the master plan. Label roadmap statuses as planning context. |
| Setup, credentials and deployment | README, setup and deployment repeated scripts with mismatched extras and `.env.local` or `DATABASE_DSN`. Setup called Earthdata required. | `pyproject.toml`, `config.py`, `backend_service.py`, root Alembic and Compose specify the actual requirements. Demo and the offline suite run without provider credentials. | Setup owns installation. Config owns process and dotenv precedence. Deployment covers Compose and migrations. Test and troubleshooting pages link to those authorities. |
