# UI/UX Improvement Plan — Pakistan Flood Monitor

> **Version:** 1.0 · **Date:** 2026-11-18 · **Branch:** `feat/ui-ux-redesign`
> **Prerequisite reads:** `AGENTS.md`, `docs/adr/ADR-001-canonical-runtime.md`, `MASTER_TASK_PLAN.md`

## 1. Executive Summary

The Pakistan Flood Monitor has 18 Streamlit pages, a homepage, and a standalone HTML dashboard. Despite
significant functional depth, user experience is fragmented by technology-first navigation, inconsistent
page structures, and audience-unclear groupings. Public safety pages compete for sidebar space with
specialist ML, SAR, and training pages. Many pages lack demo/operational mode separation, error states,
empty states, or loading indicators. This plan prioritizes improvements that make existing features
discoverable, understandable, and usable — not new feature development.

## 2. User Personas and Primary Journeys

| Persona | Pages They Need First | Current Pain |
|---|---|---|
| Resident / Farmer | Home → Public Dashboard → My Area → Farmer/Livestock Preparedness → Official Info | Pages 10–15 (specialist) clutter the sidebar; no audience filter |
| Community Reporter | Field Reports (page 3) | Only available in demo mode; practice form is hidden |
| Analyst | Analyst Review (page 2) → Satellite Viewer (page 9) → ML Water Detection (page 11) | API-mode queue requires a password; demo mode shows all 7 attestation checkboxes unchecked by default |
| Operations Staff | Operations (page 7) → Settings (page 8) | Hardcoded health statuses; buttons only display shell commands |
| Partner / NGO | Partner Mode (page 4) → Export Center (page 5) | Partner page has no access control; export is demo-only |
| ML Researcher | ML Training (page 6) → Advanced ML SAR (page 14) → Flood Forecasting (page 13) | Buttons show shell commands, not results; forecasting gated in operational |

## 3. Current Navigation Audit

### Sidebar Structure (Technology-First)
```
🌊 Pakistan Flood Monitor
├── 🌍 Public Dashboard
├── 👨‍💻 Analyst Review
├── 📱 Field Reports
├── 🤝 Partner Mode
├── 📤 Export Center
├── 🧠 ML Training
├── ⚙️ Operations
├── 🔑 Settings
├── 🛰️ Satellite Viewer
├── 🌧️ NASA Hydromet
├── 🤖 ML Water Detection
├── 🗺️ Historical Flood Map
├── 🔮 Flood Forecasting
├── 🧠 Advanced ML SAR
├── 🏗️ Dam Flood Risk
├── 📚 Official Information
├── 🌾 Farmer Preparedness
└── 🐄 Livestock Preparedness
```

### Problems
1. No grouping by audience: a farmer sees ML Training before Farmer Preparedness.
2. Two pages use the same emoji (🧠): ML Training and Advanced ML SAR.
3. Official Information is buried at page 16 — it should be prominent.
4. Homepage has minimal content (24 lines); no navigation hub.
5. No "My Area" standalone page; it is embedded in Public Dashboard.

## 4. Proposed Navigation Redesign

### User-Oriented Groups (Recommended)

```
🌊 Pakistan Flood Monitor ─ Home
│
├── 👤 For Residents
│   ├── 🌍 Public Dashboard (My Area)
│   ├── 📚 Official Information
│   ├── 🌾 Farmer Preparedness
│   ├── 🐄 Livestock Preparedness
│   └── 📱 Community Reports
│
├── 🔬 Research & Analysis
│   ├── 🛰️ Satellite Viewer
│   ├── 🌧️ NASA Hydromet
│   ├── 🤖 ML Water Detection
│   ├── 🗺️ Historical Flood Map
│   ├── 🔮 Flood Forecasting (demo)
│   ├── 🧠 Advanced ML SAR (demo)
│   └── 🏗️ Dam Flood Risk (demo)
│
├── 📋 Review & Operations
│   ├── 👨‍💻 Analyst Review
│   ├── 🤝 Partner Mode
│   ├── 📤 Export Center
│   ├── ⚙️ Operations
│   └── 🔑 Settings
│
└── 🎓 Training & Models
    └── 🧠 ML Training
```

### Implementation Approach
Streamlit does not natively support grouped sidebar navigation. Options:
1. **st.sidebar sections with markdown headers** (simplest, compatible, chosen).
2. `st.navigation` / `st.Page` (Streamlit ≥ 1.36, requires restructuring).
3. Custom CSS injection for sidebar dividers.

**Chosen: Option 1** — Add `st.sidebar.markdown("---")` and `st.sidebar.markdown("### Section")` in the
homepage to create visual grouping. This requires no Streamlit version changes and is immediately testable.

## 5. Homepage Redesign

### Current State
The homepage (`streamlit_app.py`) has 24 lines: title, event count, and a single Official Information link.

### Proposed Changes
1. Add a brief system description and safety disclaimer.
2. Add quick navigation links to the four audience groups using `st.page_link`.
3. Show overall system status (demo/operational, event count, freshness).
4. Keep the Official Information link prominent at top.
5. Add sidebar grouping headers.

### Wireframe
```
┌─────────────────────────────────────────┐
│ 🌊 Pakistan Flood Monitor               │
│                                         │
│ [Official flood information →]          │
│                                         │
│ ⚠️ DEMO MODE — not operational data     │
│                                         │
│ Published events: 5                     │
│                                         │
│ ── For Residents ──────────────────     │
│ [🌍 Public Dashboard] [📚 Official]     │
│ [🌾 Farmer Safety]  [🐄 Livestock]     │
│                                         │
│ ── Research & Analysis ────────────     │
│ [🛰️ Satellite] [🌧️ Hydromet]          │
│ [🤖 Water Detection] [🗺️ History]      │
│                                         │
│ ── Review & Operations ────────────     │
│ [👨‍💻 Analyst] [🤝 Partner] [📤 Export]  │
│                                         │
│ ⚠️ For emergencies, follow official     │
│    NDMA/PDMA instructions.              │
└─────────────────────────────────────────┘
```

## 6. Per-Page Visual Consistency Audit

| Page | Demo Watermark | Error State | Empty State | Loading State | Official Link | Limitations |
|---|---|---|---|---|---|---|
| Home | ✅ | ✅ | ✅ (empty events) | ❌ | ✅ | ❌ |
| 1 Public Dashboard | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| 2 Analyst Review | ✅ | ✅ | ✅ | ✅ (spinner) | ❌ | ❌ |
| 3 Field Reports | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| 4 Partner Mode | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| 5 Export Center | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| 6 ML Training | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 7 Operations | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 8 Settings | ❌ partial | ❌ | N/A | N/A | ❌ | ❌ |
| 9 Satellite Viewer | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 10 NASA Hydromet | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| 11 ML Water Detection | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ partial |
| 12 Historical Flood Map | ✅ | ✅ | N/A | ❌ | ✅ | ✅ |
| 13 Flood Forecasting | ✅ | ✅ (operational gate) | ✅ | ✅ | ✅ | ✅ |
| 14 Advanced ML SAR | ❌ | ✅ (import guard) | ✅ | ✅ | ❌ | ❌ |
| 15 Dam Flood Risk | ✅ | ✅ (operational gate) | ✅ | ✅ | ❌ | ❌ |
| 16 Official Information | N/A | N/A | N/A | N/A | N/A (is the page) | ✅ |
| 17 Farmer Preparedness | ✅ | ✅ | N/A | N/A | ✅ | ✅ |
| 18 Livestock Preparedness | ✅ | ✅ | N/A | N/A | ✅ | ✅ |

## 7. Priority Improvements (Ordered by Impact)

### Slice 1 — Homepage Navigation Hub (This PR)
- Redesign homepage with audience-oriented navigation links.
- Add sidebar grouping headers.
- Add system status summary.
- Add limitations and safety footer.
- Tests: AppTest for all navigation links, demo/operational modes, empty events.

### Slice 2 — Page Consistency (Next PR)
- Add demo watermark to pages 6, 7, 9, 11, 14 (currently missing).
- Add limitations expander to pages 2, 4, 5, 6, 7, 8, 9, 11, 14, 15.
- Add official information link to pages 2, 3, 4, 5, 9, 11, 14, 15.

### Slice 3 — Specialist Page Gating (Future)
- Pages 6 (ML Training), 7 (Operations), 8 (Settings): add operational mode gates.
- Buttons that only display shell commands should be labelled as reference commands.
- Hardcoded diagnostics table on page 7 should state it is a placeholder.

### Slice 4 — Accessibility and Mobile (Future, Requires Browser)
- Test 360px reflow for all public pages.
- Keyboard navigation order audit.
- RTL/Urdu text rendering audit.
- Color contrast check for status indicators.

## 8. Design System Guidelines

### Typography
- Page titles: `st.title` with emoji prefix matching sidebar.
- Section headers: `st.subheader`.
- Captions for data provenance: `st.caption`.
- Body text: `st.write` or `st.markdown`.

### Status Colors
- 🟢 Healthy / Normal / Approved — green
- 🟡 Watch / Warning / Needs Info — yellow/gold
- 🟠 Elevated / In Review — orange
- 🔴 Critical / Rejected / Failed — red
- ⚪ Unknown / Unavailable — gray

### Mode Indicators
- Demo mode: `st.warning(DEMO_WATERMARK)` at top of every page.
- Operational unavailable: `st.error(...)` with ADR-001 reference.
- API error: `st.error(...)` with specific error message.

### Standard Page Structure
```python
# 1. Imports
# 2. Page config
st.set_page_config(page_title="...", page_icon="...", layout="wide")
# 3. Title
st.title("emoji Page Name")
# 4. Official link (public pages)
st.page_link("pages/16_📚_Official_Information.py", label="Official flood information")
# 5. Mode gate (operational-restricted pages)
# 6. Demo watermark
# 7. Main content
# 8. Limitations expander (bottom)
```

## 9. Interaction Patterns

### Forms
- Always use `st.form` or explicit `st.button` → action pattern.
- Show success/failure feedback after every action.
- Disable buttons when prerequisites are missing.

### Data Loading
- Use `st.spinner` for any network or computation.
- Show `st.progress` for multi-step operations.
- Cache results in `st.session_state` with clear invalidation.

### Error Handling
- Network errors: `st.error(...)` with retry guidance.
- Empty data: `st.info(...)` explaining why no data appears.
- Missing dependencies: `st.warning(...)` with install instructions.

## 10. Accessibility Requirements

- Semantic HTML via Streamlit components (no custom raw HTML for content).
- Text alternatives for all visual indicators (emoji + text, not emoji alone).
- Keyboard-navigable forms and buttons.
- Minimum 4.5:1 contrast ratio for text.
- 360px minimum reflow without horizontal scrolling.
- RTL/Urdu support deferred to PK-003 with human-reviewed translations.

## 11. Mobile Considerations

- Use `layout="wide"` with responsive column counts.
- Avoid fixed-width maps; use `use_container_width=True`.
- Collapse advanced options into `st.expander`.
- Test touch targets ≥ 44px.

## 12. Demo / Operational Mode UX Contract

| State | User Experience |
|---|---|
| Demo (default) | Visible `DEMO_WATERMARK` banner; all features available with synthetic data |
| Operational (no API) | Error message; most pages stop; fail closed per ADR-001 |
| Operational (with API) | Real data; demo-only pages stop with explanation |
| Test | Same as demo but for automated testing |

## 13. Safety Boundaries (Non-Negotiable)

1. Never display evacuation directives from machine scores.
2. Never present model outputs as official warnings.
3. Always link to official NDMA/PDMA sources on public pages.
4. Demo data must always carry `DEMO_WATERMARK`.
5. Exposure figures must be labelled as estimates, not verified damage.
6. Field report receipts are practice previews only until P1-002/SEC-001 complete.

## 14. Testing Strategy

### AppTest Coverage Required for Each Slice
- Page renders without exception in test mode.
- Demo watermark appears when expected.
- Operational gate activates when expected.
- Empty data state renders correctly.
- Error state renders correctly.
- Navigation links point to real pages.
- No fabricated observations in any mode.

### Test Commands
```bash
# Focused test for homepage
APP_MODE=test PYTHONPATH=. .venv/Scripts/python.exe -m pytest tests/test_homepage_navigation.py -v

# Full offline suite
APP_MODE=test PYTHONPATH=. .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```

## 15. Implementation Schedule

| Phase | Scope | Deliverables | Dependencies |
|---|---|---|---|
| 5 (this commit) | Documentation | This plan + acceptance matrix | None |
| 6 (next commit) | GitHub checkpoint | Push docs, open draft PR | Phase 5 |
| 7 (next commits) | Homepage navigation | Redesigned homepage + tests | Phase 6 |
| 8+ (incremental) | Page consistency | Watermarks, links, gates | Phase 7 |

## Appendix A — Existing Task ID Mapping

| This Plan Section | Existing Task IDs |
|---|---|
| Homepage navigation | UI-001, PK-001 |
| Page consistency | UI-001 |
| Accessibility | PK-003 |
| Specialist gating | PK-011, FL-08 |
| Field reports UX | PK-006, FL-05 |
| Partner mode | PK-009 |
| Preparedness pages | PK-010 |
