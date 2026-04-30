# Crowdsourced Field Reports: Schema, Moderation, and Safety Controls

## Field report schema
- `report_id`: Deterministic ID generated from client dedupe key.
- `event_id`: Required linkage to an existing event.
- `observed_at`: Reporter-observed timestamp (ISO-8601).
- `location`: `{lat, lon}` with range validation.
- `reporter_metadata`: Channel/device/source metadata and normalized submitter principal.
- `evidence_urls`: Optional links to photo/video artifacts (max 8).
- `notes`: Free-form text (max 2000 chars).
- `status`: `submitted | needs_more_info | approved | rejected | flagged_spam`.
- `trusted`: Boolean; only `approved + trusted=true` contributes to trusted summary counters.
- `moderation_reason`: Analyst rationale for moderation action.
- `moderation_tags`: Analyst tags for classification/abuse tracking.
- `created_at`, `updated_at`: Server-side timestamps.

## Ingestion workflow
1. Authenticated internal principal submits report to `/internal/reports/field`.
2. API validates event link, location, notes length, and evidence URL count.
3. API deduplicates using `client_report_id` (or deterministic fallback) and stores the report.
4. Report is linked on the event record under `linked_field_reports` and counted in `field_report_summary.total_count`.

## Moderation workflow
- Endpoint: `/internal/admin/reports/field/{report_id}/moderate`.
- Allowed actions by current state:
  - `submitted -> approve|reject|needs_more_info|flag_spam`
  - `needs_more_info -> approve|reject|flag_spam`
  - `approved -> reject`
- Roles: `admin` and `analyst` only.
- Each action updates status/trust flags and recomputes event `trusted_count`.

## Audit trail
- Moderation actions append to `field_report_audit_log` using a hash-chain entry (`previous_hash`, `entry_hash`).
- Logged attributes include principal, action, old/new status, trust, reason, and linked `event_id`.

## Public safety and data quality limitations
- Unmoderated reports are never marked trusted and must not be treated as canonical outputs.
- Reports can be malicious, spoofed, stale, or inaccurate; moderation and cross-signal corroboration are required.
- `flag_spam` state and dedupe controls reduce abuse impact but do not eliminate coordinated attacks.
