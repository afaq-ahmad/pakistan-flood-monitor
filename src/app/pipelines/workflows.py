"""Deprecated compatibility shims for the former string-only workflows.

Canonical callers must use ``pakistan_flood_monitor.workflow``. These shims
persist a typed degraded task rather than claiming that an unimplemented
processor has started successfully.
"""
from __future__ import annotations

import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pakistan_flood_monitor.workflow.flood_daily import run_unavailable_workflow_task


def _legacy_task(task_name: str) -> dict[str, Any]:
    warnings.warn(
        "app.pipelines is deprecated; use pakistan_flood_monitor.workflow instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return run_unavailable_workflow_task(task_name).as_dict()


def discover_scenes_pipeline() -> dict[str, Any]:
    return _legacy_task("discover_scenes")


def fetch_hydromet_pipeline() -> dict[str, Any]:
    return _legacy_task("fetch_hydromet")


def preprocess_sar_pipeline() -> dict[str, Any]:
    return _legacy_task("preprocess_sar")


def task_planner_pipeline() -> dict[str, Any]:
    return _legacy_task("task_planner")


def detect_flood_pipeline() -> dict[str, Any]:
    return _legacy_task("detect_flood")


def detect_breach_pipeline() -> dict[str, Any]:
    return _legacy_task("detect_breach")


def compute_exposure_pipeline() -> dict[str, Any]:
    return _legacy_task("compute_exposure")


def publish_events_pipeline() -> dict[str, Any]:
    return _legacy_task("publish_events")


def write_processing_manifest(
    *,
    corridor_id: str,
    run_type: str,
    run_id: str,
    source_files: list[Path],
    output_files: list[Path],
    software_version: str,
) -> Path:
    """Temporary compatibility wrapper retained for legacy analyst tooling."""
    from app.config import get_settings
    from app.utils import FileNameFactory, StorageLayout, build_run_manifest, write_run_manifest

    settings = get_settings()
    layout = StorageLayout(
        raw_root=settings.storage_raw_root,
        prepared_root=settings.storage_prepared_root,
        derived_root=settings.storage_derived_root,
        published_root=settings.storage_published_root,
    )
    run_dir = layout.derived_run_dir(
        corridor_id=corridor_id,
        run_type=run_type,
        run_date=datetime.now(UTC).date(),
        run_id=run_id,
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    default_name = FileNameFactory.exposure_summary()
    manifest_name = f"{Path(default_name).stem}_manifest.json" if output_files else "run_manifest.json"
    manifest = build_run_manifest(
        run_id=run_id,
        run_type=run_type,
        software_version=software_version,
        source_files=source_files,
        output_files=output_files,
    )
    return write_run_manifest(manifest, run_dir / manifest_name)
