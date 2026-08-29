from datetime import UTC, datetime, timedelta

import pytest
from shapely.geometry import LineString, Point, Polygon

from pakistan_flood_monitor.geo.measurements import (
    area_sqkm,
    buffer_m,
    distance_m,
    intersection_area_sqkm,
    length_km,
    local_metric_crs,
)
from pakistan_flood_monitor.models.observations import SourceAvailabilityStatus
from pakistan_flood_monitor.models.product_metadata import (
    AssetReference,
    AssetStage,
    FreshnessPolicy,
    FreshnessPolicyRegistry,
    FreshnessStatus,
    ProcessingMetadata,
    ProductMetadata,
    QualityGrade,
    SourceIdentity,
    TemporalMetadata,
)


def _pakistan_square() -> Polygon:
    return Polygon([(70.0, 30.0), (70.1, 30.0), (70.1, 30.1), (70.0, 30.1)])


def test_geodesic_measurements_are_plausible_at_pakistan_latitudes() -> None:
    square = _pakistan_square()
    east_west_degree = LineString([(70.0, 30.0), (71.0, 30.0)])

    assert 105.0 < area_sqkm(square) < 110.0
    assert 96.0 < length_km(east_west_degree) < 97.0
    assert 96_000.0 < distance_m(Point(70.0, 30.0), Point(71.0, 30.0)) < 97_000.0
    assert 52.0 < intersection_area_sqkm(square, Polygon([(70.05, 30.0), (70.1, 30.0), (70.1, 30.1), (70.05, 30.1)])) < 55.0
    assert area_sqkm(buffer_m(Point(70.0, 30.0), 1_000)) == pytest.approx(3.14, rel=0.03)
    assert local_metric_crs(square).is_projected


def test_product_metadata_composes_lineage_asset_quality_and_freshness() -> None:
    checked_at = datetime(2026, 8, 29, tzinfo=UTC)
    freshness = FreshnessPolicyRegistry(
        policies={"sar": FreshnessPolicy(product_family="sar", current_max_age_hours=24, aging_max_age_hours=72)}
    ).assess("sar", checked_at - timedelta(hours=30), evaluated_at=checked_at)

    metadata = ProductMetadata(
        source=SourceIdentity(provider="copernicus", item_id="S1A-test", uri="https://example.test/item"),
        temporal=TemporalMetadata(acquired_at=checked_at - timedelta(hours=30), processed_at=checked_at),
        processing=ProcessingMetadata(processing_version="sar-preprocess-v1", threshold_version="flood-v1"),
        runtime_mode="operational",
        quality=QualityGrade.B,
        data_state=SourceAvailabilityStatus.AVAILABLE,
        freshness=freshness,
        assets=[
            AssetReference(
                href="s3://bucket/raw/vv.tif",
                stage=AssetStage.RAW,
                checksum_sha256="a" * 64,
            )
        ],
    )

    assert metadata.freshness is not None
    assert metadata.freshness.status is FreshnessStatus.AGING
    assert metadata.assets[0].stage is AssetStage.RAW
    assert metadata.assets[0].checksum_sha256 == "a" * 64
