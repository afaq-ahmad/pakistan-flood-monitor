# Local Setup

This guide explains how to configure and run the Pakistan Flood Monitor locally.

## Prerequisites

- **Python**: Version 3.10 or higher.
- **Git**: To clone the repository.
- **Pip/Venv**: Standard Python packaging.

## 1. Clone the Repository

```bash
git clone <repository_url> pakistan-flood-monitor
cd pakistan-flood-monitor
```

## 2. Create Virtual Environment

Create and activate a virtual environment:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python -m venv .venv
source .venv/bin/activate
```

## 3. Install Dependencies

The project uses a standard `pyproject.toml`. Install the application along with development dependencies:

```bash
pip install -e ".[dev]"
```

*Note: If testing is required, ensure you install `pytest` explicitly if not covered by the dev block.*

## 4. Environment Variables

Create a local environment file. 

```bash
cp .env.local.example .env.local
```

### Required Credentials

While the application primarily uses open/free data sources (like the public STAC endpoints for Earth Search), certain NASA APIs require a free Earthdata login.
1. Register for free at [NASA Earthdata](https://urs.earthdata.nasa.gov/users/new).
2. Generate a Bearer Token.
3. Update `.env.local` with your credentials:
   ```env
   NASA_EARTHDATA_USERNAME=your_username
   NASA_BEARER_TOKEN=your_token
   STAC_ENDPOINT=https://earth-search.aws.element84.com/v1
   ```

## 5. Storage Directories

The system requires local directories for caching images and model outputs. Ensure these exist (they are usually created by the scripts, but creating them avoids startup warnings):

```bash
mkdir -p storage/satellite storage/ml storage/flood_memory storage/dams/imagery storage/dams/water_masks storage/dams/fill_history
```

## 6. Running the Dashboard

The primary user interface is the Streamlit dashboard.

```bash
python -m streamlit run streamlit_app.py
```

The application will start and be available at `http://localhost:8501`.

## 7. Running the FastAPI Backend (Optional)

If you are developing API integrations or internal toolchains, you can run the FastAPI server:

```bash
APP_MODE=demo uvicorn pakistan_flood_monitor.api.main:app --reload --port 8000
```
This API will be available at `http://localhost:8000`, with interactive Swagger documentation at `http://localhost:8000/docs`.
