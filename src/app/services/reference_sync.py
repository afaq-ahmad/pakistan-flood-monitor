from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import shutil


@dataclass(slots=True)
class SyncResult:
    layer_name: str
    version: str
    source_date: str
    output_path: Path
    changed: bool


class ReferenceSyncJob:
    """Idempotent file-based sync job for static reference layers."""

    def __init__(self, destination_root: str | Path) -> None:
        self._destination_root = Path(destination_root)
        self._destination_root.mkdir(parents=True, exist_ok=True)

    def sync_layer(self, *, layer_name: str, source_path: str | Path, version: str, source_date: str) -> SyncResult:
        source = Path(source_path)
        layer_dir = self._destination_root / layer_name / version
        layer_dir.mkdir(parents=True, exist_ok=True)
        destination = layer_dir / source.name
        marker = layer_dir / "metadata.txt"

        changed = True
        if destination.exists() and marker.exists():
            existing_metadata = marker.read_text()
            expected_prefix = self._metadata_prefix(layer_name=layer_name, version=version, source_date=source_date)
            if existing_metadata.startswith(expected_prefix) and destination.read_bytes() == source.read_bytes():
                changed = False

        if changed:
            shutil.copy2(source, destination)
            marker.write_text(self._metadata_text(layer_name=layer_name, version=version, source_date=source_date))

        return SyncResult(
            layer_name=layer_name,
            version=version,
            source_date=source_date,
            output_path=destination,
            changed=changed,
        )

    @staticmethod
    def _metadata_prefix(*, layer_name: str, version: str, source_date: str) -> str:
        return f"layer={layer_name}\nversion={version}\nsource_date={source_date}\n"

    @classmethod
    def _metadata_text(cls, *, layer_name: str, version: str, source_date: str) -> str:
        synced_at = datetime.now(UTC).isoformat()
        return cls._metadata_prefix(layer_name=layer_name, version=version, source_date=source_date) + f"synced_at={synced_at}\n"


class ReferenceSyncSuite:
    def __init__(self, job: ReferenceSyncJob) -> None:
        self._job = job

    def run_dem_sync(self, source_path: str | Path, *, version: str, source_date: str) -> SyncResult:
        return self._job.sync_layer(layer_name="dem", source_path=source_path, version=version, source_date=source_date)

    def run_water_mask_sync(self, source_path: str | Path, *, version: str, source_date: str) -> SyncResult:
        return self._job.sync_layer(
            layer_name="water_mask", source_path=source_path, version=version, source_date=source_date
        )

    def run_exposure_sync(self, source_path: str | Path, *, version: str, source_date: str) -> SyncResult:
        return self._job.sync_layer(
            layer_name="exposure", source_path=source_path, version=version, source_date=source_date
        )
