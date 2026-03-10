from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape

from app.services.scoring import score_breach_candidate, score_flood_candidate_confidence


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
    embankment_distance_raster_path: str | Path | None = None
    district_id_raster_path: str | Path | None = None
    hydromet_stress_raster_path: str | Path | None = None
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
    morphology_iterations: int = 1
    merge_neighbor_pixels: int = 1
    include_permanent_water: bool = False


@dataclass(slots=True)
class FloodAnomalyResult:
    scene_id: str
    candidate_count: int
    valid_pixel_count: int
    candidate_ratio: float
    candidate_features: list[dict[str, Any]]
    output_rasters: dict[str, Path]
    candidate_vector_path: Path | None = None


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
        embankment_distance = self._load_optional_raster(
            payload.embankment_distance_raster_path, fallback=np.full_like(vv, np.nan)
        )
        district_ids = self._load_optional_raster(payload.district_id_raster_path, fallback=np.zeros_like(vv))
        hydromet_stress = self._load_optional_raster(payload.hydromet_stress_raster_path, fallback=np.zeros_like(vv))

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
        threshold_mask = self._threshold_mask(final_score, valid_mask)
        initial_candidates = np.logical_and(valid_mask, threshold_mask > 0)
        filtered_candidates, candidate_features = self._filter_candidates(
            initial_candidates,
            final_score,
            previous_candidates,
            next_candidates,
            slope,
            relative_elevation,
            river_distance,
            embankment_distance,
            seasonal_water,
            district_ids,
            hydromet_stress,
        )
        cleaned_candidates = self._morphological_cleanup(filtered_candidates)

        candidate_vector_path = self._vectorize_candidates(
            path=out_dir / f"{payload.scene_id}_flood_candidates.parquet",
            mask=cleaned_candidates,
            profile=profile,
            features=candidate_features,
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
            "flood_candidates_cleaned": self._write_raster(
                out_dir / f"{payload.scene_id}_flood_candidates_cleaned.tif", cleaned_candidates.astype(np.float32), profile
            ),
            "flood_threshold_mask": self._write_raster(
                out_dir / f"{payload.scene_id}_flood_threshold_mask.tif", threshold_mask.astype(np.float32), profile
            ),
            "valid_analysis_mask": self._write_raster(
                out_dir / f"{payload.scene_id}_valid_analysis_mask.tif", valid_mask.astype(np.float32), profile
            ),
        }

        valid_pixel_count = int(valid_mask.sum())
        candidate_count = int(cleaned_candidates.sum())
        candidate_ratio = 0.0 if valid_pixel_count == 0 else candidate_count / valid_pixel_count

        return FloodAnomalyResult(
            scene_id=payload.scene_id,
            candidate_count=candidate_count,
            valid_pixel_count=valid_pixel_count,
            candidate_ratio=float(candidate_ratio),
            candidate_features=candidate_features,
            output_rasters=output_rasters,
            candidate_vector_path=candidate_vector_path,
        )

    def _threshold_mask(self, score: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
        threshold_mask = np.zeros_like(score, dtype=np.uint8)
        threshold_mask[valid_mask & (score >= self._config.anomaly_threshold)] = 1
        threshold_mask[valid_mask & (score >= self._config.strong_evidence_threshold)] = 2
        return threshold_mask

    def _morphological_cleanup(self, mask: np.ndarray) -> np.ndarray:
        cleaned = mask.copy()
        components = self._connected_components(cleaned)
        for component in components:
            if len(component) >= self._config.min_object_pixels:
                continue
            for row, col in component:
                cleaned[row, col] = False
        for _ in range(self._config.morphology_iterations):
            cleaned = self._binary_close(cleaned)
        for _ in range(self._config.merge_neighbor_pixels):
            cleaned = self._binary_dilate(cleaned)
            cleaned = self._binary_erode(cleaned)
        return cleaned

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
        slope: np.ndarray,
        relative_elevation: np.ndarray,
        river_distance: np.ndarray,
        embankment_distance: np.ndarray,
        seasonal_water: np.ndarray,
        district_ids: np.ndarray,
        hydromet_stress: np.ndarray,
    ) -> tuple[np.ndarray, list[dict[str, Any]]]:
        labeled_objects = self._connected_components(initial_candidates)
        previous_components = self._connected_components(previous_candidates > 0)
        next_components = self._connected_components(next_candidates > 0)
        filtered = np.zeros_like(initial_candidates, dtype=bool)
        features: list[dict[str, Any]] = []

        for idx, component in enumerate(labeled_objects, start=1):
            area_pixels = len(component)
            perimeter = self._component_perimeter(component, initial_candidates.shape)
            compactness = 0.0 if perimeter == 0 else float(4 * np.pi * area_pixels / (perimeter**2))
            elongation = self._component_elongation(component)
            has_predecessor = any(previous_candidates[r, c] > 0 for r, c in component)
            has_successor = any(next_candidates[r, c] > 0 for r, c in component)
            mean_score = float(np.nanmean([final_score[r, c] for r, c in component]))
            slope_mean = float(np.nanmean([slope[r, c] for r, c in component]))
            relative_elevation_mean = float(np.nanmean([relative_elevation[r, c] for r, c in component]))
            distance_to_river = self._safe_component_nanmean(component, river_distance)
            distance_to_embankment = self._safe_component_nanmean(component, embankment_distance)
            seasonal_overlap = float(np.mean([1.0 if seasonal_water[r, c] > 0 else 0.0 for r, c in component]))
            district_values = [int(district_ids[r, c]) for r, c in component if district_ids[r, c] > 0]
            district_intersections = sorted(set(district_values))
            hydromet_mean = self._safe_component_nanmean(component, hydromet_stress)
            persistence_score = float(((1.0 if has_predecessor else 0.0) + (1.0 if has_successor else 0.0)) / 2.0)

            change_direction_relative_to_levee = self._change_direction_relative_to_levee(
                component=component,
                previous_candidates=previous_candidates,
                embankment_distance=embankment_distance,
            )
            inland_propagation_direction = max(0.0, change_direction_relative_to_levee)

            confidence = score_flood_candidate_confidence(
                mean_anomaly_score=mean_score,
                slope_mean=slope_mean,
                relative_elevation_mean=relative_elevation_mean,
                distance_to_river_m=distance_to_river,
                seasonal_overlap_ratio=seasonal_overlap,
                hydromet_stress_score=hydromet_mean,
                persistence_score=persistence_score,
                rainfall_24h_mm=hydromet_mean * 100.0,
                rainfall_72h_mm=hydromet_mean * 180.0,
                forecast_discharge_percentile=hydromet_mean,
                inland_propagation_direction=inland_propagation_direction,
            )

            keep = area_pixels >= self._config.min_object_pixels and compactness >= self._config.min_compactness
            if keep:
                for r, c in component:
                    filtered[r, c] = True

            overlap_prev = self._count_component_overlaps(component, previous_components)
            overlap_next = self._count_component_overlaps(component, next_components)
            sudden_emergence = 1.0 if overlap_prev == 0 else max(0.0, 1.0 - min(1.0, overlap_prev / 3.0))
            expansion_speed = self._estimate_expansion_speed(area_pixels, overlap_prev)
            split_merge_complexity = min(1.0, max(0, overlap_prev - 1) * 0.5 + max(0, overlap_next - 1) * 0.5)

            protected_side_ratio = self._protected_side_ratio(component, embankment_distance, relative_elevation)
            side_of_embankment = "protected" if protected_side_ratio >= 0.5 else "riverward"
            first_appearance_timestamp = "current_scene" if overlap_prev == 0 else "prior_scene"
            terrain_plausibility = confidence["components"]["terrain_plausibility"]

            breach_assessment = None
            if keep:
                breach_assessment = score_breach_candidate(
                    protected_side_ratio=protected_side_ratio,
                    distance_to_embankment_m=distance_to_embankment,
                    expansion_away_from_levee_score=inland_propagation_direction,
                    sudden_emergence_score=sudden_emergence,
                    hydromet_support_score=hydromet_mean,
                    terrain_plausibility_score=terrain_plausibility,
                    persistence_score=persistence_score,
                    split_merge_complexity=split_merge_complexity,
                )

            features.append(
                {
                    "candidate_id": f"cand_{idx}",
                    "area_pixels": area_pixels,
                    "perimeter_pixels": perimeter,
                    "compactness": compactness,
                    "elongation": elongation,
                    "mean_score": mean_score,
                    "slope_mean": slope_mean,
                    "relative_elevation_mean": relative_elevation_mean,
                    "distance_to_river_m": distance_to_river,
                    "distance_to_embankment_m": distance_to_embankment,
                    "side_of_embankment": side_of_embankment,
                    "first_appearance_timestamp": first_appearance_timestamp,
                    "change_direction_relative_to_levee": change_direction_relative_to_levee,
                    "inland_propagation_direction": inland_propagation_direction,
                    "expansion_speed": expansion_speed,
                    "sudden_emergence": sudden_emergence,
                    "split_merge_complexity": split_merge_complexity,
                    "seasonal_water_overlap_ratio": seasonal_overlap,
                    "district_intersections": district_intersections,
                    "has_predecessor": has_predecessor,
                    "has_successor": has_successor,
                    "hydromet_context_score": hydromet_mean,
                    "confidence": confidence["confidence"],
                    "confidence_status": confidence["status"],
                    "confidence_components": confidence["components"],
                    "breach_assessment": breach_assessment,
                    "accepted": keep,
                }
            )

        return filtered, features

    def _count_component_overlaps(
        self,
        component: list[tuple[int, int]],
        reference_components: list[list[tuple[int, int]]],
    ) -> int:
        if not reference_components:
            return 0
        component_set = set(component)
        overlaps = 0
        for ref in reference_components:
            if any(pixel in component_set for pixel in ref):
                overlaps += 1
        return overlaps

    @staticmethod
    def _estimate_expansion_speed(area_pixels: int, overlap_prev: int) -> float:
        baseline = max(1.0, float(overlap_prev))
        return float(max(0.0, min(5.0, area_pixels / baseline)))

    def _change_direction_relative_to_levee(
        self,
        *,
        component: list[tuple[int, int]],
        previous_candidates: np.ndarray,
        embankment_distance: np.ndarray,
    ) -> float:
        current_centroid = self._component_centroid(component)
        prev_pixels = [(r, c) for r, c in component if previous_candidates[r, c] > 0]
        if prev_pixels:
            previous_centroid = self._component_centroid(prev_pixels)
        else:
            previous_centroid = current_centroid
        move = np.array([
            current_centroid[0] - previous_centroid[0],
            current_centroid[1] - previous_centroid[1],
        ], dtype=np.float32)
        grad_y, grad_x = np.gradient(np.nan_to_num(embankment_distance, nan=0.0))
        r = int(round(current_centroid[0]))
        c = int(round(current_centroid[1]))
        r = max(0, min(r, grad_y.shape[0] - 1))
        c = max(0, min(c, grad_y.shape[1] - 1))
        levee_normal = np.array([grad_y[r, c], grad_x[r, c]], dtype=np.float32)
        move_norm = float(np.linalg.norm(move))
        levee_norm = float(np.linalg.norm(levee_normal))
        if move_norm == 0.0 or levee_norm == 0.0:
            return 0.0
        return float(np.dot(move, levee_normal) / (move_norm * levee_norm))

    @staticmethod
    def _protected_side_ratio(
        component: list[tuple[int, int]],
        embankment_distance: np.ndarray,
        relative_elevation: np.ndarray,
    ) -> float:
        protected_pixels = 0
        for r, c in component:
            near_levee = np.isfinite(embankment_distance[r, c]) and embankment_distance[r, c] <= 2000
            inland_proxy = relative_elevation[r, c] >= 0
            if near_levee and inland_proxy:
                protected_pixels += 1
        return float(protected_pixels / max(1, len(component)))

    @staticmethod
    def _component_centroid(component: list[tuple[int, int]]) -> tuple[float, float]:
        coords = np.array(component, dtype=np.float32)
        return float(coords[:, 0].mean()), float(coords[:, 1].mean())

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

    @staticmethod
    def _safe_component_nanmean(component: list[tuple[int, int]], array: np.ndarray, *, default: float = 0.0) -> float:
        values = np.array([array[r, c] for r, c in component], dtype=np.float32)
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            return default
        return float(finite.mean())

    @staticmethod
    def _component_elongation(component: list[tuple[int, int]]) -> float:
        if len(component) < 3:
            return 0.0
        coords = np.array(component, dtype=np.float32)
        centered = coords - coords.mean(axis=0, keepdims=True)
        cov = np.cov(centered[:, 0], centered[:, 1])
        eigvals = np.linalg.eigvals(cov)
        eigvals = np.sort(np.real(eigvals))
        if eigvals[-1] <= 0:
            return 0.0
        return float(np.sqrt(max(eigvals[-1], 1e-6) / max(eigvals[0], 1e-6)))

    @staticmethod
    def _binary_dilate(mask: np.ndarray) -> np.ndarray:
        padded = np.pad(mask.astype(np.uint8), 1, mode="constant")
        windows = np.lib.stride_tricks.sliding_window_view(padded, (3, 3))
        return (np.max(windows, axis=(2, 3)) > 0).astype(bool)

    @staticmethod
    def _binary_erode(mask: np.ndarray) -> np.ndarray:
        padded = np.pad(mask.astype(np.uint8), 1, mode="constant")
        windows = np.lib.stride_tricks.sliding_window_view(padded, (3, 3))
        return (np.min(windows, axis=(2, 3)) > 0).astype(bool)

    def _binary_open(self, mask: np.ndarray) -> np.ndarray:
        return self._binary_dilate(self._binary_erode(mask))

    def _binary_close(self, mask: np.ndarray) -> np.ndarray:
        return self._binary_erode(self._binary_dilate(mask))

    def _vectorize_candidates(
        self,
        *,
        path: Path,
        mask: np.ndarray,
        profile: dict,
        features: list[dict[str, Any]],
    ) -> Path | None:
        if not features or int(mask.sum()) == 0:
            return None

        records: list[dict[str, Any]] = []
        feature_map = {f["candidate_id"]: f for f in features if f.get("accepted")}
        idx = 1
        for geom, value in shapes(mask.astype(np.uint8), mask=mask.astype(bool), transform=profile["transform"]):
            if int(value) != 1:
                continue
            candidate_id = f"cand_{idx}"
            attrs = feature_map.get(candidate_id, {})
            records.append({**attrs, "candidate_id": candidate_id, "geometry": shape(geom)})
            idx += 1

        if not records:
            return None

        gdf = gpd.GeoDataFrame(records, crs=profile.get("crs"))
        try:
            gdf.to_parquet(path, index=False)
            return path
        except ImportError:
            fallback_path = path.with_suffix(".geojson")
            payload = json.loads(gdf.to_json())
            fallback_path.write_text(json.dumps(payload), encoding="utf-8")
            return fallback_path

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
