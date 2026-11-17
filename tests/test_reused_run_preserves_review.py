from fastapi.testclient import TestClient

from pakistan_flood_monitor.api import main


def test_reused_run_preserves_review_and_does_not_duplicate(monkeypatch):
    main.rate_limiter.reset()
    main.run_history.clear()
    main.event_store.clear()
    main.historical_event_library.clear()
    monkeypatch.setenv("FLOOD_MONITOR_ADMIN_TOKEN", "reuse-admin")
    monkeypatch.setenv("FLOOD_MONITOR_ANALYST_TOKEN", "reuse-analyst")
    monkeypatch.setenv("FLOOD_MONITOR_RATE_LIMIT_REQUESTS", "1000")
    client = TestClient(main.app)
    admin = {"Authorization": "Bearer reuse-admin"}
    analyst = {"Authorization": "Bearer reuse-analyst"}
    first = client.get("/internal/run/Indus-Lower", headers=admin)
    assert first.status_code == 200
    event_id = first.json()["published_outputs"]["review_queue_event"]["event_id"]
    review = client.post(f"/internal/admin/review-event?event_id={event_id}", headers=analyst, json={"action": "review", "notes": "review in progress"})
    assert review.status_code == 200
    second = client.get("/internal/run/Indus-Lower", headers=admin)
    assert second.status_code == 200
    assert main.event_store[event_id]["status"] == "review"
    assert len(main.run_history["Indus-Lower"]) == 1

    # A changed retry for the same event must be rejected rather than silently
    # returning new machine results alongside the old reviewed event.
    from copy import deepcopy
    from fastapi import HTTPException
    import pytest

    changed = deepcopy(first.json())
    changed["trigger_reason"] = "a different processing result"
    with pytest.raises(HTTPException) as error:
        main._record_run(changed, persist_pipeline_run=False)
    assert error.value.status_code == 409
    assert error.value.detail["error"] == "existing_event_report_conflict"
    assert main.event_store[event_id]["status"] == "review"
    assert len(main.run_history["Indus-Lower"]) == 1

    collided = deepcopy(first.json())
    collided["run_id"] = "another-run"
    with pytest.raises(HTTPException) as error:
        main._record_run(collided, persist_pipeline_run=False)
    assert error.value.status_code == 409
    assert error.value.detail["error"] == "existing_event_run_conflict"
    assert main.event_store[event_id]["status"] == "review"
    assert len(main.run_history["Indus-Lower"]) == 1
