from __future__ import annotations

from pakistan_flood_monitor.services.gis_qa import publication_gate


def _valid_event() -> dict:
    return {
        "event_class": "flood",
        "source_scenes": ["S1-A"],
        "notes": "validated",
        "timestamps": {"detected_at": "2026-01-01T00:00:00+00:00"},
        "district_overlays": ["Dadu"],
        "geometry": {
            "type": "Polygon",
            "crs": "EPSG:4326",
            "coordinates": [
                [
                    [67.0, 24.0],
                    [67.1, 24.0],
                    [67.1, 24.1],
                    [67.0, 24.1],
                    [67.0, 24.0],
                    [67.0, 24.0],
                ]
            ],
        },
        "label_metadata": {
            "label_type": "flood_extent",
            "label_tier": "tier_1",
            "analyst": "analyst-1",
            "date": "2026-01-01T00:00:00+00:00",
            "notes": "manual review",
            "uncertainty": 0.3,
        },
        "mapping_rules": {
            "river_inclusion_exclusion": "include main channel",
            "cloud_limitation_notes": "none",
            "disconnected_pool_handling": "retain pools over threshold",
            "certainty_class": "high",
        },
    }


def test_publication_gate_passes_and_normalizes_geometry() -> None:
    event = _valid_event()
    result = publication_gate(event)

    assert result.passed is True
    assert result.errors == []
    assert result.normalized_geometry is not None
    assert len(result.normalized_geometry["coordinates"][0]) == 5


def test_publication_gate_fails_without_sop_metadata() -> None:
    event = _valid_event()
    event.pop("label_metadata")

    result = publication_gate(event)

    assert result.passed is False
    assert "Missing label_metadata for reviewed geometry." in result.errors
