# Repository-wide AI agent operating contract

This contract applies to every AI coding agent working anywhere in this repository. Read it before
planning or changing files. A more specific `AGENTS.md` may add stricter local requirements, but it
must not weaken this contract. User instructions define task scope; accepted architecture decision
records (ADRs) define repository architecture.

## 1. Start with evidence and stay in scope

- Before modifying the repository, inspect the relevant implementation and its callers in both
  `src/pakistan_flood_monitor/` and `src/app/`, plus migrations, tests, documentation, CI/configuration,
  and any existing implementation of the requested capability. When GitHub access is available,
  inspect current open issues and pull requests for conflicts or prior work.
- Read [`docs/engineering/IMPLEMENTATION_STATUS.md`](docs/engineering/IMPLEMENTATION_STATUS.md) and
  the applicable ADRs first. Record material assumptions and distinguish observed repository facts
  from inferences. Treat the ledger as a navigation aid, then verify its claims against code and Git
  history before relying on them.
- Work on a descriptive dedicated branch. Make only the requested change and its necessary tests,
  migrations, schemas, and documentation. Do not silently begin another roadmap item, repair an
  unrelated defect, or hide unrelated refactoring in the same pull request.
- Reuse or refactor sound existing code. Do not duplicate a subsystem merely because moving the
  existing implementation requires care.
- Establish the baseline before editing when practical. Do not claim a regression for a failure that
  was already present; document pre-existing failures with the exact command and result.

## 2. Canonical architecture

- Per [ADR-001](docs/adr/ADR-001-canonical-runtime.md), `src/pakistan_flood_monitor/` is the canonical
  public package and `pakistan_flood_monitor.api.main:app` is the supported FastAPI application.
- Treat `src/app/` as a migration source, not a second operational runtime. If it contains useful
  behavior, migrate or refactor that behavior behind canonical interfaces and add parity tests. Do
  not add new canonical-to-legacy coupling without a documented, temporary migration reason.
- Never create a third parallel implementation tree. A later accepted ADR may supersede this package
  decision explicitly; an incidental code pattern or convenience does not.
- Preserve backward compatibility deliberately. When a breaking change is unavoidable, document the
  affected API/data contract, migration path, compatibility window, and rollback.

## 3. Environmental data truth and availability

- Runtime behavior has exactly three safety modes: `test`, `demo`, and `operational`, selected by
  `APP_MODE` as defined by ADR-001. Do not add an implicit fourth mode or infer operational mode from
  a deployment environment. Tests may use deterministic fixtures; demos must carry the visible
  `SIMULATED / DEMO DATA — NOT FOR OPERATIONAL DECISIONS` label; operational execution must use real,
  traceable inputs or fail closed.
- Never fabricate an environmental observation in operational code. Hash-derived, random, synthetic,
  stub, or plausibly hard-coded measurements are prohibited as fallbacks for missing live data.
- Synthetic data may exist only in explicit automated-test or demo fixtures. Label it in code and in
  every output as `SIMULATED`, include the visible demo watermark required by ADR-001, and prevent it
  from passing an operational publication gate.
- Missing, stale, incomplete, failed, or low-quality inputs must remain typed `UNAVAILABLE` or
  `DEGRADED` states with a reason. Fail closed where the missing input is required. Do not replace an
  unknown value with zero, a historical average, or a realistic-looking proxy unless the product is
  explicitly an estimate and the method and uncertainty are exposed.
- Represent data that exceeded its defined freshness window as a typed `STALE` state, not merely a UI
  string. Availability states must include a stable reason code, the relevant source/acquisition time,
  the evaluation time, and the freshness or quality rule that produced the state.
- Preserve source semantics and units through ingestion, processing, persistence, APIs, exports, and
  UI. Never upgrade a field report, model output, or proxy into an observation by renaming it.

## 4. GIS and remote-sensing correctness

- Every geospatial calculation must declare and validate its CRS, datum, axis/order assumptions, and
  output units. Treat missing or ambiguous CRS metadata as a data-quality failure.
- EPSG:4326 is suitable for geographic storage/interchange, not planar metric area, length, buffer,
  or distance calculations. Never interpret degrees or EPSG:4326 planar results as metres, kilometres,
  square metres, or square kilometres.
- For metric operations, use a defensible local projected CRS or a geodesic method appropriate to the
  operation and extent. Document CRS-selection logic and test known geometries, reprojection, units,
  antimeridian/zone/boundary cases when relevant.
- Preserve raster CRS, transform, resolution, nodata, pixel alignment, resampling method, acquisition
  geometry, and band semantics. Use categorical-safe resampling for masks/classes and state all
  resolution or reprojection effects on uncertainty.
- Scientific thresholds, model outputs, and exposure overlays require unit, range, temporal-alignment,
  and spatial-alignment validation. Add geospatial/golden tests for material scientific changes.

## 5. Provenance, time, quality, and uncertainty

Every observation, forecast, derived product, exposure result, and impact estimate must preserve
enough lineage to reproduce and judge it. As applicable, retain:

- source/provider and stable source URI or dataset identifier;
- acquisition/valid time and source publication time;
- processing time, expressed as timezone-aware UTC;
- code version/commit and algorithm or processing version;
- configuration, model, threshold, and reference-dataset versions;
- input asset identifiers/checksums and processing-step lineage;
- quality/availability status, validation result, known limitations, and uncertainty/confidence with
  its meaning and method.

Do not discard provenance at serialization or UI boundaries. Do not mix event time, acquisition time,
forecast valid time, report time, and processing time. Parse explicitly, store timezone-aware values,
and expose the relevant timestamp meaning.

## 6. Scientific and decision semantics

- Keep these concepts separate in domain models, persistence, APIs, tests, and user-facing language:
  public observation, forecast, model inference, exposure, estimated impact, verified damage, and
  warning. Links between them must be explicit lineage or associations, not silent status promotion.
- An **observation** reports a measured or reported condition at a stated place and time. A
  **forecast** describes a future valid time. A **model inference** is a derived classification,
  probability, or estimate and is not itself an observation. **Exposure** is the intersection of a
  hazard extent/scenario with people or assets; it does not prove loss. **Damage** must say whether it
  is estimated or field/officially verified. A **warning** is an authorized communication, not a
  synonym for an alert score or candidate detection.
- A machine risk/anomaly/damage score supports analyst triage; it is not verified damage and is not an
  authoritative emergency decision.
- Never automatically publish an emergency warning, evacuation instruction, or insurance eligibility/
  payout decision from a machine score. Require the appropriate human/official review and auditable
  approval gate. Make non-authoritative status and limitations clear in public outputs.
- Communicate false-positive/false-negative risk, latency, coverage gaps, uncertainty, and validation
  limits. Use precise terms such as `detected water extent`, `forecast`, `estimated exposure`, and
  `field-verified damage` rather than treating all outputs as a confirmed flood impact.

## 7. Dependencies, security, and operations

- Prefer free/open data sources and open-source libraries. Do not make a paid API, proprietary service,
  paid model, or metered SaaS a required dependency for core operation or tests.
- Do not commit secrets, credentials, personal data, sensitive precise locations, generated databases,
  caches, or unreviewed third-party data. Minimize and protect field-report and contact information.
- Validate untrusted paths, URLs, geometries, uploads, and serialized content. Preserve authorization,
  audit, rate-limit, and publication boundaries; fail safely without leaking credentials or internals.
- Consider retry/idempotency, partial failure, stale data, concurrency, memory/VRAM, storage growth,
  provider limits, network absence, and restart recovery. Do not hide degraded operation behind a
  successful status.
- Pin or constrain dependencies consistently with repository policy, document material additions,
  and avoid adding heavyweight packages when an existing dependency or standard-library solution is
  sufficient.

## 8. Implementation, tests, and documentation

- Implement the smallest coherent change. Add or update tests for every behavior change: unit,
  integration, API/schema, migration, geospatial/golden, and failure-mode tests as appropriate.
- Tests must be deterministic and offline by default. Mock external services with clearly labelled
  fixtures; do not make standard tests depend on live environmental observations.
- For schema changes, update API models/examples and provide forward and rollback-safe migrations.
  Test upgrade/downgrade behavior where the project supports it. Never edit an applied migration to
  disguise a new schema change.
- Update nearby documentation and configuration examples when behavior or operation changes. Do not
  claim production readiness that evidence does not support. UI changes require useful before/after
  screenshots or an explicit explanation of why screenshots are not applicable.
- Run the narrow relevant tests first, then the repository-wide documented smoke/build/test checks.
  Leave the repository passing; if an unrelated pre-existing failure remains, report it precisely and
  demonstrate that focused checks for the task pass.

## 9. ADRs and implementation ledger

- Use [`docs/adr/ADR-TEMPLATE.md`](docs/adr/ADR-TEMPLATE.md) for decisions that materially constrain
  later implementation or are expensive to reverse. This includes SAR RTC-versus-GRD processing,
  metric CRS strategy, alert-authority boundaries, flood-depth maturity, and changes to the canonical
  runtime or migration strategy. Do not hide such decisions in code comments.
- ADRs are immutable decision history once accepted. Supersede an accepted ADR with a new ADR; do not
  rewrite its decision or status to make current code appear compliant. A proposed ADR is not accepted
  until review/merge records that status.
- Update `docs/engineering/IMPLEMENTATION_STATUS.md` in every consolidated-prompt PR. Keep it concise,
  evidence-based, and explicit about partial work, blockers, deprecated code, schema heads, P0/P1
  defects, exact test/CI results, and the next recommended prompt. Code presence alone is not evidence
  that a capability is operational. Use only `NOT_STARTED`, `IN_PROGRESS`, `PARTIAL`, `BLOCKED`, or
  `COMPLETE` in the prompt table, and never mark `COMPLETE` without merged acceptance evidence.

## 10. Review, commits, and pull requests

- Self-review the diff for task scope, GIS CRS/units, timezone semantics, provenance, data truth,
  scientific terminology, security/privacy, backward compatibility, migrations, failure modes,
  performance, accessibility, and documentation.
- Use small, coherent commits with descriptive messages. Do not rewrite or discard user changes.
- If repository permissions allow, push the dedicated branch and open a focused pull request using
  `.github/pull_request_template.md`. The PR must state the problem, approach, changed components,
  migrations/config changes, exact tests and results, scientific assumptions and data limitations,
  UI screenshots when applicable, backward-compatibility impact, rollback notes, pre-existing
  failures, and follow-up work explicitly out of scope.
- Stop when the requested task and its definition of done are complete. Do not start the next task.
