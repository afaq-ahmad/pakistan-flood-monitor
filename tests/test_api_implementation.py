from fastapi.testclient import TestClient

from pakistan_flood_monitor.api.main import (
    app,
    event_store,
    model_registry,
    review_audit_log,
    run_history,
    threshold_registry,
)


def _reset_state() -> None:
    run_history.clear()
    event_store.clear()
    review_audit_log.clear()
    threshold_registry.clear()
    model_registry.clear()


def test_monitoring_and_event_endpoints() -> None:
    _reset_state()
    client = TestClient(app)

    run_response = client.get("/run/Indus-Lower")
    assert run_response.status_code == 200
    event_id = run_response.json()["published_outputs"]["review_queue_event"]["event_id"]

    corridors_response = client.get("/corridors")
    assert corridors_response.status_code == 200
    assert any(item["corridor_id"] == "Indus-Lower" for item in corridors_response.json())

    status_response = client.get("/corridors/Indus-Lower/status")
    assert status_response.status_code == 200
    assert "latest_hydromet_stress" in status_response.json()

    events_response = client.get("/corridors/Indus-Lower/events")
    assert events_response.status_code == 200
    assert events_response.json()[0]["event_id"] == event_id

    event_response = client.get(f"/events/{event_id}")
    assert event_response.status_code == 200
    assert "confidence_breakdown" in event_response.json()

    exposure_response = client.get(f"/events/{event_id}/exposure")
    assert exposure_response.status_code == 200
    assert "asset_summary" in exposure_response.json()

    historical_response = client.get(f"/events/{event_id}/historical")
    assert historical_response.status_code == 200
    assert "event_area_trend" in historical_response.json()

    confidence_response = client.get(f"/events/{event_id}/confidence")
    assert confidence_response.status_code == 200
    assert "confidence_breakdown" in confidence_response.json()


def test_admin_and_registry_endpoints() -> None:
    _reset_state()
    client = TestClient(app)

    run_response = client.get("/run/Chenab-Middle")
    event_id = run_response.json()["published_outputs"]["review_queue_event"]["event_id"]

    review_response = client.post(
        f"/admin/review-event?event_id={event_id}",
        json={
            "action": "accept",
            "actor": "analyst-1",
            "analyst_confidence": 0.88,
            "notes": "Validated",
        },
    )
    assert review_response.status_code == 200

    latest_alerts_response = client.get("/alerts/latest")
    assert latest_alerts_response.status_code == 200
    assert any(item["event_id"] == event_id for item in latest_alerts_response.json())

    audit_response = client.get("/admin/review-audit")
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_id"] == event_id

    threshold_response = client.post(
        "/admin/register-threshold",
        json={
            "threshold_name": "flood_thresholds",
            "file_path": "configs/alert_thresholds.yaml",
            "version": "v2",
            "actor": "mlops",
            "notes": "monsoon calibration",
        },
    )
    assert threshold_response.status_code == 200

    model_response = client.post(
        "/admin/register-model",
        json={
            "model_id": "rules-v2",
            "training_data_snapshot_version": "snapshot-2024-10",
            "training_config_path": "configs/training_config.yaml",
            "evaluation_report_path": "reports/evaluation/rules_v1.md",
            "actor": "mlops",
            "notes": "uplifted ranking",
        },
    )
    assert model_response.status_code == 200

    reprocess_response = client.post("/admin/reprocess-scene?aoi_name=Chenab-Middle")
    assert reprocess_response.status_code == 200
    assert reprocess_response.json()["history_depth"] == 2
