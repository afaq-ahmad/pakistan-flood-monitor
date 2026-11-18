# Functionality gap audit

Baseline: `main` at `339ad5de0951260a52f9ea3505c42962cec1a109`, reviewed 2026-11-18.
The GitHub connector returned no open issues or pull requests. PR #84 is merged and is the starting
point. This report follows ADR-001 and claims the public-data and export slice of UI-001.

## Highest-value confirmed gaps

| Priority | Task | Evidence at baseline | Acceptance and disposition |
|---|---|---|---|
| P0 | P0-001, UI-001 | `get_events()` still returns CSV with no API, even in operational mode. Home uses that feed with no watermark. Public warns about the missing API but continues rendering; its map and district filter use all rows, cards accept approved/active, and exposures can include unpublished events. Public also reads the feed multiple times and treats unknown freshness as success. | In this PR. Use one published-event snapshot for the public screen and filter exposure to that snapshot. Fail closed with no API unless explicitly in demo/test. Distinguish an API outage from an empty feed. Mark local demo and avoid using local run logs as API freshness. |
| P1 | UI-001 | The standalone FastAPI/HTML prototype serves the mock feed in operational mode and advertises a live map and active system. | In this PR. Gate the entry point and event route to demo/test and label the page and feed. |
| P1 | UI-001, OPS-001 | After installing `.[dev,dashboard]`, the Public Dashboard raises `ModuleNotFoundError: folium`. Compose uses the same extra. Forecast imports Plotly unconditionally. Offline CI installs only `.[dev]`. | In this PR. Declare UI imports and run offline Streamlit page tests in CI. |
| P1 | UI-001 | Export Center accepts API-backed events and emits prototype assets. COG and GeoParquet are text with misleading extensions; validation always says valid; the manifest claims API provenance for local demo data. No download control is offered. | In this PR. Offer downloadable, labelled GeoJSON points and manifest for local demo fixtures only. Return explicit unavailability for API-backed exports and unimplemented formats. |
| P1 | UI-001, P1-003 | The analyst queue reads the public endpoint; consequently no drafts reach it. Review buttons have a real canonical handler, but the UI cannot discover candidates in API mode. Partner sharing is independently composed from the sparse public feed. | Follow-up. Specify an authenticated, paginated review queue and review identity. Define separate reviewed-product and sharing contracts before wiring either. |
| P1 | P1-001, P1-002 | Tasks are durable and claims atomic. A crashed worker can leave work stranded, and the API keeps mutable review, report, registry and audit state in memory. Persisted runs and a state snapshot round-trip cover only part of the restart story. | Follow-up. Decide ownership/fencing and side-effect semantics before recovery. Choose transactional persistence and identity/rollback contracts before moving review state. |
| P1 | DATA-001, GIS-001 | Canonical operational runs fail closed when required data and derived products are unavailable. The legacy and dashboard implementations cover different subsets, several via proxies or simulated sources. | Follow-up. Migrate validated source adapters in vertical slices. Establish independent reference data and product-specific freshness/quality rules before claiming coverage. |

## End-to-end functionality matrix

**Verification** indicates what the baseline evidence establishes. **Executed** means locally
reproduced in the audited entry point. **Traced** means code, configuration and callers were checked.
**Fixture** means offline coverage exists. Individual provider and deployment checks remain open.

| Feature and entry point | Implementation and dependencies | Expected output | Actual behavior at baseline | Verification |
|---|---|---|---|---|
| Streamlit home, `streamlit_app.py` | `DataService.summary_stats`, events feed, local run CSV | Public summary with source and availability | Unlabelled local fixtures in no-API operational and demo modes; drafts included in summary; run freshness from CSV | Executed under operational mode; showed 99,900 fixture population |
| Public area search, map, event cards and exposure, page 1 | `DataService`, CSV or `/public/events`, Folium, bundled corridors | One coherent published snapshot and meaningful states | Clean install fails import. Multiple fetches, inconsistent status filters, and demo exposure detached from published event selection. Unknown freshness reads as active. API sends only a subset of the fields the mapper expects. | Executed dependency failure; fixture and call-site trace |
| Analyst review, page 2 | Published feed, CSV audit and `POST /internal/admin/review-event` | Discover and review drafts; reflect authenticated transitions and audit | API mode has no draft queue. Local CSV actions cover demo; writes to API only with provided token and valid transition. No audit consumer for the API queue. | Traced, fixture |
| Field reports, page 3 | Local reports CSV; canonical ingest/moderate endpoints separate | Authenticated report inbox, moderation and status | Page mutates local files and never calls canonical submission/moderation; success handling is partial. API moderation operates on process-local state. | Traced, API fixture |
| Partner mode, page 4 | Public/CSV events, advisory text and expandable SitRep sections | Source-attributed approved brief and real export | Local advisory text downloadable; reviewed-product sharing absent; PDF preview is text; local contacts/actions are static. | Traced |
| GIS exports, page 5 | Dashboard `generate_export`; separate legacy export library | Valid labelled files with truthful manifest and download | GeoJSON demo point; raster/Parquet are plain text; validation flags hardcoded; no download button. Legacy export tests cover a different implementation. | Traced, fixture |
| ML training, page 6 | Registry CSV, fixed benchmark values and legacy CLI scripts | Actual registry, training state, drift and benchmarks | Controls display fixed text/commands and do not run jobs; model registry is disconnected from API registrations. | Traced |
| Operations, page 7 | Local pipeline/notification CSV, static checklist and diagnostics | Live run state and actionable controls | Trigger/backup buttons print instructions and can report actions that never ran. Health and readiness tables are static. | Traced |
| Settings, page 8 | Local YAML and illustrative controls | Read-only material where appropriate, effective config on save | Credential/environment buttons explain non-persistence; threshold/weight writes hit YAML separate from canonical settings and API registration. | Traced |
| Satellite viewer, page 9 | STAC client and Folium, credential/provider dependent | Traceable scene catalogue and failure/empty feedback | Direct discovery UI, separate from canonical daily ingestion. A successful catalogue search alone provides no flood measurement. | Traced; offline AppTest caught an initial STAC connection error |
| NASA hydromet, page 10 | `nasa_service.py`, Earthdata credentials, POWER/HLS/IMERG UI | Observations, scenes and IMERG product data with lineage | Opens with direct provider requests. Interactive fetches are separate from workflow. IMERG lists products without a canonical precipitation processor. | Traced; offline AppTest caught the initial provider errors |
| Optical water detection, page 11 | `satellite_ml_service.py`, cached thumbnails, image processing | Georeferenced masked water extent using proper bands | Thumbnail/RGB preview proxy; separate from canonical segmentation, and no validated metric product from the UI. | Traced; live/scientific validation pending |
| Historical map, page 12 | Bundled JSON, Folium | Dated historical extents with evidence | Static approximate regions presented as training targets. The page does not establish verified extent labels. | Traced |
| Forecasting, page 13 | Open-Meteo, forecast service, Plotly and optional ML dependencies | Reproducible forecast with skill and uncertainty | Forecast service import can fail without optional packages; LSTM untrained; prototype is disconnected from operational workflow. | Traced, separate probabilistic forecast fixture |
| Advanced SAR/HAND/ML, page 14 | Advanced ML service, optional model and terrain dependencies | Calibrated SAR extent and aligned terrain features | Simulation and architecture placeholders reachable from prototype UI; no validated operational product. | Traced |
| Dam flood risk, page 15 | Reservoir thumbnails, local fill histories and derived scoring | Traceable observed dam levels and risk | Pixel-derived estimated surface proxy, no calibrated storage/release measurement; diagnostic backtest uses fixtures. | Traced, fixture |
| Official information, page 16 | Curated source registry | Attributed official links | Static FFD/NDMA directory; no ingestion, availability monitoring or warning relay. | Traced, fixture; current links not revalidated |
| Standalone dashboard, `dashboard_app.py`, `dashboard/` | FastAPI wrapper, mock CSV, Leaflet/CDNs | Clearly labelled standalone prototype | Separate mock endpoint hardwired regardless of mode; overview has data, other views/search incomplete. | Traced |
| Public API, `/public/events*`, corridors, alerts, risk and history | Public event gate, run/event stores, lineage | Published-only traceable products | Published-only gates work in fixtures; collection omits fields the dashboard expects; event creation uses a fixed draft polygon before review. Several raw-run/mobile endpoints deliberately 503 outside tests. | Traced, fixture |
| Internal API, review/reports/audit/metrics/SitRep/state/registry | Role tokens, in-memory stores, persisted run/audit support | Authenticated actions, honest metrics and persistent histories | Routes cover actions; dashboard consumes only review write. Metrics contain default values and readiness is process liveness; PDF exists separately from partner UI. | Traced, fixture |
| Daily run, CLI and `/internal/run` | Canonical workflow engine, SQLAlchemy, manifest/config and adapters | Durable results with explicit retry/failure state | Demo runs persist. Operational gaps yield unavailable; CLI returns success for some terminal non-success executions without a raised integrity error. No cancellation or fenced crash recovery. | Traced, fixture |
| Scheduling and legacy jobs, `workers.py`, `scripts/*_job.py` | CLI/legacy adapters, optional Prefect and ingestion services | Actual scheduled executions with monitored failures | Compose/CI define no scheduler. Legacy wrappers and sample providers do not establish an operational worker deployment. | Traced |
| Notification delivery | Notification dispatcher and stub providers, CSV operations view | Authorized delivery with retry and durable history | Channel classes are stubs; no verified runtime sender or dashboard/API reconciliation. | Traced, fixture |
| GIS, exposure, candidate scoring and backtesting | Canonical helpers plus legacy preprocessing/overlay and benchmarks | Aligned, validated quantitative products | Metric helper and fixture coverage exist; real data alignment, warning skill, and end-to-end QA are unresolved. | Traced, fixture |
| Docker, DB, CI and external deployment | Docker/Compose, root SQLite/PG migration chain, separate legacy chain | Installable dashboard, migration, readiness and parity | Dashboard extra incomplete, CI lacks dashboard smoke and PostgreSQL, Compose defaults to demo with no migration service or worker, and legacy DB history differs. The package declares Python 3.10 although the canonical workflow imports `datetime.UTC`, which requires 3.11. | Executed local dependency failure, traced; Docker/PostgreSQL/deployment pending |

## Decisions needed

- **Live dashboard contract.** Keep the existing public event collection and add a versioned
  reviewed summary, or make the dashboard combine published event, confidence and exposure endpoints.
  Decide field semantics, source of freshness and meaningful unknown states before adding live totals.
- **Analyst and field-report identity.** Provide authenticated API list endpoints behind
  per-user authorization, or use a separate protected analyst deployment with explicit principal
  and persistence contracts. Define permitted roles and community reporter privacy first.
- **Scheduled runs and recovery.** Evaluate an external scheduler with durable leases versus a
  supervised queue worker. Require restart, duplicate-run, stale-owner and retry-limit evidence.
- **Real export products.** Specify the eligible reviewed event identity, authoritative geometry,
  CRS, validation and expiration before wiring legacy export code into the canonical API.
- Additional hazards, new providers, relief directories and expanded translations are product
  backlog items. They are outside the confirmed behavior fixes above.

## Changes in PR #85

- The Streamlit home and public dashboard consume one published event snapshot each. The map,
  district filter, event list and exposure use that snapshot. A missing API in operational mode
  suppresses local events and local review writes. An empty response and an outage get distinct
  messages. The API-backed view shows unavailable freshness and skips markers without a position.
- The dashboard extra provides Folium, Streamlit-Folium and Plotly. The public map uses
  the OpenStreetMap basemap option so local startup does not require Carto credentials.
- The standalone prototype's page and feed require demo/test mode. The page and API label
  fixtures as simulated. Its search and other incomplete views remain tracked as follow-up work.
- The Export Center downloads a GeoJSON point and manifest from local demo fixtures. Both carry
  the simulation label and the manifest identifies the fixture dataset. The app reports
  unavailability for API-backed assets, COG and GeoParquet. There are no schema changes.

## Verification and handoff

| Check | Result |
|---|---|
| `APP_MODE=test .venv/bin/python -m pytest --disable-socket --allow-unix-socket tests/ -q --tb=short` | Baseline 228 passed, 475 warnings. Branch 245 passed, 475 warnings. |
| Streamlit focused page and backend tests | 31 passed for public scenarios, 23 passed for export and prior P0-003 coverage. Three standalone boundary tests passed. |
| Standalone AppTest processes, `APP_MODE=operational`, no API URL | The baseline home showed 99,900 fixture population and three pending reviews. The fixed home showed an unavailable message and no metrics. |
| Offline Streamlit initial render after dependency install | All 16 pages started without uncaught exceptions. Satellite Viewer and NASA Hydromet displayed connection errors with external sockets disabled. No provider actions were exercised. |
| `alembic upgrade head` → `alembic downgrade base` → `alembic upgrade head` on a fresh SQLite DB | Passed. Head `b4d9d93f2a10`. |
| Canonical and dashboard Python compile, workflow YAML parse, `git diff --check`, `git diff --exit-code -- storage data` | Passed. |
| Chromium screenshots and browser downloads | The environment blocked Chromium at local socket creation. AppTest verified the controls and inspected the exact generated files. Browser download transfer and accessibility remain unverified. |
| Hosted GitHub Actions | The branch implementation checkpoint and the current main baseline both reported failure with zero jobs, so no hosted test job result was available. [Branch run](https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44253138615) · [Main baseline](https://github.com/afaq-ahmad/pakistan-flood-monitor/actions/runs/44252001189) |

Docker, PostgreSQL, live providers, scientific acceptance and mobile/assistive browser checks
remain open. The next UI-001 step is to specify an authenticated analyst queue and test listing,
transition feedback and audit together against the canonical API. The implementation ledger and
session log record the scope and restart point.

## Analyst queue continuation

After PR #85 merged, PR #86 addressed the disconnected analyst list in UI-001. API mode now
reads a private queue for draft, review, and approved candidates. Role checks, bounded
pagination, and the minimized projection protect the response. The viewer accepts a supplied
session credential, distinguishes an empty queue from a credential or API failure, and avoids
the local audit CSV. The API, per-session auth, and Streamlit boundary were verified offline.

Review decisions still depend on the existing canonical API. The queue covers the current API
process and may be incomplete after restart. P1-002 tracks a transactional review and audit
contract before exposing live transitions in the dashboard. This slice adds no product
publication, scientific inputs, or validated warning capabilities.
