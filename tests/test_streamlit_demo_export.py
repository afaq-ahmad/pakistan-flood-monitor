import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "streamlit_app.py"
EXPORT = next((ROOT / "pages").glob("5_*")).relative_to(ROOT)


@pytest.fixture
def demo_service(monkeypatch, tmp_path):
    import backend_service

    monkeypatch.setattr(backend_service, "API_BASE_URL", None)
    monkeypatch.setattr(backend_service, "_APP_MODE", "demo")
    monkeypatch.setattr(backend_service, "DATA_DIR", ROOT / "data")
    monkeypatch.chdir(tmp_path)
    return backend_service


@pytest.mark.parametrize("fmt", ["cog", "geoparquet", "unknown"])
def test_placeholder_formats_are_rejected(demo_service, fmt):
    result = demo_service.DataService().generate_export("evt-indus-001", fmt)
    assert "error" in result
    assert not Path(".cache").exists()


@pytest.mark.parametrize("app_mode,api_url", [
    ("operational", None),
    ("demo", "http://api.test"),
])
def test_export_is_unavailable_outside_local_demo(demo_service, monkeypatch, app_mode, api_url):
    monkeypatch.setattr(demo_service, "_APP_MODE", app_mode)
    monkeypatch.setattr(demo_service, "API_BASE_URL", api_url)

    page = AppTest.from_file(HOME).switch_page(str(EXPORT)).run()

    assert not page.exception
    assert "GIS export is unavailable" in page.info[0].value
    assert not page.button
    assert "error" in demo_service.DataService().generate_export("evt-indus-001", "geojson")
    assert not Path(".cache").exists()


def test_export_rejects_invalid_coordinates(demo_service, monkeypatch):
    service = demo_service.DataService()
    monkeypatch.setattr(service, "get_event", lambda event_id: {"latitude": 95, "longitude": 67})

    assert "error" in service.generate_export("demo-event", "geojson")
    assert not Path(".cache").exists()


def test_demo_export_page_downloads_labelled_assets(demo_service):
    page = AppTest.from_file(HOME).switch_page(str(EXPORT)).run()
    assert not page.exception
    page.selectbox[0].select("evt-indus-001").run()
    page.button[0].click().run()
    assert not page.exception
    assert not page.error
    assert [button.proto.label for button in page.get("download_button")] == [
        "Download GeoJSON", "Download manifest",
    ]

    result = page.session_state["demo_export"][1]
    output = Path(result["output_path"]).read_bytes()
    feature_collection = json.loads(output)
    manifest = json.loads(Path(result["manifest_path"]).read_bytes())
    feature = feature_collection["features"][0]
    point = shape(feature["geometry"])
    assert (point.x, point.y) == (67.78, 26.73)
    for item in (manifest, feature_collection, feature["properties"]):
        assert item["product_label"] == "SIMULATED"
        assert item["demo_watermark"] == demo_service.DEMO_WATERMARK
    assert manifest["lineage"]["source_type"] == "local_demo_fixture"
    assert manifest["outputs"] == [{"path": "event.geojson", "size_bytes": len(output)}]
