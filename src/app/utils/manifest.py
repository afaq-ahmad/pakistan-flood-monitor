from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import rasterio


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _raster_stats(path: Path) -> dict[str, Any]:
    with rasterio.open(path) as dataset:
        band_stats: list[dict[str, float | int]] = []
        stats = dataset.stats()
        for index, stat in enumerate(stats, start=1):
            band_stats.append({"band": index, "min": float(stat.min), "max": float(stat.max)})
        return {
            "crs": str(dataset.crs) if dataset.crs else None,
            "extent": [dataset.bounds.left, dataset.bounds.bottom, dataset.bounds.right, dataset.bounds.top],
            "statistics": band_stats,
        }


def build_run_manifest(
    *,
    run_id: str,
    run_type: str,
    software_version: str,
    source_files: list[Path],
    output_files: list[Path],
) -> dict[str, Any]:
    def file_entry(path: Path) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        if path.suffix.lower() in {".tif", ".tiff"}:
            entry.update(_raster_stats(path))
        return entry

    return {
        "run_id": run_id,
        "run_type": run_type,
        "software_version": software_version,
        "generated_at": datetime.now(UTC).isoformat(),
        "source_files": [file_entry(path) for path in source_files],
        "output_files": [file_entry(path) for path in output_files],
    }


def write_run_manifest(manifest: dict[str, Any], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return destination
