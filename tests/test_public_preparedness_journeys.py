"""Offline public journeys through the production Streamlit entrypoint."""

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from official_sources import OFFICIAL_SOURCES, SOURCE_REVIEWED_ON
from pakistan_flood_monitor.api import main
from preparedness_ui import NDMA_FLOOD_GUIDE

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "streamlit_app.py"
API = "http://api.test"


@pytest.fixture
def dashboard(monkeypatch):
    import backend_service

    monkeypatch.setattr(backend_service, "API_BASE_URL", None)
    monkeypatch.setattr(backend_service, "_APP_MODE", "operational")
    return backend_service


def follow_link(page, label, route):
    link, = [item.proto for item in page.page_link if item.value == label]
    assert link.page == route and link.page_script_hash and not link.disabled
    destination, = (ROOT / "pages").glob(f"*_{route}.py")
    # PageLink is read-only in AppTest. Resolve the destination and exercise it
    # in the same session through Streamlit's routing registry.
    page.switch_page(str(destination.relative_to(ROOT))).run()
    assert not page.exception
    return page


def confirm_official_directory(page):
    assert page.title[0].value == "Official flood information"
    assert any(SOURCE_REVIEWED_ON in caption.value for caption in page.caption)
    assert any("check its issue date" in warning.value for warning in page.warning)
    for source in OFFICIAL_SOURCES:
        assert any(f"[{source['link_label']}]({source['url']})" in item.value for item in page.markdown)


@pytest.mark.parametrize("label,route,visible,topic,reference", [
    ("Prepare my farm", "Farmer_Preparedness", "Plan where to move portable pumps", "Crops, equipment and chemicals",
     "University of Vermont Extension farm preparedness"),
    ("Prepare my livestock", "Livestock_Preparedness", "protected fodder and clean water",
     "Feed and water before flooding", "https://livestock.sindh.gov.pk/contact-us"),
], ids=["A-farmer", "B-livestock"])
def test_preparedness_to_official_sources(dashboard, monkeypatch, label, route, visible, topic, reference):
    def forbidden(*args, **kwargs):
        pytest.fail("Static guide used a provider or event data")

    monkeypatch.setattr(httpx, "get", forbidden)
    monkeypatch.setattr(dashboard.DataService, "_load", forbidden)
    page = follow_link(AppTest.from_file(HOME).run(), label, route)
    assert not page.warning
    assert [heading.value for heading in page.header[:3]] == [
        "Before flooding", "During flooding", "After flooding",
    ]
    assert any(visible in item.value for item in page.main.markdown)
    assert any(item.label == topic for item in page.expander)
    assert not page.get("component_instance") and not page.get("imgs")
    if route == "Livestock_Preparedness":
        assert any("Veterinary Information" in item.value for item in page.header)
        assert any("cannot verify" in item.value for item in page.markdown)

    page.checkbox[0].check().run()
    assert not page.exception
    assert any(item.value == topic for item in page.subheader)
    assert not page.expander
    assert any(reference in item.value for item in page.markdown)
    assert any(NDMA_FLOOD_GUIDE in item.value for item in page.markdown)
    confirm_official_directory(follow_link(page, "View official flood information", "Official_Information"))


@pytest.mark.parametrize("fail_request", [False, True], ids=["C-empty", "D-timeout"])
def test_area_information_to_official_sources(dashboard, monkeypatch, fail_request):
    monkeypatch.setattr(dashboard, "API_BASE_URL", API)
    calls = []

    def get(url, *, timeout: float):
        calls.append((url, timeout))
        if fail_request:
            raise httpx.ReadTimeout("offline fixture")
        return httpx.Response(200, json={"events": []})

    monkeypatch.setattr(httpx, "get", get)
    page = follow_link(AppTest.from_file(HOME).run(), "Open My Area", "Public_Dashboard")
    page.selectbox(key="my_area_corridor").select("Chenab-Middle").run()
    assert not page.exception
    assert page.selectbox(key="my_area_corridor").value == "Chenab-Middle"
    assert not page.metric and not page.get("component_instance") and not page.checkbox
    if fail_request:
        assert any("Flood information is unavailable" in item.value for item in page.error)
    else:
        assert any("No published events are linked to Chenab-Middle" in item.value and
                   "conditions may still be unknown" in item.value for item in page.info)
    confirm_official_directory(follow_link(page, "View official flood information", "Official_Information"))
    assert calls == [(f"{API}/public/events", 2.0)] * 3


def test_report_practice_acknowledges_preview_without_persisting(dashboard, monkeypatch, tmp_path):
    monkeypatch.setattr(dashboard, "_APP_MODE", "demo")
    monkeypatch.setattr(dashboard, "DATA_DIR", tmp_path)

    page = follow_link(AppTest.from_file(HOME).run(), "Community Reporting", "Field_Reports")
    assert any("Practice a community report (demo)" == block.label for block in page.expander)
    page.selectbox(key="sub_cat").select("🌿 Fodder or clean water need")
    page.selectbox(key="sub_corridor").select("Chenab-Middle")
    page.checkbox(key="sub_consent").check()
    page.button(key="sub_submit_btn").click().run()
    assert not page.exception
    assert any("Practice preview" in item.value and "Nothing was submitted" in item.value for item in page.info)
    assert not page.success and not list(tmp_path.iterdir())

    monkeypatch.setattr(dashboard, "_APP_MODE", "operational")
    page = follow_link(AppTest.from_file(HOME).run(), "Community Reporting", "Field_Reports")
    assert any("Resident report submission is unavailable" in item.value for item in page.info)
    assert not page.button


def test_visitor_cannot_read_review_queue_or_change_settings(dashboard, monkeypatch, tmp_path):
    monkeypatch.setattr(dashboard, "API_BASE_URL", API)
    monkeypatch.setattr(dashboard, "CONFIG_DIR", tmp_path)
    configuration = tmp_path / "flood_thresholds.yaml"
    configuration.write_text("fixture_private_marker: test-only\n")
    page = AppTest.from_file(HOME)
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(200, json={"events": []}))
    page.run()
    assert all(link.proto.page not in {"Analyst_Review", "Settings"} for link in page.page_link)

    calls = []

    def unexpected(url, **kwargs):
        calls.append(url)
        pytest.fail("Anonymous route requested internal data")

    monkeypatch.setattr(httpx, "get", unexpected)
    analyst, = (ROOT / "pages").glob("2_*")
    page.switch_page(str(analyst.relative_to(ROOT))).run()
    assert not page.exception
    assert any("Enter a review credential" in item.value for item in page.info)
    assert not page.dataframe and not page.button

    settings, = (ROOT / "pages").glob("8_*")
    page.switch_page(str(settings.relative_to(ROOT))).run()
    assert not page.exception
    assert not page.button and not page.text_input and not page.json
    assert any("authorized operators" in item.value for item in page.info)
    assert configuration.read_text() == "fixture_private_marker: test-only\n"
    assert not calls

    with TestClient(main.app) as client:
        assert client.get("/internal/review-queue").status_code == 401
        assert client.get("/internal/admin/state/export").status_code == 401
