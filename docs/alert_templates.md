# Alert Templates (NDMA/PDMA-style)

This project now supports two API-backed alert template variants:

- `ndma_pdma_flood_alert_v1` + `official_internal`
- `ndma_pdma_flood_alert_v1` + `public_safe`

## Required fields

Both variants render from reviewed/published event data and include:

- `event_id`, `aoi`, `status`
- `event_timestamp`, `generated_at`
- `affected_area`
- `confidence` (`score`, `label`, method/breakdown)
- `limitations`
- `recommended_actions`
- `source_lineage` (scene IDs, processing version, thresholds)

## Variant differences

### official_internal

Adds workflow-oriented details for institutional operations:

- `workflow.approval_trace`
- `workflow.analyst_notes`

Suggested use: NDMA/PDMA/EOC internal coordination and escalation.

### public_safe

Adds public safety framing:

- `public_disclaimer`
- `limitations.reference` -> `/public/limitations`
- public-safe action phrasing

Suggested use: web/mobile public-facing advisory outputs.

## API endpoints

- Public latest alerts (default variant is public-safe):
  - `GET /public/alerts/latest?variant=public_safe`
- Public feed:
  - `GET /public/alerts/feed?variant=public_safe`
- Internal on-demand template rendering:
  - `GET /internal/alerts/templates?event_id=<id>&variant=official_internal`

## Content assumptions

- Template rendering expects a published event lifecycle state.
- Confidence values are model-derived and should be interpreted with uncertainty.
- Source lineage fields may be partially populated if upstream provenance is incomplete.
