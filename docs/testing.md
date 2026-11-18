# Test and verify a change

Install the project using [local setup](setup.md). Match the checked-in offline
workflow by installing its test guard and starting in test mode:

```bash
python -m pip install pytest-socket==0.8.1
APP_MODE=test python -m pytest --disable-socket --allow-unix-socket tests/ -q --tb=short
git diff --exit-code -- storage data
```

In PowerShell set `$env:APP_MODE = "test"` and omit the Bash prefix. Tests
choose a temporary SQLite database in `tests/conftest.py`. Test fixtures
replace provider responses. Start with the affected suite before running
all tests.

## Choose focused evidence

| Changed boundary | Tests or records to consult |
|---|---|
| Workflow, persistence or retries | `test_workflow_foundation.py`, `test_workflow_concurrent_retry.py`, `test_canonical_runtime_smoke.py` |
| Publication, authorization or provenance | `test_publication_boundary.py`, `test_publication_lineage_boundary.py`, `test_canonical_review_queue.py` |
| Public pages, farmer or livestock journeys | `test_streamlit_public_pages.py`, `test_public_preparedness_journeys.py`, [UX acceptance matrix](product/UI_UX_ACCEPTANCE_MATRIX.md) |
| Research and GIS diagnostics | `test_geo_measurements.py`, `test_dam_service.py`, `test_backtesting.py` |

Historical replay tests use scenario rainfall and simulated dam inputs.
Their results exercise software behavior. They do not establish warning
accuracy, historical lead time, or scientifically validated site conditions.

## Exercise the migration chain

Use a separate disposable database. From Bash:

```bash
migration_dir=$(mktemp -d)
export DATABASE_URL="sqlite:///$migration_dir/flood-monitor.db"
alembic upgrade head
alembic downgrade base
alembic upgrade head
alembic current
python -m compileall -q src/pakistan_flood_monitor
```

End at `b4d9d93f2a10`. The downgrade removes the schema, so use this sequence
only against an isolated database prepared for this check. For a target
deployment see [deployment](deployment.md).

## Report scope

The workflow definition in `.github/workflows/canonical-checks.yml` targets
Python 3.12 and these offline checks. Confirm hosted results separately.
The [implementation ledger](engineering/IMPLEMENTATION_STATUS.md) records
verified runs and gaps. Component tests establish route, widget and API
behavior. Use rendered browser evidence for layout, keyboard and assistive
technology acceptance. Live providers, domain validity, target database
behavior and deployment readiness require separate verification.
