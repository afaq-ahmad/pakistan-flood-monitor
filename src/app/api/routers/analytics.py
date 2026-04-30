from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.schemas.dashboard import (
    DashboardViewResponse,
    ExportRequest,
    ExportResponse,
    ReviewDashboardResponse,
    SnapshotRecord,
    SnapshotRequest,
)
from app.services.dashboard import dashboard_service
from app.services.export_center import export_center_service

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


@router.get("/dashboard/review", response_model=ReviewDashboardResponse)
def review_dashboard(
    corridor_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    event_class: str | None = Query(default=None, alias="class"),
    review_status: str | None = None,
    breach_suspicion_min: float | None = Query(default=None, ge=0.0, le=1.0),
    confidence_band: str | None = Query(default=None, pattern="^(low|medium|high)$"),
) -> dict:
    return dashboard_service.review_dashboard(
        corridor_id=corridor_id,
        date_from=date_from,
        date_to=date_to,
        event_class=event_class,
        review_status=review_status,
        breach_suspicion_min=breach_suspicion_min,
        confidence_band=confidence_band,
    )


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


@router.post("/exports", response_model=ExportResponse)
def create_export(payload: ExportRequest) -> dict:
    try:
        bundle = export_center_service.create_export(event_id=payload.event_id, export_format=payload.format)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "export_id": bundle.export_id,
        "event_id": bundle.event_id,
        "format": bundle.format,
        "output_path": str(bundle.output_path),
        "manifest_path": str(bundle.manifest_path),
        "validation": bundle.validation,
        "download_url": f"/analytics/exports/{bundle.export_id}/file",
        "manifest_url": f"/analytics/exports/{bundle.export_id}/manifest",
    }


@router.get("/exports/{export_id}/file")
def download_export(export_id: str) -> FileResponse:
    export_root = export_center_service._export_dir / export_id
    files = [item for item in export_root.iterdir() if item.is_file() and item.name != "manifest.json"]
    if not files:
        raise HTTPException(status_code=404, detail=f"Export not found: {export_id}")
    file_path = files[0]
    return FileResponse(file_path, filename=file_path.name)


@router.get("/exports/{export_id}/manifest")
def download_manifest(export_id: str) -> FileResponse:
    manifest = export_center_service._export_dir / export_id / "manifest.json"
    if not manifest.exists():
        raise HTTPException(status_code=404, detail=f"Manifest not found: {export_id}")
    return FileResponse(manifest, media_type="application/json", filename=f"{export_id}-manifest.json")
