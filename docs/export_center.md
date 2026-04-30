# Export Center

The Export Center provides validated GIS exports for event geometries and related provenance metadata.

## API endpoints

- `POST /analytics/exports`
  - body: `{ "event_id": "evt-indus-001", "format": "geojson|cog|geoparquet" }`
  - returns output path, manifest path, validation results, and download links.
- `GET /analytics/exports/{export_id}/file`
  - downloads the exported file.
- `GET /analytics/exports/{export_id}/manifest`
  - downloads the export metadata manifest.

## Supported formats

1. **GeoJSON** (`.geojson`)
   - FeatureCollection payload for vector interoperability.
   - Validation checks: valid JSON, `type=FeatureCollection`, readable via GeoPandas.

2. **Cloud Optimized GeoTIFF (COG)** (`.tif`)
   - Tiled GeoTIFF with overviews and CRS metadata.
   - Validation checks: tiled profile, at least one overview, readable via Rasterio.

3. **GeoParquet** (`.parquet`)
   - Columnar geospatial format with geometry metadata and CRS.
   - Validation checks: readable via GeoPandas, CRS present, non-empty geometry set.

## Metadata manifest schema

Each export writes `manifest.json` alongside the file with:

- `schema`: `pakistan-flood-monitor/export-manifest/v1`
- `export_id`, `event_id`, `format`, `generated_at`
- `lineage`
  - `source_endpoint` (event geometry source)
  - `exposure_endpoint` (linked impact endpoint)
  - `processing_version`
- `outputs[]`
  - artifact path and file size

## QGIS/GIS usage examples

- **GeoJSON**: Layer → Add Layer → Add Vector Layer → choose `.geojson`
- **COG**: Layer → Add Layer → Add Raster Layer → choose `.tif`
- **GeoParquet** (QGIS with GDAL/Parquet support): Layer → Add Layer → Add Vector Layer → choose `.parquet`

## Limitations

- Current COG is an event footprint rasterized to a minimal synthetic mask for interoperability testing, not full SAR intensity imagery.
- Export storage is local filesystem cache (`.cache/exports`) and intended for runtime/demo workflows.


## Analyst guide

- QGIS integration guide: `docs/qgis_export_integration_workflow.md`
