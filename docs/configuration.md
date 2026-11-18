# Configuration reference

The canonical API and CLI load settings from the process environment. At
import, `src/pakistan_flood_monitor/config.py` reads a simple repository-root
`.env` file when present and leaves already-set variables in effect. Start
from `.env.example` if you need a local file. Keep credentials in untracked
local or deployment configuration.

| Setting | Consumer and meaning |
|---|---|
| `APP_MODE` | Canonical safety mode, one of `test`, `demo` or `operational`. Default `demo`. Invalid values fail startup. |
| `DATABASE_URL` | Canonical SQLAlchemy URL. Default `sqlite:///./storage/pakistan_flood_monitor.db`. Export it explicitly when running root Alembic, which reads the process environment. |
| `WORKFLOW_MAX_ATTEMPTS` | Canonical per-task attempt limit, default 3. |
| `API_BASE_URL` | Streamlit adapter's canonical API origin. When set, Home and My Area use the API with no fixture fallback. Unset in standalone demo/test to use local fixtures. |
| `FLOOD_MONITOR_ADMIN_TOKEN`, `FLOOD_MONITOR_ANALYST_TOKEN`, `FLOOD_MONITOR_REVIEWER_TOKEN`, `FLOOD_MONITOR_SERVICE_TOKEN` | Role secrets for internal FastAPI routes. Each route declares allowed roles. See [authorization](api.md#authorization). |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Compose interpolation and database settings. `POSTGRES_PASSWORD` must be set before using Compose. |
| `NASA_BEARER_TOKEN`, `NASA_EARTHDATA_USERNAME` | Optional provider settings consumed by the research hydromet tooling. Standalone demo and offline tests do not require them. |

`DATABASE_DSN` and environment-specific files mentioned in old guidance refer
to legacy or prototype paths. The canonical loader does not discover
`.env.local`, `.env.staging`, or `.env.prod` by convention. Use the
process environment or the local `.env` described above. A research helper
may explicitly read a separate file.

## Threshold sources

The canonical workflow consumes the Pydantic `Settings.thresholds` from
`src/pakistan_flood_monitor/config.py` and records the threshold values
with input versions. The YAML files under `config/thresholds/` belong to
file-based configuration and legacy or prototype paths. Their top-level
groups include `corridor_thresholds`, `hydromet_thresholds`,
`review_thresholds` and `breach_weights`, across the two files.

Check the actual consumer before changing a value. The Streamlit Settings
page directs authorized operators to server-side configuration. The API
registration endpoint records version metadata, so changing a registry entry
alone does not edit the deployed threshold file.

See [setup](setup.md), [deployment](deployment.md) and [ADR-001](adr/ADR-001-canonical-runtime.md).
