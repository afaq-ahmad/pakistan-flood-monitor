from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.schemas.dashboard import DashboardViewResponse, SnapshotRecord, SnapshotRequest
from app.services.dashboard import dashboard_service

router = APIRouter()


@router.get("/summary")
def analytics_summary() -> dict[str, int]:
    events = dashboard_service.list_events()
    return {
        "active_events": len([event for event in events if event.status == "active"]),
        "published_events": len([event for event in events if event.status == "published"]),
    }


@router.get("/dashboard/views/{corridor_id}", response_model=DashboardViewResponse)
def dashboard_view(corridor_id: str) -> dict:
    return dashboard_service.dashboard_view(corridor_id)


@router.get("/map/events")
def map_event_layer(
    corridor_id: str | None = None,
    simplify_tolerance: float = Query(default=0.005, ge=0.0, le=0.05),
) -> dict:
    return dashboard_service.map_ready_event_layer(corridor_id=corridor_id, simplify_tolerance=simplify_tolerance)


@router.get("/map/corridors")
def map_corridor_layer(corridor_id: str | None = None) -> dict:
    try:
        return dashboard_service.map_ready_corridor_layer(corridor_id=corridor_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown corridor: {corridor_id}") from exc


@router.post("/snapshots/precompute", response_model=list[SnapshotRecord])
def precompute_snapshots(payload: SnapshotRequest) -> list[dict]:
    return dashboard_service.precompute_snapshots(event_ids=payload.event_ids)


@router.get("/snapshots/{event_id}")
def get_snapshot(event_id: str) -> FileResponse:
    path = dashboard_service.snapshot_path(event_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Snapshot not found for event: {event_id}")
    return FileResponse(path, media_type="image/png", filename=f"{event_id}.png")
