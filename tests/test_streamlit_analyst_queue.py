from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from pakistan_flood_monitor.api import main
from pakistan_flood_monitor.config import AppMode

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "streamlit_app.py"
PAGE = next((ROOT / "pages").glob("2_*")).relative_to(ROOT)
TEST_TOKEN = "fixture-analyst-role"


@pytest.fixture
def backend(monkeypatch):
    import backend_service

    monkeypatch.setattr(backend_service, "API_BASE_URL", "http://api.test")
    monkeypatch.setattr(backend_service, "_APP_MODE", "operational")
    monkeypatch.setattr(backend_service, "DATA_DIR", ROOT / "data")
    return backend_service


def _page():
    return AppTest.from_file(HOME).switch_page(str(PAGE)).run()


def _authenticate(page):
    return page.text_input(key="review_queue_token").input(TEST_TOKEN).run()


def test_live_view_uses_supplied_token_and_canonical_api(backend, monkeypatch):
    monkeypatch.setenv("FLOOD_MONITOR_ANALYST_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("FLOOD_MONITOR_ADMIN_TOKEN", "fixture-admin-not-for-dashboard")
    monkeypatch.setattr(main.settings, "app_mode", AppMode.DEMO)
    monkeypatch.setattr(main, "event_store", {
        "canonical-draft": {
            "event_id": "canonical-draft", "status": "draft", "aoi": "Indus-Lower",
            "machine_confidence": 84.5, "notes": "private fixture details",
            "timestamps": {"detected_at": "2026-03-01T12:00:00Z"},
        },
    })
    calls = []

    def forbid_local(*args, **kwargs):
        pytest.fail("API-connected analyst page read a local record")

    def local_request(url, *, headers, params, timeout):
        calls.append((url, headers, params))
        assert url == "http://api.test/internal/review-queue"
        with TestClient(main.app) as client:
            return client.get("/internal/review-queue", headers=headers, params=params)

    monkeypatch.setattr(backend.DataService, "_load", forbid_local)
    monkeypatch.setattr(httpx, "get", local_request)
    page = _page()
    assert not page.exception
    assert not calls
    assert not page.dataframe
    credential = page.text_input(key="review_queue_token").proto
    assert credential.type == credential.PASSWORD

    page = _authenticate(page)
    assert not page.exception
    assert not page.error
    assert len(calls) == 1
    assert calls[0][1] == {"Authorization": f"Bearer {TEST_TOKEN}"}
    assert any("SIMULATED / DEMO DATA" in item.value for item in page.warning)
    rows = page.dataframe[0].value
    assert rows["Event"].tolist() == ["canonical-draft"]
    assert rows["Model confidence (%)"].tolist() == [84.5]
    assert rows["Status"].tolist() == ["draft"]
    assert "private fixture details" not in rows.to_string()
    assert not page.checkbox
    assert all("Publish" not in button.label for button in page.button)

    page.selectbox(key="api_review_status").select("approved").run()
    assert "No candidates match" in page.info[0].value


@pytest.mark.parametrize("status,detail", [
    (401, "rejected"), (403, "rejected"), (429, "rate limited"), (503, "unavailable"),
    (200, "invalid response"),
])
def test_api_failure_never_loads_local_queue_or_audit(backend, monkeypatch, status, detail):
    def no_local(*args, **kwargs):
        pytest.fail("API queue failure read local fixtures")

    monkeypatch.setattr(backend.DataService, "_load", no_local)
    monkeypatch.setattr(httpx, "get", lambda *a, **kw: httpx.Response(status, json={"raw": "private error"}))
    page = _authenticate(_page())
    assert not page.exception
    assert detail in page.error[0].value
    assert "private error" not in page.error[0].value
    assert not page.dataframe
    assert not page.warning


def test_api_queue_pagination_and_token_reset(backend, monkeypatch):
    calls = []

    def fetch(url, *, headers, params, timeout):
        calls.append(params["offset"])
        return httpx.Response(200, json={
            "app_mode": "operational",
            "items": [{"event_id": str(params["offset"]), "status": "draft"}],
            "next_offset": 25 if params["offset"] == 0 else None,
        })

    monkeypatch.setattr(httpx, "get", fetch)
    page = _authenticate(_page())
    next_button = next(button for button in page.button if button.label == "Next page")
    next_button.click().run()
    assert not page.exception
    assert calls == [0, 25]
    assert page.dataframe[0].value["Event"].tolist() == ["25"]
    page.text_input(key="review_queue_token").input("fixture-different-role").run()
    assert calls == [0, 25, 0]


@pytest.mark.parametrize("mode", ["demo", "operational"])
def test_local_review_only_renders_in_demo_and_never_prechecks(backend, monkeypatch, mode):
    monkeypatch.setattr(backend, "API_BASE_URL", None)
    monkeypatch.setattr(backend, "_APP_MODE", mode)
    page = _page()
    assert not page.exception
    if mode == "operational":
        assert "No API endpoint is configured" in page.error[0].value
        assert not page.dataframe
        assert not page.checkbox
    else:
        assert any("SIMULATED / DEMO DATA" in item.value for item in page.warning)
        assert page.checkbox
        assert not any(box.value for box in page.checkbox)


def test_invalid_credential_is_not_sent_or_logged(backend, monkeypatch):
    def no_request(*args, **kwargs):
        pytest.fail("Invalid review credential was sent")

    monkeypatch.setattr(httpx, "get", no_request)
    page = _page()
    page.text_input(key="review_queue_token").input("غلط ٹوکن").run()
    assert not page.exception
    assert page.error[0].value == "Enter a valid bearer credential without spaces."
    assert not page.dataframe


def test_disconnected_api_never_reuses_local_records(backend, monkeypatch):
    def offline(*args, **kwargs):
        raise httpx.ConnectError("offline fixture")

    def no_local(*args, **kwargs):
        pytest.fail("Offline queue read a local record")

    monkeypatch.setattr(httpx, "get", offline)
    monkeypatch.setattr(backend.DataService, "_load", no_local)
    page = _authenticate(_page())
    assert not page.exception
    assert "unavailable" in page.error[0].value
    assert not page.dataframe
