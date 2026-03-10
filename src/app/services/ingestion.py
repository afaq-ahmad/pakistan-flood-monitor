from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Iterable, Protocol

from shapely.geometry import shape

from app.services.observability import log_failure, log_structured, metrics_registry


@dataclass(slots=True)
class SceneAsset:
    href: str
    role: str


@dataclass(slots=True)
class NormalizedScene:
    provider: str
    sensor: str
    scene_id: str
    acquisition_time: datetime
    geometry: dict
    asset_urls: dict[str, str]
    polarizations: list[str] = field(default_factory=list)
    available_bands: list[str] = field(default_factory=list)
    cloud_cover: float | None = None


@dataclass(slots=True)
class SceneDiscoverySummary:
    discovered: int
    inserted: int
    queued: int
    skipped: int


@dataclass(slots=True)
class EnqueuedTask:
    task_type: str
    payload: dict


class SceneProvider(Protocol):
    name: str

    def search(self, corridor_geometry: dict, start_time: datetime, end_time: datetime) -> Iterable[dict]:
        ...


class SceneRepository(Protocol):
    def has_scene(self, scene_id: str) -> bool:
        ...

    def has_processed_overlap(self, corridor_id: str, scene: NormalizedScene, overlap_threshold: float) -> bool:
        ...

    def insert_scene(self, corridor_id: str, scene: NormalizedScene, intersection_area_sqkm: float) -> int:
        ...


class TaskQueue(Protocol):
    def enqueue(self, task_type: str, payload: dict) -> None:
        ...


class STACDiscoveryService:
    """Event-driven, metadata-first corridor scene discovery."""

    def __init__(
        self,
        providers: Iterable[SceneProvider],
        scene_repository: SceneRepository,
        task_queue: TaskQueue,
        *,
        min_intersection_area_sqkm: float = 5.0,
        watch_window_hours: int = 240,
    ) -> None:
        self._providers = list(providers)
        self._scene_repository = scene_repository
        self._task_queue = task_queue
        self._min_intersection_area_sqkm = min_intersection_area_sqkm
        self._watch_window = timedelta(hours=watch_window_hours)

    def discover(
        self,
        *,
        corridor_id: str,
        corridor_geometry: dict,
        start_time: datetime,
        end_time: datetime,
        now: datetime | None = None,
    ) -> SceneDiscoverySummary:
        discovered = 0
        inserted = 0
        queued = 0
        skipped = 0
        failure_count = 0
        now = now or datetime.now(UTC)

        corridor_shape = shape(corridor_geometry)
        run_id = f"discover-{corridor_id}-{int(now.timestamp())}"
        end_timing = metrics_registry.time_block("pipeline.processing_latency_ms")

        for provider in self._providers:
            for item in provider.search(corridor_geometry, start_time, end_time):
                discovered += 1
                metrics_registry.increment("pipeline.discovery_count")
                checkpoint = "normalize_item"
                scene_id = str(item.get("id") or item.get("properties", {}).get("scene_id") or "unknown")
                started = datetime.now(UTC)
                try:
                    scene = self._normalize_item(provider.name, item)
                    checkpoint = "intersection_filter"
                    intersection_area_sqkm = self._intersection_area_sqkm(corridor_shape, shape(scene.geometry))

                    if self._should_skip(
                        corridor_id=corridor_id,
                        scene=scene,
                        intersection_area_sqkm=intersection_area_sqkm,
                        now=now,
                    ):
                        skipped += 1
                        continue

                    checkpoint = "persist_scene"
                    scene_row_id = self._scene_repository.insert_scene(corridor_id, scene, intersection_area_sqkm)
                    inserted += 1
                    checkpoint = "enqueue_candidate"
                    self._task_queue.enqueue(
                        "scene-processing-candidate",
                        {
                            "scene_row_id": scene_row_id,
                            "scene_id": scene.scene_id,
                            "sensor": scene.sensor,
                            "corridor_id": corridor_id,
                            "acquisition_time": scene.acquisition_time.isoformat(),
                        },
                    )
                    queued += 1
                    metrics_registry.increment("pipeline.candidates_created")
                    log_structured(
                        "scene_discovery_item",
                        run_id=run_id,
                        corridor_id=corridor_id,
                        scene_id=scene.scene_id,
                        task_type="discover_scene",
                        provider=provider.name,
                        duration_ms=(datetime.now(UTC) - started).total_seconds() * 1000,
                        success=True,
                        output_paths=[f"queue://scene-processing-candidate/{scene_row_id}"],
                    )
                except Exception as exc:
                    failure_count += 1
                    metrics_registry.increment("pipeline.download_failures")
                    log_failure(
                        "scene_discovery_item",
                        error=exc,
                        run_id=run_id,
                        corridor_id=corridor_id,
                        scene_id=scene_id,
                        task_type="discover_scene",
                        pipeline_stage="discovery",
                        last_completed_checkpoint=checkpoint,
                        input_identifiers={"provider": provider.name, "scene_id": scene_id},
                        duration_ms=(datetime.now(UTC) - started).total_seconds() * 1000,
                        output_paths=[],
                    )

        total_latency = end_timing()
        metrics_registry.increment("pipeline.aois_processed")
        metrics_registry.observe_latency_ms("ops.response_latency_ms", total_latency)
        metrics_registry.set_gauge("ops.queue_backlog", float(len(getattr(self._task_queue, "tasks", []))))
        metrics_registry.set_gauge("ops.stale_job_count", 0.0)
        metrics_registry.update_disk_usage(".")

        log_structured(
            "scene_discovery_summary",
            run_id=run_id,
            corridor_id=corridor_id,
            scene_id=None,
            task_type="discover_scene_batch",
            duration_ms=total_latency,
            success=failure_count == 0,
            discovered=discovered,
            inserted=inserted,
            queued=queued,
            skipped=skipped,
            failures=failure_count,
            output_paths=["queue://scene-processing-candidate"],
        )
        return SceneDiscoverySummary(discovered=discovered, inserted=inserted, queued=queued, skipped=skipped)

    def _normalize_item(self, provider: str, item: dict) -> NormalizedScene:
        props = item.get("properties", {})
        assets = item.get("assets", {})

        sensor = (
            props.get("sensor")
            or props.get("platform")
            or props.get("constellation")
            or item.get("collection", "unknown")
        )
        acquisition_raw = props.get("datetime") or props.get("acquired") or props.get("start_datetime")
        acquisition_time = datetime.fromisoformat(str(acquisition_raw).replace("Z", "+00:00"))

        asset_urls = {name: details.get("href") for name, details in assets.items() if details.get("href")}

        return NormalizedScene(
            provider=provider,
            sensor=sensor,
            scene_id=item.get("id") or props.get("scene_id"),
            acquisition_time=acquisition_time,
            geometry=item.get("geometry"),
            asset_urls=asset_urls,
            polarizations=props.get("polarization") or props.get("sar:polarizations") or [],
            available_bands=props.get("bands") or props.get("eo:bands") or list(asset_urls.keys()),
            cloud_cover=props.get("cloud_cover") or props.get("eo:cloud_cover"),
        )

    @staticmethod
    def _intersection_area_sqkm(corridor_shape, scene_shape) -> float:
        # Shapely area in geographic coordinates is not exact, but adequate for lightweight filtering.
        intersection = corridor_shape.intersection(scene_shape)
        return max(0.0, float(intersection.area) * 12_321.0)

    def _should_skip(
        self,
        *,
        corridor_id: str,
        scene: NormalizedScene,
        intersection_area_sqkm: float,
        now: datetime,
    ) -> bool:
        if self._scene_repository.has_scene(scene.scene_id):
            return True
        if intersection_area_sqkm < self._min_intersection_area_sqkm:
            return True
        if scene.acquisition_time < now - self._watch_window:
            return True
        return self._scene_repository.has_processed_overlap(
            corridor_id,
            scene,
            overlap_threshold=self._min_intersection_area_sqkm,
        )


class OpticalSceneDiscoveryService:
    """Corridor-aware optical discovery as a non-blocking enrichment feed."""

    _OPTICAL_SENSORS = ("sentinel-2", "landsat", "hls")

    def __init__(self, discovery_service: STACDiscoveryService) -> None:
        self._discovery_service = discovery_service

    def discover(
        self,
        *,
        corridor_id: str,
        corridor_geometry: dict,
        start_time: datetime,
        end_time: datetime,
        now: datetime | None = None,
    ) -> SceneDiscoverySummary:
        return self._discovery_service.discover(
            corridor_id=corridor_id,
            corridor_geometry=corridor_geometry,
            start_time=start_time,
            end_time=end_time,
            now=now,
        )

    def is_optical_scene(self, scene: NormalizedScene) -> bool:
        sensor = scene.sensor.lower()
        return any(marker in sensor for marker in self._OPTICAL_SENSORS)


class InMemorySceneRepository:
    def __init__(self) -> None:
        self._rows: list[dict] = []

    @property
    def rows(self) -> list[dict]:
        return self._rows

    def has_scene(self, scene_id: str) -> bool:
        return any(row["scene"].scene_id == scene_id for row in self._rows)

    def has_processed_overlap(self, corridor_id: str, scene: NormalizedScene, overlap_threshold: float) -> bool:
        scene_geom = shape(scene.geometry)
        for row in self._rows:
            if row["corridor_id"] != corridor_id:
                continue
            known_geom = shape(row["scene"].geometry)
            overlap_sqkm = float(known_geom.intersection(scene_geom).area) * 12_321.0
            if overlap_sqkm >= overlap_threshold:
                return True
        return False

    def insert_scene(self, corridor_id: str, scene: NormalizedScene, intersection_area_sqkm: float) -> int:
        row = {
            "id": len(self._rows) + 1,
            "corridor_id": corridor_id,
            "scene": scene,
            "intersection_area_sqkm": intersection_area_sqkm,
            "status": "discovered",
        }
        self._rows.append(row)
        return int(row["id"])


class InMemoryTaskQueue:
    def __init__(self) -> None:
        self.tasks: list[EnqueuedTask] = []

    def enqueue(self, task_type: str, payload: dict) -> None:
        self.tasks.append(EnqueuedTask(task_type=task_type, payload=payload))
