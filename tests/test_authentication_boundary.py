import base64
import json

from fastapi.testclient import TestClient

from pakistan_flood_monitor.api.main import app, rate_limiter


def test_unsigned_admin_and_unconfigured_tokens_are_rejected(monkeypatch):
    monkeypatch.setenv("FLOOD_MONITOR_ADMIN_TOKEN", "known-admin-secret")
    payload = {"role": "admin", "principal_id": "attacker", "exp": "2099-01-01T00:00:00+00:00"}
    forged = "v1." + base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    rate_limiter.reset()
    client = TestClient(app)
    for token in (forged, "incorrect-secret", "v1.not-base64!!"):
        response = client.get("/internal/workflow-runs/not-a-run", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
    response = client.get("/internal/workflow-runs/not-a-run", headers={"Authorization": "Bearer known-admin-secret"})
    assert response.status_code == 404


def test_configured_v1_prefixed_secret_is_still_accepted(monkeypatch):
    monkeypatch.setenv("FLOOD_MONITOR_ADMIN_TOKEN", "v1.configured-secret")
    rate_limiter.reset()
    response = TestClient(app).get("/internal/workflow-runs/not-a-run", headers={"Authorization": "Bearer v1.configured-secret"})
    assert response.status_code == 404


def test_configured_roles_cannot_access_admin_boundary(monkeypatch):
    monkeypatch.setenv("FLOOD_MONITOR_SERVICE_TOKEN", "service-secret")
    monkeypatch.setenv("FLOOD_MONITOR_REVIEWER_TOKEN", "reviewer-secret")
    rate_limiter.reset()
    client = TestClient(app)
    for token in ("service-secret", "reviewer-secret"):
        response = client.get("/internal/workflow-runs/not-a-run", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
