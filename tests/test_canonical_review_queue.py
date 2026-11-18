import pytest
from fastapi.testclient import TestClient

from pakistan_flood_monitor.api import main
from pakistan_flood_monitor.config import AppMode
from pakistan_flood_monitor.models.review_queue import SIMULATION_WATERMARK


def _candidate(event_id, status, detected_at=None, **fields):
    return {
        "event_id": event_id,
        "status": status,
        "timestamps": {"detected_at": detected_at} if detected_at else {},
        **fields,
    }


@pytest.fixture
def client(monkeypatch):
    for role in ("admin", "analyst", "reviewer", "service"):
        monkeypatch.setenv(f"FLOOD_MONITOR_{role.upper()}_TOKEN", f"fixture-{role}")
    monkeypatch.setattr(main.settings, "app_mode", AppMode.OPERATIONAL)
    monkeypatch.setattr(main, "event_store", {
        "draft-old": _candidate("draft-old", "draft", "2026-01-01T10:00:00Z"),
        "approved": _candidate("approved", "approved", "2026-01-01T14:00:00+04:00"),
        "draft-new": _candidate(
            "draft-new", "draft", "2026-01-02T15:00:00Z", aoi="Indus-Lower",
            event_class="flood", machine_confidence=82.5, app_mode="demo",
            notes="private fixture note", geometry={"type": "Polygon"},
            linked_field_reports=[{"notes": "private fixture field report"}],
        ),
        "review": _candidate("review", "review"),
        "public": _candidate("public", "published", "2026-01-03T13:00:00Z"),
        "retracted": _candidate("retracted", "retracted"),
    })
    return TestClient(main.app)


def _bearer(role):
    return {"Authorization": f"Bearer fixture-{role}"}


@pytest.mark.parametrize("role,expected", [
    (None, 401), ("invalid", 401), ("service", 403),
    ("admin", 200), ("analyst", 200), ("reviewer", 200),
])
def test_review_queue_roles(client, role, expected):
    response = client.get("/internal/review-queue", headers=_bearer(role) if role else {})
    assert response.status_code == expected
    if expected == 200:
        assert response.headers["Cache-Control"] == "no-store"


def test_review_queue_pages_are_ordered_filtered_and_minimized(client):
    first = client.get("/internal/review-queue", params={"limit": 2}, headers=_bearer("analyst"))
    payload = first.json()
    assert [row["event_id"] for row in payload["items"]] == ["draft-new", "approved"]
    assert payload["next_offset"] == 2
    row = payload["items"][0]
    assert row["corridor_id"] == "Indus-Lower"
    assert row["machine_confidence_pct"] == 82.5
    assert row["product_label"] == "SIMULATED"
    assert row["watermark"] == SIMULATION_WATERMARK
    assert {"notes", "geometry", "linked_field_reports"}.isdisjoint(row)
    assert "private fixture" not in first.text

    second = client.get("/internal/review-queue", params={"limit": 2, "offset": 2}, headers=_bearer("analyst"))
    payload = second.json()
    assert [row["event_id"] for row in payload["items"]] == ["draft-old", "review"]
    assert payload["items"][1]["detected_at"] is None
    assert payload["items"][1]["machine_confidence_pct"] is None
    assert payload["next_offset"] is None

    drafts = client.get("/internal/review-queue", params={"status": "draft"}, headers=_bearer("analyst"))
    assert [row["event_id"] for row in drafts.json()["items"]] == ["draft-new", "draft-old"]
    assert "draft-new" not in client.get("/public/events").text


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"status": "published"}])
def test_review_queue_rejects_invalid_filters(client, params):
    assert client.get("/internal/review-queue", params=params, headers=_bearer("analyst")).status_code == 422


def test_empty_review_queue_uses_process_state_without_hydrating_db(client, monkeypatch):
    monkeypatch.setattr(main, "event_store", {})

    def unexpected_read():
        pytest.fail("Review queue attempted a database read")

    monkeypatch.setattr(main, "SessionLocal", unexpected_read)
    response = client.get("/internal/review-queue", headers=_bearer("reviewer"))
    assert response.json() == {"app_mode": "operational", "items": [], "next_offset": None}


def test_review_queue_from_actual_pipeline_run(client, monkeypatch):
    monkeypatch.setattr(main.settings, "app_mode", AppMode.TEST)
    monkeypatch.setattr(main.pipeline, "app_mode", AppMode.TEST)
    monkeypatch.setattr(main, "event_store", {})
    monkeypatch.setattr(main, "run_history", {})
    monkeypatch.setattr(main, "historical_event_library", {})
    result = client.post("/internal/run/Indus-Lower", headers=_bearer("admin"))
    assert result.status_code == 200
    event_id = result.json()["published_outputs"]["review_queue_event"]["event_id"]

    queued = client.get("/internal/review-queue", headers=_bearer("reviewer")).json()["items"]
    assert [row["event_id"] for row in queued] == [event_id]
    assert queued[0]["status"] == "draft"
    assert queued[0]["detected_at"].endswith("Z")
    assert queued[0]["watermark"] == SIMULATION_WATERMARK
    assert client.get("/public/events").json()["events"] == []
