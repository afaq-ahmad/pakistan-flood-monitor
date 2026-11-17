from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from pakistan_flood_monitor.api import main
from pakistan_flood_monitor.config import AppMode


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main.settings, "app_mode", AppMode.OPERATIONAL)
    monkeypatch.setattr(main, "publication_gate", lambda event, app_mode: SimpleNamespace(passed=event.get("valid", False)))
    monkeypatch.setattr(main, "event_store", {
        "draft": {"event_id": "draft", "status": "draft", "valid": True, "timestamps": {"detected_at": "2026-01-01"}},
        "bad": {"event_id": "bad", "status": "published", "valid": False, "timestamps": {"detected_at": "2026-01-02"}},
        "good": {"event_id": "good", "status": "published", "valid": True, "timestamps": {"detected_at": "2026-01-03"}},
    })
    monkeypatch.setattr(main, "run_history", {"Indus-Lower": [{"run_id": "raw-secret", "detections": [{"alert_level": "critical", "review_status": "analyst_validated"}]}]})
    main.rate_limiter.reset()
    return TestClient(main.app)


def test_public_collection_only_contains_valid_published_events(client):
    response = client.get("/public/events")
    assert response.status_code == 200
    assert [e["event_id"] for e in response.json()["events"]] == ["good"]


@pytest.mark.parametrize("path", ["/public/publish/Indus-Lower", "/public/advisories/Indus-Lower/mobile", "/public/corridors/Indus-Lower/status"])
def test_raw_latest_run_is_not_public(client, path):
    assert client.get(path).status_code == 503


def test_public_corridor_listing_does_not_leak_raw_alert(client):
    response = client.get("/public/corridors")
    assert response.status_code == 200
    assert "raw-secret" not in response.text
    assert "critical" not in response.text


def test_public_alert_does_not_accept_internal_variant(client):
    assert client.get("/public/alerts/latest?variant=official_internal").status_code == 422


def test_public_collection_excludes_internal_event_fields(client):
    main.event_store["good"]["approval_trace"] = [{"private": "sensitive"}]
    assert "approval_trace" not in client.get("/public/events").json()["events"][0]


def test_nonpublic_historical_record_is_not_exposed(client, monkeypatch):
    monkeypatch.setattr(main, "historical_event_library", {"draft": {"event_id": "draft"}})
    assert client.get("/public/historical-events").json() == []
    assert client.get("/public/historical-events/draft").status_code == 404


def test_nonpublic_published_event_fails_detail_check(client):
    assert client.get("/public/events/bad").status_code == 404
    assert client.get("/public/events/draft").status_code == 404
