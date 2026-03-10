from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings
from app.utils import FileNameFactory, StorageLayout, build_run_manifest, write_run_manifest


def _storage_layout() -> StorageLayout:
    settings = get_settings()
    return StorageLayout(
        raw_root=settings.storage_raw_root,
        prepared_root=settings.storage_prepared_root,
        derived_root=settings.storage_derived_root,
        published_root=settings.storage_published_root,
    )


def discover_scenes_pipeline() -> str:
    return "discover-scenes:started"


def fetch_hydromet_pipeline() -> str:
    return "fetch-hydromet:started"


def preprocess_sar_pipeline() -> str:
    return "preprocess-sar:started"


def task_planner_pipeline() -> str:
    return "task-planner:started"


def detect_flood_pipeline() -> str:
    return "detect-flood:started"


def detect_breach_pipeline() -> str:
    return "detect-breach:started"


def compute_exposure_pipeline() -> str:
    return "compute-exposure:started"


def publish_events_pipeline() -> str:
    return "publish-events:started"


def write_processing_manifest(
    *,
    corridor_id: str,
    run_type: str,
    run_id: str,
    source_files: list[Path],
    output_files: list[Path],
    software_version: str,
) -> Path:
    layout = _storage_layout()
    run_date = datetime.now(UTC).date()
    run_dir = layout.derived_run_dir(corridor_id=corridor_id, run_type=run_type, run_date=run_date, run_id=run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    default_name = FileNameFactory.exposure_summary()
    if output_files:
        manifest_name = f"{Path(default_name).stem}_manifest.json"
    else:
        manifest_name = "run_manifest.json"

    manifest = build_run_manifest(
        run_id=run_id,
        run_type=run_type,
        software_version=software_version,
        source_files=source_files,
        output_files=output_files,
    )
    return write_run_manifest(manifest, run_dir / manifest_name)
