from app.schemas.monitoring import SceneDiscoveryRequest


def discover_scenes(request: SceneDiscoveryRequest) -> dict:
    return {
        "corridor_id": request.corridor_id,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "status": "queued",
    }
