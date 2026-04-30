# Repository Mapping and Claim Verification (2026-04-30)

Active roles:
- Lead role: Engineering Lead / Principal Architect
- Supporting roles: Backend Engineer, Technical Writer, QA Lead, DevOps Engineer
- Why these roles are needed: This review verifies what exists in code versus documentation and identifies production-like versus prototype behavior.

## Repository Map

### Main directories and important files
- `README.md` (project overview, runtime stack claims, setup commands).
- `docs/` (architecture, runtime contract, release readiness/checklist/runbooks, dashboard lineage docs).
- `src/pakistan_flood_monitor/` (canonical runtime package: API, pipeline runner, core detection/exposure primitives, services).
- `src/app/` (prototype/dashboard-oriented stack: API routers, services, DB models/migrations, workers).
- `tests/` (API behavior, workflows, scoring, ingestion, QA/security contracts, storage checks).
- `scripts/` (daily run, ingestion/discovery, baseline/corridor asset build, training stub scripts).
- `config/thresholds/` and `configs/` (threshold YAMLs + training/alert config).
- `data_contracts/README.md` (contract direction but limited executable enforcement).
- `infra/README.md` (infrastructure intent, no substantial IaC manifests found).
- `pyproject.toml` (single Python package metadata and deps).
- `.env.local`, `.env.staging`, `.env.prod` (environment variable templates).

### Canonical production-like modules (present)
- Canonical API entrypoint: `src/pakistan_flood_monitor/api/main.py`.
- Canonical orchestration entrypoint: `src/pakistan_flood_monitor/pipeline/runner.py`.
- Canonical detection/exposure logic: `src/pakistan_flood_monitor/core/detection.py`, `core/exposure.py`.
- Canonical alert/gate helpers: `src/pakistan_flood_monitor/services/alerts.py`, `services/gis_qa.py`, `services/triggers.py`.

### Prototype/demo/stub modules (present)
- Non-canonical API: `src/app/api/main.py` with prototype routers.
- Dashboard service with seeded events: `src/app/services/dashboard.py`.
- Runner uses synthetic feature literals in daily flow: `src/pakistan_flood_monitor/pipeline/runner.py`.
- Training script is framed as reproducibility stub: `scripts/train_candidate_ranker.py` and README wording.

### Duplicate or conflicting areas
1. **Two API stacks**:
   - Canonical runtime: `pakistan_flood_monitor.api.main`.
   - Prototype stack: `app.api.main`.
   - Risk: deployment ambiguity and inconsistent behavior/contracts.
2. **Dual config roots**:
   - `config/thresholds/` and `configs/` both exist with related threshold/training semantics.
   - Risk: operator confusion around authoritative config source.
3. **DB presence mismatch**:
   - SQLAlchemy/Alembic exist under `src/app/db/*`, while canonical runtime API primarily uses in-memory stores.

### Missing expected components (not verified in repo)
- Dockerfiles / Compose manifests.
- CI workflow files (e.g., `.github/workflows/*`).
- Formal IaC (Terraform/Pulumi/Helm) beyond infra README placeholder.
- Strong auth provider integration (OIDC/JWT issuer validation) for privileged actions.
- End-to-end STAC/COG/GeoParquet publication contracts with automated compliance checks.

## Claim Verification Matrix

| Claim | Source File | Status | Evidence | Risk | Recommended Fix | Owner Role | Owner Squad |
|---|---|---|---|---|---|---|---|
| Repo has canonical runtime API with internal/public split | `README.md`, `src/pakistan_flood_monitor/api/main.py` | implemented | Canonical app and `/internal` + `/public` routers exist | Low | Keep canonical route; add `/v1` versioning plan | Backend Engineer | Core Platform & APIs |
| Project has two API stacks by design | `README.md`, `src/app/api/main.py`, `src/pakistan_flood_monitor/api/main.py` | implemented | Both entrypoints exist and are separately runnable | High | Deprecate prototype API for release; enforce single runtime target | Engineering Lead | Core Platform & APIs |
| Persistent operational event/review state exists in canonical runtime | `src/pakistan_flood_monitor/api/main.py` | partial | Canonical API stores run/event/audit registries in module globals | Critical | Migrate run/event/review/audit to PostGIS repositories and transactions | Database/PostGIS Engineer | Core Platform & APIs |
| Dashboard/map outputs are sourced from authoritative reviewed events | `src/app/services/dashboard.py` | hardcoded | `DashboardService` seeds static `_events` in constructor | High | Replace seeded events with DB-backed reviewed event queries + freshness metadata | Frontend Engineer | Public Dashboard & Mobile UX |
| Actor identity in privileged actions is strongly bound to authenticated principal | `src/pakistan_flood_monitor/api/main.py`, `tests/test_api_implementation.py` | partial | Payloads include client-supplied `actor`; tests post explicit actor strings | High | Derive actor from token claims; ignore/forbid client actor field for privileged endpoints | Application Security Engineer | Reliability, Security & Release |
| Daily monitoring pipeline ingests real dynamic feature signals in detection | `src/pakistan_flood_monitor/pipeline/runner.py` | hardcoded | `DetectionFeatures` literals (e.g., fixed SAR/rainfall values) used in run flow | High | Wire scene/hydromet-derived features from ingestion outputs with provenance | EO Pipeline Engineer | Flood Detection & Remote Sensing |
| Historical event dashboard outputs represent real historical catalog | `src/pakistan_flood_monitor/pipeline/runner.py` | hardcoded | Fixed `HistoricalEventRecord` (`hist-{aoi}-2022`) emitted by runner | Medium | Back historical outputs with attributed datasets and versioned source lineage | Data Architect | Exposure & Impact Intelligence |
| DB schema and migrations are available | `src/app/db/alembic/versions/*`, `src/app/models/core.py` | implemented | Alembic revisions and ORM models exist | Medium | Connect canonical runtime to these models/repos and add migration gates in release checklist | DevOps Engineer | Reliability, Security & Release |
| Testing is broad across API/workflow/security contracts | `tests/` | implemented | Multiple suites for API, orchestration, ingestion, review, security-contract-style checks | Medium | Add restart durability, multi-instance consistency, and auth-abuse negative tests | QA Lead | Reliability, Security & Release |
| Containerized deployment instructions are available in repo | repo root/file scan | documented but missing | No Dockerfile/Compose found despite deployment-oriented docs | Medium | Add Dockerfile + compose + reproducible runtime images | DevOps Engineer | Reliability, Security & Release |
| CI automation pipelines are present | repo root/file scan | documented but missing | No CI workflow files detected | High | Add CI for lint/test/security scan/migration dry-run | DevOps Engineer | Reliability, Security & Release |
| Infrastructure-as-code is present for environments | `infra/README.md` and infra scan | unclear | Infra README present; concrete IaC manifests not verified | Medium | Add minimal IaC baseline for dev/staging/prod | Cloud Infrastructure Lead | Reliability, Security & Release |

