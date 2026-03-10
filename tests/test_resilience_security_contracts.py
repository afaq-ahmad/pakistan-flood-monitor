from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from pakistan_flood_monitor.api.main import (
    app,
    event_store,
    historical_event_library,
    model_registry,
    privileged_audit_log,
    rate_limiter,
    retraining_decisions,
    review_audit_log,
    run_history,
    threshold_registry,
)

ADMIN_TOKEN = "resilience-admin-token"
ANALYST_TOKEN = "resilience-analyst-token"


def _reset_state() -> None:
    run_history.clear()
    event_store.clear()
    historical_event_library.clear()
    review_audit_log.clear()
    privileged_audit_log.clear()
    threshold_registry.clear()
    model_registry.clear()
    retraining_decisions.clear()
    rate_limiter.reset()
    os.environ["FLOOD_MONITOR_ADMIN_TOKEN"] = ADMIN_TOKEN
    os.environ["FLOOD_MONITOR_ANALYST_TOKEN"] = ANALYST_TOKEN
    os.environ["FLOOD_MONITOR_RATE_LIMIT_REQUESTS"] = "1000"
    os.environ["FLOOD_MONITOR_RATE_LIMIT_WINDOW_SECONDS"] = "60"


def _admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def _analyst_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {ANALYST_TOKEN}"}


def test_runtime_state_export_restore_supports_restart_recovery() -> None:
    _reset_state()
    client = TestClient(app)

    run_response = client.get("/internal/run/Indus-Lower", headers=_admin_headers())
    assert run_response.status_code == 200

    exported = client.get("/internal/admin/state/export", headers=_admin_headers())
    assert exported.status_code == 200
    snapshot = exported.json()["state"]
    assert snapshot["event_store"]

    run_history.clear()
    event_store.clear()
    historical_event_library.clear()
    review_audit_log.clear()

    restore = client.post("/internal/admin/state/restore", headers=_admin_headers(), json={"state": snapshot})
    assert restore.status_code == 200
    assert restore.json()["events"] >= 1

    event_id = next(iter(event_store.keys()))
    review = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        headers=_analyst_headers(),
        json={"action": "accept", "actor": "analyst-ops", "notes": "post-restart recovered"},
    )
    assert review.status_code == 200


def test_concurrent_writes_and_read_after_write_across_clients() -> None:
    _reset_state()

    def _run(aoi: str) -> int:
        with TestClient(app) as client:
            return client.get(f"/internal/run/{aoi}", headers=_admin_headers()).status_code

    aois = ["Indus-Lower", "Chenab-Middle", "Indus-Lower", "Chenab-Middle"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(_run, aois))

    assert all(code == 200 for code in statuses)

    with TestClient(app) as reader:
        corridors = reader.get("/public/corridors").json()
        assert len(corridors) >= 2
        assert sum(len(runs) for runs in run_history.values()) >= 4


def test_actor_spoofing_is_rejected_and_token_misuse_forbidden() -> None:
    _reset_state()
    client = TestClient(app)

    run_response = client.get("/internal/run/Indus-Lower", headers=_admin_headers())
    event_id = run_response.json()["published_outputs"]["review_queue_event"]["event_id"]

    spoof_attempt = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        headers=_analyst_headers(),
        json={"action": "accept", "actor": "admin-fake", "notes": "spoof"},
    )
    assert spoof_attempt.status_code == 403
    assert "not allowed" in spoof_attempt.json()["detail"]

    admin_only = client.post(
        "/internal/admin/register-threshold",
        headers=_analyst_headers(),
        json={
            "threshold_name": "bad",
            "file_path": "configs/alert_thresholds.yaml",
            "version": "v0",
            "actor": "analyst-a",
            "notes": "should fail",
        },
    )
    assert admin_only.status_code == 403


def test_internal_rate_limiting_and_prometheus_export() -> None:
    _reset_state()
    os.environ["FLOOD_MONITOR_RATE_LIMIT_REQUESTS"] = "2"
    os.environ["FLOOD_MONITOR_RATE_LIMIT_WINDOW_SECONDS"] = "60"
    client = TestClient(app)

    first = client.get("/internal/run/Indus-Lower", headers=_admin_headers())
    second = client.get("/internal/monitoring/metrics", headers=_analyst_headers())
    third = client.get("/internal/monitoring/metrics", headers=_analyst_headers())
    fourth = client.get("/internal/monitoring/metrics", headers=_analyst_headers())

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200
    assert fourth.status_code == 429

    rate_limiter.reset()
    metrics = client.get("/internal/monitoring/metrics/prometheus", headers=_analyst_headers())
    assert metrics.status_code == 200
    assert "pipeline_alerts_published_total" in metrics.text


def test_end_to_end_contract_flow_with_realistic_dataset() -> None:
    _reset_state()
    client = TestClient(app)

    run_response = client.get("/internal/run/Indus-Lower", headers=_admin_headers())
    assert run_response.status_code == 200
    event_id = run_response.json()["published_outputs"]["review_queue_event"]["event_id"]

    publish = client.post(
        f"/internal/admin/review-event?event_id={event_id}",
        headers=_analyst_headers(),
        json={
            "action": "published",
            "actor": "analyst-qa",
            "notes": "publish from realistic rainy-day ingestion",
            "label_metadata": {
                "label_type": "flood_extent",
                "label_tier": "tier_1",
                "analyst": "analyst-qa",
                "date": "2026-01-01T00:00:00+00:00",
                "notes": "clear SAR signal",
                "uncertainty": 0.15,
            },
            "mapping_rules": {
                "river_inclusion_exclusion": "include active floodplain",
                "cloud_limitation_notes": "sar unaffected",
                "disconnected_pool_handling": "retain if above 0.1km2",
                "certainty_class": "high",
            },
        },
    )
    assert publish.status_code == 200

    public_event = client.get(f"/public/events/{event_id}")
    public_exposure = client.get(f"/public/events/{event_id}/exposure")
    alerts = client.get("/public/alerts/latest")

    assert public_event.status_code == 200
    assert public_exposure.status_code == 200
    assert alerts.status_code == 200
    assert public_event.json()["status"] == "published"
    assert "asset_summary" in public_exposure.json()
    assert any(item["event_id"] == event_id for item in alerts.json())
