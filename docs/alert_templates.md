# Alert Templates (NDMA/PDMA-style)

This project now supports two API-backed alert template variants:

- `ndma_pdma_flood_alert_v1` + `official_internal`
- `ndma_pdma_flood_alert_v1` + `public_safe`

Both public-facing outputs support bilingual rendering (`en`, `ur`) via a query-param language toggle and ship localization metadata for clients.

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
- `public_disclaimer_ur`
- `localized` bilingual content bundle (`disclaimer`, `limitations_summary`, `recommended_actions`)
- `limitations.reference` -> `/public/limitations`
- public-safe action phrasing

Localization behavior:
- `language=en` (default) returns LTR payloads with English content.
- `language=ur` returns RTL payloads (`dir=rtl`) and Urdu disclaimer/action content when available.
- Missing localized fields fall back to the default English content.

Suggested use: web/mobile public-facing advisory outputs.

## API endpoints

- Public latest alerts (default variant is public-safe):
  - `GET /public/alerts/latest?variant=public_safe&language=en|ur`
- Public feed:
  - `GET /public/alerts/feed?variant=public_safe&language=en|ur`
- Mobile advisory:
  - `GET /public/advisories/{aoi_name}/mobile?language=en|ur`
- Internal on-demand template rendering:
  - `GET /internal/alerts/templates?event_id=<id>&variant=official_internal`

## Content assumptions

- Template rendering expects a published event lifecycle state.
- Confidence values are model-derived and should be interpreted with uncertainty.
- Source lineage fields may be partially populated if upstream provenance is incomplete.
- Urdu translations are safety-first and preserve imperative meaning; maintainers should update `localized` fields alongside any English content changes.
