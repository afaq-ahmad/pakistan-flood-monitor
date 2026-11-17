# Testing Strategy

The Pakistan Flood Monitor employs a testing strategy centered around `pytest`. Because the system relies heavily on external satellite APIs and ML inferences, testing is divided into structural unit tests, data integrity tests, and historical backtesting.

## Running Tests

To run the entire test suite:
```bash
python -m pytest tests/ -v
```

## Historical Backtesting Framework

The most critical test of the flood monitor is its ability to detect real, historical catastrophes. We have implemented a backtesting framework (`tests/test_backtesting.py`) that replays major historical events (e.g., the 2010 and 2022 Mega Floods) through the current risk model.

```mermaid
flowchart TD
    GT[Ground Truth Event<br/>e.g. 2022 Mega Flood] --> R[replay_event]
    R --> C1[Compute risk: Indus-Lower]
    R --> C2[Compute risk: Indus-Upper]
    R --> C3[Compute risk: Chenab-Middle]
    C1 --> E{Risk >= medium?}
    C2 --> E
    C3 --> E
    E -- Yes --> D[Event Detected ✅]
    E -- No --> M[Event Missed ❌]
```

**Limitation**: The replay uses deterministic simulated dam inputs in tests, not historical observed dam conditions or independently verified outcomes. It is a software diagnostic and cannot establish historical warning accuracy or operational readiness.

## Unit Testing

Unit tests focus heavily on:
1. **Dam Database Integrity**: Ensuring all hardcoded dams have correct metadata, IDs, and upstream mapping.
2. **Haversine Math**: Verifying geographic distance calculations between coordinates.
3. **Risk Scoring Logic**: Validating that various fill-level classifications generate the correct upstream risk scores.
4. **Edge Cases**: Ensuring missing imagery or boundary conditions don't crash the risk pipelines.

## Test Directory Structure

```text
tests/
├── test_dam_service.py      # Validates dam mappings, graph edges, and risk math
├── test_backtesting.py      # Replays historical events against the risk model
└── ...
```

## Writing New Tests

1. Create a file prefixed with `test_` in the `tests/` directory.
2. Use `pytest` fixtures for mocking external API calls (e.g., STAC or Open-Meteo).
3. Do not run live network calls in standard unit tests. Mock the responses to ensure tests remain fast and deterministic.
4. If writing a new backtest event, add the ground truth data to `GROUND_TRUTH_EVENTS` in `test_backtesting.py`.

## Offline CI

`.github/workflows/canonical-checks.yml` installs the project and runs the complete `tests/` suite
with network sockets disabled, Unix-domain sockets enabled for the in-process test client, and an
temporary SQLite database selected by the test configuration even if `DATABASE_URL` is set. Tests
requiring another database must create it explicitly. Test fixtures replace live provider calls and keep prototype dam histories
and generated reports in temporary directories. CI checks that tracked `storage/` and `data/` files
were not changed. Pillow is a declared dependency for image-processing imports. A green result does
not validate real provider integrations, historical warning accuracy, Docker, PostgreSQL, worker
crash recovery, or scientific and operational readiness. Dependency versions are not fully locked.
