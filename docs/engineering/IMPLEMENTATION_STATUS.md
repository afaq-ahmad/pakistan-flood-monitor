# Implementation status

Last verified: **2026-08-29**, against `main` at `cc109c6`; the focused
`feat/metric-gis-contracts` workstream is not yet merged. Read this file with root
[`AGENTS.md`](../../AGENTS.md) and applicable [ADRs](../adr/README.md) before every task. Verify stale
claims against code and Git history; update this ledger in each consolidated-prompt PR.

## Current contract

| Item | Repository state |
|---|---|
| Canonical package | `src/pakistan_flood_monitor/` |
| Supported API runtime | `pakistan_flood_monitor.api.main:app` |
| Legacy migration source | `src/app/`; deprecated API entrypoint warns of removal after 2026-12-31 |
| Runtime modes | `test`, `demo`, `operational` via `APP_MODE`; default is `demo`; mode is persisted in canonical run metadata |
| Accepted ADRs | [ADR-001: canonical runtime and operational data integrity](../adr/ADR-001-canonical-runtime.md) |
| Package version | `0.1.0` in `pyproject.toml` |
| Canonical DB migration head | Root Alembic chain: `b4d9d93f2a10` (durable canonical pipeline tasks) |
| Legacy DB migration head | `src/app/db/alembic`: `0005_add_lineage_metadata_to_provenance` |
| CI | No workflow exists under `.github/workflows/` |

The two Alembic histories are not reconciled. The root chain imports canonical package metadata; the
legacy chain belongs to `src/app`. A later migration task must not create another chain or silently
choose between them.

## Consolidated prompt ledger

`COMPLETE` means merged acceptance evidence exists; it does not by itself mean production maturity.

| Prompt | State | Evidence / scope |
|---|---|---|
| 00 | COMPLETE | Repository operating contract merged in [PR #69](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/69); ledger and ADR policy added by the current Prompt 00 follow-up PR |
| 01 | COMPLETE | [PR #68](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/68) merged the first observation-state contract and [PR #71](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/71) merged canonical API/CLI/worker wiring, explicit demo-only helpers, typed availability, publication eligibility, and durable run/task persistence. |
| 02 | IN_PROGRESS | `feat/metric-gis-contracts` adds the canonical geodesic/local-projection measurement helpers, compact product provenance/quality/freshness/asset contracts, and targeted legacy migration-source call-site corrections. No migration is required: the canonical persistence boundary already stores composed metadata in JSON. |
| 03 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 04 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 05 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 06 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 07 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 08 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 09 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 10 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 11 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 12 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 13 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 14 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
| 15 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |

## Current limitations and deprecated work

- Operational execution fails closed because real required IMERG, GloFAS, optical, floodplain,
  flood-extent, and exposure-overlay processors are not all implemented. This structured unavailable
  response is a safety behavior, not an operational capability.
- Advanced SAR remains simulated, optical water detection uses RGB proxies, forecast LSTM weights are
  untrained, and dam surface extent is only a fill proxy. None is validated for warning authority.
- The canonical runner and API no longer import `app.*`; `src/app` remains a deprecated compatibility
  source for prototype routes, analyst tooling, and workflow shims. Its separate Alembic history is
  still unreconciled and must not receive new canonical runtime features.
- Canonical pipeline runs and dependency-aware tasks now persist with signature-based idempotency and
  retry counts. Event, review, audit, and dashboard state remain partly in memory; full restart-safe
  API-state migration is still outstanding.
- Availability now represents `AVAILABLE`, `NO_DATA`, `UNAVAILABLE`, `DEGRADED`, `STALE`, and
  `PARTIAL` with a reason code, evaluation time, and optional freshness rule. Real source adapters
  must populate these fields rather than relying on default values.
- Code, routes, dashboards, or tests existing in the tree do not establish operational readiness.

## Known P0/P1 defects

Severity reflects current evidence, not an exhaustive safety assessment.

| Priority | Defect / risk | Evidence and disposition |
|---|---|---|
| P0 | None formally triaged | Do not interpret this as evidence of operational safety or readiness |
| P1 | Repository test baseline is red | 24 failures: shared rate-limit/test state, lifecycle/resilience contract mismatches, and database datetime JSON serialization |
| P1 | CI and reproducible test environment are absent | No workflow is configured. `pytest` is now declared in the `dev` extra, but the full baseline has not been rerun from a fresh environment on this branch |
| P1 | Runtime and migration split-brain remains | Canonical and legacy packages plus two independent Alembic histories require incremental reconciliation |
| P1 | Canonical durable task migration must be applied before operational use | Root Alembic head is `b4d9d93f2a10`; demo/test may initialize local tables, but operational deployments must use Alembic |

## Test and validation status

Baseline verified before this documentation change:

- `python -m pytest tests/ -q --tb=short` — **blocked** in the base environment: `No module named pytest`.
- After `uv sync --all-extras` and locally adding `pytest`: `.venv/bin/python -m pytest tests/ -q
  --tb=short` — **136 passed, 24 failed, 569 warnings**.
- Prompt 00 focused contract and local-link validation: `.venv/bin/python -m pytest
  tests/test_agent_operating_contract.py -q` — **4 passed**.
- Prompt 00 post-change full run: `.venv/bin/python -m pytest tests/ -q --tb=no` — **138 passed,
  24 failed, 569 warnings**; the same 24 pre-existing failure set remains.
- No repository documentation-lint command or CI workflow is configured.

Focused checks on the unmerged canonical-runtime workstream:

- `python -m compileall -q src/pakistan_flood_monitor src/app/pipelines src/app/workers scripts alembic/versions tests/test_workflow_foundation.py` — **passed**.
- Canonical configuration loaded with `APP_MODE=test` and `APP_MODE=demo` — **passed**.
- Canonical `DataCatalog` in `APP_MODE=operational` returned a typed `UNAVAILABLE` observation for a provider outage and typed `NO_DATA` for an empty provider response — **passed**; neither observation contained a value or synthetic lineage.
- Root migration modules were syntax-parsed — **passed**.
- `tests/test_workflow_foundation.py` — **not run** because this workspace has no virtual environment and its available base runtime lacks `pytest`, `SQLAlchemy`, and raster dependencies. The new `dev` extra supplies `pytest`; no broad dependency install or full-suite run was performed for this workstream.

Focused checks on the unmerged metric-GIS contracts workstream:

- `PYTHONPATH=src uv run --no-project --with 'shapely>=2.0' --with 'pyproj>=3.6' --with 'pytest>=8.0' --with 'pydantic>=2.6' python -m pytest tests/test_geo_measurements.py tests/test_lineage_schema.py -q` — **4 passed**. Pakistan-latitude geometry assertions confirm plausible km/km² values; the two existing Pydantic `schema`-field warnings remain.
- `python -m compileall -q src/pakistan_flood_monitor/geo src/pakistan_flood_monitor/models src/pakistan_flood_monitor/pipeline/runner.py src/app/services src/app/db/spatial.py` — **passed**.
- Static call-site check confirms scene ingestion, exposure, preprocessing, and corridor buffer services import `pakistan_flood_monitor.geo.measurements`; no raw Shapely metric calculation remains outside the helper implementation.

## Next recommended prompt

**Stop after Prompt 02 review/merge.** The next prompt must preserve these metric and metadata
contracts when migrating additional GIS services or introducing real EO products.
