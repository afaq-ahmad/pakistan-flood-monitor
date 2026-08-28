# ADR-001: Canonical runtime and operational data integrity

- **Status:** Accepted
- **Date:** 2026-08-28
- **Decision owners:** Solution architecture, backend, GIS/remote sensing, QA

## Context

The repository currently contains two application trees. The supported FastAPI entrypoint is under
`src/pakistan_flood_monitor`, while stronger but partly disconnected GIS services live under
`src/app`. The canonical pipeline could also manufacture plausible environmental values from stable
hashes when source data were missing. That behaviour is useful for deterministic tests and product
demos, but it cannot be allowed to look like an observation.

## Decision

1. `pakistan_flood_monitor` is the only public package namespace and
   `pakistan_flood_monitor.api.main:app` is the only supported FastAPI application.
2. `src/app` is a migration source, not a second operational runtime. Scientifically valid services
   will be migrated behind canonical interfaces in later focused PRs. Production code must not add
   new dependencies on demo/synthetic modules.
3. Runtime behaviour is controlled by `APP_MODE=test|demo|operational`:
   - `test`: deterministic fixtures are allowed for automated verification.
   - `demo`: fixtures are allowed only with the visible watermark
     `SIMULATED / DEMO DATA — NOT FOR OPERATIONAL DECISIONS`.
   - `operational`: missing sources fail closed with an explicit `UNAVAILABLE` state. Hash, random,
     stub, or synthetic fallback values are prohibited.
4. Every scientific input is labelled `OBSERVED`, `FORECAST`, `ESTIMATED`, `SIMULATED`,
   `FIELD_REPORTED`, `OFFICIAL`, or `UNAVAILABLE`, with units, source URI/time, processing version,
   quality status, and availability.
5. Public publication outside test mode requires scientific lineage. Synthetic or unavailable
   lineage is rejected by the publication gate. Failed review/publication transitions are atomic.
6. Streamlit and standalone prototype services remain demo/analyst-development surfaces until they
   call the canonical API and use the same integrity contract.

## Consequences

- The current pipeline intentionally cannot complete in operational mode where real IMERG, GloFAS,
  optical, or floodplain measurements are not implemented. It returns a structured 503 response
  listing unavailable observations rather than inventing numbers.
- Demo functionality remains usable, but its reports, lineage, detections, and alert summaries carry
  a machine-readable `SIMULATED` label and visible watermark.
- Later PRs can replace each unavailable adapter with a real provider without changing the safety
  boundary or public contract.

## Migration sequence

1. Build/dependency cleanup and CI.
2. Metric-correct GIS measurement helpers.
3. Geospatial asset/provenance contract.
4. Real STAC, hydromet, SAR/optical, terrain, exposure, workflow, and publication implementations.
5. Remove remaining `src/app` imports only after parity tests prove canonical replacements.
