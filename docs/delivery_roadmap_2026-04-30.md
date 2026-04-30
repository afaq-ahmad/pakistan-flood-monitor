# Delivery Plans: Immediate Sprint to 1-Year Public Launch (2026-04-30)

Active roles:
- Lead role: Program Director / Delivery Owner
- Supporting roles: Technical Project Manager / Scrum Lead, Release Manager, Senior Product Manager, Engineering Lead, QA Lead
- Why these roles are needed: Delivery plans must balance execution realism, dependencies, release safety, and user-value outcomes.

## 7-Day Sprint Plan

**Goal:** De-risk launch blockers by locking canonical architecture, security trust model, and implementation kickoff scope.

| Task | Owner Squad | Roles Involved | Deliverables | Acceptance Criteria |
|---|---|---|---|---|
| Freeze canonical runtime decision (`src/pakistan_flood_monitor`) | A | Engineering Lead, TPM, Release Manager | Architecture decision record + deprecation notice for prototype API | Team agrees one runtime path; decision doc merged |
| Open P0 implementation tickets (persistence, actor binding, immutable audit) | F + A | TPM, AppSec, Backend Lead, QA Lead | Sized backlog with owners, dependencies, sprint labels | P0 tickets have DoD, effort, and sequence commitments |
| Draft PostGIS schema migration for event/review/audit lifecycle | A | DB Engineer, Backend Engineer | Migration spec + ERD draft | Schema reviewed; migration plan approved by engineering + QA |
| Define security acceptance tests (spoofing, restore abuse, token misuse) | F | AppSec Engineer, Test Automation Engineer | Test plan and first failing test cases | Security tests reviewed and scheduled in CI roadmap |
| Publish public safety disclaimer draft and alert language policy | E + D | Product Manager, Technical Writer, Govt Liaison | Advisory language guide (official vs public variants) | Draft approved by product, security, and stakeholder liaison |

## 30-Day Roadmap

### Week-by-week priorities

| Week | Priorities | Owner Squads | Major Deliverables | Risks | Acceptance Criteria |
|---|---|---|---|---|---|
| Week 1 | Architecture lock + schema groundwork + security design | A, F | Canonical architecture ADR, DB schema proposal, auth actor-binding design | Scope creep on architecture cleanup | ADR signed off; schema + auth designs approved |
| Week 2 | Implement persistence backbone and repository interfaces | A | Initial PostGIS-backed repositories and migration branch | Data model churn / migration friction | Core CRUD for runs/events/reviews/audits working in dev |
| Week 3 | Integrate security hardening and review lifecycle guards | F, D | Principal-bound actor handling, stricter state transitions, audit append model | Backward compatibility with existing tests | Spoofing and invalid-transition tests pass |
| Week 4 | Wire dashboard/read APIs to authoritative persisted data and release gates v1 | E, A, F | Dashboard source migration, release gate checklist automation plan | UI/API drift and hidden dependencies | Dashboard uses persisted reviewed events; release gate checklist mapped to commands |

## 90-Day Pilot-Readiness Roadmap

### Workstreams and outcomes

1. **Architecture stabilization (Squads A, F)**
   - Canonical API only, persisted lifecycle state, migration strategy hardened.
   - Acceptance: restart and multi-instance consistency tests pass in staging.

2. **Flood detection credibility (Squad B)**
   - Replace synthetic features with scene-derived features, baseline processing integrated, validation pack against known events.
   - Acceptance: monthly validation report with baseline metrics (precision/recall/false-positive rate).

3. **Dashboard workflow (Squad E)**
   - Analyst dashboard with provenance and review controls, public dashboard with confidence/disclaimer cards.
   - Acceptance: analyst completes review→publish workflow in single interface with traceability.

4. **Exposure outputs (Squad C)**
   - Transition from scalar exposure stubs to overlay-based district/tehsil summaries.
   - Acceptance: exposure outputs reproducible from source layers with lineage metadata.

5. **Alert approval and governance (Squad D, G)**
   - NDMA/PDMA-style template variants, approval chain, official/public message distinction.
   - Acceptance: each published alert includes approver, rationale, confidence band, disclaimer.

6. **Security baseline (Squad F)**
   - RBAC hardening, immutable audit, signed restore operations, token policies.
   - Acceptance: security abuse regression suite passes; incident response runbook drill completed.

7. **Pilot documentation (Squad G, E)**
   - SOPs, onboarding guides, scenario replay kit, pilot support workflow.
   - Acceptance: at least one dry-run pilot session completed with documented feedback.

8. **Validation process (Squads B, C, G)**
   - Field validation loop, known-event benchmark replay, post-event review cadence.
   - Acceptance: validation governance doc + first review cycle completed.

## 1-Year Public Launch Roadmap

### Q1 — Foundation and Technical Cleanup
- **Goals:** remove trust blockers and stabilize architecture.
- **Deliverables:** persisted state, actor-binding auth, immutable audits, canonical API consolidation, release gate definitions.
- **Owner squads:** A, F, D.
- **Required roles:** Engineering Lead, AppSec Engineer, TPM, QA Lead.
- **Success metrics:** 0 critical trust blockers open; restart consistency pass rate 100% in staging.
- **Release gates:** P0 security/persistence tests pass; migration and rollback rehearsal completed.

### Q2 — Private Beta
- **Goals:** raise scientific credibility and operational usability.
- **Deliverables:** scene-derived detection pipeline, validation reports, district/tehsil exposure summaries, analyst workflow improvements.
- **Owner squads:** B, C, E.
- **Required roles:** SAR Lead, Hydrology Lead, Exposure Modeler, UX Lead.
- **Success metrics:** measurable detection quality baseline published; analyst throughput improves against baseline.
- **Release gates:** validation suite pass, dashboard backed by authoritative persisted data.

### Q3 — Pilot with Selected Users
- **Goals:** institutional workflow fit and field-validated operations.
- **Deliverables:** NDMA/PDMA-aligned templates, SitRep exports, bilingual advisories, partner onboarding pack, field feedback loop.
- **Owner squads:** D, E, G.
- **Required roles:** Govt Liaison, Training Specialist, Field Validation Coordinator, Product Manager.
- **Success metrics:** pilot stakeholder satisfaction targets met; false-alert handling SLA achieved.
- **Release gates:** pilot drills completed; documented corrective actions closed.

### Q4 — Public Launch Readiness
- **Goals:** operational hardening, interoperability, and governance sign-off.
- **Deliverables:** CI/CD release gates fully enforced, export contracts (GeoJSON/COG/GeoParquet where applicable), observability and incident playbooks, final public documentation.
- **Owner squads:** F, A, C, E.
- **Required roles:** Release Manager, SRE, Data Architect, Technical Writer.
- **Success metrics:** zero open critical release blockers; successful launch simulation with rollback drill.
- **Release gates:** final security audit pass, launch checklist completed with evidence, rollback test successful.

## Hiring and Skill Gap Recommendations

| Hiring Priority | Role | Why Needed | Skills Required | Full-Time/Part-Time | First 90-Day Deliverable |
|---|---|---|---|---|---|
| 1 | Senior Database/PostGIS Engineer | Persistence migration is the top trust blocker | PostGIS schema design, indexing, SQLAlchemy, migration strategy | Full-Time | Production-ready event/review/audit persistence layer |
| 2 | Application Security Engineer | Actor binding and immutable audit controls are release-critical | AuthN/AuthZ design, API security testing, audit integrity | Full-Time | Principal-bound privileged workflow + abuse test suite |
| 3 | EO Pipeline Engineer (SAR) | Detection credibility depends on scene-derived features | Sentinel-1 preprocessing, raster workflows, provenance metadata | Full-Time | Canonical scene-derived feature pipeline integrated |
| 4 | Geospatial QA Engineer | Spatial quality and interoperability are high-risk for public trust | CRS/topology QA, geospatial validation automation | Full-Time | Geospatial QA gate with blocking checks in CI |
| 5 | Senior Frontend/UX Engineer (Crisis UX) | Public and analyst usability directly affect adoption and safety | Map UX, low-bandwidth design, accessibility, stateful API integration | Full-Time | Mobile-first public advisory view + analyst review workflow v1 |
| 6 | Government/NGO Liaison | Pilot adoption requires institutional workflow alignment | Emergency workflow mapping, stakeholder engagement, advisory templates | Part-Time (can scale FT during pilot) | NDMA/PDMA-aligned alert template and SOP pack |
| 7 | Training & Implementation Specialist | Real users need repeatable onboarding and drills | SOP design, training delivery, support playbooks | Part-Time | Pilot onboarding kit + first simulation session |
| 8 | SRE/DevOps Engineer | Reliability and release gates currently underpowered | CI/CD, observability, incident response, backup/restore drills | Full-Time | CI pipeline with release gates + incident runbook draft |

