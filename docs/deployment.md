# Run a local deployment

Use [local setup](setup.md) for the tutorial and loopback commands. This page
covers the existing development Compose stack and canonical database
migration. An operational deployment requires the outstanding data and
recovery acceptance work in the [master task plan](engineering/MASTER_TASK_PLAN.md).

## Existing Compose stack

The root `docker-compose.yml` defines three services:

| Service | Actual configuration |
|---|---|
| `db` | PostGIS 15 container with a named database volume, health check and host port 5432 |
| `api` | Canonical FastAPI in demo mode on port 8000, using the shared development Dockerfile and repository bind mount |
| `streamlit` | Streamlit on port 8501 with `API_BASE_URL=http://api:8000` inside the stack |

The Dockerfile uses Python 3.11 and installs the dashboard extra. Compose
publishes ports on the host, enables API reload and mounts local source and
data. Treat the stack as development infrastructure. Use it on a trusted host
with access limited to intended users. For a loopback-only demo use the native
local commands in the setup tutorial.

With Docker Compose installed and `POSTGRES_PASSWORD` set in your development
environment, start the database and apply the canonical migration explicitly:

```bash
docker compose config --quiet
docker compose up -d db
docker compose run --rm api alembic upgrade head
docker compose up --build -d api streamlit
```

Open `http://localhost:8501` and check the API at
`http://localhost:8000/health`. Compose provides a database, and migration is
a separate command. Docker/PostGIS startup and migration were not exercised in
the documentation verification environment.

## Migrate the canonical database

From the repository root, export the intended SQLAlchemy `DATABASE_URL` and run:

```bash
alembic upgrade head
alembic current
```

The canonical head is `b4d9d93f2a10`. Use the root `alembic.ini`. The
independent legacy history under `src/app/db/alembic/` is a migration source,
so apply only the chain that belongs to the target database. In demo/test, the
workflow repository can initialize missing canonical tables for local use.
Operational runs require an applied schema.

A SQLite round trip is listed in [testing](testing.md). Back up deployed data
and verify both migrations and rollback in the target environment. The
workflow tables persist runs and tasks. Event review, field reports and
runtime audit state remain partly process-local. Use the protected snapshot
API for explicit export or restore, and track durable review and worker crash
recovery in the [task plan](engineering/MASTER_TASK_PLAN.md).

See [architecture](architecture.md) for runtime boundaries and
[configuration](configuration.md) for settings.
