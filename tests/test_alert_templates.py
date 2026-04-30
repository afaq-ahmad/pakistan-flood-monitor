import os

from fastapi.testclient import TestClient

from pakistan_flood_monitor.api.main import app, event_store, run_history
from pakistan_flood_monitor.services.alert_templates import render_alert_template

ADMIN_TOKEN = "test-admin-token"
ANALYST_TOKEN = "test-analyst-token"


def _reset_state() -> None:
    run_history.clear()
    event_store.clear()
    os.environ["FLOOD_MONITOR_ADMIN_TOKEN"] = ADMIN_TOKEN
    os.environ["FLOOD_MONITOR_ANALYST_TOKEN"] = ANALYST_TOKEN


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {ANALYST_TOKEN}"}


def _publish_event(client: TestClient) -> str:
    run_response = client.get("/internal/run/Indus-Lower", headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    event_id = run_response.json()["published_outputs"]["review_queue_event"]["event_id"]
    assert client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json={"action": "review", "notes": "ok"},
        headers=_headers(),
    ).status_code == 200
    assert client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json={"action": "approved", "notes": "ok"},
        headers=_headers(),
    ).status_code == 200
    response = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        json={
            "action": "published",
            "notes": "ok",
            "label_metadata": {"label_type": "flood_extent", "label_tier": "tier_1", "analyst": "analyst", "date": "2026-01-01T00:00:00+00:00", "notes": "ok", "uncertainty": 0.2},
            "mapping_rules": {"river_inclusion_exclusion": "include main channel", "cloud_limitation_notes": "n/a", "disconnected_pool_handling": "retain", "certainty_class": "high"},
        },
        headers=_headers(),
    )
    assert response.status_code == 200
    return event_id


def test_alert_templates_variant_behavior_and_required_fields() -> None:
    _reset_state()
    client = TestClient(app)
    event_id = _publish_event(client)

    public_payload = client.get("/public/alerts/latest?variant=public_safe").json()[0]
    official_payload = client.get(f"/internal/alerts/templates?event_id={event_id}&variant=official_internal", headers=_headers()).json()

    assert public_payload["variant"] == "public_safe"
    assert public_payload["public_disclaimer"]
    assert public_payload["limitations"]["reference"] == "/public/limitations"

    assert official_payload["variant"] == "official_internal"
    assert "workflow" in official_payload
    assert "public_disclaimer" not in official_payload

    for required in ("confidence", "affected_area", "event_timestamp", "source_lineage", "recommended_actions"):
        assert required in public_payload


def test_alert_template_missing_required_data_raises() -> None:
    bad_event = {"event_id": "evt-1", "aoi": "Indus-Lower"}
    try:
        render_alert_template(event=bad_event, variant="public_safe")
        raise AssertionError("expected missing field validation")
    except ValueError as exc:
        assert "missing required field" in str(exc)


def test_alert_template_snapshot_like_output() -> None:
    event = {
        "event_id": "evt-42",
        "aoi": "Indus-Lower",
        "status": "published",
        "timestamps": {"detected_at": "2026-04-30T00:00:00+00:00"},
        "confidence_bucket": "high",
        "confidence_breakdown": {"score": 0.9, "method": "ensemble-v1"},
        "lineage": {"source_scene_ids": ["S1A_001"], "processing_version": "sar-preprocess-v1", "thresholds": {"flood": 0.7}},
    }
    payload = render_alert_template(event=event, variant="public_safe")
    assert payload["template"] == "ndma_pdma_flood_alert_v1"
    assert payload["source_lineage"]["source_scene_ids"] == ["S1A_001"]
    assert payload["confidence"]["score"] == 0.9
