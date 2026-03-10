import os

from fastapi.testclient import TestClient

from pakistan_flood_monitor.api.main import (
    app,
    event_store,
    model_registry,
    privileged_audit_log,
    retraining_decisions,
    review_audit_log,
    run_history,
    threshold_registry,
)


ADMIN_TOKEN = "test-admin-token"
ANALYST_TOKEN = "test-analyst-token"


def _reset_state() -> None:
    run_history.clear()
    event_store.clear()
    review_audit_log.clear()
    privileged_audit_log.clear()
    threshold_registry.clear()
    model_registry.clear()
    retraining_decisions.clear()
    os.environ["FLOOD_MONITOR_ADMIN_TOKEN"] = ADMIN_TOKEN
    os.environ["FLOOD_MONITOR_ANALYST_TOKEN"] = ANALYST_TOKEN


def _admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def _analyst_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {ANALYST_TOKEN}"}


def test_monitoring_and_event_endpoints() -> None:
    _reset_state()
    client = TestClient(app)

    run_response = client.get("/internal/run/Indus-Lower", headers=_admin_headers())
    assert run_response.status_code == 200
    event_id = run_response.json()["published_outputs"]["review_queue_event"]["event_id"]

    review_response = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json={"action": "published", "actor": "analyst-1", "notes": "approved for public"},
        headers=_analyst_headers(),
    )
    assert review_response.status_code == 200

    hidden_after_reject = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json={"action": "reject", "actor": "analyst-1", "notes": "not publishable"},
        headers=_analyst_headers(),
    )
    assert hidden_after_reject.status_code == 200
    assert client.get(f"/public/events/{event_id}").status_code == 404

    republish_response = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json={"action": "published", "actor": "analyst-1", "notes": "approved for public"},
        headers=_analyst_headers(),
    )
    assert republish_response.status_code == 200

    corridors_response = client.get("/public/corridors")
    assert corridors_response.status_code == 200
    assert any(item["corridor_id"] == "Indus-Lower" for item in corridors_response.json())

    status_response = client.get("/public/corridors/Indus-Lower/status")
    assert status_response.status_code == 200
    assert "latest_hydromet_stress" in status_response.json()

    events_response = client.get("/public/corridors/Indus-Lower/events")
    assert events_response.status_code == 200
    assert events_response.json()[0]["event_id"] == event_id

    event_response = client.get(f"/public/events/{event_id}")
    assert event_response.status_code == 200
    assert "confidence_breakdown" in event_response.json()

    exposure_response = client.get(f"/public/events/{event_id}/exposure")
    assert exposure_response.status_code == 200
    assert "asset_summary" in exposure_response.json()

    historical_response = client.get(f"/public/events/{event_id}/historical")
    assert historical_response.status_code == 200
    assert "event_area_trend" in historical_response.json()

    confidence_response = client.get(f"/public/events/{event_id}/confidence")
    assert confidence_response.status_code == 200
    assert "confidence_breakdown" in confidence_response.json()


def test_admin_and_registry_endpoints() -> None:
    _reset_state()
    client = TestClient(app)

    unauthorized_run = client.get("/internal/run/Chenab-Middle")
    assert unauthorized_run.status_code == 401

    run_response = client.get("/internal/run/Chenab-Middle", headers=_admin_headers())
    event_id = run_response.json()["published_outputs"]["review_queue_event"]["event_id"]

    review_response = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json={
            "action": "accept",
            "actor": "analyst-1",
            "analyst_confidence": 0.88,
            "notes": "Validated",
        },
        headers=_analyst_headers(),
    )
    assert review_response.status_code == 200

    latest_alerts_response = client.get("/public/alerts/latest")
    assert latest_alerts_response.status_code == 200
    assert any(item["event_id"] == event_id for item in latest_alerts_response.json())

    audit_response = client.get("/internal/admin/review-audit", headers=_analyst_headers())
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_id"] == event_id

    threshold_response = client.post(
        "/internal/admin/register-threshold",
        json={
            "threshold_name": "flood_thresholds",
            "file_path": "configs/alert_thresholds.yaml",
            "version": "v2",
            "actor": "mlops",
            "notes": "monsoon calibration",
        },
        headers=_admin_headers(),
    )
    assert threshold_response.status_code == 200

    model_response = client.post(
        "/internal/admin/register-model",
        json={
            "model_id": "rules-v2",
            "model_type": "logistic_regression",
            "training_data_snapshot_version": "snapshot-2024-10",
            "training_config_path": "configs/training_config.yaml",
            "evaluation_report_path": "reports/evaluation/rules_v1.md",
            "actor": "mlops",
            "validation_metrics": {"f1": 0.81},
            "deployment_status": "active",
            "rollback_parent_model_id": "rules-v1",
            "notes": "uplifted ranking",
        },
        headers=_admin_headers(),
    )
    assert model_response.status_code == 200

    reprocess_response = client.post("/internal/admin/reprocess-scene?aoi_name=Chenab-Middle", headers=_admin_headers())
    assert reprocess_response.status_code == 200
    assert reprocess_response.json()["history_depth"] == 2

    retraining_response = client.post(
        "/internal/admin/evaluate-retraining",
        json={
            "model_id": "rules-v2",
            "label_quality_gain": 0.12,
            "drift_score": 0.05,
            "feature_schema_changed": False,
            "actor": "mlops",
            "notes": "better labels, no drift",
        },
        headers=_admin_headers(),
    )
    assert retraining_response.status_code == 200
    assert retraining_response.json()["decision"]["should_retrain"] is True
    assert "label_quality_improved" in retraining_response.json()["decision"]["reasons"]

    privileged_audit_response = client.get("/internal/admin/privileged-audit", headers=_admin_headers())
    assert privileged_audit_response.status_code == 200
    assert len(privileged_audit_response.json()) >= 4


def test_monitoring_metrics_endpoint_tracks_pipeline_ops_and_product() -> None:
    _reset_state()
    client = TestClient(app)

    run_response = client.get("/internal/run/Indus-Lower", headers=_admin_headers())
    assert run_response.status_code == 200
    event_id = run_response.json()["published_outputs"]["review_queue_event"]["event_id"]

    accept_response = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json={"action": "accept", "actor": "analyst-2", "notes": "confirmed"},
        headers=_analyst_headers(),
    )
    assert accept_response.status_code == 200

    metrics_response = client.get("/internal/monitoring/metrics", headers=_analyst_headers())
    assert metrics_response.status_code == 200
    payload = metrics_response.json()
    assert payload["pipeline_metrics"]["alerts_published"] >= 1
    assert payload["ops_metrics"]["queue_backlog"] >= 1
    assert payload["product_metrics"]["alerts_produced"] >= 1
    assert payload["product_metrics"]["alerts_confirmed"] >= 1

    reject_response = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json={"action": "false_alarm", "actor": "analyst-2", "notes": "qa false alarm"},
        headers=_analyst_headers(),
    )
    assert reject_response.status_code == 200

    metrics_after_reject = client.get("/internal/monitoring/metrics", headers=_analyst_headers()).json()
    assert metrics_after_reject["product_metrics"]["false_alarms"] >= 1
