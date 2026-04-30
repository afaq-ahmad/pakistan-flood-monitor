# Hard Release Checklist

## Pre-release gates
- [ ] Canonical runtime command validated: `uvicorn pakistan_flood_monitor.api.main:app --reload`.
- [ ] No deployment artifact or runbook uses deprecated prototype entrypoint `app.api.main:app`.
- [ ] Alembic migration state is current and applied in staging/prod.
- [ ] Runtime config validation completed (`.env`, thresholds, token vars).
- [ ] `/health` returns OK in deployment environment.
- [ ] `/internal/monitoring/metrics` and `/internal/monitoring/metrics/prometheus` reachable.
- [ ] Backup snapshot exported via `/internal/admin/state/export`.

## Security gates
- [ ] Admin and analyst tokens rotated within policy window.
- [ ] Actor-prefix checks verified (`admin-*`, `analyst-*`).
- [ ] Audit integrity verified (`GET /internal/admin/audit/verify`) before release.
- [ ] Internal rate limit thresholds configured for expected traffic.

## Validation gates
- [ ] Known-event benchmark validation run: `python scripts/run_benchmark_validation.py --benchmark tests/fixtures/validation/known_events_benchmark.json --output-dir reports/validation` and report artifact attached.
- [ ] Monthly corridor false-positive trend reviewed from `reports/validation/accuracy_report_<YYYY-MM>.json`.
- [ ] End-to-end contract test passes (ingestion -> review -> public event/exposure/alerts).
- [ ] Resilience tests pass (snapshot restore + concurrent writes/read-after-write).

## Rollback plan
1. Revert deployment artifact to previous release.
2. Restore previous known-good runtime state snapshot.
3. Re-run health and public API smoke checks.
4. Communicate rollback and incident summary.


## CI command gates
- [ ] `pytest tests/test_api_implementation.py` (API contract and auth behavior)
- [ ] `pytest tests/test_resilience_security_contracts.py` (state export/restore and security resilience)
- [ ] `curl -H "Authorization: Bearer $FLOOD_MONITOR_ADMIN_TOKEN" http://localhost:8000/internal/admin/audit/verify`
- [ ] `pytest tests/test_review_workflow.py` (review lifecycle transitions)
- [ ] `pytest tests/test_sar_preprocessing_pipeline.py` (SAR preprocessing integrity)
- [ ] Evidence captured: attach command output snippets and commit SHA in release artifact.
