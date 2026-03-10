from fastapi.testclient import TestClient

from app.api.main import app


def test_dashboard_view_and_map_layers() -> None:
    client = TestClient(app)

    view_response = client.get('/analytics/dashboard/views/Indus-Lower')
    assert view_response.status_code == 200
    payload = view_response.json()
    assert payload['corridor_id'] == 'Indus-Lower'
    assert payload['active_events'] >= 1
    assert payload['recent_events']

    events_layer = client.get('/analytics/map/events?corridor_id=Indus-Lower&simplify_tolerance=0.004')
    assert events_layer.status_code == 200
    layer_payload = events_layer.json()
    assert layer_payload['type'] == 'FeatureCollection'
    assert all(feature['properties']['corridor_id'] == 'Indus-Lower' for feature in layer_payload['features'])

    corridor_layer = client.get('/analytics/map/corridors?corridor_id=Indus-Lower')
    assert corridor_layer.status_code == 200
    assert corridor_layer.json()['features'][0]['id'] == 'Indus-Lower'


def test_snapshot_precompute_and_download() -> None:
    client = TestClient(app)

    precompute_response = client.post('/analytics/snapshots/precompute', json={'event_ids': ['evt-indus-001']})
    assert precompute_response.status_code == 200
    records = precompute_response.json()
    assert records[0]['event_id'] == 'evt-indus-001'

    snapshot_response = client.get('/analytics/snapshots/evt-indus-001')
    assert snapshot_response.status_code == 200
    assert snapshot_response.headers['content-type'] == 'image/png'
    assert snapshot_response.content.startswith(b'\x89PNG')
