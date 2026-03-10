# Backup, Restore, and Disaster Recovery Runbook

## Scope
This runbook covers operational state used by the canonical API, including:

- run history
- event store
- historical event library
- review audit log
- threshold/model registry records
- privileged audit log

## Backup procedure
1. Obtain admin token.
2. Export runtime state snapshot:
   - `GET /internal/admin/state/export`
3. Persist response JSON into versioned object storage (e.g. `s3://.../runtime-state/YYYY-MM-DDTHH:MM:SSZ.json`).
4. Record snapshot checksum in release notes.

## Restore procedure
1. Quiesce write traffic to internal endpoints.
2. Retrieve latest validated snapshot JSON.
3. Restore snapshot:
   - `POST /internal/admin/state/restore` with payload `{ "state": <snapshot.state> }`.
4. Run health checks:
   - `/health`
   - `/internal/monitoring/metrics`
   - `/public/corridors`
5. Verify at least one known event is readable from `/public/events/{id}`.

## Disaster scenarios

### Process restart
- Use latest state export from object storage.
- Restore and re-open internal write traffic.

### Region outage
- Stand up warm replica deployment in DR region.
- Restore latest snapshot and environment variables.
- Confirm token validity and rotate if compromise suspected.

## Recovery objectives
- Target RPO: 15 minutes (scheduled exports every 15m)
- Target RTO: 30 minutes (bootstrap + restore + health verification)
