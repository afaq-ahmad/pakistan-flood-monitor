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
    assert report.product_label == "SIMULATED"
    assert report.contains_synthetic is True
    assert report.watermark == "SIMULATED / DEMO DATA — NOT FOR OPERATIONAL DECISIONS"


def test_runner_emits_run_and_event_lineage(tmp_path) -> None:
    pipeline = FloodMonitoringPipeline()
    pipeline.catalog = StubCatalog()
    pipeline.feature_extractor = pipeline.feature_extractor.__class__(snapshot_root=tmp_path / "snaps")

    report = pipeline.run_daily("Indus-Lower")
    assert report.run_lineage.source_scene_ids == ["SCENE-REAL-001"]
    assert report.run_lineage.processing_version == "sar-preprocess-v1"
    assert report.published_outputs.review_queue_event.lineage is not None
    assert report.published_outputs.review_queue_event.lineage.model["model_id"] == "rules-v1"
    assert report.published_outputs.review_queue_event.lineage.contains_synthetic is True
    assert report.run_lineage.observations["rainfall_mm_72h"].status == "SIMULATED"
