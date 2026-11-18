# Pakistan Flood Monitor

Pakistan Flood Monitor is an open-source prototype for flood situational
awareness in Pakistan. The public dashboard provides pilot river corridor
references, eligible published events, official source links, and farm and
livestock preparedness guides. Coverage and publication availability vary.
Follow official authorities for warnings and emergency decisions.

## Get started

**[Open the documentation homepage](docs/INDEX.md)** for setup, architecture,
API contracts, community needs, QA and current work. Contributors can go
straight to [local setup](docs/setup.md). Coding agents start with the
[operating contract](AGENTS.md).

## Repository at a glance

| Location | Purpose |
|---|---|
| `streamlit_app.py` and `pages/` | Home and 18 registered pages grouped into public information, research and operations |
| `src/pakistan_flood_monitor/` | Canonical FastAPI, CLI, workflow and domain code |
| `alembic/` | Canonical database migrations |
| `src/app/` | Deprecated compatibility and migration source |
| `dashboard_app.py` and `dashboard/` | Separate HTML prototype for demo and test |
| `docs/` | Shared Markdown documentation and Obsidian vault |

The six [configured pilot corridors](docs/overview.md) describe the catalogue.
An empty feed leaves local conditions unknown. See
[implementation status](docs/engineering/IMPLEMENTATION_STATUS.md) for
operational data, scientific validation and release limits.

[MIT License](LICENSE)
