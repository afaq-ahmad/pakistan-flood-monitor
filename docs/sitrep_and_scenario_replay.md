# SitRep PDF generation and scenario replay

## One-click SitRep export
- Trigger: `POST /internal/admin/sitrep/export` (admin/analyst/reviewer token).
- Source event: latest event in lifecycle status `review`, `approved`, or `published`.
- Output file: `reports/sitrep/sitrep_<event_id>.pdf` and streamed response as `application/pdf`.
- Included sections:
  - Event Summary
  - District/Tehsil Priorities
  - Recommended Actions
  - Exposure/Risk Summary
  - Confidence and Limitations
  - Contacts
- Public safety disclaimer text is included from system limitations.

## Scenario replay kit
Data location: `data/demo/scenario_replay/`
- `scenario_indus_2022.json`
- `scenario_chenab_2014.json`

Both fixtures are synthetic/sample datasets intended for training/pilot demos.

### Replay workflow
1. Start API.
2. Run corridor event (`GET /internal/run/{aoi}`), transition event to `review` then `approved`.
3. Export SitRep with `POST /internal/admin/sitrep/export`.
4. Validate expected outputs in fixture:
   - lifecycle status
   - minimum risk summary counts
   - SitRep section presence
   - checklist completion

## Limitations
- Current PDF writer is lightweight and text-only for deterministic testing.
- Contacts include one static control-room number and one operator-filled placeholder.
