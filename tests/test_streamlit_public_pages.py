from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import streamlit as st
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "streamlit_app.py"
PUBLIC = next((ROOT / "pages").glob("1_*")).relative_to(ROOT)
HOME_LINKS = [
    ("My Area", "Public_Dashboard", "Public Flood Dashboard"),
    ("Official Information", "Official_Information", "Official flood information"),
    ("Farmer Safety", "Farmer_Preparedness", "Farmer Preparedness Guide"),
    ("Livestock Safety", "Livestock_Preparedness", "Livestock Preparedness Guide"),
    ("Community Reporting", "Field_Reports", "Field Reports Moderation"),
]


@pytest.fixture
def dashboard(monkeypatch):
    # Other backend tests reload this module to exercise environment configuration.
    import backend_service

    monkeypatch.setattr(backend_service, "API_BASE_URL", None)
    monkeypatch.setattr(backend_service, "_APP_MODE", "demo")
    return backend_service


def assert_public_home_navigation(page):
    assert not page.exception
    links = [item.proto for item in page.get("page_link")]
    assert [(link.label, link.page) for link in links] == [
        (label, route) for label, route, _ in HOME_LINKS
    ]
    assert all(link.page_script_hash and not link.external and not link.disabled for link in links)
    order = [item.type if item.type == "page_link" else getattr(item, "value", None) for item in page.main]
    assert max(i for i, kind in enumerate(order) if kind == "page_link") < order.index("Published events")
    assert not page.button


def test_native_navigation_groups_public_pages_and_keeps_all_existing_urls(dashboard, monkeypatch):
    navigation = st.navigation
    calls = []

    def track_navigation(pages, *, position):
        groups = {
            section: [st.Page(item).url_path if isinstance(item, str) else item.url_path for item in items]
            for section, items in pages.items()
        }
        calls.append((groups, position))
        return navigation(pages, position=position)

    monkeypatch.setattr(st, "navigation", track_navigation)
    page = AppTest.from_file(HOME).run()

    assert not page.exception
    (groups, position), = calls
    assert position == "top"
    assert list(groups) == ["", "Public information", "Research", "Operations"]
    assert groups[""] == [""]
    assert groups["Public information"] == [
        "Public_Dashboard", "Farmer_Preparedness", "Livestock_Preparedness",
        "Official_Information", "Field_Reports",
    ]
    assert "Analyst_Review" in groups["Operations"]
    assert "Satellite_Viewer" in groups["Research"]
    expected_routes = [path.stem.split("_", 2)[2] for path in (ROOT / "pages").glob("*.py")]
    assert sorted(route for group in groups.values() for route in group) == sorted(["", *expected_routes])


def test_home_links_resolve_to_existing_public_pages(dashboard, monkeypatch):
    monkeypatch.setattr(dashboard, "_APP_MODE", "operational")
    page = AppTest.from_file(HOME).run()
    assert_public_home_navigation(page)
    for _, route, title in HOME_LINKS:
        target, = (ROOT / "pages").glob(f"*_{route}.py")
        destination = AppTest.from_file(HOME).switch_page(str(target.relative_to(ROOT))).run()
        assert not destination.exception
        assert any(title in heading.value for heading in destination.title)


def test_demo_home_shows_only_published_fixtures(dashboard):
    page = AppTest.from_file(HOME).run()

    assert_public_home_navigation(page)
    watermark = dashboard.DEMO_WATERMARK.removeprefix("⚠️ ")
    assert any(watermark in warning.value for warning in page.warning)
    expected = f"Events in this feed: {len(dashboard.DataService().get_public_events())}."
    assert any(item.value == expected for item in page.markdown)
    main = list(page.main)
    assert next(i for i, item in enumerate(main) if item.type == "warning") < next(
        i for i, item in enumerate(main) if getattr(item, "value", None) == expected
    )


@pytest.mark.parametrize("result", ["operational-empty", "outage", "timeout", "published"])
def test_home_keeps_public_links_when_event_feed_changes(dashboard, monkeypatch, result):
    monkeypatch.setattr(dashboard, "_APP_MODE", "operational")
    monkeypatch.setattr(dashboard, "API_BASE_URL", "http://api.test")
    calls = []

    def get(url, *, timeout):
        calls.append((url, timeout))
        if result == "timeout":
            raise httpx.ReadTimeout("fixture timeout")
        events = []
        if result == "published":
            events = [
                {"event_id": "private-draft", "status": "draft"},
                {"event_id": "published-fixture", "status": "published"},
            ]
        return httpx.Response(503 if result == "outage" else 200, json={"events": events})

    monkeypatch.setattr(httpx, "get", get)
    page = AppTest.from_file(HOME).run()

    assert_public_home_navigation(page)
    assert calls == [("http://api.test/public/events", 2.0)]
    assert not page.warning
    assert not page.success
    assert not page.metric
    if result in {"outage", "timeout"}:
        assert "Event information is unavailable" in page.error[0].value
    elif result == "operational-empty":
        assert not page.error
        assert any("No published events" in info.value and "unknown" in info.value for info in page.info)
    else:
        assert not page.error
        assert any(text.value == "Events in this feed: 1." for text in page.markdown)


def test_demo_public_page_filters_cards_map_and_exposure(dashboard, monkeypatch):
    rendered_maps = []
    monkeypatch.setattr("streamlit_folium.st_folium", lambda map_, **kwargs: rendered_maps.append(map_.get_root().render()))
    page = AppTest.from_file(HOME).switch_page(str(PUBLIC)).run()
    page.checkbox(key="my_area_map").check().run()

    assert not page.exception
    assert any(dashboard.DEMO_WATERMARK.removeprefix("⚠️ ") in warning.value for warning in page.warning)
    assert "evt-indus-001" in rendered_maps[-1]
    assert "evt-chenab-001" not in rendered_maps[-1]
    assert all("evt-chenab-001" not in card.label for card in page.expander)
    assert "evt-chenab-001" not in page.dataframe[0].value["event_id"].tolist()

    page.selectbox(key="demo_district").select("Dadu").run()
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
    if path is None:
        assert_public_home_navigation(page)
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
    assert not rendered_maps
    page.checkbox(key="my_area_map").check().run()
    assert not page.exception
    assert "with-location" in rendered_maps[0]
    assert "missing-location" not in rendered_maps[0]
    assert any("missing-location" in card.label for card in page.expander)
    assert "unreviewed" not in rendered_maps[0]
    assert not page.dataframe


@pytest.mark.parametrize("feed", ["empty", "error", "timeout", "unconfigured"])
def test_reference_corridors_available_without_published_feed(dashboard, monkeypatch, feed):
    from pakistan_flood_monitor.config import settings

    monkeypatch.setattr(dashboard, "_APP_MODE", "operational")
    monkeypatch.setattr(dashboard, "API_BASE_URL", None if feed == "unconfigured" else "http://api.test")
    requested = []

    def get(url, **kwargs):
        requested.append(url)
        if feed == "timeout":
            raise httpx.ReadTimeout("offline fixture")
        return httpx.Response(503 if feed == "error" else 200, json={"events": []})

    monkeypatch.setattr(httpx, "get", get)
    page = AppTest.from_file(HOME).switch_page(str(PUBLIC)).run()

    assert not page.exception
    assert "My Area" in [item.value for item in page.subheader]
    selector = page.selectbox(key="my_area_corridor")
    assert selector.options == ["All published events", *(corridor.name for corridor in settings.pilot_corridors)]
    selector.select("Chenab-Middle").run()
    assert not page.exception
    assert page.selectbox(key="my_area_corridor").value == "Chenab-Middle"
    assert any("coverage is unverified" in item.value for item in page.caption)
    assert page.get("page_link")[0].proto.label == "Official flood information"
    assert not page.metric
    assert not page.success
    assert not page.dataframe
    assert requested == ([] if feed == "unconfigured" else ["http://api.test/public/events"] * 2)


def test_reference_catalogue_can_be_unconfigured(dashboard, monkeypatch):
    from pakistan_flood_monitor.config import settings

    monkeypatch.setattr(settings, "pilot_corridors", [])
    monkeypatch.setattr(dashboard, "_APP_MODE", "operational")
    page = AppTest.from_file(HOME).switch_page(str(PUBLIC)).run()

    assert not page.exception
    assert "No reference river corridors are configured." in [item.value for item in page.info]
    assert not page.selectbox
    assert not page.metric


def test_my_area_filters_the_real_public_api_and_preserves_unassigned_events(dashboard, monkeypatch):
    from pakistan_flood_monitor.api import main
    from pakistan_flood_monitor.config import AppMode

    monkeypatch.setattr(dashboard, "_APP_MODE", "operational")
    monkeypatch.setattr(dashboard, "API_BASE_URL", "http://api.test")
    monkeypatch.setattr(main.settings, "app_mode", AppMode.OPERATIONAL)
    monkeypatch.setattr(main, "publication_gate", lambda event, app_mode: SimpleNamespace(passed=event["accepted"]))
    monkeypatch.setattr(main, "event_store", {
        "chenab": {
            "event_id": "chenab-published", "aoi": "Chenab-Middle", "status": "published", "accepted": True,
            "timestamps": {"detected_at": "2026-04-30T08:00:00Z", "published_at": "2026-05-01T10:00:00Z"},
            "geometry": {"type": "Point", "coordinates": [72.40, 31]},
        },
        "indus": {"event_id": "indus-published", "aoi": "Indus-Lower", "status": "published", "accepted": True},
        "unknown": {"event_id": "unknown-published", "aoi": "Unverified-Village", "status": "published", "accepted": True},
        "draft": {"event_id": "chenab-draft", "aoi": "Chenab-Middle", "status": "draft", "accepted": True},
        "ineligible": {"event_id": "chenab-ineligible", "aoi": "Chenab-Middle", "status": "published", "accepted": False},
    })
    client = TestClient(main.app)
    calls = []
    maps = []

    def get(url, **kwargs):
        calls.append(url)
        return client.get("/public/events")

    def render_map(map_, **kwargs):
        maps.append((map_.get_root().render(), kwargs))

    monkeypatch.setattr(httpx, "get", get)
    monkeypatch.setattr("streamlit_folium.st_folium", render_map)
    page = AppTest.from_file(HOME).switch_page(str(PUBLIC)).run()
    assert not page.exception
    assert page.metric[0].value == "3"
    assert any(item.label == "unknown-published · Corridor unavailable" for item in page.expander)
    assert any(item.value == "Published time unavailable." for item in page.markdown)
    assert not any("Unverified-Village" in item.label for item in page.expander)
    assert not page.warning
    assert not maps

    page.selectbox(key="my_area_corridor").select("Chenab-Middle").run()
    assert not page.exception
    assert page.metric[0].value == "1"
    assert any("chenab-published" in item.label for item in page.expander)
    assert not any("indus-published" in item.label for item in page.expander)
    assert not any("chenab-draft" in item.label or "chenab-ineligible" in item.label for item in page.expander)
    assert any("2026-05-01T10:00:00Z" in item.value and "Published" in item.value for item in page.markdown)
    assert any("2026-04-30T08:00:00Z" in item.value and "Detected" in item.value for item in page.markdown)
    assert any("freshness is unavailable" in item.value for item in page.caption)
    assert any("Exposure data is unavailable" in item.value for item in page.info)
    assert not page.dataframe
    assert len(calls) == 2

    page.checkbox(key="my_area_map").check().run()
    assert not page.exception
    assert maps[-1][1]["use_container_width"] is True
    assert "chenab-published" in maps[-1][0]
    assert "indus-published" not in maps[-1][0]

    page.selectbox(key="my_area_corridor").select("Kabul-Nowshera").run()
    assert not page.exception
    assert any("No published events are linked to Kabul-Nowshera" in item.value for item in page.info)
    assert any("all-events view" in item.value for item in page.caption)
    assert not page.metric
    assert len(maps) == 1
    assert calls == ["http://api.test/public/events"] * 4
