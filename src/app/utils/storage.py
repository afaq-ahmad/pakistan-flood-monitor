from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class StorageLayout:
    raw_root: Path
    prepared_root: Path
    derived_root: Path
    published_root: Path

    def raw_scene_dir(self, sensor: str, acquired_at: datetime | date, scene_id: str) -> Path:
        dt = acquired_at if isinstance(acquired_at, date) else acquired_at.date()
        return self.raw_root / sensor.lower() / f"{dt.year:04d}" / f"{dt.month:02d}" / scene_id

    def prepared_scene_dir(self, corridor_id: str, sensor: str, scene_date: date, scene_id: str) -> Path:
        return self.prepared_root / corridor_id / sensor.lower() / scene_date.isoformat() / scene_id

    def derived_run_dir(self, corridor_id: str, run_type: str, run_date: date, run_id: str) -> Path:
        return self.derived_root / corridor_id / run_type / run_date.isoformat() / run_id

    def published_event_dir(self, corridor_id: str, event_id: str | int) -> Path:
        return self.published_root / corridor_id / str(event_id)


class FileNameFactory:
    @staticmethod
    def sar_vv_prepared() -> str:
        return "sar_vv_prepared.tif"

    @staticmethod
    def sar_vh_prepared() -> str:
        return "sar_vh_prepared.tif"

    @staticmethod
    def flood_mask_raw() -> str:
        return "flood_mask_raw.tif"

    @staticmethod
    def flood_mask_cleaned() -> str:
        return "flood_mask_cleaned.tif"

    @staticmethod
    def flood_candidates() -> str:
        return "flood_candidates.parquet"

    @staticmethod
    def breach_features() -> str:
        return "breach_features.parquet"

    @staticmethod
    def exposure_summary() -> str:
        return "exposure_summary.json"
