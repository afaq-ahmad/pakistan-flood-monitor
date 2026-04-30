import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from pakistan_flood_monitor.api.main import app, event_store, historical_event_library, model_registry, privileged_audit_log, retraining_decisions, review_audit_log, run_history, threshold_registry

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


def _lifecycle_transition(client: TestClient, event_id: str, action: str) -> None:
    response = client.post(f"/internal/admin/review-event?event_id={event_id}", json={"action": action}, headers=_analyst_headers())
    assert response.status_code == 200


def test_sitrep_export_contains_required_sections() -> None:
    _reset_state()
    client = TestClient(app)
    run_response = client.get('/internal/run/Indus-Lower', headers=_admin_headers())
    event_id = run_response.json()['published_outputs']['review_queue_event']['event_id']
    _lifecycle_transition(client, event_id, 'review')
    _lifecycle_transition(client, event_id, 'approved')

    response = client.post('/internal/admin/sitrep/export', headers=_analyst_headers())
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('application/pdf')
    assert b'Situation Report \\(SitRep\\)' in response.content
    for marker in [
        b'Section: Event Summary',
        b'Section: District/Tehsil Priorities',
        b'Section: Recommended Actions',
        b'Section: Exposure/Risk Summary',
        b'Section: Confidence and Limitations',
        b'Section: Contacts',
    ]:
        assert marker in response.content


def test_replay_scenarios_have_expected_outputs_and_checklists() -> None:
    base = Path('data/demo/scenario_replay')
    scenarios = sorted(base.glob('scenario_*.json'))
    assert len(scenarios) >= 2
    for scenario_path in scenarios:
        payload = json.loads(scenario_path.read_text())
        assert payload['synthetic_sample'] is True
        assert payload['expected_outputs']['status'] == 'approved'
        assert payload['expected_outputs']['risk_summary_count_min'] >= 2
        assert len(payload['expected_outputs']['sitrep_sections']) >= 6
        assert len(payload['checklist']) >= 4
