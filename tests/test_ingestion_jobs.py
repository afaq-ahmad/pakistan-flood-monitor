from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services.hydromet import (
    GloFASFetcher,
    HydrometIngestionJob,
    IMERGRainfallFetcher,
    InMemoryHydrometRepository,
    SequenceRainfallProvider,
    StaticGloFASProvider,
)
from app.services.ingestion import InMemorySceneRepository, InMemoryTaskQueue, STACDiscoveryService
from app.services.reference_sync import ReferenceSyncJob, ReferenceSyncSuite


def _square(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_lon, min_lat],
                [min_lon, max_lat],
                [max_lon, max_lat],
                [max_lon, min_lat],
                [min_lon, min_lat],
            ]
        ],
    }


class FakeProvider:
    def __init__(self, name: str, items: list[dict]) -> None:
        self.name = name
        self.items = items

    def search(self, corridor_geometry: dict, start_time: datetime, end_time: datetime) -> list[dict]:
        return self.items


def test_stac_discovery_normalizes_deduplicates_and_enqueues() -> None:
    now = datetime(2026, 1, 10, tzinfo=UTC)
    corridor = _square(70.0, 30.0, 71.0, 31.0)

    scene = {
        "id": "S1_SCENE_A",
        "collection": "sentinel-1",
        "geometry": _square(70.1, 30.1, 70.9, 30.9),
        "properties": {"datetime": "2026-01-09T06:00:00Z", "sar:polarizations": ["VV", "VH"]},
        "assets": {"vv": {"href": "s3://bucket/vv.tif"}},
    }

    service = STACDiscoveryService(
        providers=[FakeProvider("copernicus", [scene, scene])],
        scene_repository=InMemorySceneRepository(),
        task_queue=InMemoryTaskQueue(),
        min_intersection_area_sqkm=1.0,
        watch_window_hours=24 * 7,
    )

    summary = service.discover(
        corridor_id="indus-lower",
        corridor_geometry=corridor,
        start_time=now - timedelta(days=2),
        end_time=now,
        now=now,
    )

    assert summary.discovered == 2
    assert summary.inserted == 1
    assert summary.queued == 1
    assert summary.skipped == 1


def test_hydromet_ingestion_generates_summary_and_stress() -> None:
    rainfall_provider = SequenceRainfallProvider(
        {
            24: [4.0] * 24,
            72: [3.0] * 72,
            168: [2.0] * 168,
        }
    )
    repository = InMemoryHydrometRepository()
    job = HydrometIngestionJob(
        rainfall_fetcher=IMERGRainfallFetcher(rainfall_provider),
        glofas_fetcher=GloFASFetcher(StaticGloFASProvider(percentile=0.95)),
        repository=repository,
    )

    timestamp = datetime(2026, 1, 10, tzinfo=UTC)
    summary = job.run(
        corridor_id="indus-mid",
        corridor_geometry=_square(70.0, 30.0, 71.0, 31.0),
        timestamp=timestamp,
        baseline_7d_mm=200.0,
    )

    assert summary.rainfall_24h_mm == 96.0
    assert summary.warning_exceedance is True
    assert summary.stress_score > 0.5
    assert ("indus-mid", timestamp) in repository.records


def test_reference_sync_is_versioned_and_idempotent(tmp_path) -> None:
    source = tmp_path / "roads.geojson"
    source.write_text('{"type": "FeatureCollection", "features": []}')

    suite = ReferenceSyncSuite(ReferenceSyncJob(tmp_path / "reference"))
    first = suite.run_exposure_sync(source, version="2026.01", source_date="2026-01-03")
    second = suite.run_exposure_sync(source, version="2026.01", source_date="2026-01-03")

    assert first.output_path.exists()
    assert first.changed is True
    assert second.changed is False
