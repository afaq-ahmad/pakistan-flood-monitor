# Functionality gap audit

Baseline: `main` at `339ad5de0951260a52f9ea3505c42962cec1a109`, reviewed 2026-11-18.
The GitHub connector returned no open issues or pull requests. PR #84 is merged and is the starting
point. This report follows ADR-001 and claims the public-data and export slice of UI-001.

## Highest-value confirmed gaps

| Priority | Task | Evidence at baseline | Acceptance and disposition |
|---|---|---|---|
| P0 | P0-001, UI-001 | `get_events()` still returns CSV with no API, even in operational mode. Home uses that feed with no watermark. Public warns about the missing API but continues rendering; its map and district filter use all rows, cards accept approved/active, and exposures can include unpublished events. Public also reads the feed multiple times and treats unknown freshness as success. | In this PR. Use one published-event snapshot for the public screen and filter exposure to that snapshot. Fail closed with no API unless explicitly in demo/test. Distinguish an API outage from an empty feed. Mark local demo and avoid using local run logs as API freshness. |
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
| Streamlit home, `streamlit_app.py` | `DataService.summary_stats`, events feed, local run CSV | Public summary with source and availability | Unlabelled local fixtures in no-API operational and demo modes; drafts included in summary; run freshness from CSV | Executed (AppTest home), traced configuration |
| Public area search, map, event cards and exposure, page 1 | `DataService`, CSV or `/public/events`, Folium, bundled corridors | One coherent published snapshot and meaningful states | Clean install fails import. Multiple fetches, inconsistent status filters, and demo exposure detached from published event selection. Unknown freshness reads as active. API sends only a subset of the fields the mapper expects. | Executed dependency failure; fixture and call-site trace |
| Analyst review, page 2 | Published feed, CSV audit and `POST /internal/admin/review-event` | Discover and review drafts; reflect authenticated transitions and audit | API mode has no draft queue. Local CSV actions cover demo; writes to API only with provided token and valid transition. No audit consumer for the API queue. | Traced, fixture |
| Field reports, page 3 | Local reports CSV; canonical ingest/moderate endpoints separate | Authenticated report inbox, moderation and status | Page mutates local files and never calls canonical submission/moderation; success handling is partial. API moderation operates on process-local state. | Traced, API fixture |
| Partner mode, page 4 | Public/CSV events, advisory text and expandable SitRep sections | Source-attributed approved brief and real export | Local advisory text downloadable; reviewed-product sharing absent; PDF preview is text; local contacts/actions are static. | Traced |
| GIS exports, page 5 | Dashboard `generate_export`; separate legacy export library | Valid labelled files with truthful manifest and download | GeoJSON demo point; raster/Parquet are plain text; validation flags hardcoded; no download button. Legacy export tests cover a different implementation. | Traced, fixture |
| ML training, page 6 | Registry CSV, fixed benchmark values and legacy CLI scripts | Actual registry, training state, drift and benchmarks | Controls display fixed text/commands and do not run jobs; model registry is disconnected from API registrations. | Traced |
| Operations, page 7 | Local pipeline/notification CSV, static checklist and diagnostics | Live run state and actionable controls | Trigger/backup buttons print instructions and can report actions that never ran. Health and readiness tables are static. | Traced |
| Settings, page 8 | Local YAML and illustrative controls | Read-only material where appropriate, effective config on save | Credential/environment buttons explain non-persistence; threshold/weight writes hit YAML separate from canonical settings and API registration. | Traced |
| Satellite viewer, page 9 | STAC client and Folium, credential/provider dependent | Traceable scene catalogue and failure/empty feedback | Direct discovery UI, separate from canonical daily ingestion. A successful catalogue search alone provides no flood measurement. | Traced; live provider pending |
| NASA hydromet, page 10 | `nasa_service.py`, Earthdata credentials, POWER/HLS/IMERG UI | Observations, scenes and IMERG product data with lineage | Interactive fetch buttons are separate from workflow. IMERG lists products, with no canonical precipitation processor wired. | Traced; live provider pending |
| Optical water detection, page 11 | `satellite_ml_service.py`, cached thumbnails, image processing | Georeferenced masked water extent using proper bands | Thumbnail/RGB preview proxy; separate from canonical segmentation, and no validated metric product from the UI. | Traced; live/scientific validation pending |
| Historical map, page 12 | Bundled JSON, Folium | Dated historical extents with evidence | Static approximate regions presented as training targets. The page does not establish verified extent labels. | Traced |
| Forecasting, page 13 | Open-Meteo, forecast service, Plotly and optional ML dependencies | Reproducible forecast with skill and uncertainty | Forecast service import can fail without optional packages; LSTM untrained; prototype is disconnected from operational workflow. | Traced, separate probabilistic forecast fixture |
| Advanced SAR/HAND/ML, page 14 | Advanced ML service, optional model and terrain dependencies | Calibrated SAR extent and aligned terrain features | Simulation and architecture placeholders reachable from prototype UI; no validated operational product. | Traced |
| Dam flood risk, page 15 | Reservoir thumbnails, local fill histories and derived scoring | Traceable observed dam levels and risk | Pixel-derived estimated surface proxy, no calibrated storage/release measurement; diagnostic backtest uses fixtures. | Traced, fixture |
| Official information, page 16 | Curated source registry | Attributed official links | Static FFD/NDMA directory; no ingestion, availability monitoring or warning relay. | Traced, fixture; current links not revalidated |
| Standalone dashboard, `dashboard_app.py`, `dashboard/` | FastAPI wrapper, mock CSV, Leaflet/CDNs | Clearly labelled standalone prototype | Separate mock endpoint hardwired regardless of mode; overview has data, other views/search incomplete. | Traced |
| Public API, `/public/events*`, corridors, alerts, risk and history | Public event gate, run/event stores, lineage | Published-only traceable products | Published-only gates work in fixtures; collection omits fields the dashboard expects; several raw-run/mobile endpoints deliberately 503 outside tests. | Traced, fixture |
| Internal API, review/reports/audit/metrics/SitRep/state/registry | Role tokens, in-memory stores, persisted run/audit support | Authenticated actions, honest metrics and persistent histories | Routes cover actions; dashboard consumes only review write. Metrics contain default values and readiness is process liveness; PDF exists separately from partner UI. | Traced, fixture |
| Daily run, CLI and `/internal/run` | Canonical workflow engine, SQLAlchemy, manifest/config and adapters | Durable results with explicit retry/failure state | Demo runs persist. Operational gaps yield unavailable; CLI returns success for some terminal non-success executions without a raised integrity error. No cancellation or fenced crash recovery. | Traced, fixture |
| Scheduling and legacy jobs, `workers.py`, `scripts/*_job.py` | CLI/legacy adapters, optional Prefect and ingestion services | Actual scheduled executions with monitored failures | Compose/CI define no scheduler. Legacy wrappers and sample providers do not establish an operational worker deployment. | Traced |
| Notification delivery | Notification dispatcher and stub providers, CSV operations view | Authorized delivery with retry and durable history | Channel classes are stubs; no verified runtime sender or dashboard/API reconciliation. | Traced, fixture |
| GIS, exposure, candidate scoring and backtesting | Canonical helpers plus legacy preprocessing/overlay and benchmarks | Aligned, validated quantitative products | Metric helper and fixture coverage exist; real data alignment, warning skill, and end-to-end QA are unresolved. | Traced, fixture |
| Docker, DB, CI and external deployment | Docker/Compose, root SQLite/PG migration chain, separate legacy chain | Installable dashboard, migration, readiness and parity | Dashboard extra incomplete, CI lacks dashboard smoke and PostgreSQL, Compose defaults to demo with no migration service or worker, and legacy DB history differs. | Executed local dependency failure, traced; Docker/PostgreSQL/deployment pending |

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

## Verification and handoff

Start with offline CI parity at the baseline, then exercise the actual Streamlit entry points with
local temporary data and stubbed HTTP responses. Apply a SQLite migration round-trip and compile
checks. Docker, PostgreSQL, live environmental feeds, mobile/assistive browser checks and scientific
acceptance need separate evidence. See the implementation ledger and session log for results.
