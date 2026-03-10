from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio


@dataclass(slots=True)
class FloodAnomalyInput:
    scene_id: str
    current_scene_rasters: dict[str, str | Path]
    baseline_rasters: dict[str, str | Path]
    corridor_mask_path: str | Path | None = None
    permanent_water_mask_path: str | Path | None = None
    slope_raster_path: str | Path | None = None
    nuisance_mask_path: str | Path | None = None


@dataclass(slots=True)
class FloodAnomalyConfig:
    minimum_std: float = 0.75
    max_slope_degrees: float = 15.0
    anomaly_threshold: float = 0.6
    include_permanent_water: bool = False


@dataclass(slots=True)
class FloodAnomalyResult:
    scene_id: str
    candidate_count: int
    valid_pixel_count: int
    candidate_ratio: float
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

        likelihood = self._flood_likelihood(
            vv_delta=vv_delta,
            vh_delta=vh_delta,
            contrast_delta=contrast_delta,
            vv_z=vv_z,
            vh_z=vh_z,
            texture_change=texture_change,
        )

        likelihood = np.where(valid_mask, likelihood, np.nan).astype(np.float32)
        candidates = np.logical_and(valid_mask, likelihood >= self._config.anomaly_threshold)

        output_rasters = {
            "flood_likelihood": self._write_raster(out_dir / f"{payload.scene_id}_flood_likelihood.tif", likelihood, profile),
            "valid_analysis_mask": self._write_raster(
                out_dir / f"{payload.scene_id}_valid_analysis_mask.tif", valid_mask.astype(np.float32), profile
            ),
        }

        valid_pixel_count = int(valid_mask.sum())
        candidate_count = int(candidates.sum())
        candidate_ratio = 0.0 if valid_pixel_count == 0 else candidate_count / valid_pixel_count

        return FloodAnomalyResult(
            scene_id=payload.scene_id,
            candidate_count=candidate_count,
            valid_pixel_count=valid_pixel_count,
            candidate_ratio=float(candidate_ratio),
            output_rasters=output_rasters,
        )

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
