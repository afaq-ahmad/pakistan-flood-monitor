# Hard Release Checklist

## Pre-release gates
- [ ] Alembic migration state is current and applied in staging/prod.
- [ ] Runtime config validation completed (`.env`, thresholds, token vars).
- [ ] `/health` returns OK in deployment environment.
- [ ] `/internal/monitoring/metrics` and `/internal/monitoring/metrics/prometheus` reachable.
- [ ] Backup snapshot exported via `/internal/admin/state/export`.

## Security gates
- [ ] Admin and analyst tokens rotated within policy window.
- [ ] Actor-prefix checks verified (`admin-*`, `analyst-*`).
- [ ] Internal rate limit thresholds configured for expected traffic.

## Validation gates
- [ ] End-to-end contract test passes (ingestion -> review -> public event/exposure/alerts).
- [ ] Resilience tests pass (snapshot restore + concurrent writes/read-after-write).

## Rollback plan
1. Revert deployment artifact to previous release.
2. Restore previous known-good runtime state snapshot.
3. Re-run health and public API smoke checks.
4. Communicate rollback and incident summary.
