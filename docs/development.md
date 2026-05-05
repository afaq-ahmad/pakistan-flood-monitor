# Local Development Workflow

This document outlines the directory structure and common tasks for developers working on the Pakistan Flood Monitor.

## Directory Structure

```text
pakistan-flood-monitor/
├── .env.local                 # Local environment variables
├── streamlit_app.py           # Streamlit entry point
├── dashboard_app.py           # Alternate FastAPI entry point (static HTML serving)
├── backend_service.py         # Data wrapper reading from CSVs
├── nasa_service.py            # NASA POWER integration
├── satellite_ml_service.py    # STAC discovery & ML water detection
│
├── pages/                     # Streamlit multi-page routes
│   ├── 1_🌍_Public_Dashboard.py
│   ├── 11_🤖_ML_Water_Detection.py
│   ├── 15_🏗️_Dam_Flood_Risk.py
│   └── ...                    # (15 pages total)
│
├── src/pakistan_flood_monitor/
│   ├── api/                   # FastAPI routes (in-memory state)
│   ├── core/                  # Legacy core pipeline logic
│   ├── models/                # Pydantic schemas
│   └── services/              # Domain-specific logic
│       ├── dam_service.py     # Dam DB and analysis
│       ├── forecast_service.py # Open-Meteo & LSTM
│       └── advanced_ml_service.py # SAR & Topography
│
├── data/                      # Local JSON/CSV Data Store
│   ├── historical_flood_regions.json
│   ├── corridors.csv
│   └── ...
│
├── config/thresholds/         # YAML threshold configurations
├── storage/                   # File-based runtime storage
├── tests/                     # Pytest suite
└── docs/                      # Technical Documentation
```

## Creating a New Dashboard Page

Streamlit uses the `pages/` directory to automatically route multi-page applications.

1. Create a new Python file in `pages/` named with a number prefix (to enforce ordering) and an emoji for UI appeal. E.g., `pages/16_📊_Analytics_Report.py`.
2. Import the necessary data services (e.g., `from backend_service import data_service`).
3. Build the UI using standard `streamlit` widgets (`st.dataframe`, `st.metric`, `st.map`).
4. Ensure the page handles exceptions gracefully, as Streamlit re-renders the file entirely on state changes.

## Adding a New Backend Service

If you need a new domain (e.g., `drought_service.py`):
1. Create the module inside `src/pakistan_flood_monitor/services/`.
2. Keep data storage file-based (in `storage/` or `data/`). Avoid requiring complex database migrations unless structurally necessary.
3. Import your service into the relevant `pages/` Streamlit script.
4. Ensure you add unit tests in the `tests/` directory.

## Testing Your Changes

Before committing changes, ensure tests pass locally.

```bash
python -m pytest tests/ -v
```

See [testing.md](testing.md) for more details.
