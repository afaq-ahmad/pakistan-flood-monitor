# Known-Event Validation Suite

This document defines the scientific QA benchmark process for known historical flood events.

## Benchmark dataset format
Benchmark packs are JSON files with:
- `benchmark_pack`: name, description, version, and source provenance
- `generated_at`: ISO timestamp for reporting month
- `events[]`: each event includes
  - `event_id`
  - `event_date` (ISO)
  - `corridor`
  - `expected_detection_ids`
  - `observed_detection_ids`

Reference fixture: `tests/fixtures/validation/known_events_benchmark.json`.

## Validation command
Run the repeatable validation workflow:

```bash
python scripts/run_benchmark_validation.py \
  --benchmark tests/fixtures/validation/known_events_benchmark.json \
  --output-dir reports/validation
```

## Metrics and interpretation
Per corridor:
- `precision = TP / (TP + FP)`
- `recall = TP / (TP + FN)`
- Monthly false-positive trend as `{YYYY-MM: count}`

Overall report includes macro precision and macro recall (mean across corridors).

Interpretation guide:
- Precision downtrend with stable recall suggests escalating false alarms.
- Recall downtrend with stable precision suggests missed flood extent detections.
- Corridor-level trend divergence indicates localized model or data issues.

## Monthly reports
Reports are generated as deterministic JSON in:
- `reports/validation/accuracy_report_<YYYY-MM>.json`

For fixed fixtures in tests, deterministic output is validated in regression tests.

## CI / release gate guidance
Use this suite as a release gate command in CI and monthly release operations:

```bash
pytest tests/test_validation_reporting.py
python scripts/run_benchmark_validation.py
```
