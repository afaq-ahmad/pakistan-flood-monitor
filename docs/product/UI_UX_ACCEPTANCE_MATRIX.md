# UI/UX Acceptance Matrix — Pakistan Flood Monitor

> **Version:** 1.0 · **Date:** 2026-11-18 · **Branch:** `feat/ui-ux-redesign`
> **Prerequisites:** `AGENTS.md`, `docs/product/UI_UX_IMPROVEMENT_PLAN.md`, `MASTER_TASK_PLAN.md`

## 1. Overview

This matrix defines the acceptance criteria and current verification status for end-user interaction
scenarios across resident, farmer, livestock owner, community volunteer, analyst, and operations personas.

Status definitions:
- **PASS**: Verified by automated test (AppTest / pytest) or validated inspection.
- **FAIL**: Verified defect or missing behavior against acceptance criteria.
- **UNTESTED**: Not yet verified in an automated or manual test run.
- **BLOCKED**: Blocked on external dependency (e.g., live provider, hardware/browser socket limitation).

## 2. End-to-End Persona Scenarios

| Scenario ID | Persona | Starting Page | Action | Expected Visual Result | Actual Current Result | Acceptance Criterion | Test Method | Status |
|---|---|---|---|---|---|---|---|---|
| UX-001 | Resident | Homepage (`streamlit_app.py`) | Open homepage in demo mode | Clear navigation hub categorized by audience, demo banner, link to official info | Minimal 24-line stub with single metric and single link | Homepage clearly routes residents, analysts, and operators without overwhelming sidebar | AppTest (`test_homepage_navigation.py`) | FAIL |
| UX-002 | Resident | Public Dashboard (`pages/1_🌍_Public_Dashboard.py`) | View local river corridor flood alerts | Corridor dropdown, clear status per corridor, official disclaimer | Shows corridor filter and published event list, but requires manual map toggle | Filter functions; empty corridors show clear explanation, not blank screen | AppTest (`test_streamlit_public_pages.py`) | PASS |
| UX-003 | Farmer | Farmer Preparedness (`pages/17_🌾_Farmer_Preparedness.py`) | Read crop and grain storage guidance | Sourced agricultural safety guidance (FAO/NDMA/PARC), demo banner, no fake live data | Comprehensive text guidance with source attribution and demo banner | No fabricated observations; clear attribution and limitations present | AppTest (`test_preparedness_pages.py`) | PASS |
| UX-004 | Livestock Owner | Livestock Preparedness (`pages/18_🐄_Livestock_Preparedness.py`) | Check emergency fodder and animal welfare checklist | Sourced animal evacuation and fodder guidance; disclaimer that local service availability is unverified | Guidance displayed with explicit notice that veterinary/shelter availability is unverified | Explicit service availability disclaimer present; no fake veterinary contacts | AppTest (`test_preparedness_pages.py`) | PASS |
| UX-005 | Community Reporter | Field Reports (`pages/3_📱_Field_Reports.py`) | Try community practice reporting | Practice preview with standard categories, consent checkbox, pilot corridor selector | Practice preview renders and explains nothing is saved; no unbacked receipt | Clear practice notice; no submission to moderation queue; consent required | AppTest (`test_safety_gates_and_community_reporting.py`) | PASS |
| UX-006 | Analyst | Analyst Review (`pages/2_👨‍💻_Analyst_Review.py`) | Access candidate review queue in API mode | Requires API review credential; shows paginated candidates without local CSV fallback | Secure token input renders; handles unavailable API gracefully | Fail closed on missing/invalid auth; no silent local file edits | AppTest (`test_dashboard_api_fail_closed.py`) | PASS |
| UX-007 | Resident / Farmer | Official Information (`pages/16_📚_Official_Information.py`) | Find verified contact info and bulletins | Curated links to PMD/FFD, NDMA, and PDMAs with reviewed-on date | Static HTTPS directory with explicit date stamp and safety disclaimer | All links valid HTTPS; explicit warning that page does not auto-monitor warnings | AppTest (`test_official_sources_directory.py`) | PASS |
| UX-008 | Partner / NGO | Partner Mode (`pages/4_🤝_Partner_Mode.py`) | Generate event brief and advisory card | Watermarked advisory card with clear limitations | Watermarked card generated in demo mode; download text option | Watermark prepended; clear instructions to consult NDMA/PDMA | AppTest (`test_p0003_exposure_boundary.py`) | PASS |
| UX-009 | GIS Analyst | Export Center (`pages/5_📤_Export_Center.py`) | Download GeoJSON demo package | Watermarked GeoJSON point and provenance manifest download | GeoJSON and manifest generated and downloadable in demo mode | Disabled in operational mode; clear demo labels on artifacts | AppTest (`test_p0003_exposure_boundary.py`) | PASS |
| UX-010 | Operations | Operations (`pages/7_⚙️_Operations.py`) | Check pipeline freshness SLA and run history | Live pipeline metrics, clear SLA indicator (fresh/watch/stale) | Static display; run trigger buttons display bash command snippets | Buttons should be clearly labelled as reference commands, not live triggers | AppTest / Visual | FAIL |
| UX-011 | Researcher | Flood Forecasting (`pages/13_🔮_Flood_Forecasting.py`) | View 14-day predictive water level model | Operational fail-closed gate; demo watermark; research disclaimer; NO evacuation notices | Operational mode refuses execution; demo displays research prototype with Plotly/native chart | Operational fail-closed; no machine evacuation orders; official bulletins cited | AppTest (`test_safety_gates_and_community_reporting.py`) | PASS |
| UX-012 | Researcher | Dam Flood Risk (`pages/15_🏗️_Dam_Flood_Risk.py`) | Check reservoir storage and breach risk | Operational fail-closed gate; demo watermark; research disclaimer; NO alarmist alerts | Operational mode refuses execution; demo displays synthetic estimates with WAPDA disclaimers | Operational fail-closed; no alarmist unverified breach warnings | AppTest (`test_safety_gates_and_community_reporting.py`) | PASS |

## 3. High-Priority Defect Matrix

| ID | Page | Issue / Defect | Remediation Target | Priority | Status |
|---|---|---|---|---|---|
| DEF-001 | Homepage | Minimal 24-line entrypoint lacks audience routing and discoverability | Add structured audience navigation cards/links | High | PENDING |
| DEF-002 | Sidebar | All 18 pages flatly listed with emojis without grouping | Group pages visually or logically by audience persona | Medium | PENDING |
| DEF-003 | Pages 6, 7, 9, 11, 14 | Missing explicit DEMO_WATERMARK when running in demo mode | Add `st.warning(DEMO_WATERMARK)` | Medium | PENDING |
| DEF-004 | Page 6 (ML Training) | Retraining buttons display code snippets rather than executing or explaining status | Label controls clearly as reference commands | Low | PENDING |
| DEF-005 | Page 7 (Operations) | Diagnostics table is hardcoded without indicating placeholder status | Add explicit disclaimer that diagnostics table is simulated | Low | PENDING |
| DEF-006 | Mobile/Accessibility | 360px viewport reflow and keyboard navigation order | Test and adjust container widths and expander nesting | High | BLOCKED (Socket) |
