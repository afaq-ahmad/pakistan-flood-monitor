from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.services.anomaly import FloodAnomalyDetector, FloodAnomalyInput


def _write_raster(path: Path, array: np.ndarray, *, nodata: float | None = np.nan) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=array.shape[0],
        width=array.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(70.0, 30.05, 0.01, 0.01),
        nodata=nodata,
    ) as dst:
        dst.write(array.astype(np.float32), 1)


def test_flood_anomaly_detector_computes_likelihood_and_candidates(tmp_path: Path) -> None:
    shape = (6, 6)
    vv_current = np.full(shape, -14.0, dtype=np.float32)
    vh_current = np.full(shape, -19.0, dtype=np.float32)
    vv_current[2:4, 2:4] = -20.0
    vh_current[2:4, 2:4] = -25.0

    vv_median = np.full(shape, -14.0, dtype=np.float32)
    vh_median = np.full(shape, -19.0, dtype=np.float32)
    vv_std = np.full(shape, 1.0, dtype=np.float32)
    vh_std = np.full(shape, 1.0, dtype=np.float32)

    corridor_mask = np.ones(shape, dtype=np.float32)
    corridor_mask[0, 0] = 0
    permanent_water = np.zeros(shape, dtype=np.float32)
    permanent_water[0, 5] = 1
    seasonal_water = np.zeros(shape, dtype=np.float32)
    slope = np.full(shape, 5.0, dtype=np.float32)
    slope[5, 5] = 22
    nuisance = np.zeros(shape, dtype=np.float32)
    nuisance[1, 1] = 1
    previous = np.zeros(shape, dtype=np.float32)
    previous[2:4, 2:4] = 1

    files = {
        "vv": tmp_path / "vv.tif",
        "vh": tmp_path / "vh.tif",
        "vv_median": tmp_path / "vv_median.tif",
        "vh_median": tmp_path / "vh_median.tif",
        "vv_std": tmp_path / "vv_std.tif",
        "vh_std": tmp_path / "vh_std.tif",
        "corridor": tmp_path / "corridor.tif",
        "water": tmp_path / "water.tif",
        "seasonal": tmp_path / "seasonal.tif",
        "slope": tmp_path / "slope.tif",
        "nuisance": tmp_path / "nuisance.tif",
        "previous": tmp_path / "previous.tif",
    }

    _write_raster(files["vv"], vv_current)
    _write_raster(files["vh"], vh_current)
    _write_raster(files["vv_median"], vv_median)
    _write_raster(files["vh_median"], vh_median)
    _write_raster(files["vv_std"], vv_std)
    _write_raster(files["vh_std"], vh_std)
    _write_raster(files["corridor"], corridor_mask)
    _write_raster(files["water"], permanent_water)
    _write_raster(files["seasonal"], seasonal_water)
    _write_raster(files["slope"], slope)
    _write_raster(files["nuisance"], nuisance)
    _write_raster(files["previous"], previous)

    detector = FloodAnomalyDetector()
    result = detector.detect(
        FloodAnomalyInput(
            scene_id="S1_TEST",
            current_scene_rasters={"vv": files["vv"], "vh": files["vh"]},
            baseline_rasters={
                "vv_median": files["vv_median"],
                "vh_median": files["vh_median"],
                "vv_std": files["vv_std"],
                "vh_std": files["vh_std"],
            },
            corridor_mask_path=files["corridor"],
            permanent_water_mask_path=files["water"],
            seasonal_water_mask_path=files["seasonal"],
            slope_raster_path=files["slope"],
            nuisance_mask_path=files["nuisance"],
            previous_candidate_mask_path=files["previous"],
        ),
        output_dir=tmp_path / "derived",
    )

    assert result.scene_id == "S1_TEST"
    assert result.valid_pixel_count == 32
    assert result.candidate_count == 4
    assert result.output_rasters["flood_likelihood"].exists()
    assert result.output_rasters["flood_plausibility"].exists()
    assert result.output_rasters["flood_candidates_filtered"].exists()

    with rasterio.open(result.output_rasters["flood_likelihood"]) as src:
        likelihood = src.read(1)
    with rasterio.open(result.output_rasters["flood_score_filtered"]) as src:
        filtered_score = src.read(1)

    assert np.nanmean(likelihood[2:4, 2:4]) > 0.7
    assert np.nanmean(filtered_score[2:4, 2:4]) > 0.55
    assert np.isnan(filtered_score[0, 0])
    assert np.isnan(filtered_score[5, 5])
    assert np.isnan(filtered_score[1, 1])

    assert len(result.candidate_features) == 1
    assert result.candidate_features[0]["has_predecessor"] is True
    assert result.candidate_features[0]["has_successor"] is False
    assert result.candidate_features[0]["accepted"] is True


def test_flood_anomaly_detector_suppresses_tiny_artifact_candidates(tmp_path: Path) -> None:
    shape = (5, 5)
    vv_current = np.full(shape, -14.0, dtype=np.float32)
    vh_current = np.full(shape, -19.0, dtype=np.float32)
    vv_current[2, 2] = -20.0
    vh_current[2, 2] = -25.0

    vv_median = np.full(shape, -14.0, dtype=np.float32)
    vh_median = np.full(shape, -19.0, dtype=np.float32)
    vv_std = np.full(shape, 1.0, dtype=np.float32)
    vh_std = np.full(shape, 1.0, dtype=np.float32)

    files = {
        "vv": tmp_path / "vv.tif",
        "vh": tmp_path / "vh.tif",
        "vv_median": tmp_path / "vv_median.tif",
        "vh_median": tmp_path / "vh_median.tif",
        "vv_std": tmp_path / "vv_std.tif",
        "vh_std": tmp_path / "vh_std.tif",
    }

    for key, value in {
        "vv": vv_current,
        "vh": vh_current,
        "vv_median": vv_median,
        "vh_median": vh_median,
        "vv_std": vv_std,
        "vh_std": vh_std,
    }.items():
        _write_raster(files[key], value)

    detector = FloodAnomalyDetector()
    result = detector.detect(
        FloodAnomalyInput(
            scene_id="S1_ARTIFACT",
            current_scene_rasters={"vv": files["vv"], "vh": files["vh"]},
            baseline_rasters={
                "vv_median": files["vv_median"],
                "vh_median": files["vh_median"],
                "vv_std": files["vv_std"],
                "vh_std": files["vh_std"],
            },
        ),
        output_dir=tmp_path / "derived",
    )

    assert result.candidate_count == 0
    assert len(result.candidate_features) == 1
    assert result.candidate_features[0]["accepted"] is False
