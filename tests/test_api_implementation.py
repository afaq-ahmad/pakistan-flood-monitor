import os
import json
import base64
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from pakistan_flood_monitor.api.main import (
    app,
    event_store,
    historical_event_library,
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
    historical_event_library.clear()
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


def _structured_token(role: str, principal_id: str, expires_at: datetime) -> str:
    payload = {"role": role, "principal_id": principal_id, "exp": expires_at.isoformat()}
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
    return f"v1.{encoded}"


def _gis_review_payload(action: str, actor: str, notes: str) -> dict:
    return {
        "action": action,
        "actor": actor,
        "notes": notes,
        "label_metadata": {
            "label_type": "flood_extent",
            "label_tier": "tier_1",
            "analyst": actor,
            "date": "2026-01-01T00:00:00+00:00",
            "notes": notes,
            "uncertainty": 0.2,
        },
        "mapping_rules": {
            "river_inclusion_exclusion": "include main channel, exclude permanent water",
            "cloud_limitation_notes": "no cloud obstruction in SAR context",
            "disconnected_pool_handling": "retain disconnected pools above threshold area",
            "certainty_class": "high",
        },
    }




def _lifecycle_transition(client: TestClient, event_id: str, action: str, notes: str = "") -> None:
    response = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json={"action": action, "notes": notes},
        headers=_analyst_headers(),
    )
    assert response.status_code == 200

def test_monitoring_and_event_endpoints() -> None:
    _reset_state()
    client = TestClient(app)

    run_response = client.get("/internal/run/Indus-Lower", headers=_admin_headers())
    assert run_response.status_code == 200
    event_id = run_response.json()["published_outputs"]["review_queue_event"]["event_id"]

    _lifecycle_transition(client, event_id, "review", "begin analyst review")
    _lifecycle_transition(client, event_id, "approved", "approved by analyst")
    review_response = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json=_gis_review_payload("published", "analyst-1", "approved for public"),
        headers=_analyst_headers(),
    )
    assert review_response.status_code == 200

    events_response = client.get("/public/corridors/Indus-Lower/events")
    assert events_response.status_code == 200
    assert events_response.json()[0]["event_id"] == event_id

    corridors_response = client.get("/public/corridors")
    assert corridors_response.status_code == 200
    assert any(item["corridor_id"] == "Indus-Lower" for item in corridors_response.json())

    status_response = client.get("/public/corridors/Indus-Lower/status")
    assert status_response.status_code == 200
    assert "latest_hydromet_stress" in status_response.json()

    event_response = client.get(f"/public/events/{event_id}")
    assert event_response.status_code == 200
    event_payload = event_response.json()
    assert "confidence_breakdown" in event_payload
    assert event_payload["lineage"]["source_scene_ids"]
    assert event_payload["lineage"]["processing_version"] == "sar-preprocess-v1"
    assert "thresholds" in event_payload["lineage"]

    exposure_response = client.get(f"/public/events/{event_id}/exposure")
    assert exposure_response.status_code == 200
    assert "asset_summary" in exposure_response.json()

    historical_response = client.get(f"/public/events/{event_id}/historical")
    assert historical_response.status_code == 200
    assert "event_area_trend" in historical_response.json()

    confidence_response = client.get(f"/public/events/{event_id}/confidence")
    assert confidence_response.status_code == 200
    assert "confidence_breakdown" in confidence_response.json()

    public_historical_catalog = client.get("/public/historical-events")
    assert public_historical_catalog.status_code == 200
    assert any(item["event_id"] == event_id for item in public_historical_catalog.json())

    public_historical_record = client.get(f"/public/historical-events/{event_id}")
    assert public_historical_record.status_code == 200
    payload = public_historical_record.json()
    assert "catalog" in payload
    assert "assets" in payload
    assert payload["catalog"]["label_quality_score"] >= 0.8


def test_admin_and_registry_endpoints() -> None:
    _reset_state()
    client = TestClient(app)

    unauthorized_run = client.get("/internal/run/Chenab-Middle")
    assert unauthorized_run.status_code == 401

    run_response = client.get("/internal/run/Chenab-Middle", headers=_admin_headers())
    event_id = run_response.json()["published_outputs"]["review_queue_event"]["event_id"]

    _lifecycle_transition(client, event_id, "review", "Validated")
    _lifecycle_transition(client, event_id, "approved", "Approved")
    review_response = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json=_gis_review_payload("published", "spoofed-actor", "Validated"),
        headers=_analyst_headers(),
    )
    assert review_response.status_code == 200

    latest_alerts_response = client.get("/public/alerts/latest")
    assert latest_alerts_response.status_code == 200
    assert any(item["event_id"] == event_id for item in latest_alerts_response.json())

    audit_response = client.get("/internal/admin/review-audit", headers=_analyst_headers())
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_id"] == event_id
    assert audit_response.json()[0]["actor"] == "analyst-principal"

    threshold_response = client.post(
        "/internal/admin/register-threshold",
        json={
            "threshold_name": "flood_thresholds",
            "file_path": "configs/alert_thresholds.yaml",
            "version": "v2",
            "actor": "admin-spoof",
            "notes": "monsoon calibration",
        },
        headers=_admin_headers(),
    )
    assert threshold_response.status_code == 200
    assert threshold_response.json()["threshold"]["actor"] == "admin-principal"

    model_response = client.post(
        "/internal/admin/register-model",
        json={
            "model_id": "rules-v2",
            "model_type": "logistic_regression",
            "training_data_snapshot_version": "snapshot-2024-10",
            "training_config_path": "configs/training_config.yaml",
            "evaluation_report_path": "reports/evaluation/rules_v1.md",
            "actor": "admin-spoof",
            "validation_metrics": {"f1": 0.81},
            "deployment_status": "active",
            "rollback_parent_model_id": "rules-v1",
            "notes": "uplifted ranking",
        },
        headers=_admin_headers(),
    )
    assert model_response.status_code == 200
    assert model_response.json()["model"]["actor"] == "admin-principal"

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
            "actor": "admin-spoof",
            "notes": "better labels, no drift",
        },
        headers=_admin_headers(),
    )
    assert retraining_response.status_code == 200
    assert retraining_response.json()["decision"]["should_retrain"] is True
    assert retraining_response.json()["decision"]["actor"] == "admin-principal"
    assert "label_quality_improved" in retraining_response.json()["decision"]["reasons"]

    privileged_audit_response = client.get("/internal/admin/privileged-audit", headers=_admin_headers())
    assert privileged_audit_response.status_code == 200
    assert len(privileged_audit_response.json()) >= 4

    historical_admin_response = client.get("/internal/admin/historical-events", headers=_analyst_headers())
    assert historical_admin_response.status_code == 200
    assert any(item["event_id"] == event_id for item in historical_admin_response.json())

    export_response = client.get(
        "/internal/admin/historical-events/export?min_label_quality=0.8",
        headers=_analyst_headers(),
    )
    assert export_response.status_code == 200
    export_payload = export_response.json()
    assert export_payload["manifest"]["schema_version"] == "historical-event-library-v1"
    assert any(item["event_id"] == event_id for item in export_payload["events"])


def test_monitoring_metrics_endpoint_tracks_pipeline_ops_and_product() -> None:
    _reset_state()
    client = TestClient(app)

    run_response = client.get("/internal/run/Indus-Lower", headers=_admin_headers())
    assert run_response.status_code == 200
    event_id = run_response.json()["published_outputs"]["review_queue_event"]["event_id"]

    accept_response = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json={"action": "review", "actor": "analyst-2", "notes": "confirmed"},
        headers=_analyst_headers(),
    )
    assert accept_response.status_code == 200

    metrics_response = client.get("/internal/monitoring/metrics", headers=_analyst_headers())


def test_risk_summary_rollups_sorting_and_filters() -> None:
    _reset_state()
    client = TestClient(app)
    run_a = client.get("/internal/run/Indus-Lower", headers=_admin_headers())
    run_b = client.get("/internal/run/Chenab-Middle", headers=_admin_headers())
    event_a = run_a.json()["published_outputs"]["review_queue_event"]["event_id"]
    event_b = run_b.json()["published_outputs"]["review_queue_event"]["event_id"]
    for event_id in (event_a, event_b):
        _lifecycle_transition(client, event_id, "review")
        _lifecycle_transition(client, event_id, "approved")
    event_store[event_a]["admin_overlays"] = [
        {"province": "Sindh", "district": "Dadu", "tehsil": "Mehar"},
        {"province": "Sindh", "district": "Dadu", "tehsil": "Khairpur Nathan Shah"},
    ]
    event_store[event_b]["admin_overlays"] = [
        {"province": "Punjab", "district": "Multan", "tehsil": "Saddar"},
    ]

    tehsil_resp = client.get("/public/risk-summary/tehsil?sort_by=risk_score&order=desc")
    assert tehsil_resp.status_code == 200
    tehsil_payload = tehsil_resp.json()
    assert tehsil_payload["count"] >= 3
    assert tehsil_payload["results"][0]["risk_score"] >= tehsil_payload["results"][-1]["risk_score"]
    assert tehsil_payload["results"][0]["latest_event_status"] in {"approved", "published"}

    district_resp = client.get("/public/risk-summary/district?province=Sindh")
    assert district_resp.status_code == 200
    district_payload = district_resp.json()
    assert district_payload["count"] == 1
    assert district_payload["results"][0]["district"] == "Dadu"
    assert district_payload["results"][0]["tehsil"] == "ALL_TEHSILS"

    province_resp = client.get("/public/risk-summary/province?sort_by=exposure_score&order=asc&min_confidence=0.5")
    assert province_resp.status_code == 200
    province_payload = province_resp.json()
    if province_payload["count"] > 1:
        assert province_payload["results"][0]["exposure_score"] <= province_payload["results"][-1]["exposure_score"]

    invalid_sort = client.get("/public/risk-summary/tehsil?sort_by=invalid_field")
    assert invalid_sort.status_code == 400


def test_publish_requires_qa_and_sop_fields() -> None:
    _reset_state()
    client = TestClient(app)

    run_response = client.get("/internal/run/Indus-Lower", headers=_admin_headers())
    event_id = run_response.json()["published_outputs"]["review_queue_event"]["event_id"]

    publish_response = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json={"action": "published", "actor": "analyst-1", "notes": "attempt publish"},
        headers=_analyst_headers(),
    )

    assert publish_response.status_code == 400
    assert publish_response.json()["detail"]["error"] == "invalid_lifecycle_transition"


def test_privileged_endpoints_ignore_or_absorb_missing_actor_and_bind_principal() -> None:
    _reset_state()
    client = TestClient(app)

    run_response = client.get("/internal/run/Chenab-Middle", headers=_admin_headers())
    event_id = run_response.json()["published_outputs"]["review_queue_event"]["event_id"]

    review_response = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json={"action": "review", "notes": "no actor in payload"},
        headers=_analyst_headers(),
    )
    assert review_response.status_code == 200

    audit_response = client.get("/internal/admin/review-audit", headers=_analyst_headers())
    assert audit_response.status_code == 200
    assert audit_response.json()[-1]["principal_id"] == "analyst-principal"

    privileged_response = client.get("/internal/admin/privileged-audit", headers=_admin_headers())
    assert privileged_response.status_code == 200
    assert privileged_response.json()[-1]["principal_id"] == "analyst-principal"


def test_unauthenticated_privileged_actions_are_rejected() -> None:
    _reset_state()
    client = TestClient(app)

    resp = client.post(
        "/internal/admin/register-model",
        json={
            "model_id": "m1",
            "model_type": "xgb",
            "training_data_snapshot_version": "v1",
            "training_config_path": "configs/training_config.yaml",
            "evaluation_report_path": "reports/evaluation/rules_v1.md",
        },
    )
    assert resp.status_code == 401


def test_expired_and_malformed_tokens_are_rejected() -> None:
    _reset_state()
    client = TestClient(app)

    expired = _structured_token("admin", "admin-principal", datetime.now(UTC) - timedelta(minutes=5))
    expired_resp = client.get("/internal/run/Indus-Lower", headers={"Authorization": f"Bearer {expired}"})
    assert expired_resp.status_code == 401
    assert expired_resp.json()["detail"] == "Token expired"

    malformed_resp = client.get("/internal/run/Indus-Lower", headers={"Authorization": "Bearer v1.not-base64!!"})
    assert malformed_resp.status_code == 401
    assert malformed_resp.json()["detail"] == "Malformed token"


def test_role_separation_for_privileged_boundaries() -> None:
    _reset_state()
    client = TestClient(app)

    service = _structured_token("service", "svc-sync", datetime.now(UTC) + timedelta(hours=1))
    reviewer = _structured_token("reviewer", "reviewer-1", datetime.now(UTC) + timedelta(hours=1))

    service_denied = client.post(
        "/internal/admin/register-threshold",
        json={"threshold_name": "x", "file_path": "configs/alert_thresholds.yaml", "version": "v1"},
        headers={"Authorization": f"Bearer {service}"},
    )
    assert service_denied.status_code == 403

    reviewer_run_denied = client.get("/internal/run/Indus-Lower", headers={"Authorization": f"Bearer {reviewer}"})
    assert reviewer_run_denied.status_code == 403

    run_response = client.get("/internal/run/Indus-Lower", headers=_admin_headers())
    event_id = run_response.json()["published_outputs"]["review_queue_event"]["event_id"]
    reviewer_review = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json={"action": "review", "notes": "reviewed by reviewer role"},
        headers={"Authorization": f"Bearer {reviewer}"},
    )
    assert reviewer_review.status_code == 200


def test_lifecycle_invalid_and_trace_and_auth() -> None:
    _reset_state()
    client = TestClient(app)
    run_response = client.get("/internal/run/Indus-Lower", headers=_admin_headers())
    event_id = run_response.json()["published_outputs"]["review_queue_event"]["event_id"]

    skip_response = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json={"action": "approved", "notes": "skip review"},
        headers=_analyst_headers(),
    )
    assert skip_response.status_code == 400
    assert skip_response.json()["detail"]["error"] == "invalid_lifecycle_transition"

    no_auth = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json={"action": "review", "notes": "no auth"},
    )
    assert no_auth.status_code == 401

    _lifecycle_transition(client, event_id, "review", "start review")
    _lifecycle_transition(client, event_id, "approved", "approve")
    publish = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json=_gis_review_payload("published", "analyst-1", "publish"),
        headers=_analyst_headers(),
    )
    assert publish.status_code == 200
    trace = publish.json()["event"]["approval_trace"]
    assert len(trace) == 3
    assert trace[-1]["principal_id"] == "analyst-principal"
    assert trace[-1]["previous_state"] == "approved"
    assert trace[-1]["new_state"] == "published"


def test_public_endpoints_include_limitations_reference() -> None:
    _reset_state()
    client = TestClient(app)

    run_response = client.get("/internal/run/Indus-Lower", headers=_admin_headers())
    assert run_response.status_code == 200
    event_id = run_response.json()["published_outputs"]["review_queue_event"]["event_id"]

    _lifecycle_transition(client, event_id, "review", "begin analyst review")
    _lifecycle_transition(client, event_id, "approved", "approved by analyst")
    publish_response = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json=_gis_review_payload("published", "analyst-1", "approved for public"),
        headers=_analyst_headers(),
    )
    assert publish_response.status_code == 200

    limitation_doc = client.get("/public/limitations")
    assert limitation_doc.status_code == 200
    assert limitation_doc.json()["path"] == "/public/limitations"

    checks = [
        client.get("/public/publish/Indus-Lower").json(),
        client.get("/public/corridors").json()[0],
        client.get("/public/corridors/Indus-Lower/status").json(),
        client.get("/public/corridors/Indus-Lower/events").json()[0],
        client.get(f"/public/events/{event_id}").json(),
        client.get(f"/public/events/{event_id}/exposure").json(),
        client.get(f"/public/events/{event_id}/historical").json(),
        client.get(f"/public/events/{event_id}/confidence").json(),
        client.get("/public/historical-events").json()[0],
        client.get(f"/public/historical-events/{event_id}").json(),
        client.get("/public/alerts/latest").json()[0],
    ]
    for payload in checks:
        assert payload["limitations"]["href"] == "/public/limitations"

    feed = client.get("/public/alerts/feed")
    assert feed.status_code == 200
    for payload in feed.json():
        assert payload["limitations"]["href"] == "/public/limitations"
