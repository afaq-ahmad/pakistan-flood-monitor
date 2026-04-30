from __future__ import annotations

import json
from datetime import date

import numpy as np
import rasterio
from rasterio.transform import from_origin

from pakistan_flood_monitor.data.sources import SceneMetadata
from pakistan_flood_monitor.pipeline.feature_generation import SceneFeatureExtractor


def _write_raster(path, value: float) -> None:
    arr = np.full((4, 4), value, dtype=np.float32)
    with rasterio.open(path, "w", driver="GTiff", height=4, width=4, count=1, dtype="float32", crs="EPSG:4326", transform=from_origin(70, 30, 0.01, 0.01)) as dst:
        dst.write(arr, 1)


def test_scene_feature_extractor_persists_deterministic_snapshot(tmp_path) -> None:
    vv1 = tmp_path / "scene1_vv.tif"
    vv2 = tmp_path / "scene2_vv.tif"
    _write_raster(vv1, -16.0)
    _write_raster(vv2, -12.0)
    scenes = [
        SceneMetadata(sensor="sentinel-1", scene_id="S1A_001", acquisition_date=date(2026, 1, 1), assets={"vv": str(vv1)}),
        SceneMetadata(sensor="sentinel-1", scene_id="S1A_002", acquisition_date=date(2026, 1, 2), assets={"vv": str(vv2)}),
    ]
    extractor = SceneFeatureExtractor(snapshot_root=tmp_path / "snapshots")

    first = extractor.extract(run_id="run-1", aoi_name="Indus-Lower", scenes=scenes, support_layers={"imerg": "imerg://x", "glofas": "glofas://x"}, processing_version="sar-v1", threshold_version="thr-v1", thresholds={"sar_drop_db": 2.5, "ndwi": 0.2})

    assert first.features.sar_drop_db == 4.0
    payload = json.loads(first.snapshot_path.read_text())
    assert payload["processing_version"] == "sar-v1"
    assert payload["thresholds"]["sar_drop_db"] == 2.5


def test_scene_feature_extractor_is_replay_deterministic(tmp_path) -> None:
    scenes = [SceneMetadata(sensor="sentinel-1", scene_id="S1X", acquisition_date=date(2026, 1, 1), assets=None)]
    extractor = SceneFeatureExtractor(snapshot_root=tmp_path / "snapshots")
    a = extractor.extract(run_id="run-a", aoi_name="Chenab-Middle", scenes=scenes, support_layers={"imerg": "imerg://x", "glofas": "glofas://x"}, processing_version="sar-v1", threshold_version="thr-v1", thresholds={"sar_drop_db": 2.5, "ndwi": 0.2})
    b = extractor.extract(run_id="run-b", aoi_name="Chenab-Middle", scenes=scenes, support_layers={"imerg": "imerg://x", "glofas": "glofas://x"}, processing_version="sar-v1", threshold_version="thr-v1", thresholds={"sar_drop_db": 2.5, "ndwi": 0.2})
    assert a.features == b.features
