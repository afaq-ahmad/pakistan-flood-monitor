# Pakistan Flood Monitor — Remaining Work Documentation

## Current checkpoint · 18 November 2026

Baseline `90062a0` on main includes PRs #89–91. The full offline suite passed
333 tests with 480 warnings here. No open PR or issue owned PK-006 at intake.

| Existing task | Implemented on main | Remaining acceptance |
|---|---|---|
| PK-006 / FL-05 (selected) | Eight categories and a standalone demo form. The submit handler hashes the input and displays a receipt without saving a report or adding it to a queue. | Practice preview verified in draft PR #92. Browser and assistive-technology acceptance remain open. |
| PK-006 / P1-002 / SEC-001 | Authorized internal API and demo fixture moderation | Agree on reporter identity, consent, retention, coarse location and private retrieval. Acknowledge operational submissions only after a durable write. Verify retry, restart and rollback before enabling resident intake. |
| PK-011 / FL-08, FL-03, FL-09 | PR #91 added forecast/dam operational gates and corrected historical language and rainfall result counts. | Independent provider and scientific validation remain open. |
| PK-001 / PK-003 / PK-010 | Corridor lookup, source directory and English preparedness guides | Verify small-screen and keyboard journeys, review Urdu with people and validate administrative coverage before expanding it. |
| PK-007 | Exposure prerequisites specified | Licensed boundaries, consent, validated extent, CRS/time alignment, crop and model uncertainty, and independent loss evidence remain outstanding. |

## Findings and verification

| FL-05 end-user journey | Result on this branch | Evidence |
|---|---|---|
| Preview a fictional agricultural report, then repeat | Practice form displays the selected category, configured corridor and date. No free-text identity field, receipt or queued status. | Streamlit AppTest checks UI output, total report count and unchanged CSV bytes on two consecutive actions. |
| Open Field Reports without usable moderation data | Practice is available independently. Fixture moderation displays unavailable. | Missing, empty and incomplete CSV cases. |
| Open Field Reports without configured coverage | Explicit unavailable message for practice. Existing fixture moderation is accessible. | AppTest with an empty corridor list. |
| Open in operational or API-backed mode | Resident intake and local moderation are unavailable. | Three mode combinations check for absent actions and zero CSV reads or mutations. |
| Submit a real report and track it through review | BLOCKED | The demo cannot issue a durable receipt. The authorized internal API does not offer private resident intake. |

Baseline 333 passed. Six focused acceptance cases failed before the page edit.
After implementation 29 focused tests and all 336 offline tests passed. See the
[QA matrix](../product/FARMER_LIVESTOCK_QA_MATRIX.md) for the other user journeys.

## Other pending work

| Task | Remaining dependency or verification |
|---|---|
| P0-001 / UI-001 / ENG-001 | Browser acceptance, dashboard flow coverage and hosted CI execution. |
| P1-001 / P1-002 / P1-003 | Worker lease/fencing decisions, transactional review and audit storage, reviewed products. |
| DATA-001 / GIS-001 / PK-008 / PK-011 | Traceable environmental sources, spatial and temporal validation, river observations and evaluated forecasting. |
| PK-002 / PK-003 / PK-010 | Revalidate official links, review Urdu, and exercise the area lookup and preparedness guides on slow connections and small screens. |
| PK-004 / PK-005 / PK-009 | Approved shareable products, consent, delivery confirmation and expiry. Relief listings need verified service ownership and availability. |
| SEC-001 / OPS-001 | Outstanding privacy and authorization boundaries, PostgreSQL and deployed runtime verification. |

**Next PK-006 task:** specify the private receipt lifecycle, including who may
retrieve it, what is retained, and what happens after a failed commit or a
retry following restart. Use that contract to write acceptance tests before
enabling operational intake. Individual tasks and dependencies are tracked in
the [master plan](MASTER_TASK_PLAN.md).
