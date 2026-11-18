import pytest
from fastapi.testclient import TestClient

from pakistan_flood_monitor.config import AppMode, settings


@pytest.mark.parametrize("mode", [AppMode.DEMO, AppMode.TEST])
def test_standalone_dashboard_labels_its_fixtures(monkeypatch, mode):
    import dashboard_app

    monkeypatch.setattr(settings, "app_mode", mode)
    with TestClient(dashboard_app.app) as client:
        page = client.get("/")
        feed = client.get("/api/events")

    assert page.status_code == 200
    assert "SIMULATED / DEMO DATA — NOT FOR OPERATIONAL DECISIONS" in page.text
    assert "System Active" not in page.text
    assert feed.status_code == 200
    assert feed.json()["product_label"] == "SIMULATED"
    assert "SIMULATED / DEMO DATA" in feed.json()["demo_watermark"]
    assert feed.json()["data"]


def test_standalone_dashboard_cannot_serve_fixture_events_in_operational_mode(monkeypatch):
    import dashboard_app

    monkeypatch.setattr(settings, "app_mode", AppMode.OPERATIONAL)
    with TestClient(dashboard_app.app) as client:
        for path in ("/", "/api/events"):
            response = client.get(path)
            assert response.status_code == 503
            assert "data" not in response.json()
