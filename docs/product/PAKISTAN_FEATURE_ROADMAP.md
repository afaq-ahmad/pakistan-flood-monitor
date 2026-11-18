# Pakistan feature roadmap

The authoritative checklist and task statuses are in [MASTER_TASK_PLAN.md](../engineering/MASTER_TASK_PLAN.md). This document is a design aid, not a second progress tracker. Research and validation are documented in [needs and evidence](PAKISTAN_USER_NEEDS_AND_EVIDENCE.md), [farmer and livestock journeys](FARMER_LIVESTOCK_USER_JOURNEYS.md), and the [QA matrix](FARMER_LIVESTOCK_QA_MATRIX.md).

## Value and feasibility matrix

Scores 1–5: benefit (B), data readiness (D), reuse (R), verifiability (V); effort (E), safety/privacy risk (S), maintenance (M), and partnership dependence (P), where 5 is highest. Scores are provisional engineering judgments, not measured outcomes; rural access and problem frequency inform B. Lower E/S/M/P improves feasibility.

| Feature | B | D | R | V | E | S | M | P |
|---|---:|---:|---:|---:|---:|---:|---:|
| PK-001 My Area | 5 | 2 | 4 | 2 | 4 | 5 | 4 | 3 |
| PK-002 Official source hub | 5 | 4 | 2 | 4 | 1 | 2 | 2 | 1 |
| PK-003 Urdu and low-bandwidth access | 5 | 3 | 3 | 3 | 3 | 3 | 3 | 2 |
| PK-004 Community sharing cards | 4 | 2 | 2 | 3 | 3 | 4 | 3 | 2 |
| PK-005 Verified relief directory | 5 | 1 | 2 | 2 | 4 | 5 | 5 | 5 |
| PK-006 Community reports | 4 | 2 | 4 | 3 | 4 | 5 | 4 | 3 |
| PK-007 Farmers and livestock | 4 | 1 | 3 | 2 | 5 | 5 | 5 | 4 |
| PK-008 River observation explorer | 4 | 1 | 2 | 2 | 4 | 4 | 4 | 4 |
| PK-009 Partner and NGO information | 4 | 2 | 4 | 3 | 4 | 5 | 4 | 3 |
| PK-010 Historical and preparedness explorer | 3 | 2 | 3 | 2 | 3 | 3 | 3 | 3 |
| PK-011 Validated forecasting | 5 | 1 | 3 | 1 | 5 | 5 | 5 | 5 |

## Feature specifications

Common requirements: English and reviewed Urdu where appropriate; text-first mobile access; source and issue/verification dates; explicit unavailable states; no automatic official warnings or evacuation instructions. External data reuse and licensing require provider review. Tests must cover authorization, stale/missing data, accessibility and privacy as relevant. Complexity is provisional.

### PK-001 — My Area
- **Priority/status:** P1 / PARTIAL. **Dependencies:** UI-001, P0-003, P1-003.
- **User/problem:** Pakistani residents, responders or analysts need reliable my area suited to local flood conditions. See the linked needs research; validate with affected communities.
- **Relevant code:** pages/1_🌍_Public_Dashboard.py; backend_service.py; data/corridors.csv; named screens are prototypes unless verified. See linked engineering tasks for exact boundaries.
- **Data/provider:** Validated administrative boundaries and area/corridor mapping. Verify permission, attribution, timestamps and coverage before use.
- **Slice and acceptance:** Audit district data and show no-data/unknown coverage; never infer property risk. Missing or unsupported information must remain unavailable and distinguish official, estimated, reported and simulated content.
- **Frontend:** text-first mobile view with language and accessibility review; communicate uncertainty and no-data. **Backend/model:** preserve source, timestamp, status and lineage; use canonical authorization.
- **Privacy/science:** minimize personal information, moderate reports, validate units/CRS and independently evaluate any model before operational use. **Tests:** offline unit/API/UI, negative, stale and unauthorized cases; no live network dependency.
- **Complexity/blockers:** medium/high; dependent on source access and safety validation. **Next:** Audit district data and show no-data/unknown coverage; never infer property risk.
- **Farmer and community acceptance.** Keep configured corridor names visible before the live event request, including empty, offline, and unconfigured states. Validate licensed district, tehsil and mouza identifiers and aliases separately. Keep parcel and village coverage unknown until verified. Use an exact configured corridor ID selector and reviewed public event association for the next bounded slice. Preserve the all-events view when the association is unavailable.


### PK-002 — Official source hub
- **Priority/status:** P1 / PARTIAL. **Dependencies:** P0-003.
- **User/problem:** Pakistani residents, responders or analysts need reliable official source hub suited to local flood conditions. See the linked needs research; validate with affected communities.
- **Relevant code:** official_sources.py; pages/16_📚_Official_Information.py; named screens are prototypes unless verified. See linked engineering tasks for exact boundaries.
- **Data/provider:** Curated FFD and NDMA links; source permissions for any ingestion. Verify permission, attribution, timestamps and coverage before use.
- **Slice and acceptance:** Static attributed directory implemented; verify ongoing link maintenance and accessibility. Missing or unsupported information must remain unavailable and distinguish official, estimated, reported and simulated content.
- **Frontend:** text-first mobile view with language and accessibility review; communicate uncertainty and no-data. **Backend/model:** preserve source, timestamp, status and lineage; use canonical authorization.
- **Privacy/science:** minimize personal information, moderate reports, validate units/CRS and independently evaluate any model before operational use. **Tests:** offline unit/API/UI, negative, stale and unauthorized cases; no live network dependency.
- **Complexity/blockers:** low for static links; larger for ingestion. **Next:** Static attributed directory implemented; verify ongoing link maintenance and accessibility.
- **Farmer and community acceptance.** Separate national and provincial channels and check issue time and geography at the publisher. Maintain a dated source registry. A direct-link timeout must not be turned into an active notice or outage inference about its services.


### PK-003 — Urdu and low-bandwidth access
- **Priority/status:** P1 / PARTIAL. **Dependencies:** UI-001, P0-003.
- **User/problem:** Pakistani residents, responders or analysts need reliable urdu and low-bandwidth access suited to local flood conditions. See the linked needs research; validate with affected communities.
- **Relevant code:** pages/1_🌍_Public_Dashboard.py; src/pakistan_flood_monitor/services/alert_templates.py; named screens are prototypes unless verified. See linked engineering tasks for exact boundaries.
- **Data/provider:** Human-reviewed translations and accessibility research. Verify permission, attribution, timestamps and coverage before use.
- **Slice and acceptance:** Audit translations, mobile layout, text-only and print views. Missing or unsupported information must remain unavailable and distinguish official, estimated, reported and simulated content.
- **Frontend:** text-first mobile view with language and accessibility review; communicate uncertainty and no-data. **Backend/model:** preserve source, timestamp, status and lineage; use canonical authorization.
- **Privacy/science:** minimize personal information, moderate reports, validate units/CRS and independently evaluate any model before operational use. **Tests:** offline unit/API/UI, negative, stale and unauthorized cases; no live network dependency.
- **Complexity/blockers:** medium/high; dependent on source access and safety validation. **Next:** Audit translations, mobile layout, text-only and print views.
- **Farmer and community acceptance.** Test essential text on an inexpensive Android device at 360 px and under throttling or failed tiles. Review Urdu and RTL with local speakers and test keyboard and screen-reader order. Verify forwardable plain text and cold offline behavior separately.


### PK-004 — Community sharing cards
- **Priority/status:** P1 / NOT_STARTED. **Dependencies:** P1-003, PK-003.
- **User/problem:** Pakistani residents, responders or analysts need reliable community sharing cards suited to local flood conditions. See the linked needs research; validate with affected communities.
- **Relevant code:** src/pakistan_flood_monitor/services/alert_templates.py; pages/5_📤_Export_Center.py; named screens are prototypes unless verified. See linked engineering tasks for exact boundaries.
- **Data/provider:** Authorized reviewed products and issue timestamps. Verify permission, attribution, timestamps and coverage before use.
- **Slice and acceptance:** Design source-attributed cards; test expiry and publication authorization. Missing or unsupported information must remain unavailable and distinguish official, estimated, reported and simulated content.
- **Frontend:** text-first mobile view with language and accessibility review; communicate uncertainty and no-data. **Backend/model:** preserve source, timestamp, status and lineage; use canonical authorization.
- **Privacy/science:** minimize personal information, moderate reports, validate units/CRS and independently evaluate any model before operational use. **Tests:** offline unit/API/UI, negative, stale and unauthorized cases; no live network dependency.
- **Complexity/blockers:** medium/high; dependent on source access and safety validation. **Next:** Design source-attributed cards; test expiry and publication authorization.
- **Farmer and community acceptance.** Require issuer, source link, issue time, expiry, area, review state and uncertainty in the forwarded text. Preserve demo labels and exclude expired or unreviewed products. Provider stub receipts do not establish delivery.


### PK-005 — Verified relief directory
- **Priority/status:** P1/P2 / BLOCKED. **Dependencies:** P1-002, SEC-001.
- **User/problem:** Pakistani residents, responders or analysts need reliable verified relief directory suited to local flood conditions. See the linked needs research; validate with affected communities.
- **Relevant code:** pages/3_📱_Field_Reports.py; pages/4_🤝_Partner_Mode.py; named screens are prototypes unless verified. See linked engineering tasks for exact boundaries.
- **Data/provider:** Verified official contacts and maintained service status. Verify permission, attribution, timestamps and coverage before use.
- **Slice and acceptance:** Design verification, expiry and moderation; never infer active shelter availability. Missing or unsupported information must remain unavailable and distinguish official, estimated, reported and simulated content.
- **Frontend:** text-first mobile view with language and accessibility review; communicate uncertainty and no-data. **Backend/model:** preserve source, timestamp, status and lineage; use canonical authorization.
- **Privacy/science:** minimize personal information, moderate reports, validate units/CRS and independently evaluate any model before operational use. **Tests:** offline unit/API/UI, negative, stale and unauthorized cases; no live network dependency.
- **Complexity/blockers:** medium/high; dependent on source access and safety validation. **Next:** Design verification, expiry and moderation; never infer active shelter availability.
- **Farmer and community acceptance.** For veterinary, fodder, safe-water and animal shelter listings, require a verified operator, supported area/species, timestamp and expiry. Track reported road/access constraints separately from authoritative closure status.


### PK-006 — Community reports
- **Priority/status:** P2 / PARTIAL. **Dependencies:** P1-002, SEC-001.
- **User/problem:** Pakistani residents, responders or analysts need reliable community reports suited to local flood conditions. See the linked needs research; validate with affected communities.
- **Relevant code:** pages/3_📱_Field_Reports.py; src/pakistan_flood_monitor/api/main.py; named screens are prototypes unless verified. See linked engineering tasks for exact boundaries.
- **Data/provider:** Moderated field reports and privacy/retention policy. Verify permission, attribution, timestamps and coverage before use.
- **Slice and acceptance:** Audit existing field-report flow; distinguish reports from verified observations. Missing or unsupported information must remain unavailable and distinguish official, estimated, reported and simulated content.
- **Frontend:** text-first mobile view with language and accessibility review; communicate uncertainty and no-data. **Backend/model:** preserve source, timestamp, status and lineage; use canonical authorization.
- **Privacy/science:** minimize personal information, moderate reports, validate units/CRS and independently evaluate any model before operational use. **Tests:** offline unit/API/UI, negative, stale and unauthorized cases; no live network dependency.
- **Complexity/blockers:** medium/high; dependent on source access and safety validation. **Next:** Audit existing field-report flow; distinguish reports from verified observations.
- **Farmer and community acceptance.** Separate crop, stored grain, livestock, road, irrigation and water incidents. Future consent, receipt and moderation should work without requiring a land title. Prevent public disclosure of exact locations or raw evidence, and preserve state across restarts.


### PK-007 — Farmers and livestock
- **Priority/status:** P2 / BLOCKED. **Dependencies:** DATA-001, GIS-001, PK-006.
- **User/problem:** Pakistani residents, responders or analysts need reliable farmers and livestock suited to local flood conditions. See the linked needs research; validate with affected communities.
- **Relevant code:** src/app/services/exposure.py; src/pakistan_flood_monitor/services/damage_classification.py; named screens are prototypes unless verified. See linked engineering tasks for exact boundaries.
- **Data/provider:** Validated flood extents and licensed agricultural layers. Verify permission, attribution, timestamps and coverage before use.
- **Slice and acceptance:** Separate estimated exposure, reported losses and verified damage. Missing or unsupported information must remain unavailable and distinguish official, estimated, reported and simulated content.
- **Frontend:** text-first mobile view with language and accessibility review; communicate uncertainty and no-data. **Backend/model:** preserve source, timestamp, status and lineage; use canonical authorization.
- **Privacy/science:** minimize personal information, moderate reports, validate units/CRS and independently evaluate any model before operational use. **Tests:** offline unit/API/UI, negative, stale and unauthorized cases; no live network dependency.
- **Complexity/blockers:** medium/high; dependent on source access and safety validation. **Next:** Separate estimated exposure, reported losses and verified damage.
- **Farmer and community acceptance.** Support crop stage, irrigated land, pumps and stored grain as distinct information needs. Calibrate crop exposure with licensed spatial and seasonal data, maintain units and resolution, and keep livestock losses and verified damage separate. Provide only sourced, dated preparedness materials until scientific and provider validation exists.


### PK-008 — River observation explorer
- **Priority/status:** P2 / BLOCKED. **Dependencies:** DATA-001.
- **User/problem:** Pakistani residents, responders or analysts need reliable river observation explorer suited to local flood conditions. See the linked needs research; validate with affected communities.
- **Relevant code:** nasa_service.py; pages/10_🌧️_NASA_Hydromet.py; named screens are prototypes unless verified. See linked engineering tasks for exact boundaries.
- **Data/provider:** Licensed gauge data, units and timestamps. Verify permission, attribution, timestamps and coverage before use.
- **Slice and acceptance:** Validate official measurements, freshness and stage definitions. Missing or unsupported information must remain unavailable and distinguish official, estimated, reported and simulated content.
- **Frontend:** text-first mobile view with language and accessibility review; communicate uncertainty and no-data. **Backend/model:** preserve source, timestamp, status and lineage; use canonical authorization.
- **Privacy/science:** minimize personal information, moderate reports, validate units/CRS and independently evaluate any model before operational use. **Tests:** offline unit/API/UI, negative, stale and unauthorized cases; no live network dependency.
- **Complexity/blockers:** medium/high; dependent on source access and safety validation. **Next:** Validate official measurements, freshness and stage definitions.

### PK-009 — Partner and NGO information
- **Priority/status:** P2 / PARTIAL. **Dependencies:** P1-002, SEC-001.
- **User/problem:** Pakistani residents, responders or analysts need reliable partner and ngo information suited to local flood conditions. See the linked needs research; validate with affected communities.
- **Relevant code:** pages/4_🤝_Partner_Mode.py; pages/5_📤_Export_Center.py; named screens are prototypes unless verified. See linked engineering tasks for exact boundaries.
- **Data/provider:** Authorization, audited exports and reviewed summaries. Verify permission, attribution, timestamps and coverage before use.
- **Slice and acceptance:** Audit partner mode; constrain access and sensitive data. Missing or unsupported information must remain unavailable and distinguish official, estimated, reported and simulated content.
- **Frontend:** text-first mobile view with language and accessibility review; communicate uncertainty and no-data. **Backend/model:** preserve source, timestamp, status and lineage; use canonical authorization.
- **Privacy/science:** minimize personal information, moderate reports, validate units/CRS and independently evaluate any model before operational use. **Tests:** offline unit/API/UI, negative, stale and unauthorized cases; no live network dependency.
- **Complexity/blockers:** medium/high; dependent on source access and safety validation. **Next:** Audit partner mode; constrain access and sensitive data.
- **Farmer and community acceptance.** Do not describe local advisories or exports as authorized. Test that source, area, issue/expiry and demo markers survive copying, while personal details and raw evidence stay protected.


### PK-010 — Historical and preparedness explorer
- **Priority/status:** P3 / PARTIAL. **Dependencies:** DATA-001, GIS-001.
- **User/problem:** Pakistani residents, responders or analysts need reliable historical and preparedness explorer suited to local flood conditions. See the linked needs research; validate with affected communities.
- **Relevant code:** pages/12_🗺️_Historical_Flood_Map.py; data/historical_flood_regions.json; named screens are prototypes unless verified. See linked engineering tasks for exact boundaries.
- **Data/provider:** Dated licensed historical sources and approved preparedness guidance. Verify permission, attribution, timestamps and coverage before use.
- **Slice and acceptance:** Distinguish history from prediction; validate maps and legends. Missing or unsupported information must remain unavailable and distinguish official, estimated, reported and simulated content.
- **Frontend:** text-first mobile view with language and accessibility review; communicate uncertainty and no-data. **Backend/model:** preserve source, timestamp, status and lineage; use canonical authorization.
- **Privacy/science:** minimize personal information, moderate reports, validate units/CRS and independently evaluate any model before operational use. **Tests:** offline unit/API/UI, negative, stale and unauthorized cases; no live network dependency.
- **Complexity/blockers:** medium/high; dependent on source access and safety validation. **Next:** Distinguish history from prediction; validate maps and legends.
- **Farmer and community acceptance.** Add the extent source, event dates, resolution and confidence, distinguishing historical extent, estimated crop exposure and field-verified loss. Remove unsupported ground-truth language. Keep authoritative preparedness links dated and usable without imagery. The text-first English preparedness slice can proceed when government or humanitarian source material is verified. Cover crop and seed supplies, equipment, chemicals and records, then species-relevant animal water, fodder and welfare guidance. Require human-reviewed Urdu before publication. PK-005 owns verified service availability and PK-007 retains exposure validation.


### PK-011 — Validated forecasting
- **Priority/status:** P3 / BLOCKED. **Dependencies:** DATA-001.
- **User/problem:** Pakistani residents, responders or analysts need reliable validated forecasting suited to local flood conditions. See the linked needs research; validate with affected communities.
- **Relevant code:** pages/13_🔮_Flood_Forecasting.py; src/pakistan_flood_monitor/services/forecast_service.py; named screens are prototypes unless verified. See linked engineering tasks for exact boundaries.
- **Data/provider:** Independent historical rainfall/gauge datasets and out-of-sample evaluation. Verify permission, attribution, timestamps and coverage before use.
- **Slice and acceptance:** Keep operational forecast disabled until independently validated. Missing or unsupported information must remain unavailable and distinguish official, estimated, reported and simulated content.
- **Frontend:** text-first mobile view with language and accessibility review; communicate uncertainty and no-data. **Backend/model:** preserve source, timestamp, status and lineage; use canonical authorization.
- **Privacy/science:** minimize personal information, moderate reports, validate units/CRS and independently evaluate any model before operational use. **Tests:** offline unit/API/UI, negative, stale and unauthorized cases; no live network dependency.
- **Complexity/blockers:** medium/high; dependent on source access and safety validation. **Next:** Keep operational forecast disabled until independently validated.
- **Farmer and community acceptance.** Prioritize guarding unvalidated prototype water-level and dam views in operational mode. Replace evacuation wording and missing-imagery flood scores with explicit unavailable states pending hindcast, gauge and provider validation.
