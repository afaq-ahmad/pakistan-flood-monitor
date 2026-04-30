import json
import warnings

from fastapi.testclient import TestClient

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from app.api.main import app


def test_export_center_geojson_cog_geoparquet_and_manifest() -> None:
    client = TestClient(app)

    for fmt in ("geojson", "cog", "geoparquet"):
        response = client.post("/analytics/exports", json={"event_id": "evt-indus-001", "format": fmt})
        assert response.status_code == 200
        payload = response.json()
        assert payload["format"] == fmt
        assert payload["validation"]["valid"] is True

        export_file = client.get(payload["download_url"])
        assert export_file.status_code == 200

        manifest_response = client.get(payload["manifest_url"])
        assert manifest_response.status_code == 200
        manifest = json.loads(manifest_response.content.decode("utf-8"))
        assert manifest["schema"] == "pakistan-flood-monitor/export-manifest/v1"
        assert manifest["lineage"]["exposure_endpoint"].endswith("/exposure")


def test_export_center_rejects_unknown_event() -> None:
    client = TestClient(app)
    response = client.post("/analytics/exports", json={"event_id": "unknown", "format": "geojson"})
    assert response.status_code == 404
