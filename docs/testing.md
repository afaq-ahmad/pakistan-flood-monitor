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

## Python compatibility

Evidence at `ec8700b` with fresh virtual environments and the CI install
command `python -m pip install -e '.[dev,dashboard]' pytest-socket==0.8.1`.

| Python | Verified outcome |
|---|---|
| 3.10.22 | Loading `pakistan_flood_monitor.api.main` fails at `from datetime import UTC`. The declared `>=3.10` floor is too low for the canonical runtime. |
| 3.11.18 | Editable install, package dependency check, API and Streamlit loopback startup, disposable SQLite migration round-trip and 353 offline tests passed. Docker targets this minor version. |
| 3.12.14 | Same checks passed, with 353 offline tests. The checked-in GitHub Actions workflow targets this minor version. |

The loopback checks reached the API `/health` and empty event feed, and
Streamlit's root and health pages in demo mode. Full browser acceptance,
optional research extras, image build and PostGIS need separate checks.
Recommend Python 3.12 for contributors and a Python 3.11 package floor under
[OPS-001](engineering/MASTER_TASK_PLAN.md#ops-001--deployment-and-operational-verification).
The evidence covers the tested versions and extras.

## Choose focused evidence

| Changed boundary | Tests or records to consult |
|---|---|
| Agent contract and Git helpers | `test_agent_operating_contract.py`, `test_agent_git_workflow.py`, [agent workflow](engineering/AGENT_GITHUB_WORKFLOW.md#optional-local-git-helpers) |
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

## Quality checks and staged adoption

Keep the offline suite, tracked-data check, SQLite migration round-trip and
canonical compile check as the baseline. Choose additional checks for the
affected files. The checks below describe verified pilots and suggested
adoption steps.

| Check | Scope and next step |
|---|---|
| Ruff lint and format | An isolated correctness pilot (`E9,F63,F7,F82`) passed on `src/pakistan_flood_monitor/workflow/`. The full canonical package reported one undefined name, and a format check reported 36 files needing formatting. Resolve or baseline existing findings before adding a gate. Start with a small canonical directory and keep formatting to touched code. |
| Typing | Use focused checks on changed models and provider interfaces first. Baseline third-party typing and existing annotations before choosing a type checker or widening its coverage. |
| Markdown, links and Mermaid | Check changed notes with the [documentation guide](DOCUMENTATION_GUIDE.md#author-link-and-verify). Prioritize broken local targets, heading anchors and changed diagram grammar. Render changed diagrams where possible. A prose-formatting gate needs a baseline for historical notes. |
| Actions and Compose YAML | Validate workflow semantics with Actionlint when available. Check Compose interpolation with `docker compose config --quiet` and dummy development credentials. Each checks a different configuration contract. |
| Secret scanning | Inspect the staged diff and use existing checkpoint guards. If a maintained scanner is available, pilot it on new commits or the changed range. Review findings privately and record scanner scope and limitations. |
| Existing test and migration gates | Keep test mode, the socket guard, tracked-data check and disposable SQLite round-trip. Add target-database evidence for storage changes when applicable. |

No new quality tools are required by this baseline. Record any proposed gate,
its scope and its clean baseline before enabling it in CI.

## Report scope

The workflow definition in `.github/workflows/canonical-checks.yml` targets
Python 3.12 and these offline checks. Confirm hosted results separately.
The [implementation ledger](engineering/IMPLEMENTATION_STATUS.md) records
verified runs and gaps. Component tests establish route, widget and API
behavior. Use rendered browser evidence for layout, keyboard and assistive
technology acceptance. Live providers, domain validity, target database
behavior and deployment readiness require separate verification.
