# QGIS Export Integration Workflow

This guide shows analysts how to generate sample exports from the Export Center and load them into QGIS for review.

## Scope

Validated formats covered in this workflow:

- GeoJSON (`.geojson`) vector export
- Cloud Optimized GeoTIFF (`.tif`) raster export
- GeoParquet (`.parquet`) vector export
- Export metadata manifest (`manifest.json`) for lineage and QA context

## Prerequisites

- Repo checkout with Python dependencies installed.
- QGIS 3.28+ recommended.
- For GeoParquet export generation, install `pyarrow` in the runtime used by the API/tests.

## 1) Generate sample exports from Export Center

From repo root:

```bash
PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)
for fmt in ("geojson", "cog", "geoparquet"):
    response = client.post("/analytics/exports", json={"event_id": "evt-indus-001", "format": fmt})
    print(fmt, response.status_code)
    if response.status_code == 200:
        payload = response.json()
        print(" output:", payload["output_path"])
        print(" manifest:", payload["manifest_path"])
PY
```

Expected output location pattern:

- `.cache/exports/exp-evt-indus-001-<timestamp>/evt-indus-001.geojson`
- `.cache/exports/exp-evt-indus-001-<timestamp>/evt-indus-001.tif`
- `.cache/exports/exp-evt-indus-001-<timestamp>/evt-indus-001.parquet`
- `.cache/exports/exp-evt-indus-001-<timestamp>/manifest.json`

## 2) Validate exported sample files before QGIS import

### GeoJSON quick check

```bash
python -m json.tool .cache/exports/<export_id>/evt-indus-001.geojson > /dev/null
```

### COG quick check

```bash
python - <<'PY'
import rasterio

path = ".cache/exports/<export_id>/evt-indus-001.tif"
with rasterio.open(path) as ds:
    print("tiled:", bool(ds.profile.get("tiled")))
    print("overviews:", len(ds.overviews(1)))
    print("crs:", ds.crs)
PY
```

### GeoParquet quick check

```bash
python - <<'PY'
import geopandas as gpd

path = ".cache/exports/<export_id>/evt-indus-001.parquet"
gdf = gpd.read_parquet(path)
print("features:", len(gdf))
print("crs:", gdf.crs)
PY
```

### Manifest check

```bash
python - <<'PY'
import json

path = ".cache/exports/<export_id>/manifest.json"
manifest = json.loads(open(path, encoding="utf-8").read())
print("schema:", manifest["schema"])
print("format:", manifest["format"])
print("source_endpoint:", manifest["lineage"]["source_endpoint"])
print("exposure_endpoint:", manifest["lineage"]["exposure_endpoint"])
PY
```

Confirm `schema == pakistan-flood-monitor/export-manifest/v1`.

## 3) Import workflow in QGIS

### A. GeoJSON

1. Open QGIS.
2. `Layer` -> `Add Layer` -> `Add Vector Layer...`
3. Source type: `File`; browse to `evt-indus-001.geojson`.
4. Click `Add`.
5. Verify feature geometry loads and layer CRS is EPSG:4326.

### B. COG

1. `Layer` -> `Add Layer` -> `Add Raster Layer...`
2. Browse to `evt-indus-001.tif`.
3. Click `Add`.
4. Open `Layer Properties` -> `Information` and verify:
   - CRS is EPSG:4326.
   - Internal overviews exist.

### C. GeoParquet

1. Ensure QGIS build includes GDAL Parquet support.
2. `Layer` -> `Add Layer` -> `Add Vector Layer...`
3. Browse to `evt-indus-001.parquet`.
4. Click `Add`.
5. Validate feature count/extent matches GeoJSON layer.

### D. Manifest-assisted QA in analyst workflow

Use `manifest.json` alongside imported layers to capture provenance in analysis notes:

- `export_id`: tie map products to exact export run.
- `generated_at`: timestamp for reproducibility.
- `lineage.source_endpoint`: confirms event geometry source.
- `lineage.exposure_endpoint`: links the corresponding exposure context.
- `lineage.processing_version`: confirms processing version.

Recommended practice: store the manifest in the same QGIS project folder and record `export_id` in layout metadata.

## 4) Troubleshooting

- **GeoParquet export fails with `Missing optional dependency 'pyarrow.parquet'`**  
  Install dependency in your Python environment:
  ```bash
  pip install pyarrow
  ```

- **QGIS cannot open `.parquet`**  
  Your QGIS/GDAL build may lack Parquet support. Use GeoJSON as fallback and/or upgrade QGIS/GDAL.

- **COG imports but appears blank**  
  This project currently exports a minimal synthetic mask for COG validation, not SAR intensity imagery.

- **Unknown event error from export API**  
  Use an event ID returned by the dashboard event layer (for example, `evt-indus-001`).

## 5) Reproducible validation checklist

1. Run export generation command for each format.
2. Verify files exist under `.cache/exports/<export_id>/`.
3. Validate file format checks above.
4. Import into QGIS and confirm:
   - GeoJSON and GeoParquet extents align.
   - COG metadata includes CRS + overviews.
5. Capture any discrepancies with `export_id` and manifest details.
