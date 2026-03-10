from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4


CandidateKind = Literal["flood", "breach"]


@dataclass(slots=True)
class CandidateLabelLink:
    candidate_id: str
    candidate_kind: CandidateKind
    review_outcome: str
    final_class: str
    label_quality_tier: int
    reviewed_at: datetime


@dataclass(slots=True)
class SARFeatures:
    mean_drop_db: float
    min_drop_db: float
    p90_drop_db: float
    coherence_loss: float


@dataclass(slots=True)
class OpticalSupportFeatures:
    support_score: float
    supported_fraction: float
    obscured_fraction: float
    observable_fraction: float


@dataclass(slots=True)
class TerrainFeatures:
    slope_mean_deg: float
    relative_elevation_m: float
    distance_to_river_m: float
    floodplain_distance_m: float


@dataclass(slots=True)
class HydrometFeatures:
    rainfall_mm_72h: float
    rainfall_anomaly_z: float
    glofas_return_period: float
    upstream_discharge_anomaly: float


@dataclass(slots=True)
class BaselineContextFeatures:
    seasonal_overlap_ratio: float
    persistence_score: float
    historical_water_occurrence: float


@dataclass(slots=True)
class BreachGeometryFeatures:
    protected_side_ratio: float
    distance_to_embankment_m: float
    expansion_away_from_levee_score: float
    split_merge_complexity: float


@dataclass(slots=True)
class CandidateFeatureRow:
    snapshot_id: str
    candidate_id: str
    candidate_kind: CandidateKind
    sar: SARFeatures
    optical: OpticalSupportFeatures
    terrain: TerrainFeatures
    hydromet: HydrometFeatures
    baseline: BaselineContextFeatures
    breach_geometry: BreachGeometryFeatures | None
    source_event_id: str | None
    extracted_at: datetime
    rules_flood_confidence: float | None = None
    rules_breach_confidence: float | None = None
    label: CandidateLabelLink | None = None

    def to_feature_table_row(self) -> dict[str, Any]:
        row = {
            "snapshot_id": self.snapshot_id,
            "candidate_id": self.candidate_id,
            "candidate_kind": self.candidate_kind,
            "source_event_id": self.source_event_id,
            "extracted_at": self.extracted_at.isoformat(),
            "sar_mean_drop_db": self.sar.mean_drop_db,
            "sar_min_drop_db": self.sar.min_drop_db,
            "sar_p90_drop_db": self.sar.p90_drop_db,
            "sar_coherence_loss": self.sar.coherence_loss,
            "optical_support_score": self.optical.support_score,
            "optical_supported_fraction": self.optical.supported_fraction,
            "optical_obscured_fraction": self.optical.obscured_fraction,
            "optical_observable_fraction": self.optical.observable_fraction,
            "terrain_slope_mean_deg": self.terrain.slope_mean_deg,
            "terrain_relative_elevation_m": self.terrain.relative_elevation_m,
            "terrain_distance_to_river_m": self.terrain.distance_to_river_m,
            "terrain_floodplain_distance_m": self.terrain.floodplain_distance_m,
            "hydromet_rainfall_mm_72h": self.hydromet.rainfall_mm_72h,
            "hydromet_rainfall_anomaly_z": self.hydromet.rainfall_anomaly_z,
            "hydromet_glofas_return_period": self.hydromet.glofas_return_period,
            "hydromet_upstream_discharge_anomaly": self.hydromet.upstream_discharge_anomaly,
            "baseline_seasonal_overlap_ratio": self.baseline.seasonal_overlap_ratio,
            "baseline_persistence_score": self.baseline.persistence_score,
            "baseline_historical_water_occurrence": self.baseline.historical_water_occurrence,
            "rules_flood_confidence": self.rules_flood_confidence,
            "rules_breach_confidence": self.rules_breach_confidence,
            "label_review_outcome": None,
            "label_final_class": None,
            "label_quality_tier": None,
            "label_reviewed_at": None,
        }
        if self.breach_geometry is not None:
            row.update(
                {
                    "breach_protected_side_ratio": self.breach_geometry.protected_side_ratio,
                    "breach_distance_to_embankment_m": self.breach_geometry.distance_to_embankment_m,
                    "breach_expansion_away_from_levee_score": self.breach_geometry.expansion_away_from_levee_score,
                    "breach_split_merge_complexity": self.breach_geometry.split_merge_complexity,
                }
            )
        if self.label is not None:
            row.update(
                {
                    "label_review_outcome": self.label.review_outcome,
                    "label_final_class": self.label.final_class,
                    "label_quality_tier": self.label.label_quality_tier,
                    "label_reviewed_at": self.label.reviewed_at.isoformat(),
                }
            )
        return row


class FeatureSnapshotStore:
    """Stores immutable feature snapshots for reproducible ML training."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(
        self,
        *,
        feature_schema_version: str,
        created_by: str,
        source_run_ids: list[str] | None = None,
        snapshot_id: str | None = None,
    ) -> str:
        sid = snapshot_id or f"snapshot-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
        snapshot_dir = self.root_dir / sid
        snapshot_dir.mkdir(parents=True, exist_ok=False)

        manifest = {
            "snapshot_id": sid,
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": created_by,
            "feature_schema_version": feature_schema_version,
            "source_run_ids": source_run_ids or [],
            "frozen": True,
        }
        self._write_json(snapshot_dir / "manifest.json", manifest)
        (snapshot_dir / "flood_feature_table.jsonl").write_text("", encoding="utf-8")
        (snapshot_dir / "breach_feature_table.jsonl").write_text("", encoding="utf-8")
        return sid

    def persist_feature_rows(self, *, snapshot_id: str, rows: list[CandidateFeatureRow]) -> None:
        snapshot_dir = self.root_dir / snapshot_id
        manifest = self._read_json(snapshot_dir / "manifest.json")
        if not manifest.get("frozen", False):
            raise ValueError(f"Snapshot {snapshot_id} is not frozen and cannot be used for training.")

        flood_path = snapshot_dir / "flood_feature_table.jsonl"
        breach_path = snapshot_dir / "breach_feature_table.jsonl"

        with flood_path.open("a", encoding="utf-8") as flood_handle, breach_path.open("a", encoding="utf-8") as breach_handle:
            for row in rows:
                payload = json.dumps(row.to_feature_table_row(), sort_keys=True)
                if row.candidate_kind == "flood":
                    flood_handle.write(f"{payload}\n")
                else:
                    breach_handle.write(f"{payload}\n")

    def load_training_rows(
        self,
        *,
        snapshot_id: str,
        candidate_kind: CandidateKind,
        min_label_quality_tier: int = 1,
    ) -> list[dict[str, Any]]:
        snapshot_dir = self.root_dir / snapshot_id
        table_name = "flood_feature_table.jsonl" if candidate_kind == "flood" else "breach_feature_table.jsonl"
        table_path = snapshot_dir / table_name
        if not table_path.exists():
            return []

        output: list[dict[str, Any]] = []
        for line in table_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            label_tier = row.get("label_quality_tier")
            if label_tier is None or label_tier < min_label_quality_tier:
                continue
            output.append(row)
        return output

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))


def build_candidate_feature_row(
    *,
    snapshot_id: str,
    candidate_id: str,
    candidate_kind: CandidateKind,
    sar: SARFeatures,
    optical: OpticalSupportFeatures,
    terrain: TerrainFeatures,
    hydromet: HydrometFeatures,
    baseline: BaselineContextFeatures,
    breach_geometry: BreachGeometryFeatures | None = None,
    source_event_id: str | None = None,
    rules_flood_confidence: float | None = None,
    rules_breach_confidence: float | None = None,
    label: CandidateLabelLink | None = None,
) -> CandidateFeatureRow:
    if candidate_kind == "flood" and breach_geometry is not None:
        raise ValueError("Flood candidates cannot include breach-specific geometric features.")
    if candidate_kind == "breach" and breach_geometry is None:
        raise ValueError("Breach candidates require breach-specific geometric features.")

    return CandidateFeatureRow(
        snapshot_id=snapshot_id,
        candidate_id=candidate_id,
        candidate_kind=candidate_kind,
        sar=sar,
        optical=optical,
        terrain=terrain,
        hydromet=hydromet,
        baseline=baseline,
        breach_geometry=breach_geometry,
        source_event_id=source_event_id,
        rules_flood_confidence=rules_flood_confidence,
        rules_breach_confidence=rules_breach_confidence,
        label=label,
        extracted_at=datetime.now(UTC),
    )
