from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from pakistan_flood_monitor.api import main


ROOT = Path(__file__).resolve().parents[1]
PAGE = next((ROOT / "pages").glob("3_*")).relative_to(ROOT)


@pytest.fixture
def demo_reports(monkeypatch, tmp_path):
    import backend_service

    monkeypatch.setattr(backend_service, "API_BASE_URL", None)
    monkeypatch.setattr(backend_service, "_APP_MODE", "demo")
    monkeypatch.setattr(backend_service, "DATA_DIR", tmp_path)
    path = tmp_path / "field_reports.csv"
    pd.DataFrame([{
        "report_id": "demo-report",
        "event_id": "demo-event",
        "observed_at": "2026-01-02T10:00:00Z",
        "latitude": 28.0,
        "longitude": 69.0,
        "reporter_channel": "fixture",
        "status": "submitted",
        "trusted": False,
        "moderation_tags": "",
        "notes": "synthetic demo note",
    }]).to_csv(path, index=False)
    return backend_service, path


def _page():
    return AppTest.from_file(ROOT / "streamlit_app.py").switch_page(str(PAGE)).run()


@pytest.mark.parametrize("mode,api", [
    ("operational", None),
    ("operational", "http://fixture.test"),
    ("demo", "http://fixture.test"),
])
def test_non_demo_field_reports_do_not_load_or_moderate_csv(demo_reports, monkeypatch, mode, api):
    backend, path = demo_reports
    original = path.read_bytes()
    monkeypatch.setattr(backend, "_APP_MODE", mode)
    monkeypatch.setattr(backend, "API_BASE_URL", api)
    reads = []
    load = backend.DataService._load

    def count_reads(service, name):
        reads.append(name)
        return load(service, name)

    monkeypatch.setattr(backend.DataService, "_load", count_reads)
    page = _page()
    assert not page.exception
    assert any("Field report moderation is unavailable" in item.value for item in page.info)
    assert any("Resident report submission is unavailable" in item.value for item in page.info)
    assert not page.metric
    assert not page.expander
    assert not page.button
    assert backend.data_service.get_field_reports().empty
    assert backend.data_service.moderate_report("demo-report", "approved") is False
    assert not reads
    assert path.read_bytes() == original


@pytest.mark.parametrize("action", ["approve", "reject", "spam"])
def test_declined_demo_moderation_has_visible_failure(demo_reports, monkeypatch, action):
    backend, path = demo_reports
    original = path.read_bytes()
    monkeypatch.setattr(backend.data_service, "moderate_report", lambda *args: False)
    page = _page().button(key=f"mod_{action}_demo-report").click().run()
    assert not page.exception
    assert any("could not be saved" in item.value for item in page.error)
    assert not page.success
    assert path.read_bytes() == original


def test_successful_demo_moderation_survives_rerender(demo_reports):
    _, path = demo_reports
    page = _page().button(key="mod_approve_demo-report").click().run()
    assert not page.exception
    assert any("SIMULATED / DEMO DATA" in item.value for item in page.warning)
    assert any("Demo report updated" in item.value for item in page.success)
    assert any("Status: approved" in item.label for item in page.expander)
    assert pd.read_csv(path).iloc[0]["status"] == "approved"


def test_partial_csv_write_failure_preserves_previous_demo_report(demo_reports, monkeypatch):
    backend, path = demo_reports
    original = path.read_bytes()

    def fail_write(frame, target, **kwargs):
        if hasattr(target, "write"):
            target.write("incomplete fixture")
        else:
            Path(target).write_text("incomplete fixture", encoding="utf-8")
        raise OSError("injected write failure")

    monkeypatch.setattr(pd.DataFrame, "to_csv", fail_write)
    assert backend.data_service.moderate_report("demo-report", "approved") is False
    assert path.read_bytes() == original
    assert list(path.parent.iterdir()) == [path]


def test_moderation_rejects_missing_and_stale_demo_actions(demo_reports):
    backend, path = demo_reports
    original = path.read_bytes()
    assert backend.data_service.moderate_report("missing", "approved") is False
    assert backend.data_service.moderate_report("demo-report", "verified") is False
    assert path.read_bytes() == original
    assert backend.data_service.moderate_report("demo-report", "approved") is True
    approved = path.read_bytes()
    assert backend.data_service.moderate_report("demo-report", "rejected") is False
    assert path.read_bytes() == approved


@pytest.mark.parametrize("contents", ["", "report_id,status\ndemo-report,submitted\n"])
def test_unreadable_or_incomplete_demo_data_reports_unavailable(demo_reports, contents):
    _, path = demo_reports
    path.write_text(contents, encoding="utf-8")
    page = _page()
    assert not page.exception
    assert any("Demo field reports are unavailable" in item.value for item in page.info)
    assert [button.key for button in page.button] == ["sub_submit_btn"]


@pytest.fixture
def report_api(monkeypatch):
    monkeypatch.setattr(main, "event_store", {
        event_id: {"event_id": event_id, "status": "draft"}
        for event_id in ("fixture-event", "another-fixture-event")
    })
    monkeypatch.setattr(main, "field_reports", {})
    for role in ("analyst", "reviewer"):
        monkeypatch.setenv(f"FLOOD_MONITOR_{role.upper()}_TOKEN", f"fixture-{role}")
    return {
        "event_id": "fixture-event",
        "observed_at": "2026-01-02T10:00:00Z",
        "location": {"lat": 28.0, "lon": 69.0},
        "reporter_metadata": {},
        "notes": "private synthetic fixture",
        "client_report_id": "fixture-receipt",
    }


def _submit(client, body, role="analyst"):
    return client.post("/internal/reports/field", json=body, headers={"Authorization": f"Bearer fixture-{role}"})


@pytest.mark.parametrize("role,event", [
    ("reviewer", "fixture-event"),
    ("analyst", "another-fixture-event"),
])
def test_duplicate_receipt_conflict_omits_prior_payload(report_api, role, event):
    with TestClient(main.app) as client:
        accepted = _submit(client, report_api)
        assert accepted.status_code == 200
        conflict = _submit(client, {**report_api, "event_id": event, "notes": ""}, role)
        assert conflict.status_code == 409
        assert conflict.json() == {"detail": "Report receipt conflicts with an existing submission."}
        assert "private synthetic fixture" not in conflict.text
        assert len(main.field_reports) == 1

        replay = _submit(client, report_api)
        assert replay.status_code == 200
        assert replay.json()["status"] == "accepted_duplicate"
        assert replay.json()["report"]["report_id"] == accepted.json()["report"]["report_id"]
        assert len(main.event_store["fixture-event"]["linked_field_reports"]) == 1


def test_concurrent_retries_link_one_process_local_report(report_api):
    def submit(_):
        with TestClient(main.app) as client:
            response = _submit(client, report_api)
        assert response.status_code == 200
        return response.json()["status"]

    with ThreadPoolExecutor(max_workers=3) as pool:
        outcomes = list(pool.map(submit, range(3)))

    assert outcomes.count("accepted") == 1
    assert outcomes.count("accepted_duplicate") == 2
    assert len(main.field_reports) == 1
    event = main.event_store["fixture-event"]
    assert len(event["linked_field_reports"]) == 1
    assert event["field_report_summary"]["total_count"] == 1


def test_canonical_moderation_checks_role_and_current_state(report_api, monkeypatch):
    monkeypatch.setattr(main, "field_report_audit_log", [])
    with TestClient(main.app) as client:
        accepted = _submit(client, report_api)
        report = accepted.json()["report"]
        endpoint = f"/internal/field-reports/{report['report_id']}/moderate"
        request = {"action": "approve", "reason": "fixture review", "trusted": True}
        assert client.post(endpoint, json=request).status_code == 401
        reviewer = {"Authorization": "Bearer fixture-reviewer"}
        assert client.post(endpoint, json=request, headers=reviewer).status_code == 403
        assert main.field_reports[report["report_id"]]["status"] == "submitted"
        assert not main.field_report_audit_log

        analyst = {"Authorization": "Bearer fixture-analyst"}
        assert client.post(endpoint, json=request, headers=analyst).status_code == 200
        assert client.post(endpoint, json=request, headers=analyst).status_code == 400
        assert main.field_reports[report["report_id"]]["status"] == "approved"
        assert len(main.field_report_audit_log) == 1
