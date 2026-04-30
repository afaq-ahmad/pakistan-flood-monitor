from __future__ import annotations

from app.services.exposure import AssetLayer, ExposureComputationService, ExposureRequest, OverlayFeature


def _poly(minx: float, miny: float, maxx: float, maxy: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[[minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny]]],
    }


def test_route_constraints_and_shelter_proximity_are_emitted_in_district_report() -> None:
    service = ExposureComputationService()
    result = service.compute(
        ExposureRequest(
            event_id=99,
            review_status="accepted",
            machine_status="weak",
            reviewed_geometry=_poly(0, 0, 1, 1),
            machine_geometry=_poly(0, 0, 1, 1),
            corridor_geometry=_poly(0, 0, 2, 2),
            district_boundaries=[OverlayFeature("d1", _poly(0, 0, 1.5, 1.5), {"name": "District 1"})],
            asset_layers=[
                AssetLayer(
                    "roads",
                    "line",
                    [OverlayFeature("r1", {"type": "LineString", "coordinates": [[0.2, 0.2], [1.2, 0.2]]}, {"evacuation_priority": True})],
                ),
                AssetLayer(
                    "shelters",
                    "point",
                    [
                        OverlayFeature("s1", {"type": "Point", "coordinates": [0.5, 0.5]}, {}),
                        OverlayFeature("s2", {"type": "Point", "coordinates": [1.1, 1.1]}, {}),
                    ],
                    max_distance_m=1000,
                ),
            ],
        )
    )

    district = result.summary_blob["districts"][0]
    assert district["route_constraints"]["impacted_road_km"] > 0
    assert district["route_constraints"]["routing_blocked"] is True
    assert district["shelter_proximity"]["shelters_in_flood_zone"] == 1
    assert district["shelter_proximity"]["safe_shelters_within_threshold"] == 1
    assert district["shelter_proximity"]["nearest_safe_shelter_m"] is not None


def test_shelter_proximity_handles_missing_safe_shelters() -> None:
    service = ExposureComputationService()
    result = service.compute(
        ExposureRequest(
            event_id=100,
            review_status="accepted",
            machine_status="weak",
            reviewed_geometry=_poly(0, 0, 1, 1),
            machine_geometry=_poly(0, 0, 1, 1),
            corridor_geometry=_poly(0, 0, 1, 1),
            district_boundaries=[OverlayFeature("d1", _poly(0, 0, 1, 1), {})],
            asset_layers=[
                AssetLayer(
                    "shelters",
                    "point",
                    [OverlayFeature("s1", {"type": "Point", "coordinates": [0.5, 0.5]}, {})],
                    max_distance_m=500,
                )
            ],
        )
    )

    district = result.summary_blob["districts"][0]
    assert district["shelter_proximity"]["nearest_safe_shelter_m"] is None
    assert district["shelter_proximity"]["safe_shelters_within_threshold"] == 0
