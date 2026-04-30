# Audit Log Integrity Model

## Overview
The runtime API now maintains tamper-evident audit chains for:
- review lifecycle actions (`review_audit_log`)
- privileged admin actions (`privileged_audit_log`)

Each entry includes:
- `previous_hash` (hash of prior entry, `GENESIS` for first record)
- `entry_hash` (SHA-256 hash over canonicalized entry payload)
- identity and action metadata (`principal_id`, `action`, `resource_type`, `resource_id`, `details`, `timestamp`)

This creates an append-only hash chain: changing a historical entry breaks the chain from that point onward.

## Verification
Use:

- `GET /internal/admin/audit/verify`

Behavior:
- returns `200` with `{"status":"ok"...}` if both chains are valid.
- returns `409` with detailed failure (`review` and/or `privileged`) if integrity checks fail.

## Restore / Recovery Logging
Restore actions are now explicitly logged in the privileged chain:
- `restore_attempt`
- `restore_completed`

These operations are hashed/signed via the same chain mechanism so recovery actions become forensic events.

## Operational Guidance
1. Before release or cutover, run audit verification endpoint and archive the result.
2. After any restore/recovery drill, run audit verification again.
3. Treat any `409` from audit verification as a release blocker and incident trigger.
4. Preserve API responses and timestamps as evidence for compliance reviews.
