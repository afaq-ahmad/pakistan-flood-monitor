# Analyst workflow notes

## Approval state machine

Use the admin review endpoint in this sequence only:
1. `draft` -> `review`
2. `review` -> `approved`
3. `approved` -> `published`
4. `published` -> `retracted`

Skipped, reversed, or repeated transitions are blocked.

## Governance requirements

- Authenticated principal identity is used as the actor of record.
- Every transition is written to review audit logs and privileged audit logs.
- `approval_trace` is returned on event payloads for UI display and auditability.
- Publishing still requires QA gate checks and required geometry metadata when edited geometry is provided.

## Unified analyst dashboard workflow

Use `GET /analytics/dashboard/review` as the single review workspace payload. Each queue item now includes:
- event detail (`candidate_id`, corridor, district, confidence, class, status)
- provenance/lineage (`source_scene_references`, `confidence_breakdown`, `exposure_summary`)
- QA flags (`qa_flags`) such as low confidence, high breach suspicion, revision state, or missing optical support
- strict next-step controls (`allowed_actions`) derived from lifecycle transitions

Execute review actions via `POST /admin/review/{candidate_id}/actions` with header `X-Analyst-Id`.
The actor is always server-attributed from the authenticated analyst identity header and logged to audit records.

## Before/after imagery and event timeline workflow

Use `GET /public/events/{event_id}/imagery` to drive temporal comparison in map viewers.

- `comparison.mode` is currently `swipe` for a before/after slider UX.
- `comparison.before_scene` and `comparison.after_scene` include scene IDs, acquisition timestamps, SAR sensor type, and asset links.
- `comparison.missing_layers` explicitly reports absent timeline layers (`before` or `after`) and `fallback_message` provides analyst guidance when a comparison cannot be rendered.
- `source_scene_lineage` provides source-scene provenance records for trust-oriented tooltips and source drill-down.
- `timeline[]` is the event-evolution series keyed by run timestamp with area, confidence, status, and lineage metadata.
- `supported_formats` currently includes `COG`, `GeoTIFF`, and `PNG_TILE`.
- `timeline_metadata_fields` lists expected keys for clients that validate timeline payload completeness.

## Outbound notification workflow

After an event reaches `published`, dispatch alert payloads only to recipients explicitly opted into each channel.

- Every send writes channel audit entries (`attempted`, `succeeded`, `failed`, `blocked`, `retryable_failed`).
- Channel adapter failures are considered operationally visible events and should trigger on-call follow-up.
- Use environment-managed provider credentials only (`SMS_API_KEY`, `EMAIL_API_KEY`, `WHATSAPP_API_KEY`).
