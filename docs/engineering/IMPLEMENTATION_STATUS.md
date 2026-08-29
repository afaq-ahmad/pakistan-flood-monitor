# Implementation status

Last verified: **2026-08-29**, against `main` at `3c28501`. Read this file with root
[`AGENTS.md`](../../AGENTS.md) and applicable [ADRs](../adr/README.md) before every task. Verify stale
claims against code and Git history; update this ledger in each consolidated-prompt PR.

## Current contract

| Item | Repository state |
|---|---|
| Canonical package | `src/pakistan_flood_monitor/` |
| Supported API runtime | `pakistan_flood_monitor.api.main:app` |
| Legacy migration source | `src/app/`; deprecated API entrypoint warns of removal after 2026-12-31 |
| Runtime modes | `test`, `demo`, `operational` via `APP_MODE`; default is `demo` |
| Accepted ADRs | [ADR-001: canonical runtime and operational data integrity](../adr/ADR-001-canonical-runtime.md) |
| Package version | `0.1.0` in `pyproject.toml` |
| Canonical DB migration head | Root Alembic chain: `f46f1d9e187b` (initial schema) |
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
| 01 | COMPLETE | Operational observation-state contract merged in [PR #68](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/68) |
| 02 | NOT_STARTED | No authoritative prompt mapping or merged acceptance evidence recorded |
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

- Operational execution fails closed because real required IMERG, GloFAS, optical, floodplain, and
  sufficient Sentinel-1 inputs are not all implemented. This structured `UNAVAILABLE` response is a
  safety behavior, not an operational capability.
- Advanced SAR remains simulated, optical water detection uses RGB proxies, forecast LSTM weights are
  untrained, and dam surface extent is only a fill proxy. None is validated for warning authority.
- Streamlit, standalone services, CSV/file stores, and much functionality under `src/app` bypass or
  remain disconnected from the canonical API. The canonical runner still imports legacy
  `app.services.observability`.
- Canonical API state is primarily in memory. The optional database persistence path currently emits
  datetime JSON-serialization errors in tests; restart-safe audit/state durability is not established.
- Availability has `AVAILABLE`, `DEGRADED`, and `UNAVAILABLE`; a first-class scientific `STALE` state
  with reason/freshness metadata is required by the contract but is not implemented.
- Code, routes, dashboards, or tests existing in the tree do not establish operational readiness.

## Known P0/P1 defects

Severity reflects current evidence, not an exhaustive safety assessment.

| Priority | Defect / risk | Evidence and disposition |
|---|---|---|
| P0 | None formally triaged | Do not interpret this as evidence of operational safety or readiness |
| P1 | Repository test baseline is red | 24 failures: shared rate-limit/test state, lifecycle/resilience contract mismatches, and database datetime JSON serialization |
| P1 | CI and reproducible test environment are absent | No workflow; `pytest` is not declared by `pyproject.toml`, so the documented test command fails in a fresh base environment |
| P1 | Runtime and migration split-brain remains | Canonical and legacy packages plus two independent Alembic histories require incremental reconciliation |
| P1 | Scientific stale-state contract is not implemented | Freshness may appear as UI/service strings, but canonical observation availability lacks `STALE` |

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

## Next recommended prompt

**Prompt 02: build/dependency cleanup, hermetic CI, and baseline stabilization.** Prompt 01 already
merged out of sequence in PR #68; do not repeat it. Prompt 02 should preserve operational fail-closed
behavior while making the declared test command reproducible and triaging the 24 known failures.
