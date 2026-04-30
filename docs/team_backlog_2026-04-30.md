# Team-Based Implementation Backlog (2026-04-30)

Active roles:
- Lead role: Technical Project Manager / Scrum Lead
- Supporting roles: Senior Product Manager, Program Director, Engineering Lead, QA Lead, Release Manager
- Why these roles are needed: This backlog translates audit findings into sequenced, owned, testable work for a 12-month launch program.

## Team-Based Implementation Backlog

| Rank | Task | Owner Squad | Lead Role | Supporting Roles | Impact | Effort | Dependencies | Acceptance Criteria | Release Relevance |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Move canonical runtime state (runs/events/reviews/audit) from in-memory stores to PostGIS | A | Engineering Lead | Backend Engineer, DB Engineer, QA Lead | Trust + reliability | XL | Schema design, migration plan | Restart-safe persistence; multi-instance consistency tests pass; no in-memory globals used for canonical state | Must-have for trust (pilot blocker) |
| 2 | Bind privileged actor identity to authenticated principal (remove payload actor trust) | F | Application Security Engineer | Backend Engineer, QA Lead | Security trust | M | Task 1 auth schema alignment | Spoof tests fail; audit entries store principal_id from auth claims only | Must-have for trust (pilot blocker) |
| 3 | Implement append-only immutable audit log with integrity checks | F | Application Security Engineer | Backend Engineer, Release Manager | Legal/forensic trust | L | Task 1 | Tamper-evidence verified; restore attempts logged and signed | Must-have for trust |
| 4 | Canonicalize API stack to `src/pakistan_flood_monitor` and deprecate prototype runtime entrypoint | A | Engineering Lead | Technical Writer, Release Manager | Maintainability + integration confidence | M | Compatibility review | One official runtime path; deprecation notice and migration guide published | Must-have for trust |
| 5 | Promote SAR preprocessing pipeline into canonical flow (scene-derived features) | B | Remote Sensing / SAR Lead | EO Pipeline Engineer, Geospatial QA Engineer | Scientific credibility | XL | Task 4, data contracts | Runner features are computed from real assets; deterministic feature snapshots saved | Must-have for trust (pilot blocker) |
| 6 | Add source-scene lineage package (STAC-like metadata at run/event level) | B | Data Architect | EO Pipeline Engineer, Backend Engineer | Reproducibility | L | Task 5, Task 1 | Each event includes source scene IDs, processing version, thresholds/model refs | Must-have for trust |
| 7 | Implement analyst approval lifecycle (draft→review→approved→published→retracted) with strict state transitions | D | Senior Product Manager | Backend Engineer, QA Lead | Governance + safety | M | Task 1, Task 2 | Invalid transitions blocked; full approval trace visible in API/UI | Must-have for trust |
| 8 | Build known-event validation suite (historical benchmark pack) and publish monthly accuracy reports | B | QA Lead | SAR Lead, Hydrology Lead, Field Validation Coordinator | Scientific confidence | L | Task 5, Task 6 | Precision/recall + false-positive trend reported per corridor monthly | Must-have for trust |
| 9 | Create public limitations/disclaimer page and API disclaimers (confidence + intended-use warnings) | E | Technical Writer | UX Lead, Govt/NGO Liaison | Public safety communication | S | Task 7 | Every public alert and API response links to limitations statement | Must-have for trust |
| 10 | RBAC hardening + token policy (rotation, expiry, role separation) | F | Application Security Engineer | DevOps Engineer, Release Manager | Security baseline | M | Task 2 | Role misuse tests pass; token expiry/rotation runbook verified | Must-have for trust |
| 11 | District/tehsil risk summary endpoint + provincial rollups | C | Senior Product Manager | Exposure Modeler, GIS Analyst | Decision usability | L | Task 1, baseline datasets | District/tehsil tables available and sortable by risk/exposure | Must-have for usability |
| 12 | Rebuild exposure model from scalar multipliers to spatial overlays (population, roads, health, schools, cropland) | C | Exposure & Impact Modeler | GIS Analyst, Data Architect | Actionability | XL | Task 1, baseline layer ingestion | Exposure outputs reproducible from overlays with lineage and uncertainty bounds | Must-have for trust + usability |
| 13 | Analyst dashboard unification with lineage, QA flags, and review controls | E | UX Lead | Frontend Engineer, Backend Engineer | Operational efficiency | L | Task 4, Task 7 | Analyst can complete review in one workflow with provenance visible | Must-have for usability |
| 14 | Public map mobile-first redesign (low bandwidth mode) | E | UX Lead | Frontend Engineer, Critical End User | Public accessibility | M | Task 9 | Core advisory view <500KB; readable on low-end mobile | Must-have for usability |
| 15 | Alert templates for NDMA/PDMA-style workflows + official/public variants | D | Government / NGO Liaison | Product Manager, Technical Writer | Institutional adoption | M | Task 7 | Template set supports internal official + public-safe outputs | Must-have for usability |
| 16 | API examples and contract reference pack (success/failure, versioning) | A | Backend Engineer | Technical Writer, QA Lead | Developer adoption | S | Task 4 | Contract docs include examples and are validated by tests | Must-have for usability |
| 17 | PDF Situation Report generator (district priorities, actions, contacts) | G | Training & Implementation Specialist | Exposure Modeler, Govt Liaison | Field response usability | M | Task 11, Task 12 | One-click SitRep export produced from latest reviewed event | Must-have for usability |
| 18 | Demo dataset and scenario replay kit (known flood events) | G | Field Validation Coordinator | QA Lead, Training Specialist | Training + pilot readiness | M | Task 8 | At least two replay scenarios with expected outputs and checklist | Must-have for usability |
| 19 | Urdu public alert templates | E | UX Lead | Govt Liaison, Technical Writer | Public accessibility | S | Task 15 | Urdu + English toggle available for alerts and advisories | Nice-to-have (high value) |
| 20 | SMS/email/WhatsApp outbound adapters (opt-in channels) | D | Senior Product Manager | DevOps Engineer, Govt Liaison | Dissemination reach | M | Task 15 | Alert payloads sent via configured channel adapters with audit traces | Nice-to-have |
| 21 | Before/after imagery viewer and event timeline | E | Frontend Engineer | SAR Lead, GIS Analyst | Trust + interpretability | M | Task 5, Task 13 | Users can compare temporal layers and event evolution | Nice-to-have |
| 22 | Export center (GeoJSON/COG/GeoParquet + metadata manifest) | C | Data Architect | GIS Analyst, Backend Engineer | Interoperability | L | Task 6, Task 12 | Exports pass format validators and include provenance manifest | Nice-to-have |
| 23 | QGIS plugin integration workflow docs/assets | E | GIS Analyst | Technical Writer, Backend Engineer | Analyst ecosystem adoption | M | Task 22 | QGIS import workflow documented and validated with sample data | Nice-to-have |
| 24 | Probabilistic forecasting + uncertainty envelopes | B | Hydrology / Flood Risk Lead | ML Engineer, SAR Lead | Advanced forecast quality | XL | Tasks 5, 8, 12 | Forecast outputs include calibrated uncertainty metrics | Future advanced |
| 25 | Crowdsourced field report ingestion and moderation loop | G | Field Validation Coordinator | AppSec Engineer, QA Lead | Ground-truth loop | L | Task 7, Task 18 | Field reports linked to event IDs with moderation/audit workflow | Future advanced |
| 26 | Automated damage classification (housing/infrastructure classes) | C | Exposure & Impact Modeler | EO Engineer, ML Engineer | Impact depth | XL | Task 12, Task 24 | Damage class outputs validated on benchmark sample | Future advanced |
| 27 | Evacuation route intelligence and shelter proximity overlays | C | Senior Product Manager | GIS Analyst, Govt Liaison | Response actionability | L | Task 11, Task 12 | District report includes route/shelter constraints for major events | Future advanced |
| 28 | Multi-hazard expansion framework (flood + landslide/heat integration hooks) | A | Program Director | Engineering Lead, Data Architect | Strategic scale | XL | Task 4, Task 24 | Architecture supports pluggable hazard modules without API breakage | Future advanced |

## Minor Things and Quick Wins

1. **File path:** `README.md`  
   **Issue:** Two runtime stacks are described, but deprecation timeline for prototype stack is not explicit.  
   **Fix:** Add “canonical runtime from date X” note and migration path for integrators.  
   **Effort:** XS  
   **Owner role:** Technical Writer

2. **File path:** `docs/runtime_api_contract.md`  
   **Issue:** Limited failure/negative response examples for integrators.  
   **Fix:** Add 401/403/404/429/500 examples with troubleshooting notes.  
   **Effort:** S  
   **Owner role:** Backend Engineer

3. **File path:** `tests/test_api_implementation.py`  
   **Issue:** Tests still model client-provided `actor` usage pattern.  
   **Fix:** Add/update tests to assert actor is derived from auth principal and payload actor is ignored/rejected.  
   **Effort:** S  
   **Owner role:** Test Automation Engineer

4. **File path:** `src/pakistan_flood_monitor/pipeline/runner.py`  
   **Issue:** Fixed feature literals reduce scientific credibility.  
   **Fix:** Add TODO markers + feature-source interface hooks to prepare ingestion wiring.  
   **Effort:** S  
   **Owner role:** Remote Sensing / SAR Lead

5. **File path:** `docs/release_checklist.md`  
   **Issue:** Checklist is manual and not mapped to CI gate commands.  
   **Fix:** Add command-level release gates and pass/fail evidence requirements.  
   **Effort:** S  
   **Owner role:** Release Manager

