from __future__ import annotations

from app.schemas.monitoring import SceneDiscoveryRequest
from app.services.ingestion import InMemorySceneRepository, InMemoryTaskQueue, STACDiscoveryService


class EmptyProvider:
    name = "stac"

    def search(self, corridor_geometry: dict, start_time, end_time):
        return []


def discover_scenes(request: SceneDiscoveryRequest) -> dict:
    service = STACDiscoveryService(
        providers=[EmptyProvider()],
        scene_repository=InMemorySceneRepository(),
        task_queue=InMemoryTaskQueue(),
    )
    summary = service.discover(
        corridor_id=request.corridor_id,
        corridor_geometry={"type": "Polygon", "coordinates": []},
        start_time=request.start_time,
        end_time=request.end_time,
    )
    return {
        "corridor_id": request.corridor_id,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "status": "queued",
        "discovered": summary.discovered,
        "inserted": summary.inserted,
    }
