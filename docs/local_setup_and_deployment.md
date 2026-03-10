# Local Setup, Access, Keys, and Deployment Guide

This guide explains how to run the Pakistan Flood Monitor locally, configure sign-in/auth tokens and API keys, and deploy the service to staging/production.

## 1) Prerequisites

- Python 3.10+
- PostgreSQL with PostGIS enabled
- Git
- Linux/macOS shell (examples use bash)

Optional (for worker/orchestration features):

- Prefect OSS stack if you are enabling workflow workers (`ENABLE_PREFECT_WORKERS=true`)

## 2) Clone and install

```bash
git clone <your-repo-url> pakistan-flood-monitor
cd pakistan-flood-monitor
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 3) Prepare local environment configuration

The app loads env files based on `APP_ENV`:

- `local` -> `.env.local`
- `staging` -> `.env.staging`
- `prod` -> `.env.prod`

For local development, keep `APP_ENV=local` (or unset it) and update `.env.local`.

### 3.1 Required settings

At minimum, make sure these values are valid:

- `DATABASE_DSN`
- `STORAGE_RAW_ROOT`
- `STORAGE_PREPARED_ROOT`
- `STORAGE_DERIVED_ROOT`
- `STORAGE_PUBLISHED_ROOT`
- `FLOOD_THRESHOLDS_PATH`
- `BREACH_WEIGHTS_PATH`
- `STAC_ENDPOINT`
- `HYDROMET_ENDPOINT`

### 3.2 Create local storage directories

```bash
mkdir -p storage/raw storage/prepared storage/derived storage/published
```

If these directories do not exist, settings validation fails at startup.

### 3.3 Configure datasource/API credentials

If your external data providers require credentials, set:

- `STAC_TOKEN`
- `HYDROMET_TOKEN`

Example:

```bash
export STAC_TOKEN="<your-stac-token>"
export HYDROMET_TOKEN="<your-hydromet-token>"
```

> Recommendation: keep secrets out of committed `.env.*` files. Use environment variables, secret manager injection, or CI/CD secret mapping.

## 4) Database setup (PostgreSQL + PostGIS)

The application stores corridor metadata, events, exposure results, and workflow state in PostgreSQL. Spatial columns/functions require the PostGIS extension.

### 4.1 Install PostgreSQL + PostGIS

Use one of the options below depending on your local environment.

#### Option A: Ubuntu/Debian packages

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib postgis
```

> If you have multiple PostgreSQL versions installed, confirm the matching PostGIS package is present (for example `postgresql-15-postgis-3`).

#### Option B: macOS (Homebrew)

```bash
brew install postgresql@16 postgis
brew services start postgresql@16
```

If your shell PATH does not already include the Homebrew Postgres binaries, add it:

```bash
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### Option C: Docker (recommended if you do not want a host install)

```bash
docker run --name flood-monitor-postgis \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=flood_monitor \
  -p 5432:5432 \
  -d postgis/postgis:16-3.4
```

### 4.2 Create role/database and enable extension

If you used package installs (Option A/B), create database resources:

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE flood_user WITH LOGIN PASSWORD 'flood_password';
CREATE DATABASE flood_monitor OWNER flood_user;
\c flood_monitor
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
SQL
```

For Docker Option C, connect and enable extensions:

```bash
docker exec -it flood-monitor-postgis psql -U postgres -d flood_monitor -c "CREATE EXTENSION IF NOT EXISTS postgis;"
docker exec -it flood-monitor-postgis psql -U postgres -d flood_monitor -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;"
```

### 4.3 Verify PostGIS is active

Run:

```bash
psql -h localhost -U postgres -d flood_monitor -c "SELECT PostGIS_Full_Version();"
```

Expected result: one row containing PostGIS version/build details. If this fails with `function postgis_full_version() does not exist`, extension creation did not complete successfully.

### 4.4 Configure `DATABASE_DSN`

Set `DATABASE_DSN` in `.env.local`.

Examples:

```text
# local role/password example
DATABASE_DSN=postgresql+psycopg://flood_user:flood_password@localhost:5432/flood_monitor

# docker quickstart example from Option C
DATABASE_DSN=postgresql+psycopg://postgres:postgres@localhost:5432/flood_monitor
```

### 4.5 Apply schema migrations

From repository root:

```bash
alembic -c src/app/db/alembic.ini upgrade head
```

If your environment cannot locate `alembic`, run through the virtual environment:

```bash
python -m alembic -c src/app/db/alembic.ini upgrade head
```

### 4.6 Quick DB health checks

After migrations, confirm expected tables exist:

```bash
psql -h localhost -U postgres -d flood_monitor -c "\dt"
```

Optional: confirm at least one geometry-capable call works:

```bash
psql -h localhost -U postgres -d flood_monitor -c "SELECT ST_AsText(ST_Point(73.0479, 33.6844));"
```

## 5) Run locally

### 5.1 Start the prototype API (dashboard/prototyping stack)

```bash
uvicorn app.api.main:app --reload
```

### 5.2 Start the canonical runtime API

```bash
uvicorn pakistan_flood_monitor.api.main:app --reload
```

Canonical runtime API paths:

- Internal: `/internal/*`
- Public: `/public/*`

## 6) Sign-in/authentication model (internal API)

Internal API endpoints use bearer-token authentication rather than username/password sessions.

Set tokens before running runtime API:

```bash
export FLOOD_MONITOR_ADMIN_TOKEN="<admin-token>"
export FLOOD_MONITOR_ANALYST_TOKEN="<analyst-token>"
```

### 6.1 Role behavior

- Admin token: admin operations
- Analyst token: review/analyst operations

Actor naming is validated in request payloads:

- Admin token requires actor values prefixed with `admin-`
- Analyst token requires actor values prefixed with `analyst-`

### 6.2 Local request example

```bash
curl -H "Authorization: Bearer $FLOOD_MONITOR_ANALYST_TOKEN" \
  http://localhost:8000/internal/health
```

### 6.3 Token rotation guidance

- Maintain `current` and `next` token values in deployment secrets.
- Roll out support for both.
- Move clients to `next`.
- Remove old token in subsequent deploy.
- Rotate at least every 30 days or immediately after an incident.

## 7) Local pipeline run

Run a sample daily pipeline:

```bash
python scripts/run_daily.py
```

Use this to validate corridor processing and generation of downstream outputs under local configuration.

## 8) Deployment guide

This project is designed for a simple initial deployment:

- Single VM (or small split services)
- Python app + PostGIS
- Optional Prefect workers
- Docker-supported delivery

### 8.1 Environment selection

Set environment explicitly in deployment:

```bash
export APP_ENV=staging
# or
export APP_ENV=prod
```

Ensure corresponding `.env.staging` / `.env.prod` values are correct for:

- DB endpoint
- storage roots
- external endpoints
- log level
- worker toggle

### 8.2 Deployment steps (recommended)

1. Build and ship application artifact/container.
2. Inject secrets (`FLOOD_MONITOR_*_TOKEN`, provider tokens, DSN) from secret manager.
3. Ensure storage roots exist and are writable.
4. Apply Alembic migrations.
5. Start API using canonical runtime app:
   - `pakistan_flood_monitor.api.main:app`
6. Run smoke checks (`/health`, representative internal/public endpoints).
7. Start worker/cron schedules if enabled.

### 8.3 Production hardening checklist

Before production cutover:

- Token rotation policy in place.
- Rate limits configured:
  - `FLOOD_MONITOR_RATE_LIMIT_REQUESTS`
  - `FLOOD_MONITOR_RATE_LIMIT_WINDOW_SECONDS`
- Backup/export workflow validated.
- Monitoring and alert routes reachable.
- Rollback artifact and state-restore procedure tested.

## 9) Troubleshooting

- **Startup fails with config file missing**
  - Verify threshold file paths:
    - `config/thresholds/flood_thresholds.yaml`
    - `config/thresholds/breach_weights.yaml`
- **Startup fails with storage path missing**
  - Create the configured storage folders.
- **401 on internal endpoints**
  - Check bearer token presence and value.
- **403/validation errors for actor field**
  - Ensure actor prefix matches token role (`admin-` or `analyst-`).
- **Unexpected endpoint mismatch**
  - Confirm you launched the intended app (`app.api.main:app` vs `pakistan_flood_monitor.api.main:app`).

## 10) Related runbooks

- `docs/runtime_api_contract.md`
- `docs/release_checklist.md`
- `docs/monitoring_alerts.md`
- `docs/backup_restore_runbook.md`
