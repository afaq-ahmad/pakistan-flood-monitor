# Repository-wide AI agent operating contract

Read this file before planning or editing. It applies throughout the
repository. User authorization defines the task scope, and accepted ADRs
govern architecture. Follow applicable scoped `AGENTS.md` files for distinct
local requirements. They may add safeguards and must preserve this contract.

## Start or resume

Follow the [agent GitHub workflow](docs/engineering/AGENT_GITHUB_WORKFLOW.md#start-or-resume)
for the detailed sequence. First confirm repository identity and inspect the
local worktree, branch, remotes and HEAD. Check open PRs, then recover the
verified workstream branch or select a dedicated branch from the current base.
Before editing, read this contract on that branch, the applicable
[ADRs](docs/adr/README.md), the [master task plan](docs/engineering/MASTER_TASK_PLAN.md),
the [latest handoff](docs/engineering/AGENT_SESSION_LOG.md), the
[implementation ledger](docs/engineering/IMPLEMENTATION_STATUS.md), and the
relevant [engineering and feature documentation](docs/INDEX.md).

Inspect the relevant implementation, callers, migrations, tests and CI. Check
the legacy tree where it supplies evidence or behavior. Verify previous
completion claims against code, tests and Git history. Check dependencies and
coordinate ownership. Select one eligible, authorized task and record its
existing ID. Use the authoritative plan and reopen completed work only with
evidence of regression or an explicit new requirement. Run appropriate
baseline checks before implementation. Record the command and any baseline
failure or limitation.

## Canonical runtime and compatibility

- Per [ADR-001](docs/adr/ADR-001-canonical-runtime.md),
  `src/pakistan_flood_monitor/` is the canonical public package and
  `pakistan_flood_monitor.api.main:app` is the supported FastAPI application.
- Treat `src/app/` as a migration source. Port useful behavior behind
  canonical interfaces with parity tests. Any temporary canonical dependency
  on legacy code needs a documented migration reason. Never create a third
  parallel implementation tree.
- Preserve caller contracts. For unavoidable breaking changes, document the
  affected API or data contract, migration path, compatibility window and
  rollback.

## Environmental and publication safeguards

- Keep exactly three safety modes: `test`, `demo`, and `operational`, selected
  by `APP_MODE`. Synthetic data may exist only in explicit automated-test or
  demo fixtures. Label it `SIMULATED` in code and outputs. Demo outputs need
  `SIMULATED / DEMO DATA — NOT FOR OPERATIONAL DECISIONS` and synthetic
  inputs must fail the operational publication gate.
- Never fabricate an environmental observation in operational code. Missing,
  incomplete, failed or low-quality input must remain typed `UNAVAILABLE` or
  `DEGRADED` states. Represent input beyond a defined freshness window as a
  typed `STALE` state. Preserve reason code, source time, evaluation time and
  the rule applied. Fail closed for required inputs. Use proxies only in an
  explicitly estimated product with method and uncertainty.
- Validate the CRS, datum, axis order and output units. Never interpret degrees
  or EPSG:4326 planar results as metres or other metric units. Use a suitable
  local projection or geodesic method. Preserve raster and measurement
  semantics, and verify spatial and temporal alignment for scientific changes.
- Retain lineage across storage, API, exports and UI as applicable. Include
  source/provider and stable source URI, acquisition/valid time, source
  publication time, processing time, expressed as timezone-aware UTC, code
  and algorithm versions, configuration, model, threshold, and reference-dataset
  versions, input identifiers or checksums, processing lineage, and
  quality/availability status, validation result, known limitations, and
  uncertainty. Preserve the distinct meanings of event, report, source and
  processing times.
- Keep public observation, forecast, model inference, exposure, estimated
  impact, verified damage, and warning distinct. Describe coverage, latency,
  uncertainty and validation limits. Never automatically publish an emergency
  warning, evacuation instruction, or insurance eligibility or payout
  decision from a machine score. Require appropriate human or official
  review and auditable approval.

## Security, data handling and dependencies

- Validate untrusted inputs, paths, URLs, geometries, uploads and serialized
  content. Enforce authorization in the API and trusted handlers. Preserve
  audit, rate-limit and publication boundaries. Minimize sensitive
  community-report and contact data, including in logs and exports.
- Keep secrets, credentials, personal data, sensitive precise locations,
  generated databases, caches and unreviewed third-party data out of commits.
- Prefer free/open data sources and open-source libraries. Do not make a paid
  API, proprietary service or model, or metered SaaS a core or test dependency.
  Justify material additions and constrain them consistently with the project.

## Implement, verify and document

- Use the [engineering standards](docs/engineering/ENGINEERING_STANDARDS.md)
  to choose the canonical layer and review the diff. Reuse sound interfaces.
  Keep the change small and limited to the authorized task.
- Add or update tests for every behavior change. Use deterministic offline
  fixtures and cover success and applicable failure paths. Run focused checks
  first, then the applicable [repository checks](docs/testing.md). Record exact
  results and pre-existing failures. Verify migrations and rollback on
  disposable data. Preserve applied migrations. Provide before and after UI
  evidence or explain the applicable testing limitation.
- Update the owning [documentation and diagrams](docs/DOCUMENTATION_GUIDE.md)
  when changing a contract. Use [`docs/adr/ADR-TEMPLATE.md`](docs/adr/ADR-TEMPLATE.md)
  for decisions that materially constrain later work. Supersede accepted
  decisions through a new ADR. Acceptance requires review and merge.
- Update `docs/engineering/IMPLEMENTATION_STATUS.md` in every consolidated-prompt
  PR and record the task result and next action in the plan and handoff.
  Distinguish implementation presence from validation. The ledger prompt table
  uses `NOT_STARTED`, `IN_PROGRESS`, `PARTIAL`, `BLOCKED` and `COMPLETE`.
  Reserve `COMPLETE` for merged acceptance evidence.

## Checkpoint, review and hand off

Use the [agent GitHub workflow](docs/engineering/AGENT_GITHUB_WORKFLOW.md) for
small commits, authorized pushes, verified remote refs and one focused draft
PR. Preserve the user's changes and published Git history. Use the
[PR template](.github/pull_request_template.md) to report scope, compatibility,
test evidence, scientific assumptions and data limitations, rollback notes
and remaining work. Ask for human review when the acceptance checks are met.
Keep the repository task record and [session handoff](docs/engineering/AGENT_SESSION_LOG.md)
reproducible. Never merge automatically. Stop at the authorized task
boundary. Do not start the next task.
