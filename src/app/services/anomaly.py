from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rasterio


@dataclass(slots=True)
class FloodAnomalyInput:
    scene_id: str
    current_scene_rasters: dict[str, str | Path]
    baseline_rasters: dict[str, str | Path]
    corridor_mask_path: str | Path | None = None
    permanent_water_mask_path: str | Path | None = None
    seasonal_water_mask_path: str | Path | None = None
    slope_raster_path: str | Path | None = None
    relative_elevation_raster_path: str | Path | None = None
    river_distance_raster_path: str | Path | None = None
    nuisance_mask_path: str | Path | None = None
    previous_candidate_mask_path: str | Path | None = None
    next_candidate_mask_path: str | Path | None = None


@dataclass(slots=True)
class FloodAnomalyConfig:
    minimum_std: float = 0.75
    max_slope_degrees: float = 15.0
    max_relative_elevation: float = 2.5
    max_river_distance_m: float = 20000.0
    anomaly_threshold: float = 0.6
    strong_evidence_threshold: float = 0.85
    permanent_water_penalty: float = 0.65
    seasonal_water_penalty: float = 0.8
    river_distance_penalty: float = 0.7
    terrain_penalty: float = 0.6
    min_object_pixels: int = 4
    min_compactness: float = 0.015
    include_permanent_water: bool = False


@dataclass(slots=True)
class FloodAnomalyResult:
    scene_id: str
    candidate_count: int
    valid_pixel_count: int
    candidate_ratio: float
    candidate_features: list[dict[str, Any]]
    output_rasters: dict[str, Path]


class FloodAnomalyDetector:
    """Rules-based Sentinel-1 anomaly detector for MVP flood-likelihood rasters."""

    def __init__(self, *, config: FloodAnomalyConfig | None = None) -> None:
        self._config = config or FloodAnomalyConfig()

    def detect(self, payload: FloodAnomalyInput, *, output_dir: str | Path) -> FloodAnomalyResult:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        vv, profile = self._load_raster(payload.current_scene_rasters["vv"])
        vh, _ = self._load_raster(payload.current_scene_rasters["vh"])

        vv_median, _ = self._load_raster(payload.baseline_rasters["vv_median"])
        vh_median, _ = self._load_raster(payload.baseline_rasters["vh_median"])
        vv_std, _ = self._load_raster(payload.baseline_rasters["vv_std"])
        vh_std, _ = self._load_raster(payload.baseline_rasters["vh_std"])

        vv_texture_base = self._load_optional_raster(payload.baseline_rasters.get("vv_texture"), fallback=vv_median)
        vh_texture_base = self._load_optional_raster(payload.baseline_rasters.get("vh_texture"), fallback=vh_median)

        vv_delta = vv - vv_median
        vh_delta = vh - vh_median

        contrast_current = vv - vh
        contrast_baseline = vv_median - vh_median
        contrast_delta = contrast_current - contrast_baseline

        safe_vv_std = np.maximum(vv_std, self._config.minimum_std)
        safe_vh_std = np.maximum(vh_std, self._config.minimum_std)
        vv_z = vv_delta / safe_vv_std
        vh_z = vh_delta / safe_vh_std

        vv_texture_current = self._local_texture(vv)
        vh_texture_current = self._local_texture(vh)
        baseline_texture = (vv_texture_base + vh_texture_base) / 2.0
        texture_current = (vv_texture_current + vh_texture_current) / 2.0
        texture_change = baseline_texture - texture_current

        valid_mask = self._build_valid_mask(
            vv=vv,
            vh=vh,
            vv_median=vv_median,
            vh_median=vh_median,
            vv_std=vv_std,
            vh_std=vh_std,
            corridor_mask_path=payload.corridor_mask_path,
            permanent_water_mask_path=payload.permanent_water_mask_path,
            slope_raster_path=payload.slope_raster_path,
            nuisance_mask_path=payload.nuisance_mask_path,
        )

        permanent_water = self._load_optional_raster(payload.permanent_water_mask_path, fallback=np.zeros_like(vv))
        seasonal_water = self._load_optional_raster(payload.seasonal_water_mask_path, fallback=np.zeros_like(vv))
        slope = self._load_optional_raster(payload.slope_raster_path, fallback=np.zeros_like(vv))
        relative_elevation = self._load_optional_raster(payload.relative_elevation_raster_path, fallback=np.zeros_like(vv))
        river_distance = self._load_optional_raster(payload.river_distance_raster_path, fallback=np.zeros_like(vv))
        previous_candidates = self._load_optional_raster(payload.previous_candidate_mask_path, fallback=np.zeros_like(vv))
        next_candidates = self._load_optional_raster(payload.next_candidate_mask_path, fallback=np.zeros_like(vv))

        likelihood = self._flood_likelihood(
            vv_delta=vv_delta,
            vh_delta=vh_delta,
            contrast_delta=contrast_delta,
            vv_z=vv_z,
            vh_z=vh_z,
            texture_change=texture_change,
        )

        plausibility = self._plausibility_score(
            likelihood=likelihood,
            permanent_water=permanent_water,
            seasonal_water=seasonal_water,
            slope=slope,
            relative_elevation=relative_elevation,
            river_distance=river_distance,
        )

        final_score = np.where(valid_mask, likelihood * plausibility, np.nan).astype(np.float32)
        initial_candidates = np.logical_and(valid_mask, final_score >= self._config.anomaly_threshold)
        filtered_candidates, candidate_features = self._filter_candidates(
            initial_candidates,
            final_score,
            previous_candidates,
            next_candidates,
        )

        output_rasters = {
            "flood_likelihood": self._write_raster(out_dir / f"{payload.scene_id}_flood_likelihood.tif", likelihood, profile),
            "flood_plausibility": self._write_raster(
                out_dir / f"{payload.scene_id}_flood_plausibility.tif", np.where(valid_mask, plausibility, np.nan), profile
            ),
            "flood_score_filtered": self._write_raster(
                out_dir / f"{payload.scene_id}_flood_score_filtered.tif", final_score, profile
            ),
            "flood_candidates_filtered": self._write_raster(
                out_dir / f"{payload.scene_id}_flood_candidates_filtered.tif", filtered_candidates.astype(np.float32), profile
            ),
            "valid_analysis_mask": self._write_raster(
                out_dir / f"{payload.scene_id}_valid_analysis_mask.tif", valid_mask.astype(np.float32), profile
            ),
        }

        valid_pixel_count = int(valid_mask.sum())
        candidate_count = int(filtered_candidates.sum())
        candidate_ratio = 0.0 if valid_pixel_count == 0 else candidate_count / valid_pixel_count

        return FloodAnomalyResult(
            scene_id=payload.scene_id,
            candidate_count=candidate_count,
            valid_pixel_count=valid_pixel_count,
            candidate_ratio=float(candidate_ratio),
            candidate_features=candidate_features,
            output_rasters=output_rasters,
        )

    def _plausibility_score(
        self,
        *,
        likelihood: np.ndarray,
        permanent_water: np.ndarray,
        seasonal_water: np.ndarray,
        slope: np.ndarray,
        relative_elevation: np.ndarray,
        river_distance: np.ndarray,
    ) -> np.ndarray:
        plausibility = np.ones_like(likelihood, dtype=np.float32)
        strong_evidence = likelihood >= self._config.strong_evidence_threshold

        if not self._config.include_permanent_water:
            plausibility *= np.where(permanent_water > 0, self._config.permanent_water_penalty, 1.0)
        plausibility *= np.where(seasonal_water > 0, self._config.seasonal_water_penalty, 1.0)

        terrain_implausible = (slope > self._config.max_slope_degrees) | (
            relative_elevation > self._config.max_relative_elevation
        )
        plausibility *= np.where(terrain_implausible & ~strong_evidence, self._config.terrain_penalty, 1.0)

        remote_river = river_distance > self._config.max_river_distance_m
        plausibility *= np.where(remote_river & ~strong_evidence, self._config.river_distance_penalty, 1.0)

        return np.clip(plausibility, 0.0, 1.0).astype(np.float32)

    def _filter_candidates(
        self,
        initial_candidates: np.ndarray,
        final_score: np.ndarray,
        previous_candidates: np.ndarray,
        next_candidates: np.ndarray,
    ) -> tuple[np.ndarray, list[dict[str, Any]]]:
        labeled_objects = self._connected_components(initial_candidates)
        filtered = np.zeros_like(initial_candidates, dtype=bool)
        features: list[dict[str, Any]] = []

        for idx, component in enumerate(labeled_objects, start=1):
            area_pixels = len(component)
            perimeter = self._component_perimeter(component, initial_candidates.shape)
            compactness = 0.0 if perimeter == 0 else float(4 * np.pi * area_pixels / (perimeter**2))
            has_predecessor = any(previous_candidates[r, c] > 0 for r, c in component)
            has_successor = any(next_candidates[r, c] > 0 for r, c in component)
            mean_score = float(np.nanmean([final_score[r, c] for r, c in component]))

            keep = area_pixels >= self._config.min_object_pixels and compactness >= self._config.min_compactness
            if keep:
                for r, c in component:
                    filtered[r, c] = True

            features.append(
                {
                    "candidate_id": f"cand_{idx}",
                    "area_pixels": area_pixels,
                    "compactness": compactness,
                    "mean_score": mean_score,
                    "has_predecessor": has_predecessor,
                    "has_successor": has_successor,
                    "accepted": keep,
                }
            )

        return filtered, features

    @staticmethod
    def _connected_components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
        rows, cols = mask.shape
        visited = np.zeros_like(mask, dtype=bool)
        components: list[list[tuple[int, int]]] = []

        for row in range(rows):
            for col in range(cols):
                if not mask[row, col] or visited[row, col]:
                    continue
                stack = [(row, col)]
                visited[row, col] = True
                component: list[tuple[int, int]] = []
                while stack:
                    r, c = stack.pop()
                    component.append((r, c))
                    for rr in range(max(0, r - 1), min(rows, r + 2)):
                        for cc in range(max(0, c - 1), min(cols, c + 2)):
                            if mask[rr, cc] and not visited[rr, cc]:
                                visited[rr, cc] = True
                                stack.append((rr, cc))
                components.append(component)
        return components

    @staticmethod
    def _component_perimeter(component: list[tuple[int, int]], shape: tuple[int, int]) -> int:
        rows, cols = shape
        component_set = set(component)
        perimeter = 0
        for r, c in component:
            for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if rr < 0 or rr >= rows or cc < 0 or cc >= cols or (rr, cc) not in component_set:
                    perimeter += 1
        return perimeter

    def _build_valid_mask(
        self,
        *,
        vv: np.ndarray,
        vh: np.ndarray,
        vv_median: np.ndarray,
        vh_median: np.ndarray,
        vv_std: np.ndarray,
        vh_std: np.ndarray,
        corridor_mask_path: str | Path | None,
        permanent_water_mask_path: str | Path | None,
        slope_raster_path: str | Path | None,
        nuisance_mask_path: str | Path | None,
    ) -> np.ndarray:
        valid = np.isfinite(vv) & np.isfinite(vh) & np.isfinite(vv_median) & np.isfinite(vh_median)
        valid &= np.isfinite(vv_std) & np.isfinite(vh_std)

        if corridor_mask_path:
            corridor, _ = self._load_raster(corridor_mask_path)
            valid &= corridor > 0

        if permanent_water_mask_path and not self._config.include_permanent_water:
            water, _ = self._load_raster(permanent_water_mask_path)
            valid &= water <= 0

        if slope_raster_path:
            slope, _ = self._load_raster(slope_raster_path)
            valid &= slope <= self._config.max_slope_degrees

        if nuisance_mask_path:
            nuisance, _ = self._load_raster(nuisance_mask_path)
            valid &= nuisance <= 0

        return valid

    @staticmethod
    def _flood_likelihood(
        *,
        vv_delta: np.ndarray,
        vh_delta: np.ndarray,
        contrast_delta: np.ndarray,
        vv_z: np.ndarray,
        vh_z: np.ndarray,
        texture_change: np.ndarray,
    ) -> np.ndarray:
        vv_drop = np.clip((-vv_delta - 1.0) / 4.0, 0.0, 1.0)
        vh_drop = np.clip((-vh_delta - 0.75) / 3.5, 0.0, 1.0)
        contrast_shift = np.clip(np.abs(contrast_delta) / 3.0, 0.0, 1.0)
        z_anomaly = np.clip(np.maximum(-vv_z, -vh_z) / 3.0, 0.0, 1.0)
        texture_component = np.clip(texture_change / 2.5, 0.0, 1.0)

        return (
            vv_drop * 0.30
            + vh_drop * 0.20
            + contrast_shift * 0.15
            + z_anomaly * 0.25
            + texture_component * 0.10
        ).astype(np.float32)

    @staticmethod
    def _local_texture(array: np.ndarray) -> np.ndarray:
        padded = np.pad(array, 1, mode="edge")
        windows = np.lib.stride_tricks.sliding_window_view(padded, (3, 3))
        return np.nanstd(windows, axis=(2, 3)).astype(np.float32)

    @staticmethod
    def _load_raster(path: str | Path) -> tuple[np.ndarray, dict]:
        with rasterio.open(path) as src:
            data = src.read(1).astype(np.float32)
            nodata = src.nodata
            if nodata is not None:
                data = np.where(data == nodata, np.nan, data)
            return data, src.profile.copy()

    def _load_optional_raster(self, path: str | Path | None, *, fallback: np.ndarray) -> np.ndarray:
        if path is None:
            return self._local_texture(fallback)
        data, _ = self._load_raster(path)
        return data

    @staticmethod
    def _write_raster(path: Path, array: np.ndarray, profile: dict) -> Path:
        out_profile = profile.copy()
        out_profile.pop("blockxsize", None)
        out_profile.pop("blockysize", None)
        out_profile.pop("tiled", None)
        out_profile.update(dtype="float32", count=1, nodata=np.nan)
        with rasterio.open(path, "w", **out_profile) as dst:
            dst.write(array.astype(np.float32), 1)
        return path


def detect_flood_anomaly(scene_id: str) -> dict:
    return {"scene_id": scene_id, "candidate_count": 0}
