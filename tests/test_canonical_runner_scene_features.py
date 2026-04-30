from datetime import date

from pakistan_flood_monitor.data.sources import SceneMetadata
from pakistan_flood_monitor.pipeline.runner import FloodMonitoringPipeline


class StubCatalog:
    def fetch_scenes(self, sensor: str, aoi_name: str, start: date, end: date):
        return [SceneMetadata(sensor=sensor, scene_id="SCENE-REAL-001", acquisition_date=start, assets=None)]

    def fetch_supporting_layers(self, aoi_name: str):
        return {"imerg": "imerg://real", "glofas": "glofas://real", "dem": "d", "water_history": "w"}


def test_runner_uses_scene_derived_features_not_fixed_literals(tmp_path) -> None:
    pipeline = FloodMonitoringPipeline()
    pipeline.catalog = StubCatalog()
    pipeline.feature_extractor = pipeline.feature_extractor.__class__(snapshot_root=tmp_path / "snaps")

    report = pipeline.run_daily("Indus-Lower")
    indicators = report.detections[0].indicators

    assert indicators["sar_drop_db"] != 3.0
    assert indicators["ndwi"] != 0.31
    assert indicators["rainfall_mm_72h"] != 120
