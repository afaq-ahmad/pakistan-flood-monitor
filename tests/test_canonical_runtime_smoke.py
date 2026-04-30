from fastapi.testclient import TestClient

from pakistan_flood_monitor.api.main import app


def test_canonical_runtime_health_and_status_endpoints() -> None:
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    corridors = client.get("/public/corridors")
    assert corridors.status_code == 200
    assert isinstance(corridors.json(), list)
