from __future__ import annotations

from pathlib import Path
from typing import Mapping

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.mask import mask
from rasterio.transform import Affine
from rasterio.warp import reproject


def _write_raster(path: Path, array: np.ndarray, profile: dict, nodata: float | int = 0) -> Path:
    profile = profile.copy()
    profile.update(dtype=str(array.dtype), count=1, nodata=nodata)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array, 1)
    return path


def _clip_raster_to_geometry(dataset: rasterio.io.DatasetReader, geometry, working_resolution: float | None = None):
    clipped, transform = mask(dataset, [geometry], crop=True)
    array = clipped[0]

    profile = dataset.profile.copy()
    profile.update(height=array.shape[0], width=array.shape[1], transform=transform)

    if working_resolution is None:
        return array, profile

    scale_x = abs(transform.a) / working_resolution
    scale_y = abs(transform.e) / working_resolution
    target_width = max(1, int(array.shape[1] * scale_x))
    target_height = max(1, int(array.shape[0] * scale_y))

    target = np.zeros((target_height, target_width), dtype=array.dtype)
    target_transform = Affine(working_resolution, 0, transform.c, 0, -working_resolution, transform.f)
    reproject(
        source=array,
        destination=target,
        src_transform=transform,
        src_crs=dataset.crs,
        dst_transform=target_transform,
        dst_crs=dataset.crs,
        resampling=Resampling.nearest,
    )
    profile.update(height=target_height, width=target_width, transform=target_transform)
    return target, profile


def generate_permanent_water_masks(
    corridors: gpd.GeoDataFrame,
    jrc_permanent_water_raster: str | Path,
    output_dir: str | Path,
    working_resolution: float | None = None,
    water_threshold: int = 1,
) -> dict[str, Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, Path] = {}
    with rasterio.open(jrc_permanent_water_raster) as src:
        corridor_geoms = corridors.to_crs(src.crs)
        for _, corridor in corridor_geoms.iterrows():
            clipped, profile = _clip_raster_to_geometry(src, corridor.geometry, working_resolution)
            water_mask = (clipped >= water_threshold).astype(np.uint8)
            out_path = output_root / f"{corridor['corridor_id']}_permanent_water.tif"
            outputs[str(corridor["corridor_id"])] = _write_raster(out_path, water_mask, profile)

    return outputs


def generate_seasonal_water_masks(
    corridors: gpd.GeoDataFrame,
    water_occurrence_raster: str | Path,
    output_dir: str | Path,
    min_occurrence_pct: float = 5,
    max_occurrence_pct: float = 80,
    working_resolution: float | None = None,
) -> dict[str, Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, Path] = {}
    with rasterio.open(water_occurrence_raster) as src:
        corridor_geoms = corridors.to_crs(src.crs)
        for _, corridor in corridor_geoms.iterrows():
            clipped, profile = _clip_raster_to_geometry(src, corridor.geometry, working_resolution)
            seasonal = np.logical_and(clipped >= min_occurrence_pct, clipped <= max_occurrence_pct).astype(np.uint8)
            out_path = output_root / f"{corridor['corridor_id']}_seasonal_water.tif"
            outputs[str(corridor["corridor_id"])] = _write_raster(out_path, seasonal, profile)

    return outputs


def _focal_relief(array: np.ndarray) -> np.ndarray:
    padded = np.pad(array, 1, mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, (3, 3))
    local_max = windows.max(axis=(2, 3))
    local_min = windows.min(axis=(2, 3))
    return (local_max - local_min).astype(np.float32)


def derive_terrain_layers(
    corridors: gpd.GeoDataFrame,
    dem_raster: str | Path,
    output_dir: str | Path,
    working_resolution: float | None = None,
) -> dict[str, dict[str, Path]]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, dict[str, Path]] = {}
    with rasterio.open(dem_raster) as src:
        corridor_geoms = corridors.to_crs(src.crs)
        for _, corridor in corridor_geoms.iterrows():
            corridor_id = str(corridor["corridor_id"])
            clipped_dem, profile = _clip_raster_to_geometry(src, corridor.geometry, working_resolution)
            pixel_x = abs(profile["transform"].a)
            pixel_y = abs(profile["transform"].e)

            grad_y, grad_x = np.gradient(clipped_dem.astype(np.float32), pixel_y, pixel_x)
            slope = np.degrees(np.arctan(np.hypot(grad_x, grad_y))).astype(np.float32)
            local_relief = _focal_relief(clipped_dem.astype(np.float32))
            relative_elevation = (clipped_dem.astype(np.float32) - np.nanmedian(clipped_dem)).astype(np.float32)
            depressions = (relative_elevation < -np.nanstd(clipped_dem)).astype(np.uint8)
            flow_plausibility = np.logical_and(slope < 5, relative_elevation < np.nanquantile(relative_elevation, 0.4)).astype(
                np.uint8
            )

            corridor_dir = output_root / corridor_id
            corridor_dir.mkdir(parents=True, exist_ok=True)
            outputs[corridor_id] = {
                "slope": _write_raster(corridor_dir / "slope.tif", slope, profile, nodata=-9999),
                "local_relief": _write_raster(corridor_dir / "local_relief.tif", local_relief, profile, nodata=-9999),
                "depressions": _write_raster(corridor_dir / "depressions.tif", depressions, profile, nodata=0),
                "relative_elevation": _write_raster(
                    corridor_dir / "relative_elevation.tif", relative_elevation, profile, nodata=-9999
                ),
                "flow_plausibility": _write_raster(
                    corridor_dir / "flow_plausibility.tif", flow_plausibility, profile, nodata=0
                ),
            }

    return outputs


def _write_vector_layer(layer: gpd.GeoDataFrame, output_path: Path) -> Path:
    try:
        layer.to_parquet(output_path)
        return output_path
    except ImportError:
        fallback = output_path.with_suffix(".geojson")
        layer.to_file(fallback, driver="GeoJSON")
        return fallback


def prepare_exposure_baseline_layers(
    corridors: gpd.GeoDataFrame,
    exposure_layers: Mapping[str, str | Path],
    output_dir: str | Path,
    target_crs: str = "EPSG:4326",
) -> dict[str, dict[str, Path]]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict[str, Path]] = {}
    corridor_crs = corridors.to_crs(target_crs)

    for _, corridor in corridor_crs.iterrows():
        corridor_id = str(corridor["corridor_id"])
        corridor_dir = output_root / corridor_id
        corridor_dir.mkdir(parents=True, exist_ok=True)
        results[corridor_id] = {}

        for layer_name, layer_path in exposure_layers.items():
            layer = gpd.read_file(layer_path).to_crs(target_crs)
            layer["geometry"] = layer.geometry.make_valid()
            clipped = gpd.clip(layer, gpd.GeoDataFrame([corridor], geometry="geometry", crs=target_crs))
            clipped = clipped[~clipped.geometry.is_empty].copy()
            out_path = corridor_dir / f"{layer_name}.parquet"
            results[corridor_id][layer_name] = _write_vector_layer(clipped, out_path)

    return results
