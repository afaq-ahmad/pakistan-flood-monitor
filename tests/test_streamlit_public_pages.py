from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "streamlit_app.py"
PUBLIC = next((ROOT / "pages").glob("1_*")).relative_to(ROOT)


@pytest.fixture
def dashboard(monkeypatch):
    # Other backend tests reload this module to exercise environment configuration.
    import backend_service

    monkeypatch.setattr(backend_service, "API_BASE_URL", None)
    monkeypatch.setattr(backend_service, "_APP_MODE", "demo")
    return backend_service


def test_demo_home_shows_only_published_fixtures(dashboard):
    page = AppTest.from_file(HOME).run()

    assert not page.exception
    assert any(dashboard.DEMO_WATERMARK.removeprefix("⚠️ ") in warning.value for warning in page.warning)
    assert page.metric[0].value == str(len(dashboard.DataService().get_public_events()))


def test_demo_public_page_filters_cards_map_and_exposure(dashboard, monkeypatch):
    rendered_maps = []
    monkeypatch.setattr("streamlit_folium.st_folium", lambda map_, **kwargs: rendered_maps.append(map_.get_root().render()))
    page = AppTest.from_file(HOME).switch_page(str(PUBLIC)).run()

    assert not page.exception
    assert any(dashboard.DEMO_WATERMARK.removeprefix("⚠️ ") in warning.value for warning in page.warning)
    assert "evt-indus-001" in rendered_maps[-1]
    assert "evt-chenab-001" not in rendered_maps[-1]
    assert all("evt-chenab-001" not in card.label for card in page.expander)
    assert "evt-chenab-001" not in page.dataframe[0].value["event_id"].tolist()

    page.selectbox[0].select("Dadu").run()
    assert not page.exception
    assert page.metric[0].value == "1"
    assert set(page.dataframe[0].value["event_id"]) == {"evt-indus-001"}


@pytest.mark.parametrize("path", [None, PUBLIC], ids=["home", "public"])
def test_operational_without_api_shows_no_fixture_events(dashboard, monkeypatch, path):
    monkeypatch.setattr(dashboard, "_APP_MODE", "operational")
    app = AppTest.from_file(HOME)
    if path:
        app.switch_page(str(path))
    page = app.run()

    assert not page.exception
    assert not page.metric
    assert not page.warning
    assert "No event API is configured" in page.error[0].value
    assert dashboard.DataService().get_event("evt-indus-001") is None
    assert dashboard.DataService().update_event_status("evt-indus-001", "draft", "tester") is False


@pytest.mark.parametrize("response_status", [200, 503])
def test_public_page_distinguishes_empty_api_from_outage(dashboard, monkeypatch, response_status):
    monkeypatch.setattr(dashboard, "API_BASE_URL", "http://api.test")
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        return httpx.Response(response_status, json={"events": []})

    monkeypatch.setattr(httpx, "get", get)
    page = AppTest.from_file(HOME).switch_page(str(PUBLIC)).run()

    assert not page.exception
    assert calls == ["http://api.test/public/events"]
    assert bool(page.error) == (response_status == 503)
    assert any("No published events" in info.value for info in page.info) == (response_status == 200)
    assert not page.success
    assert not page.metric


def test_public_api_snapshot_skips_unknown_location(dashboard, monkeypatch):
    monkeypatch.setattr(dashboard, "API_BASE_URL", "http://api.test")
    calls = []
    rendered_maps = []

    def get(url, **kwargs):
        calls.append(url)
        return httpx.Response(200, json={"events": [
            {"event_id": "with-location", "status": "published",
             "geometry": {"type": "Point", "coordinates": [67, 27]}},
            {"event_id": "missing-location", "status": "published", "geometry": None},
            {"event_id": "unreviewed", "status": "draft"},
        ]})

    monkeypatch.setattr(httpx, "get", get)
    monkeypatch.setattr("streamlit_folium.st_folium", lambda map_, **kwargs: rendered_maps.append(map_.get_root().render()))
    page = AppTest.from_file(HOME).switch_page(str(PUBLIC)).run()

    assert not page.exception
    assert calls == ["http://api.test/public/events"]
    assert page.metric[0].value == "2"
    assert "with-location" in rendered_maps[0]
    assert "missing-location" not in rendered_maps[0]
    assert any("missing-location" in card.label for card in page.expander)
    assert "unreviewed" not in rendered_maps[0]
    assert not page.dataframe
