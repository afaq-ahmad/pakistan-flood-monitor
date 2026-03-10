from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio

from app.services.preprocessing import PreparedSarScene


SEASON_BY_MONTH = {
    12: "winter",
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "autumn",
    10: "autumn",
    11: "autumn",
}


@dataclass(slots=True)
class BaselineRasterSet:
    group_key: str
    corridor_id: str
    polarization: str
    baseline_version: str
    scene_ids: list[str]
    excluded_scene_ids: list[str]
    output_rasters: dict[str, Path]


class RollingSarBaselineService:
    def __init__(
        self,
        *,
        max_nodata_fraction: float = 0.4,
        min_valid_coverage: float = 0.5,
    ) -> None:
        self._max_nodata_fraction = max_nodata_fraction
        self._min_valid_coverage = min_valid_coverage

    def group_baseline_scenes(
        self,
        scenes: list[PreparedSarScene],
        *,
        temporal_mode: str = "month",
        include_orbit: bool = True,
        include_look_direction: bool = False,
    ) -> dict[str, list[tuple[PreparedSarScene, str]]]:
        grouped: dict[str, list[tuple[PreparedSarScene, str]]] = {}

        for scene in scenes:
            time_key = self._time_group(scene.acquisition_time, temporal_mode=temporal_mode)
            for polarization in scene.available_polarizations:
                pieces = [scene.corridor_id, temporal_mode, time_key, polarization]
                if include_orbit:
                    pieces.append(scene.orbit_pass or "orbit_unknown")
                if include_look_direction:
                    pieces.append(scene.look_direction or "look_unknown")
                key = "|".join(pieces)
                grouped.setdefault(key, []).append((scene, polarization))

        return grouped

    def build_baseline_rasters(
        self,
        grouped_scenes: dict[str, list[tuple[PreparedSarScene, str]]],
        *,
        output_dir: str | Path,
        baseline_version: str,
    ) -> list[BaselineRasterSet]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)

        results: list[BaselineRasterSet] = []

        for key, scene_pairs in grouped_scenes.items():
            included_arrays: list[np.ndarray] = []
            included_ids: list[str] = []
            excluded_ids: list[str] = []
            profile = None

            for scene, polarization in scene_pairs:
                if self._exclude_scene(scene, polarization):
                    excluded_ids.append(scene.scene_id)
                    continue
                raster_path = scene.polarization_paths.get(polarization)
                if not raster_path:
                    excluded_ids.append(scene.scene_id)
                    continue

                with rasterio.open(raster_path) as src:
                    data = src.read(1).astype(np.float32)
                    profile = src.profile.copy()
                included_arrays.append(data)
                included_ids.append(scene.scene_id)

            if not included_arrays or profile is None:
                continue

            stack = np.stack(included_arrays, axis=0)
            median = np.nanmedian(stack, axis=0).astype(np.float32)
            std = np.nanstd(stack, axis=0).astype(np.float32)
            p10 = np.nanpercentile(stack, 10, axis=0).astype(np.float32)
            p90 = np.nanpercentile(stack, 90, axis=0).astype(np.float32)

            # Lightweight texture baseline: local std proxy from immediate neighborhood.
            padded = np.pad(median, 1, mode="edge")
            windows = np.lib.stride_tricks.sliding_window_view(padded, (3, 3))
            texture = np.nanstd(windows, axis=(2, 3)).astype(np.float32)

            profile.update(dtype="float32", count=1)
            key_safe = key.replace("|", "_")
            out_paths = {
                "median": self._write(root / f"{key_safe}_{baseline_version}_median.tif", median, profile),
                "std": self._write(root / f"{key_safe}_{baseline_version}_std.tif", std, profile),
                "p10": self._write(root / f"{key_safe}_{baseline_version}_p10.tif", p10, profile),
                "p90": self._write(root / f"{key_safe}_{baseline_version}_p90.tif", p90, profile),
                "texture": self._write(root / f"{key_safe}_{baseline_version}_texture.tif", texture, profile),
            }

            corridor_id, _, _, polarization, *_ = key.split("|")
            results.append(
                BaselineRasterSet(
                    group_key=key,
                    corridor_id=corridor_id,
                    polarization=polarization,
                    baseline_version=baseline_version,
                    scene_ids=included_ids,
                    excluded_scene_ids=excluded_ids,
                    output_rasters=out_paths,
                )
            )

        return results

    def _exclude_scene(self, scene: PreparedSarScene, polarization: str) -> bool:
        stats = scene.stats.get(polarization, {})
        nodata_fraction = float(stats.get("nodata_fraction", 1.0))
        valid_coverage = float(stats.get("valid_coverage_over_corridor", 0.0))
        note = str(scene.processing_metadata.get("quality_note", ""))

        if nodata_fraction > self._max_nodata_fraction:
            return True
        if valid_coverage < self._min_valid_coverage:
            return True
        if note in {"known_corruption", "acquisition_artifact", "event_condition"}:
            return True
        return False

    @staticmethod
    def _write(path: Path, array: np.ndarray, profile: dict) -> Path:
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(array, 1)
        return path

    @staticmethod
    def _time_group(acquisition_time: datetime, *, temporal_mode: str) -> str:
        if temporal_mode == "month":
            return f"{acquisition_time.month:02d}"
        if temporal_mode == "season":
            return SEASON_BY_MONTH[acquisition_time.month]
        raise ValueError("temporal_mode must be 'month' or 'season'")
