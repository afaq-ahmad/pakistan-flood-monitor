from __future__ import annotations

from datetime import datetime

from app.services.ingestion import InMemorySceneRepository, InMemoryTaskQueue, STACDiscoveryService


class StaticProvider:
    name = "demo-stac"

    def __init__(self, items: list[dict]) -> None:
        self._items = items

    def search(self, corridor_geometry: dict, start_time: datetime, end_time: datetime) -> list[dict]:
        return self._items


if __name__ == "__main__":
    corridor = {
        "type": "Polygon",
        "coordinates": [[[70.0, 30.0], [70.0, 31.0], [71.0, 31.0], [71.0, 30.0], [70.0, 30.0]]],
    }
    item = {
        "id": "S1A_TEST_SCENE",
        "collection": "sentinel-1",
        "geometry": corridor,
        "properties": {"datetime": datetime.utcnow().isoformat(), "sar:polarizations": ["VV", "VH"]},
        "assets": {"vv": {"href": "s3://example/vv.tif"}, "vh": {"href": "s3://example/vh.tif"}},
    }
    service = STACDiscoveryService(
        providers=[StaticProvider([item])],
        scene_repository=InMemorySceneRepository(),
        task_queue=InMemoryTaskQueue(),
    )
    result = service.discover(
        corridor_id="indus-lower",
        corridor_geometry=corridor,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
    )
    print(result)
