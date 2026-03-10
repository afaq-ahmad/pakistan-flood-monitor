from __future__ import annotations

import pytest

from app.services.exposure import (
    AssetLayer,
    ExposureComputationService,
    ExposureRequest,
    OverlayFeature,
    should_trigger_exposure,
)


def _poly(minx: float, miny: float, maxx: float, maxy: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[[minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny]]],
    }


def test_trigger_only_for_accepted_or_strong_status() -> None:
    assert should_trigger_exposure(review_status="accepted", machine_status="weak") is True
    assert should_trigger_exposure(review_status="queued", machine_status="strong") is True
    assert should_trigger_exposure(review_status="queued", machine_status="weak") is False


def test_exposure_uses_reviewed_geometry_and_generates_district_rank_asset_metrics() -> None:
    service = ExposureComputationService()
    districts = [
        OverlayFeature("d1", _poly(0, 0, 1, 2), {"name": "District 1"}),
        OverlayFeature("d2", _poly(1, 0, 2, 2), {"name": "District 2"}),
    ]
    layers = [
        AssetLayer("roads", "line", [OverlayFeature("r1", {"type": "LineString", "coordinates": [[0, 1], [2, 1]]}, {})]),
        AssetLayer("settlements", "polygon", [OverlayFeature("s1", _poly(0.0, 0.0, 1.0, 1.0), {})]),
        AssetLayer("cropland", "polygon", [OverlayFeature("c1", _poly(1.0, 1.0, 2.0, 2.0), {})]),
        AssetLayer(
            "facilities",
            "point",
            [
                OverlayFeature("f1", {"type": "Point", "coordinates": [0.25, 0.25]}, {}),
                OverlayFeature("f2", {"type": "Point", "coordinates": [1.75, 1.75]}, {}),
            ],
        ),
        AssetLayer("population", "population", [OverlayFeature("p1", _poly(0, 0, 2, 2), {"pop": 1000})], value_field="pop"),
    ]

    result = service.compute(
        ExposureRequest(
            event_id=9,
            review_status="accepted",
            machine_status="weak",
            reviewed_geometry=_poly(0, 0, 1.5, 2),
            machine_geometry=_poly(0, 0, 1.0, 2),
            corridor_geometry=_poly(0, 0, 2, 2),
            district_boundaries=districts,
            asset_layers=layers,
            cloud_limited=False,
        )
    )

    assert result.geometry_source == "reviewed"
    assert result.provisional_geometry is False
    assert result.uncertainty_flag is False

    district_summary = result.summary_blob["districts"]
    assert district_summary[0]["district_id"] == "d1"
    assert district_summary[0]["impact_rank"] == 1
    assert district_summary[1]["district_id"] == "d2"
    assert district_summary[1]["impact_rank"] == 2

    # reviewed geometry covers 75% of district d2 so it should have non-zero population and cropland exposure
    assert result.summary_blob["assets"]["d2"]["population"]["estimated_population_exposed"] > 0
    assert result.summary_blob["assets"]["d2"]["cropland"]["exposed_area_sqkm"] > 0

    # d1 has one facility point inside; d2 facility is outside reviewed extent
    assert result.summary_blob["assets"]["d1"]["facilities"]["exposed_count"] == 1.0
    assert result.summary_blob["assets"]["d2"]["facilities"]["exposed_count"] == 0.0


def test_exposure_falls_back_to_machine_geometry_and_marks_uncertainty() -> None:
    service = ExposureComputationService()
    result = service.compute(
        ExposureRequest(
            event_id=10,
            review_status="unreviewed",
            machine_status="strong",
            reviewed_geometry=None,
            machine_geometry=_poly(0, 0, 1, 1),
            corridor_geometry=_poly(0, 0, 2, 2),
            district_boundaries=[OverlayFeature("d1", _poly(0, 0, 1, 1), {})],
            asset_layers=[],
            cloud_limited=True,
        )
    )

    assert result.geometry_source == "machine_provisional"
    assert result.provisional_geometry is True
    assert result.uncertainty_flag is True


def test_exposure_rejects_non_triggering_status() -> None:
    service = ExposureComputationService()
    with pytest.raises(ValueError, match="allowed only"):
        service.compute(
            ExposureRequest(
                event_id=12,
                review_status="queued",
                machine_status="weak",
                reviewed_geometry=None,
                machine_geometry=_poly(0, 0, 1, 1),
                corridor_geometry=_poly(0, 0, 1, 1),
                district_boundaries=[OverlayFeature("d", _poly(0, 0, 1, 1), {})],
                asset_layers=[],
            )
        )
