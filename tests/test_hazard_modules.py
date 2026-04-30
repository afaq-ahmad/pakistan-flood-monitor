import os
from fastapi.testclient import TestClient

from pakistan_flood_monitor.api.main import app
from pakistan_flood_monitor.pipeline.runner import FloodMonitoringPipeline
from pakistan_flood_monitor.hazards.base import HazardModule


class DemoHazard(HazardModule):
    @property
    def hazard_type(self) -> str:
        return "demo"

    def run_daily(self, aoi_name: str):
        return {"hazard": self.hazard_type, "aoi": aoi_name}


def test_registry_includes_flood_and_future_hooks() -> None:
    pipeline = FloodMonitoringPipeline()
    hazards = pipeline.registered_hazards()
    assert "flood" in hazards
    assert "landslide" in hazards
    assert "heat" in hazards


def test_registering_stub_hazard_module() -> None:
    pipeline = FloodMonitoringPipeline()
    pipeline.register_module(DemoHazard())
    result = pipeline.run_hazard_daily("demo", "Indus-Lower")
    assert result == {"hazard": "demo", "aoi": "Indus-Lower"}


def test_flood_api_routes_remain_compatible() -> None:
    os.environ["FLOOD_MONITOR_ADMIN_TOKEN"] = "test-admin-token"
    client = TestClient(app)
    run_response = client.get("/internal/run/Indus-Lower", headers={"Authorization": "Bearer test-admin-token"})
    assert run_response.status_code == 200
    payload = run_response.json()
    assert payload["published_outputs"]["alert_feed_item"]["summary"].endswith("flood signal for Indus-Lower")
