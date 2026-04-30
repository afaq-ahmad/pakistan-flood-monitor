# Security, Reliability, Testing, and Release Safety Audit (2026-04-30)

Active roles:
- Lead role: Application Security Engineer
- Supporting roles: SRE / Observability Engineer, QA Lead, Test Automation Engineer, Release Manager, Backend Engineer
- Why these roles are needed: This audit determines whether false alerts, spoofed actions, regressions, outages, and unsafe release behaviors are controlled.

## Security, Trust, and Safety Plan

### Verified current posture
- Token-based authentication and role checks exist in canonical API (`_require_role`, `_resolve_role`) with admin/analyst tokens.
- Internal/public API separation exists using `/internal` and `/public` routers.
- Internal API rate limiting middleware exists and returns HTTP 429 with retry hints.
- Review publication includes SOP/geometry QA via `publication_gate` and metadata requirements.
- Privileged/review audit logs exist, but they are in-memory structures.

### Trust/safety gaps
- **Actor spoofing risk is reduced but not fully eliminated**: prefix checks (`admin-*`, `analyst-*`) reduce obvious spoofing, but actor is still client-supplied text rather than identity bound to token principal.
- **Audit logs are mutable in memory** and can be replaced via state restore endpoint; tamper resistance and non-repudiation are not guaranteed.
- **Secret handling is env-token based only**; no key management/rotation automation integration in code.
- **Alert tampering resilience is weak** because lifecycle state and audit records are not persisted with immutable controls.

### Security actions (near-term)
1. Bind actor identity to token claims and remove actor field from privileged request payloads.
2. Persist audit records append-only in DB with integrity checksum/hash-chain fields.
3. Restrict `/internal/admin/state/restore` to emergency mode and signed snapshots only.
4. Add security regression tests for replay/mutation attempts against review and audit endpoints.

## Testing and QA Plan

### Verified current posture
- Unit/integration-like tests exist for API workflows, resilience/security contracts, SAR preprocessing prototype workflows, and orchestration.
- Security-related tests include role misuse rejection, actor-prefix spoof rejection, and rate-limit behavior.
- End-to-end API flow tests cover run → review → public event/exposure/alerts.

### QA gaps
- No persistent database-backed recovery tests in canonical runtime path.
- No CI-enforced API contract snapshot/version tests found.
- No explicit geospatial interoperability smoke tests for QGIS/ArcGIS outputs.
- No adversarial tests for alert tampering through state export/restore misuse.

### QA actions
1. Add persistence-backed restart tests once runtime state is moved to DB.
2. Add OpenAPI schema contract snapshot tests and breaking-change gate.
3. Add signed-audit verification tests and unauthorized restore path tests.
4. Add geospatial output contract tests (GeoJSON validity, CRS, topology).

## DevOps, SRE, and Reliability Plan

### Verified current posture
- Environment templates exist (`.env.local/.staging/.prod`).
- Release checklist exists with health, metrics, backup export, security and rollback steps.
- Prometheus-like text metrics endpoint exists.

### Reliability gaps
- Docker/Compose files are not verified in repository.
- CI/CD workflows are not verified in repository.
- Runtime state backup/restore exists but is API-level in-memory snapshot, not durable DB backup strategy.
- No structured incident response playbooks beyond short checklist references.

### DevOps/SRE actions
1. Add container build artifacts and reproducible image pipeline.
2. Add CI workflow gates: lint, tests, security checks, migration checks, contract checks.
3. Replace in-memory snapshot backup with database backups and restore drills.
4. Add SLO/SLA-oriented alerting rules and incident runbook with escalation matrix.

## Release Readiness Risks

| Priority | Finding | Severity | Category | Evidence | Why It Matters | Fix | Owner Role | Owner Squad | Effort | Release Blocker |
|---|---|---|---|---|---|---|---|---|---|---|
| P0 | Privileged actor identity is client-supplied | High | security | `review-event` and admin endpoints accept payload `actor`; only prefix checked | Enables impersonation within role namespace and weakens non-repudiation | Bind actor to authenticated principal claims | Application Security Engineer | Reliability, Security & Release | M | Yes |
| P0 | Audit trails are in-memory and mutable | Critical | security | `review_audit_log` and `privileged_audit_log` are global lists; state restore rewrites them | Tamper risk, no durable forensic trail after restart/incident | Append-only DB audit log with integrity checks | Backend Engineer | Core Platform & APIs | L | Yes |
| P0 | Operational state is in-memory | Critical | reliability | `run_history`, `event_store`, historical library stored in process memory | Restart/data-loss and multi-instance inconsistency can cause false/vanished alerts | Persist lifecycle state in PostGIS with transactions | SRE Engineer | Core Platform & APIs | L | Yes |
| P1 | State restore endpoint can rewrite trust records | High | public safety | `/internal/admin/state/restore` replaces runtime stores including audits | Compromised admin token can rewrite operational truth | Signed snapshots + emergency-only restore mode + full restore audit event | Application Security Engineer | Reliability, Security & Release | M | Yes |
| P1 | Rate limiting identity keyed by raw Authorization header | Medium | security | middleware uses Authorization header string as identity | Token sharing or proxy effects can reduce abuse control granularity | Use principal ID + client fingerprint and per-endpoint policies | Backend Engineer | Reliability, Security & Release | S | No |
| P1 | No verified CI/CD workflows | High | DevOps | repository scan shows no CI workflow files | Regressions/security issues can ship unblocked | Add CI with mandatory gates and status checks | DevOps Engineer | Reliability, Security & Release | M | Yes |
| P1 | No verified container deployment artifacts | Medium | DevOps | repository scan did not find Dockerfile/Compose | Reproducible runtime/deployment uncertain | Add Dockerfile/compose and pinned runtime image | DevOps Engineer | Reliability, Security & Release | M | No |
| P1 | Release checklist is manual and not enforced by automation | Medium | release | `docs/release_checklist.md` is checklist-only | Human error can bypass critical gates | Convert checklist items into automated release pipeline checks | Release Manager | Reliability, Security & Release | M | Yes |
| P2 | Security model uses static bearer tokens only | Medium | security | role resolution from env tokens in `_resolve_role` | Limited revocation/traceability/rotation granularity | Move to JWT/OIDC with claims and expiry | Application Security Engineer | Core Platform & APIs | L | No |
| P2 | Limited incident response/runbook depth | Medium | SRE | docs include checklist but limited incident SOP depth | Slower recovery and inconsistent response in live incidents | Add full incident runbook, ownership, and drill cadence | SRE Engineer | Reliability, Security & Release | S | No |

