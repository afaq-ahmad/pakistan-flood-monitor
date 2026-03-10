from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.utils import FileNameFactory, StorageLayout, build_run_manifest, write_run_manifest


def test_storage_layout_paths_are_deterministic(tmp_path: Path) -> None:
    layout = StorageLayout(
        raw_root=tmp_path / "raw",
        prepared_root=tmp_path / "prepared",
        derived_root=tmp_path / "derived",
        published_root=tmp_path / "published",
    )

    assert layout.raw_scene_dir("S1", date(2026, 3, 10), "SCENE123") == tmp_path / "raw" / "s1" / "2026" / "03" / "SCENE123"
    assert layout.prepared_scene_dir("indus-lower", "S1", date(2026, 3, 10), "SCENE123") == (
        tmp_path / "prepared" / "indus-lower" / "s1" / "2026-03-10" / "SCENE123"
    )
    assert layout.derived_run_dir("indus-lower", "detect-flood", date(2026, 3, 10), "run-1") == (
        tmp_path / "derived" / "indus-lower" / "detect-flood" / "2026-03-10" / "run-1"
    )
    assert layout.published_event_dir("indus-lower", 42) == tmp_path / "published" / "indus-lower" / "42"


def test_standardized_filenames() -> None:
    assert FileNameFactory.sar_vv_prepared() == "sar_vv_prepared.tif"
    assert FileNameFactory.sar_vh_prepared() == "sar_vh_prepared.tif"
    assert FileNameFactory.flood_mask_raw() == "flood_mask_raw.tif"
    assert FileNameFactory.flood_mask_cleaned() == "flood_mask_cleaned.tif"
    assert FileNameFactory.flood_candidates() == "flood_candidates.parquet"
    assert FileNameFactory.breach_features() == "breach_features.parquet"
    assert FileNameFactory.exposure_summary() == "exposure_summary.json"


def test_manifest_includes_checksums_and_raster_metadata(tmp_path: Path) -> None:
    raster_path = tmp_path / "flood_mask_cleaned.tif"
    data = np.ones((1, 10, 10), dtype=np.float32)
    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(10, 10, 0.1, 0.1),
    ) as dataset:
        dataset.write(data)

    output_path = tmp_path / "exposure_summary.json"
    output_path.write_text('{"population_exposed": 1200}', encoding="utf-8")

    manifest = build_run_manifest(
        run_id="run-abc",
        run_type="detect-flood",
        software_version="0.1.0",
        source_files=[raster_path],
        output_files=[output_path],
    )

    manifest_path = write_run_manifest(manifest, tmp_path / "manifest.json")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert payload["run_id"] == "run-abc"
    assert payload["source_files"][0]["sha256"]
    assert payload["source_files"][0]["crs"] == "EPSG:4326"
    assert len(payload["source_files"][0]["statistics"]) == 1
