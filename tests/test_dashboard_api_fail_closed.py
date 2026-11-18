import httpx
import pandas as pd
import pytest

import backend_service


@pytest.fixture
def configured(monkeypatch, tmp_path):
    monkeypatch.setattr(backend_service, "API_BASE_URL", "http://api.test")
    monkeypatch.setattr(backend_service, "DATA_DIR", tmp_path)
    pd.DataFrame([{"event_id": "csv-event", "status": "published"}]).to_csv(tmp_path / "flood_events.csv", index=False)
    return backend_service.DataService(), tmp_path


def test_empty_api_response_does_not_fall_back_to_csv(configured, monkeypatch):
    service, _ = configured
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(200, json={"events": []}))
    assert service.get_events().empty


def test_api_outage_does_not_fall_back_to_csv(configured, monkeypatch):
    service, _ = configured
    def fail(*args, **kwargs):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr(httpx, "get", fail)
    assert service.get_events().empty


def test_rejected_review_never_writes_local_files(configured, monkeypatch):
    service, path = configured
    original = (path / "flood_events.csv").read_bytes()
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(403))
    assert service.update_event_status("csv-event", "published", "analyst") is False
    assert (path / "flood_events.csv").read_bytes() == original
    assert not (path / "audit_log.csv").exists()


def test_valid_empty_is_distinct_from_failure(configured, monkeypatch):
    service, _ = configured
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(200, json={"events": []}))
    assert service.get_events().empty
    assert service.event_api_error is None
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(503))
    assert service.get_events().empty
    assert service.event_api_error is not None


def test_review_success_is_forwarded(configured, monkeypatch):
    service, _ = configured
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(200, json={"status": "review_updated"}))
    assert service.update_event_status("event", "review", "analyst") is True


def test_malformed_response_is_unavailable(configured, monkeypatch):
    service, _ = configured
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(200, json={"events": "invalid"}))
    assert service.get_events().empty
    assert service.event_api_error is not None


def test_valid_events_are_read_from_api(configured, monkeypatch):
    service, _ = configured
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(200, json={"events": [{"event_id": "api-event", "status": "published"}]}))
    assert service.get_events()["event_id"].tolist() == ["api-event"]
    assert service.event_api_error is None


def test_review_connection_error_does_not_write(configured, monkeypatch):
    service, path = configured
    original = (path / "flood_events.csv").read_bytes()
    def fail(*args, **kwargs):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr(httpx, "post", fail)
    assert service.update_event_status("csv-event", "published", "analyst") is False
    assert (path / "flood_events.csv").read_bytes() == original
    assert not (path / "audit_log.csv").exists()
