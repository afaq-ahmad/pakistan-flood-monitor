# Pakistan Flood Monitor — Remaining Work Documentation

## Current checkpoint · 18 November 2026

Baseline `90062a0` on main includes PRs #89–91. The full offline suite passed
333 tests with 480 warnings here. No open PR or issue owned PK-006 at intake.

| Existing task | Implemented on main | Remaining acceptance |
|---|---|---|
| PK-006 / FL-05 (selected) | Eight categories and a standalone demo form. The submit handler hashes the input and displays a receipt without saving a report or adding it to a queue. | Show a practice preview with category, configured corridor and date. Avoid collecting real descriptions or implying delivery. Keep it available when example moderation rows are missing. |
| PK-006 / P1-002 / SEC-001 | Authorized internal API and demo fixture moderation | Agree on reporter identity, consent, retention, coarse location and private retrieval. Acknowledge operational submissions only after a durable write. Verify retry, restart and rollback before enabling resident intake. |
| PK-011 / FL-08, FL-03, FL-09 | PR #91 added forecast/dam operational gates and corrected historical language and rainfall result counts. | Independent provider and scientific validation remain open. |
| PK-001 / PK-003 / PK-010 | Corridor lookup, source directory and English preparedness guides | Verify small-screen and keyboard journeys, review Urdu with people and validate administrative coverage before expanding it. |
| PK-007 | Exposure prerequisites specified | Licensed boundaries, consent, validated extent, CRS/time alignment, crop and model uncertainty, and independent loss evidence remain outstanding. |

The sections below preserve the planning snapshot from PRs #90–91. The current
checkpoint above supersedes their status labels and next-session instructions.

## 1. Completed Work (Merged to Main)

| Task | Status | PR | Evidence |
|---|---|---|---|
| P0-001 API fail-closed | PARTIAL | PR #84 | 8 focused tests; browser pending |
| P0-002 Review fallback | COMPLETE | PR #84 | 8 focused tests |
| P0-003 Exposure boundary | COMPLETE | PR #84 | 16 focused + 228 full |
| ENG-001 GitHub workflow | PARTIAL | PR #83 | 7 tests; hosted CI pending |
| UI-001 Dashboard audit | PARTIAL | PRs #85, #86 | 269 tests; analyst queue done |
| PK-001 My Area | PARTIAL | PRs #87, #88 | Corridor selector + reference list; 278 tests |
| PK-002 Official sources | PARTIAL | Community | Static FFD/NDMA links |
| PK-006 Community reports | PARTIAL | PRs #89, #90 | FL-05 boundary fixes, category taxonomy & consent rules |
| PK-007 Farmers & livestock | BLOCKED | PR #90 | 9 prerequisites documented in exposure spec; kept BLOCKED |
| PK-010 Preparedness | PARTIAL | PR #90 | Farmer (`pages/17`) & Livestock (`pages/18`) guides; 17 tests |

## 2. Work In This Workstream

| Item | Focus | Status |
|---|---|---|
| FL-08 P0 Forecast presentation risk | Gate operational forecast, eliminate evacuation wording, add watermark | In progress |
| FL-08 P0 Dam risk presentation risk | Gate operational dam analysis, eliminate alarmist alerts, add watermark | In progress |
| FL-09 NASA Hydromet counter | Fix misleading success count on failed corridor retrievals | In progress |
| FL-03 Historical Map ground truth | Remove unsupported "ground truth" claims, add disclaimer & watermark | In progress |
| FL-05 / PK-006 Resident report workflow | Add community reporting UI, consent, and category integration | In progress |

## 3. Remaining Work — By Priority

### Priority 1: PK-001 My Area (PARTIAL → needs browser/mobile)

**What exists:** Corridor selector, reference names on empty feeds, official link.

**What's missing:**
- [ ] Browser/mobile rendering at 360px with keyboard navigation
- [ ] District/tehsil/mouza validated ID mapping (BLOCKED on partner data)
- [ ] Reviewed observations with source/issue times (BLOCKED on P1-003)
- [ ] Chromium/hosted CI verification (BLOCKED on environment)

### Priority 2: PK-010 Preparedness Content (IN PROGRESS)

**What exists (this branch):** Farmer and Livestock pages with sourced guidance.

**What's missing:**
- [ ] Human-reviewed Urdu translations (PK-003 subtask)
- [ ] Mobile/low-bandwidth testing
- [ ] Link revalidation schedule
- [ ] Integration into Historical/Preparedness explorer page

### Priority 3: PK-006 Community Reports (PARTIAL)

**What exists:** Demo mode gating, moderation feedback, receipt idempotency.

**What's missing:**
- [ ] Resident-facing submission form with consent
- [ ] Agricultural report categories (crop damage, livestock, fodder, irrigation, road, equipment, water)
- [ ] Privacy/data minimization controls
- [ ] Submission acknowledgement workflow
- [ ] Duplicate/spam detection
- [ ] Durable persistence (BLOCKED on P1-002)
- [ ] Per-reporter identity and consent tracking
- [ ] Safe error handling for write failures in operational mode

### Priority 4: PK-007 Farmers and Livestock Exposure (BLOCKED)

**What's missing (all BLOCKED):**
- [ ] Licensed field boundaries
- [ ] Informed consent and access control
- [ ] Validated flood extents
- [ ] CRS/projection validation
- [ ] Spatial/temporal alignment
- [ ] Baseline vs new inundation comparison
- [ ] Crop identification with uncertainty
- [ ] Model uncertainty quantification
- [ ] Estimated exposure vs verified loss separation

**Prerequisites:** DATA-001, GIS-001, PK-006

### Priority 5: Infrastructure and Operations

| Task | Status | Blocker |
|---|---|---|
| P1-001 Worker recovery | BLOCKED | Needs fencing/lease design |
| P1-002 Durable review state | BLOCKED | Needs persistence contract |
| P1-003 Reviewed products | PARTIAL | Needs P1-002, DATA-001 |
| DATA-001 Real data processing | BLOCKED | Needs source access and validation |
| GIS-001 Spatial audit | NOT_STARTED | Needs DATA-001 |
| SEC-001 Security audit | PARTIAL | Remaining trust boundaries |
| OPS-001 Deployment | BLOCKED | Docker/PostgreSQL unavailable |
| PK-003 Urdu/accessibility | PARTIAL | Needs human review |
| PK-004 Sharing cards | NOT_STARTED | Needs P1-003, PK-003 |
| PK-005 Relief directory | BLOCKED | Needs P1-002, SEC-001 |
| PK-008 River observations | BLOCKED | Needs DATA-001 |
| PK-009 Partner/NGO info | PARTIAL | Needs P1-002, SEC-001 |
| PK-011 Validated forecasting | BLOCKED | Needs DATA-001; FL-08 P0 risk |

---

## 4. Critical Gaps (High Impact)

### 4.1 FL-08: Prototype Forecast and Dam — P0 Presentation Risk

The forecast page can display evacuation-style language from untrained model
weights.  Missing dam imagery can produce a synthetic number marked as
satellite proxy.  **Neither should be reachable in operational mode.**

- **Action needed:** Gate forecast and dam pages behind demo/test mode in
  operational config.  Add offline AppTest with injected provider.
- **Task:** PK-011
- **Severity:** P0 presentation risk

### 4.2 NASA Hydromet Success Counter (FL-09)

Auto-load shows "6 successful" after 6 provider errors.  The count measures
attempted corridors, not successful data retrieval.

- **Action needed:** Distinguish attempted from successful retrieval.
- **Task:** UI-001 / DATA-001

### 4.3 No Resident Submission Workflow (FL-05)

Internal report intake requires role credentials.  No public/resident form
exists.  Community members cannot submit reports.

- **Action needed:** Design consent, categories, acknowledgement workflow.
- **Task:** PK-006 (prerequisite: P1-002, SEC-001)

### 4.4 Historical Map "Ground Truth" Language (FL-03)

Bundled JSON outlines are described as ground truth.  They are approximate
and unverified.

- **Action needed:** Replace language; add source, date, resolution, and
  confidence disclaimers.
- **Task:** PK-010

---

## 5. Test Coverage Summary

| Test File | Tests | Coverage Area |
|---|---|---|
| test_preparedness_pages.py | 17 | Farmer & livestock pages (NEW) |
| test_field_report_boundaries.py | 15 | FL-05 mode/moderation boundaries |
| test_streamlit_public_pages.py | 12+ | Public dashboard states |
| test_p0003_exposure_boundary.py | 16 | Demo/exposure modes |
| test_dashboard_api_fail_closed.py | 8 | API fail-closed |
| test_canonical_review_queue.py | 25 | Analyst queue |
| test_streamlit_analyst_queue.py | 10 | Streamlit analyst viewer |
| test_standalone_dashboard_boundary.py | 3 | Standalone prototype |
| test_streamlit_demo_export.py | 7 | Demo export |
| test_official_sources_directory.py | 9 | Source links |
| test_agent_git_workflow.py | 7 | Git workflow helpers |
| Others | 150+ | API, pipeline, ML, services |

---

## 6. Next Implementation Steps (This Session)

1. ✅ Commit farmer + livestock preparedness pages with tests
2. ⬜ Add agricultural report category model for PK-006 prerequisites
3. ⬜ Document agricultural exposure specification (keep BLOCKED)
4. ⬜ Update MASTER_TASK_PLAN.md and AGENT_SESSION_LOG.md
5. ⬜ Run full regression suite
6. ⬜ Push and open/update draft PR
7. ⬜ Record handoff
