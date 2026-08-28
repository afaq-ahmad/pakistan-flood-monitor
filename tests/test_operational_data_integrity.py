from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from pakistan_flood_monitor.api import main as api_main
from pakistan_flood_monitor.config import AppMode
from pakistan_flood_monitor.data.sources import DataCatalog, SceneMetadata
from pakistan_flood_monitor.models.observations import (
    ObservationStatus,
    OperationalDataIntegrityError,
    ScientificObservation,
    SourceAvailabilityStatus,
)
from pakistan_flood_monitor.pipeline.feature_generation import SceneFeatureExtractor
from pakistan_flood_monitor.services.gis_qa import publication_gate


def _scene() -> SceneMetadata:
    return SceneMetadata(
        sensor="sentinel-1",
        scene_id="S1-NO-ASSETS",
        acquisition_date=date(2026, 8, 28),
        assets={},
    )


def _extract(extractor: SceneFeatureExtractor):
    return extractor.extract(
        run_id="run-integrity",
        aoi_name="Indus-Lower",
        scenes=[_scene()],
        support_layers={"imerg": "https://example.test/imerg", "glofas": "https://example.test/glofas"},
        processing_version="test-v1",
        threshold_version="threshold-v1",
        thresholds={"sar_drop_db": 2.5},
    )


def _publishable_event(lineage: dict) -> dict:
    return {
        "event_class": "flood",
        "source_scenes": ["S1-NO-ASSETS"],
        "notes": "analyst reviewed",
        "timestamps": {"detected_at": "2026-08-28T00:00:00+00:00"},
        "district_overlays": ["Dadu"],
        "geometry": {
            "type": "Polygon",
            "crs": "EPSG:4326",
            "coordinates": [[[67.0, 24.0], [67.1, 24.0], [67.1, 24.1], [67.0, 24.0]]],
        },
        "label_metadata": {
            "label_type": "flood_extent",
            "label_tier": "tier_1",
            "analyst": "analyst-1",
            "date": "2026-08-28T00:00:00+00:00",
            "notes": "reviewed",
            "uncertainty": 0.2,
        },
        "mapping_rules": {
            "river_inclusion_exclusion": "exclude permanent water",
            "cloud_limitation_notes": "SAR observation",
            "disconnected_pool_handling": "retain above threshold",
            "certainty_class": "experimental",
        },
        "lineage": lineage,
    }


def test_operational_mode_reports_unavailable_instead_of_fabricating_values(tmp_path) -> None:
    extractor = SceneFeatureExtractor(snapshot_root=tmp_path, app_mode=AppMode.OPERATIONAL)

    with pytest.raises(OperationalDataIntegrityError) as raised:
        _extract(extractor)

    payload = raised.value.as_dict()
    rainfall = payload["observations"]["rainfall_mm_72h"]
    assert rainfall["status"] == ObservationStatus.UNAVAILABLE.value
    assert rainfall["availability"] == SourceAvailabilityStatus.UNAVAILABLE.value
    assert rainfall["value"] is None
    assert all(item["status"] != ObservationStatus.SIMULATED.value for item in payload["observations"].values())


def test_demo_mode_watermarks_every_synthetic_feature(tmp_path) -> None:
    bundle = _extract(SceneFeatureExtractor(snapshot_root=tmp_path, app_mode=AppMode.DEMO))

    assert bundle.integrity.product_label is ObservationStatus.SIMULATED
    assert bundle.integrity.data_availability is SourceAvailabilityStatus.DEGRADED
    assert bundle.integrity.contains_synthetic is True
    assert bundle.integrity.watermark == "SIMULATED / DEMO DATA — NOT FOR OPERATIONAL DECISIONS"
    assert bundle.observations["rainfall_mm_72h"].synthetic is True


def test_operational_catalog_never_returns_stub_scenes(monkeypatch) -> None:
    catalog = DataCatalog(app_mode=AppMode.OPERATIONAL)
    monkeypatch.setattr(catalog, "_get_client", lambda: None)

    with pytest.raises(OperationalDataIntegrityError) as raised:
        catalog.fetch_scenes("sentinel-1", "Indus-Lower", date(2026, 8, 27), date(2026, 8, 28))

    assert raised.value.as_dict()["observations"]["sentinel-1_scene"]["status"] == "UNAVAILABLE"


def test_canonical_api_returns_structured_unavailable_response(monkeypatch) -> None:
    rainfall = ScientificObservation(
        name="rainfall_mm_72h",
        value=None,
        units="mm",
        status=ObservationStatus.UNAVAILABLE,
        availability=SourceAvailabilityStatus.UNAVAILABLE,
        source_uri="https://example.test/imerg",
        processing_version="test-v1",
        quality_status="source_unavailable",
    )

    class FailingPipeline:
        def run_daily(self, _aoi_name: str):
            raise OperationalDataIntegrityError("IMERG is unavailable", observations={rainfall.name: rainfall})

    monkeypatch.setenv("FLOOD_MONITOR_ADMIN_TOKEN", "integrity-test-token")
    monkeypatch.setattr(api_main, "pipeline", FailingPipeline())
    api_main.rate_limiter.reset()

    response = TestClient(api_main.app).get(
        "/internal/run/Indus-Lower",
        headers={"Authorization": "Bearer integrity-test-token"},
    )

    assert response.status_code == 503
    assert response.json()["observations"]["rainfall_mm_72h"]["status"] == "UNAVAILABLE"
    assert response.json()["observations"]["rainfall_mm_72h"]["value"] is None


def test_publication_gate_rejects_synthetic_lineage_outside_tests() -> None:
    event = _publishable_event(
        {
            "contains_synthetic": True,
            "observations": {
                "rainfall_mm_72h": {
                    "status": "SIMULATED",
                    "availability": "DEGRADED",
                    "synthetic": True,
                }
            },
        }
    )

    result = publication_gate(event, app_mode=AppMode.DEMO)

    assert result.passed is False
    assert "Synthetic lineage cannot be published" in " ".join(result.errors)


def test_publication_gate_requires_observation_provenance_in_operational_mode() -> None:
    result = publication_gate(
        _publishable_event({"contains_synthetic": False, "observations": {}}),
        app_mode=AppMode.OPERATIONAL,
    )

    assert result.passed is False
    assert "per-observation provenance" in " ".join(result.errors)
