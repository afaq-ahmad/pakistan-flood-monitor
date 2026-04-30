from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_bounds

from app.services.dashboard import dashboard_service


@dataclass(slots=True)
class ExportBundle:
    export_id: str
    format: str
    event_id: str
    output_path: Path
    manifest_path: Path
    validation: dict[str, Any]


class ExportCenterService:
    def __init__(self) -> None:
        self._export_dir = Path(".cache/exports")
        self._export_dir.mkdir(parents=True, exist_ok=True)

    def create_export(self, *, event_id: str, export_format: str) -> ExportBundle:
        event = next((item for item in dashboard_service.list_events() if item.event_id == event_id), None)
        if event is None:
            raise KeyError(f"Unknown event: {event_id}")

        export_id = f"exp-{event_id}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        event_dir = self._export_dir / export_id
        event_dir.mkdir(parents=True, exist_ok=True)

        if export_format == "geojson":
            output_path = self._export_geojson(event_dir, event_id)
        elif export_format == "geoparquet":
            output_path = self._export_geoparquet(event_dir, event_id)
        elif export_format == "cog":
            output_path = self._export_cog(event_dir, event_id)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")

        validation = self._validate_export(output_path, export_format)
        manifest = self._build_manifest(event_id=event_id, export_id=export_id, export_format=export_format, output_path=output_path)
        manifest_path = event_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        return ExportBundle(
            export_id=export_id,
            format=export_format,
            event_id=event_id,
            output_path=output_path,
            manifest_path=manifest_path,
            validation=validation,
        )

    def _event_gdf(self, event_id: str) -> gpd.GeoDataFrame:
        layer = dashboard_service.map_ready_event_layer()
        features = [f for f in layer["features"] if f["id"] == event_id]
        if not features:
            raise KeyError(f"Unknown event: {event_id}")
        return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")

    def _export_geojson(self, event_dir: Path, event_id: str) -> Path:
        path = event_dir / f"{event_id}.geojson"
        self._event_gdf(event_id).to_file(path, driver="GeoJSON")
        return path

    def _export_geoparquet(self, event_dir: Path, event_id: str) -> Path:
        path = event_dir / f"{event_id}.parquet"
        self._event_gdf(event_id).to_parquet(path)
        return path

    def _export_cog(self, event_dir: Path, event_id: str) -> Path:
        gdf = self._event_gdf(event_id)
        bounds = gdf.total_bounds
        path = event_dir / f"{event_id}.tif"
        width, height = 128, 128
        profile = {
            "driver": "GTiff",
            "height": height,
            "width": width,
            "count": 1,
            "dtype": rasterio.uint8,
            "crs": "EPSG:4326",
            "transform": from_bounds(*bounds, width=width, height=height),
            "compress": "deflate",
            "tiled": True,
            "blockxsize": 64,
            "blockysize": 64,
        }
        with rasterio.open(path, "w", **profile) as dst:
            band = np.zeros((height, width), dtype="uint8")
            band[:, :] = 1 if gdf.geometry.iloc[0].buffer(0).is_valid else 0
            dst.write(band, 1)
            dst.build_overviews([2, 4], rasterio.enums.Resampling.nearest)
            dst.update_tags(AREA_OR_POINT="Area")
        return path

    def _validate_export(self, path: Path, export_format: str) -> dict[str, Any]:
        if export_format == "geojson":
            parsed = json.loads(path.read_text(encoding="utf-8"))
            if parsed.get("type") != "FeatureCollection":
                raise ValueError("GeoJSON export is not a FeatureCollection")
            gdf = gpd.read_file(path)
            return {"format": "geojson", "valid": not gdf.empty, "feature_count": len(gdf)}

        if export_format == "geoparquet":
            gdf = gpd.read_parquet(path)
            return {"format": "geoparquet", "valid": not gdf.empty and gdf.crs is not None, "feature_count": len(gdf)}

        if export_format == "cog":
            with rasterio.open(path) as ds:
                tiled = bool(ds.profile.get("tiled"))
                overview_count = len(ds.overviews(1))
                valid = tiled and overview_count >= 1 and ds.crs is not None
                return {"format": "cog", "valid": valid, "width": ds.width, "height": ds.height, "overviews": overview_count}

        raise ValueError(f"Unsupported export format: {export_format}")

    def _build_manifest(self, *, event_id: str, export_id: str, export_format: str, output_path: Path) -> dict[str, Any]:
        return {
            "schema": "pakistan-flood-monitor/export-manifest/v1",
            "export_id": export_id,
            "event_id": event_id,
            "format": export_format,
            "generated_at": datetime.now(UTC).isoformat(),
            "lineage": {
                "source_endpoint": f"/analytics/map/events?event_id={event_id}",
                "exposure_endpoint": f"/public/events/{event_id}/exposure",
                "processing_version": "dashboard-service-v1",
            },
            "outputs": [{"path": str(output_path), "size_bytes": output_path.stat().st_size}],
        }


export_center_service = ExportCenterService()
