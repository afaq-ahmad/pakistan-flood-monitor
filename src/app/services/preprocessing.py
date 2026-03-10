from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.mask import mask
from rasterio.transform import from_origin
from rasterio.warp import reproject
from shapely.geometry import shape


@dataclass(slots=True)
class Sentinel1SceneCandidate:
    scene_id: str
    corridor_id: str
    geometry: dict
    assets: Mapping[str, str]
    polarizations: list[str] = field(default_factory=list)
    priority: int = 0


@dataclass(slots=True)
class AssetRetrievalPlan:
    scene_id: str
    corridor_id: str
    selected_assets: dict[str, str]
    overlap_ratio: float
    accepted: bool
    reason: str


@dataclass(slots=True)
class PreparedSarScene:
    scene_id: str
    corridor_id: str
    acquisition_time: datetime
    orbit_pass: str | None
    look_direction: str | None
    polarization_paths: dict[str, Path]
    available_polarizations: list[str]
    missing_polarizations: list[str]
    stats: dict[str, dict[str, float]]
    processing_metadata: dict[str, str | float | bool | list[str]]


class Sentinel1Preprocessor:
    """Corridor-first Sentinel-1 preprocessing pipeline.

    Implements metadata-first asset selection, early clipping, corridor-grid reprojection,
    polarization normalization, and scene-level QA statistics.
    """

    def __init__(
        self,
        *,
        corridor_geometry: dict,
        working_crs: str,
        resolution_meters: float,
        clip_buffer_meters: float = 300.0,
    ) -> None:
        self._corridor = gpd.GeoDataFrame([{"geometry": shape(corridor_geometry)}], crs="EPSG:4326")
        self._working_crs = working_crs
        self._resolution = resolution_meters
        self._clip_buffer_meters = clip_buffer_meters
        self._grid_transform, self._grid_width, self._grid_height = self._build_corridor_grid()

    def build_asset_retrieval_plan(
        self,
        candidates: Iterable[Sentinel1SceneCandidate],
        *,
        min_overlap_ratio: float = 0.05,
        min_priority: int = 0,
    ) -> list[AssetRetrievalPlan]:
        corridor_geom = self._corridor.geometry.iloc[0]
        plans: list[AssetRetrievalPlan] = []

        for candidate in candidates:
            if candidate.priority < min_priority:
                plans.append(
                    AssetRetrievalPlan(
                        scene_id=candidate.scene_id,
                        corridor_id=candidate.corridor_id,
                        selected_assets={},
                        overlap_ratio=0.0,
                        accepted=False,
                        reason="priority_below_threshold",
                    )
                )
                continue

            scene_geom = shape(candidate.geometry)
            overlap = corridor_geom.intersection(scene_geom)
            overlap_ratio = 0.0 if corridor_geom.area == 0 else float(overlap.area / corridor_geom.area)

            selected_assets = self._extract_sar_assets(candidate.assets)
            if overlap_ratio < min_overlap_ratio:
                reason = "aoi_overlap_below_threshold"
                accepted = False
                selected_assets = {}
            elif not selected_assets:
                reason = "missing_vv_vh_assets"
                accepted = False
            else:
                reason = "accepted"
                accepted = True

            plans.append(
                AssetRetrievalPlan(
                    scene_id=candidate.scene_id,
                    corridor_id=candidate.corridor_id,
                    selected_assets=selected_assets,
                    overlap_ratio=overlap_ratio,
                    accepted=accepted,
                    reason=reason,
                )
            )

        return plans

    def preprocess_scene(
        self,
        *,
        scene_id: str,
        corridor_id: str,
        acquisition_time: datetime,
        asset_paths: Mapping[str, str | Path],
        output_dir: str | Path,
        orbit_pass: str | None = None,
        look_direction: str | None = None,
    ) -> PreparedSarScene:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        normalized = self._extract_sar_assets(asset_paths)
        expected = ["vv", "vh"]
        available = [pol for pol in expected if pol in normalized]
        missing = [pol for pol in expected if pol not in normalized]

        polarization_paths: dict[str, Path] = {}
        stats: dict[str, dict[str, float]] = {}

        corridor_projected = self._corridor.to_crs(self._working_crs)
        corridor_geom = corridor_projected.geometry.iloc[0]
        corridor_area_sqkm = corridor_geom.area / 1_000_000

        for polarization, src_path in normalized.items():
            with rasterio.open(src_path) as src:
                clip_geometry = corridor_projected.to_crs(src.crs)
                buffered = clip_geometry.to_crs("EPSG:3857")
                buffered["geometry"] = buffered.geometry.buffer(self._clip_buffer_meters)
                buffered = buffered.to_crs(src.crs)
                clipped, clipped_transform = mask(src, buffered.geometry, crop=True)
                clipped_array = clipped[0]

                aligned = np.full((self._grid_height, self._grid_width), np.nan, dtype=np.float32)
                src_nodata = src.nodata
                working_clip = clipped_array.astype(np.float32)
                if src_nodata is not None:
                    working_clip = np.where(clipped_array == src_nodata, np.nan, working_clip)

                reproject(
                    source=working_clip,
                    destination=aligned,
                    src_transform=clipped_transform,
                    src_crs=src.crs,
                    dst_transform=self._grid_transform,
                    dst_crs=self._working_crs,
                    resampling=Resampling.bilinear,
                    dst_nodata=np.nan,
                )

                corridor_mask = geometry_mask(
                    [corridor_geom],
                    out_shape=(self._grid_height, self._grid_width),
                    transform=self._grid_transform,
                    invert=True,
                )
                valid = np.logical_and(~np.isnan(aligned), corridor_mask)
                total_corridor_pixels = int(corridor_mask.sum())
                valid_pixels = int(valid.sum())
                nodata_fraction = 1.0 if total_corridor_pixels == 0 else 1 - (valid_pixels / total_corridor_pixels)
                valid_coverage = 0.0 if total_corridor_pixels == 0 else valid_pixels / total_corridor_pixels
                overlap_sqkm = corridor_area_sqkm * valid_coverage

                finite_values = aligned[valid]
                if finite_values.size:
                    band_stats = {
                        "min": float(np.nanmin(finite_values)),
                        "max": float(np.nanmax(finite_values)),
                        "mean": float(np.nanmean(finite_values)),
                        "std": float(np.nanstd(finite_values)),
                        "nodata_fraction": float(nodata_fraction),
                        "valid_coverage_over_corridor": float(valid_coverage),
                        "overlap_area_sqkm": float(overlap_sqkm),
                    }
                else:
                    band_stats = {
                        "min": float("nan"),
                        "max": float("nan"),
                        "mean": float("nan"),
                        "std": float("nan"),
                        "nodata_fraction": 1.0,
                        "valid_coverage_over_corridor": 0.0,
                        "overlap_area_sqkm": 0.0,
                    }
                stats[polarization] = band_stats

                out_path = out_dir / f"{scene_id}_{polarization}_prepared.tif"
                profile = {
                    "driver": "GTiff",
                    "height": self._grid_height,
                    "width": self._grid_width,
                    "count": 1,
                    "dtype": "float32",
                    "crs": self._working_crs,
                    "transform": self._grid_transform,
                    "nodata": np.nan,
                }
                with rasterio.open(out_path, "w", **profile) as dst:
                    dst.write(aligned, 1)
                polarization_paths[polarization] = out_path

        metadata = {
            "working_crs": self._working_crs,
            "resolution_meters": self._resolution,
            "corridor_grid_width": self._grid_width,
            "corridor_grid_height": self._grid_height,
            "polarization_limitation": bool(missing),
            "polarization_limitation_note": "" if not missing else f"missing_polarizations={','.join(missing)}",
        }

        return PreparedSarScene(
            scene_id=scene_id,
            corridor_id=corridor_id,
            acquisition_time=acquisition_time,
            orbit_pass=orbit_pass,
            look_direction=look_direction,
            polarization_paths=polarization_paths,
            available_polarizations=available,
            missing_polarizations=missing,
            stats=stats,
            processing_metadata=metadata,
        )

    @staticmethod
    def _extract_sar_assets(assets: Mapping[str, str | Path]) -> dict[str, str]:
        selected: dict[str, str] = {}
        for name, href in assets.items():
            key = str(name).lower()
            if "vv" in key and "vv" not in selected:
                selected["vv"] = str(href)
            if "vh" in key and "vh" not in selected:
                selected["vh"] = str(href)
        return selected

    def _build_corridor_grid(self) -> tuple[rasterio.Affine, int, int]:
        projected = self._corridor.to_crs(self._working_crs)
        buffered = projected.geometry.buffer(self._clip_buffer_meters)
        minx, miny, maxx, maxy = buffered.total_bounds
        width = max(1, int(np.ceil((maxx - minx) / self._resolution)))
        height = max(1, int(np.ceil((maxy - miny) / self._resolution)))
        transform = from_origin(minx, maxy, self._resolution, self._resolution)
        return transform, width, height
