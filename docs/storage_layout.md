# Storage layout and artifact conventions

## Deterministic directory layout

- `raw/{sensor}/{year}/{month}/{scene_id}/`
- `prepared/{corridor_id}/{sensor}/{date}/{scene_id}/`
- `derived/{corridor_id}/{run_type}/{date}/{run_id}/`
- `published/{corridor_id}/{event_id}/`

## Standardized artifact names

- `sar_vv_prepared.tif`
- `sar_vh_prepared.tif`
- `flood_mask_raw.tif`
- `flood_mask_cleaned.tif`
- `flood_candidates.parquet`
- `breach_features.parquet`
- `exposure_summary.json`

## Format policy

### Internal
- Rasters: COG/GeoTIFF
- Vector analytics: GeoParquet
- Operational layers/state: PostGIS

### External
- API/download payloads: GeoJSON or JSON

## Manifest and checksum

Each run writes a manifest with:
- source files
- output files
- file size and SHA256 checksum
- CRS and extent (for rasters)
- per-band min/max statistics (for rasters)
- software version and timestamp
