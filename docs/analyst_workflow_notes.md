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
