from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.services.preprocessing import (
    OpticalPreprocessor,
    OpticalSceneCandidate,
    Sentinel1Preprocessor,
    Sentinel1SceneCandidate,
)
from app.services.sar_baseline import RollingSarBaselineService


def _write_raster(path: Path, array: np.ndarray) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=array.shape[0],
        width=array.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(70.0, 30.25, 0.01, 0.01),
        nodata=np.nan,
    ) as dst:
        dst.write(array.astype(np.float32), 1)


def test_s1_asset_retrieval_filters_by_overlap_and_priority() -> None:
    corridor = {
        "type": "Polygon",
        "coordinates": [[[70.0, 30.0], [70.0, 30.5], [70.5, 30.5], [70.5, 30.0], [70.0, 30.0]]],
    }
    preprocessor = Sentinel1Preprocessor(corridor_geometry=corridor, working_crs="EPSG:3857", resolution_meters=250)

    candidates = [
        Sentinel1SceneCandidate(
            scene_id="good",
            corridor_id="c1",
            geometry=corridor,
            assets={"vv": "s3://bucket/vv.tif", "vh": "s3://bucket/vh.tif", "noise": "x"},
            priority=10,
        ),
        Sentinel1SceneCandidate(
            scene_id="low-priority",
            corridor_id="c1",
            geometry=corridor,
            assets={"vv": "s3://bucket/vv.tif"},
            priority=0,
        ),
    ]

    plans = preprocessor.build_asset_retrieval_plan(candidates, min_priority=5)
    assert plans[0].accepted is True
    assert set(plans[0].selected_assets) == {"vv", "vh"}
    assert plans[1].accepted is False
    assert plans[1].reason == "priority_below_threshold"


def test_s1_preprocessing_aligns_grid_and_collects_stats(tmp_path: Path) -> None:
    corridor = {
        "type": "Polygon",
        "coordinates": [[[70.0, 30.0], [70.0, 30.2], [70.2, 30.2], [70.2, 30.0], [70.0, 30.0]]],
    }
    preprocessor = Sentinel1Preprocessor(corridor_geometry=corridor, working_crs="EPSG:3857", resolution_meters=500)

    vv_path = tmp_path / "vv.tif"
    vh_path = tmp_path / "vh.tif"
    _write_raster(vv_path, np.ones((32, 32), dtype=np.float32) * -14)
    _write_raster(vh_path, np.ones((32, 32), dtype=np.float32) * -18)

    prepared = preprocessor.preprocess_scene(
        scene_id="S1A_001",
        corridor_id="indus-1",
        acquisition_time=datetime(2024, 7, 1),
        asset_paths={"VV": vv_path, "VH": vh_path},
        output_dir=tmp_path / "prepared",
        orbit_pass="ASCENDING",
        look_direction="RIGHT",
    )

    assert prepared.processing_metadata["working_crs"] == "EPSG:3857"
    assert prepared.available_polarizations == ["vv", "vh"]
    assert prepared.missing_polarizations == []
    assert prepared.polarization_paths["vv"].exists()
    assert prepared.stats["vv"]["valid_coverage_over_corridor"] > 0

    with rasterio.open(prepared.polarization_paths["vv"]) as vv, rasterio.open(prepared.polarization_paths["vh"]) as vh:
        assert vv.width == vh.width
        assert vv.height == vh.height
        assert vv.transform == vh.transform


def test_rolling_baseline_groups_builds_and_versions_outputs(tmp_path: Path) -> None:
    corridor = {
        "type": "Polygon",
        "coordinates": [[[70.0, 30.0], [70.0, 30.2], [70.2, 30.2], [70.2, 30.0], [70.0, 30.0]]],
    }
    preprocessor = Sentinel1Preprocessor(corridor_geometry=corridor, working_crs="EPSG:3857", resolution_meters=500)

    scenes = []
    for idx, day in enumerate([1, 5, 9], start=1):
        vv = tmp_path / f"vv_{idx}.tif"
        vh = tmp_path / f"vh_{idx}.tif"
        _write_raster(vv, np.ones((32, 32), dtype=np.float32) * (-14 + idx))
        _write_raster(vh, np.ones((32, 32), dtype=np.float32) * (-18 + idx))
        scenes.append(
            preprocessor.preprocess_scene(
                scene_id=f"S1A_{idx}",
                corridor_id="indus-1",
                acquisition_time=datetime(2024, 7, day),
                asset_paths={"vv": vv, "vh": vh},
                output_dir=tmp_path / "prepared",
                orbit_pass="ASCENDING",
            )
        )

    # Flag one scene as bad so exclusion logic is exercised.
    scenes[-1].processing_metadata["quality_note"] = "acquisition_artifact"

    service = RollingSarBaselineService(max_nodata_fraction=0.8, min_valid_coverage=0.1)
    grouped = service.group_baseline_scenes(scenes, temporal_mode="month", include_orbit=True)
    outputs = service.build_baseline_rasters(grouped, output_dir=tmp_path / "baseline", baseline_version="v1")

    assert outputs
    vv_result = [o for o in outputs if o.polarization == "vv"][0]
    assert vv_result.baseline_version == "v1"
    assert "S1A_3" in vv_result.excluded_scene_ids
    assert vv_result.output_rasters["median"].exists()



def test_optical_preprocessing_masks_clouds_and_produces_indices(tmp_path: Path) -> None:
    corridor = {
        "type": "Polygon",
        "coordinates": [[[70.0, 30.0], [70.0, 30.2], [70.2, 30.2], [70.2, 30.0], [70.0, 30.0]]],
    }
    preprocessor = OpticalPreprocessor(corridor_geometry=corridor, working_crs="EPSG:3857", resolution_meters=500)

    green = tmp_path / "green.tif"
    nir = tmp_path / "nir.tif"
    swir1 = tmp_path / "swir1.tif"
    swir2 = tmp_path / "swir2.tif"

    base = np.ones((32, 32), dtype=np.float32) * 0.2
    _write_raster(green, base)
    _write_raster(nir, base * 0.5)
    _write_raster(swir1, base * 0.3)
    _write_raster(swir2, base * 0.25)

    prepared = preprocessor.preprocess_scene(
        scene_id="S2_001",
        corridor_id="indus-1",
        acquisition_time=datetime(2024, 7, 1),
        sensor="sentinel-2",
        asset_paths={"green": green, "nir": nir, "swir1": swir1, "swir2": swir2},
        output_dir=tmp_path / "prepared_optical",
    )

    assert prepared.index_paths["ndwi"].exists()
    assert prepared.index_paths["mndwi"].exists()
    assert prepared.index_paths["awei"].exists()
    assert prepared.optical_water_confidence_path.exists()
    assert 0.0 <= prepared.stats["valid_fraction"] <= 1.0


def test_optical_asset_plan_is_corridor_aware() -> None:
    corridor = {
        "type": "Polygon",
        "coordinates": [[[70.0, 30.0], [70.0, 30.5], [70.5, 30.5], [70.5, 30.0], [70.0, 30.0]]],
    }
    preprocessor = OpticalPreprocessor(corridor_geometry=corridor, working_crs="EPSG:3857", resolution_meters=250)

    plans = preprocessor.build_asset_retrieval_plan(
        [
            OpticalSceneCandidate(
                scene_id="optical-ok",
                corridor_id="c1",
                geometry=corridor,
                assets={"green": "x", "nir": "x", "swir1": "x", "swir2": "x"},
                sensor="sentinel-2",
                cloud_cover=15,
            ),
            OpticalSceneCandidate(
                scene_id="optical-cloudy",
                corridor_id="c1",
                geometry=corridor,
                assets={"green": "x", "nir": "x", "swir1": "x", "swir2": "x"},
                sensor="sentinel-2",
                cloud_cover=99,
            ),
        ],
        max_cloud_cover=80,
    )

    assert plans[0].accepted is True
    assert plans[1].accepted is False
    assert plans[1].reason == "cloud_cover_above_threshold"
