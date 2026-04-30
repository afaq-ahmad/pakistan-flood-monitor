import json
import os
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from pakistan_flood_monitor.api.main import app, event_store, rate_limiter, run_history

ADMIN_TOKEN = "test-admin-token"


def _reset_state() -> None:
    run_history.clear()
    event_store.clear()
    rate_limiter.reset()
    os.environ["FLOOD_MONITOR_ADMIN_TOKEN"] = ADMIN_TOKEN
    os.environ["FLOOD_MONITOR_ANALYST_TOKEN"] = "test-analyst-token"
    os.environ["FLOOD_MONITOR_RATE_LIMIT_REQUESTS"] = "1000"
    os.environ["FLOOD_MONITOR_RATE_LIMIT_WINDOW_SECONDS"] = "60"


def _resolve_response_schema(path: str, method: str, status: int) -> dict | None:
    openapi = app.openapi()
    operation = openapi["paths"][path][method.lower()]
    response = operation["responses"].get(str(status))
    if not response:
        return None
    schema = response.get("content", {}).get("application/json", {}).get("schema")
    if not schema:
        return None
    if "$ref" in schema:
        ref = schema["$ref"].split("/")[-1]
        return openapi["components"]["schemas"][ref]
    return schema


def _assert_matches_schema(instance: Any, schema: dict[str, Any]) -> None:
    schema_type = schema.get("type")
    if schema_type == "object":
        assert isinstance(instance, dict)
        for field in schema.get("required", []):
            assert field in instance
        for key, value in instance.items():
            child_schema = schema.get("properties", {}).get(key)
            if child_schema:
                _assert_matches_schema(value, child_schema)
    elif schema_type == "array":
        assert isinstance(instance, list)
    elif schema_type == "string":
        assert isinstance(instance, str)
    elif schema_type == "number":
        assert isinstance(instance, (int, float))
    elif schema_type == "integer":
        assert isinstance(instance, int)
    elif schema_type == "boolean":
        assert isinstance(instance, bool)


def test_api_examples_against_runtime_and_openapi() -> None:
    _reset_state()
    examples = json.loads(Path("tests/fixtures/api_contract_examples.json").read_text(encoding="utf-8"))
    client = TestClient(app)

    for group_name in ("success", "failure"):
        for example in examples[group_name]:
            if example.get("precondition") == "exhaust_rate_limit":
                os.environ["FLOOD_MONITOR_RATE_LIMIT_REQUESTS"] = "2"
                os.environ["FLOOD_MONITOR_RATE_LIMIT_WINDOW_SECONDS"] = "60"
                for _ in range(2):
                    client.request(example["method"], example["path"], headers=example.get("headers"))

            response = client.request(example["method"], example["path"], headers=example.get("headers"))
            assert response.status_code == example["status"], example["name"]

            if "expected" in example:
                assert response.json() == example["expected"], example["name"]
            if "expected_text" in example:
                assert response.text == example["expected_text"], example["name"]

            schema = _resolve_response_schema(example.get("openapi_path", example["path"]), example["method"], example["status"])
            if schema:
                _assert_matches_schema(response.json(), schema)

            for key in example.get("must_include", []):
                assert key in response.json(), example["name"]
