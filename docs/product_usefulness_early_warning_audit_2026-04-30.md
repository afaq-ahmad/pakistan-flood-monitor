# Product Usefulness and Early-Warning Workflow Audit (2026-04-30)

Active roles:
- Lead role: Senior Product Manager
- Supporting roles: Government / NGO Liaison, UX Lead, Critical End User, Training & Implementation Specialist, Field Validation Coordinator
- Why these roles are needed: This audit evaluates whether outputs are understandable, actionable, and operationally credible for Pakistan flood-monitoring/public-warning contexts.

## Flood Early-Warning System Gap Analysis

| Component | Current Support | Gap | Improvement | Lead Role | Owner Squad | Acceptance Criteria |
|---|---|---|---|---|---|---|
| Risk knowledge | Corridor concept, event records, and basic exposure output exist; historical record objects exist in canonical API | District/tehsil risk summaries, vulnerable-group context, and provenance-backed historical catalogs are weak or hardcoded | Build district/tehsil risk profiles with vulnerability overlays and source-attributed historical event library | Hydrology / Flood Risk Lead | Exposure & Impact Intelligence | District/tehsil endpoint returns risk tier, exposed population/assets, and source lineage fields for each summary |
| Detection/monitoring/forecasting | Trigger logic, confidence scoring, and review workflow are implemented; SAR/optical/hydromet concepts present | Canonical runtime uses synthetic feature values and simplified breach logic; gauge/barrage/upstream-downstream context not operationally explicit | Integrate scene-derived features + hydromet provenance + embankment-aware breach triage and validation pack | Remote Sensing / SAR Lead | Flood Detection & Remote Sensing | Detection features are sourced from ingestion artifacts; breach score includes embankment context; monthly validation report published |
| Warning dissemination | Internal/public API split exists; review/publish actions exist; alerts endpoints exist | No NDMA/PDMA-ready approval templates; no Urdu/local-language alerts; no clear official-vs-public message varianting; no channel connectors (SMS/email/WhatsApp) | Implement alert policy engine: draft/review/approve/publish + bilingual templates + channel adapters | Government / NGO Liaison | Analyst Review & Alerting | Every published alert has approval metadata, public-safe wording, confidence band, and optional channel payloads |
| Preparedness/response | Basic event/exposure retrieval is available; release checklist and runbooks exist | No actionable district response guidance, contact annex, evacuation-relevant summary, NGO/agency reporting package, or training scenario kits | Add Situation Report generator (district priorities, actions, contacts), after-action capture, and SOP/training kit | Training & Implementation Specialist | Partnerships, Validation & Pilot Adoption | One-click district SitRep export exists and is used in pilot drill with documented after-action review |

## Pakistan-Specific Usefulness Improvements

### 1) NDMA/PDMA-style alert governance package
- **Lead role:** Government / NGO Liaison
- **Squad owner:** Analyst Review & Alerting
- **Implementation sketch:** Map alert states to agency workflow (analyst review, duty officer approval, publication class, escalation path), add required fields (district, confidence, uncertainty, advisory actions).
- **Acceptance criteria:** Alert record contains role-stamped approvals and escalation level; pilot reviewers can trace lifecycle in audit view.
- **Release relevance:** **Pilot blocker**.

### 2) District/tehsil reporting with provincial rollups
- **Lead role:** Senior Product Manager
- **Squad owner:** Exposure & Impact Intelligence
- **Implementation sketch:** Build district/tehsil aggregation endpoints and periodic provincial snapshots with prioritized affected assets and populations.
- **Acceptance criteria:** API and dashboard provide sortable district/tehsil table and provincial summary for each run window.
- **Release relevance:** **High**.

### 3) River-gauge, barrage, and Indus system context cards
- **Lead role:** Hydrology / Flood Risk Lead
- **Squad owner:** Flood Detection & Remote Sensing
- **Implementation sketch:** Attach hydromet provenance (rainfall/discharge source and timestamp), upstream/downstream interpretation, and known barrage context to event cards.
- **Acceptance criteria:** Every high-priority event includes hydromet context block with source references and local-time timestamp.
- **Release relevance:** **Pilot blocker**.

### 4) Embankment breach triage workflow
- **Lead role:** Field Validation Coordinator
- **Squad owner:** Analyst Review & Alerting
- **Implementation sketch:** Add breach triage checklist (protected-side evidence, persistence, corroboration, field-verification request) and false-positive feedback loop.
- **Acceptance criteria:** Breach-labeled events require checklist completion and field validation status before public classification.
- **Release relevance:** **Pilot blocker**.

### 5) Urdu + low-bandwidth advisory outputs
- **Lead role:** UX Lead
- **Squad owner:** Public Dashboard & Mobile UX
- **Implementation sketch:** Add bilingual message templates and minimal static advisory pages optimized for poor connectivity/mobile.
- **Acceptance criteria:** Public alert view supports Urdu/English toggle, <500KB critical page payload, and readable severity/action language.
- **Release relevance:** **High**.

### 6) Government/NGO reporting formats + NGO field reports
- **Lead role:** Training & Implementation Specialist
- **Squad owner:** Partnerships, Validation & Pilot Adoption
- **Implementation sketch:** Add downloadable report templates (SitRep, exposure brief, action checklist) and structured field observation form integration.
- **Acceptance criteria:** Pilot partners can submit and view field reports linked to event IDs and generate standard briefing outputs.
- **Release relevance:** **High**.

### 7) Public safety disclaimers and local-time communication
- **Lead role:** Critical End User (with Technical Writer)
- **Squad owner:** Public Dashboard & Mobile UX
- **Implementation sketch:** Standardize advisory disclaimer blocks (machine confidence, uncertainty, not a sole evacuation authority) and enforce PKT local-time display for public outputs.
- **Acceptance criteria:** Every public alert includes disclaimer, confidence tier, and Pakistan local time (UTC+05:00).
- **Release relevance:** **Public trust blocker**.

### 8) Known flood-event demo scenarios for training/adoption
- **Lead role:** Field Validation Coordinator
- **Squad owner:** Partnerships, Validation & Pilot Adoption
- **Implementation sketch:** Package replayable known-event scenarios (e.g., monsoon case studies) for onboarding and workflow drills.
- **Acceptance criteria:** At least two scenario replays available with expected outputs, decisions, and lessons-learned notes.
- **Release relevance:** **High**.

## UX and End-User Improvements

### GIS Analyst
- **Current pain points:** Split stacks and uncertain data lineage; limited uncertainty annotation; limited advanced layer controls in canonical public path.
- **Needed improvements:** Single analyst workspace with source-scene lineage, before/after layers, QA flags, and breach checklist integration.
- **Acceptance criteria:** Analyst can review an event from source scenes to publish decision without leaving one workflow view.

### Flood Response Officer
- **Current pain points:** Outputs are data-rich but not action-packaged for district operations.
- **Needed improvements:** District-level action summary, severity tiers, recommended immediate actions, and affected critical assets list.
- **Acceptance criteria:** Officer can export district response brief in under 2 minutes with confidence and uncertainty context.

### Public API Consumer
- **Current pain points:** Canonical vs prototype ambiguity and limited formal versioning/conformance narrative.
- **Needed improvements:** Stable `/v1/public` contract, changelog policy, example payloads, and conformance notes.
- **Acceptance criteria:** External integrator can pass contract tests across releases without undocumented breaking changes.

### First-Time Developer
- **Current pain points:** Two API entrypoints and mixed prototype/canonical modules increase onboarding confusion.
- **Needed improvements:** One official quickstart path, clear module ownership map, and release-focused local runbook.
- **Acceptance criteria:** New developer can run canonical API + one end-to-end scenario in <30 minutes.

### Government/NGO Decision-Maker
- **Current pain points:** Workflow governance, approval authority, and institutional reporting format not fully operationalized.
- **Needed improvements:** Approval-traceable dashboards, NDMA/PDMA-aligned reporting templates, and field verification status indicators.
- **Acceptance criteria:** Decision-maker can identify current status, confidence, and accountable approver for each published alert.

### Public Citizen User
- **Current pain points:** Technical confidence signals may be misunderstood without simplified wording and action guidance.
- **Needed improvements:** Clear warning levels, concise do/don’t actions, bilingual communication, and clear “official confirmation” distinction.
- **Acceptance criteria:** Public page presents severity, location, recommended actions, disclaimer, and local time in plain language.

