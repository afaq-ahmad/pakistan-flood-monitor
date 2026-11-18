# Engineering standards

These standards support the repository operating contract in root `AGENTS.md`.
[ADR-001](../adr/ADR-001-canonical-runtime.md) owns the runtime and scientific
integrity decision. Use the [development guide](../development.md) and
[testing guide](../testing.md) for commands.

## Place changes in the right layer

- Canonical business logic belongs in `src/pakistan_flood_monitor/`. Use the
  [runtime map](../architecture.md) to trace existing callers, storage and
  provider boundaries before adding a service.
- API and UI adapters validate transport inputs, enforce their access
  boundaries and translate typed results to user-facing states. Keep
  processing and publication policy in the canonical services and use the
  existing dashboard adapter for API-backed reads.
- Keep provider IO and database access behind their existing interfaces.
  Domain logic should not need FastAPI request objects, Streamlit session
  state or a provider's raw payload. Adapt legacy behavior with parity
  tests. Introduce an interface when an actual boundary needs one.
- Reuse existing models, settings and repositories. Give a module one
  coherent responsibility. Prefer focused functions and clear names over
  abstractions built for possible future callers.
- Process-local state is acceptable for explicitly scoped features such as
  isolated fixtures. Use durable storage and transactions when correctness
  depends on restart, concurrency, idempotency or recoverable partial work.

## Write Python for callers and operators

- Type new and changed public interfaces, including nullable values, units,
  relevant state and return types. Use existing enums and typed models.
  Document non-obvious contracts, invariants, time semantics and side
  effects. Follow the surrounding style.
- Handle known errors at the boundary that can act on them. Use meaningful
  exception types, safe errors and structured context. Avoid catching a
  broad exception merely to return success or an empty result. Preserve
  the cause internally when translating an error.
- Put runtime options in the established configuration owner. Keep defaults
  explicit and literals that carry domain meaning named or documented.
  Use timezone-aware UTC for processing and storage, with deliberate
  conversion for display.
- For providers, validate payload shape, bounds, timestamps, units and
  provenance before use. Set network timeouts. Retry transient,
  retry-safe requests with bounded attempts and backoff when appropriate.
  Carry typed failure, availability and freshness through to the caller.
- Preserve [source and processing lineage](../architecture-environmental-data.md),
  model and configuration versions, and CRS and raster semantics. Verify
  measurement units, alignment, transforms, resolution, nodata, acquisition
  geometry and band semantics. Use categorical-safe resampling for masks
  and report its effect on uncertainty. Require independent scientific evidence before claiming
  operational validity. A test fixture verifies software behavior.
- Validate files against the intended path and access policy, and URLs
  against the intended destination and scheme policy. Enforce roles and
  visibility server-side. Keep credentials, sensitive report details and
  precise private locations out of ordinary logs, exports and errors.
  Preserve accountability in protected audit records.
- Consider provider limits, memory or VRAM, storage growth and restart
  recovery when changing resource-intensive or long-running work.

## Review before requesting acceptance

| Check | Evidence to inspect |
|---|---|
| Problem and scope | Existing task and acceptance criteria, focused diff, evidence for any reopened work |
| Architecture and interfaces | Canonical owner, applicable ADRs, caller compatibility, reuse, API and UI agreement |
| Runtime and failures | Mode and availability boundaries, useful recovery and errors, retry and restart behavior where relevant |
| Tests | Deterministic and isolated success, failure and boundary cases. Exact focused and applicable regression commands |
| Scientific evidence | Units, time semantics, CRS, provenance, versions, assumptions, uncertainty and validation coverage |
| Security and privacy | Server-side roles, invalid inputs, sensitive data, safe audit, logs and exports |
| Data and deployment | Upgrade, recovery and rollback on disposable data, including target database differences when relevant |
| Documentation | Owning reference and diagrams, checked task evidence, limits, PR and handoff |

Use the repository PR template for the review record. State which checks
apply and what remains unverified. Include user-visible evidence and
rollback notes where relevant.
