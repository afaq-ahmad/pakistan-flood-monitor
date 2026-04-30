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
