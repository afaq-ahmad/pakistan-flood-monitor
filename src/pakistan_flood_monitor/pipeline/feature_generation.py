from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import rasterio

from pakistan_flood_monitor.config import AppMode, settings
from pakistan_flood_monitor.core.detection import DetectionFeatures
from pakistan_flood_monitor.data.sources import SceneMetadata
from pakistan_flood_monitor.models.observations import (
    DataIntegritySummary,
    ObservationStatus,
    OperationalDataIntegrityError,
    ScientificObservation,
    SourceAvailabilityStatus,
    summarize_integrity,
)


@dataclass(slots=True)
class FeatureSnapshot:
    run_id: str
    aoi_name: str
    processing_version: str
    threshold_version: str
    source_scene_ids: list[str]
    parameters: dict[str, float | str]
    thresholds: dict[str, float]
    derived_features: dict[str, float | None]
    observations: dict[str, dict]
    integrity: dict


@dataclass(slots=True)
class ExtractedFeatureBundle:
    features: DetectionFeatures
    snapshot_path: Path
    source_scene_ids: list[str]
    observations: dict[str, ScientificObservation]
    integrity: DataIntegritySummary


class SceneFeatureExtractor:
    def __init__(
        self,
        snapshot_root: str | Path = ".cache/feature_snapshots",
        app_mode: AppMode | None = None,
    ) -> None:
        self._snapshot_root = Path(snapshot_root)
        self._app_mode = app_mode or settings.app_mode

    def extract(
        self,
        *,
        run_id: str,
        aoi_name: str,
        scenes: list[SceneMetadata],
        support_layers: dict[str, str],
        processing_version: str,
        threshold_version: str,
        thresholds: dict[str, float],
    ) -> ExtractedFeatureBundle:
        source_scene_ids = sorted(scene.scene_id for scene in scenes)
        source_timestamp = self._latest_scene_timestamp(scenes)
        sar_drop = self._derive_sar_drop_db(scenes)
        observations = {
            "sar_drop_db": self._observed_or_fallback(
                name="sar_drop_db",
                observed_value=sar_drop,
                simulated_value=round(1.5 + self._unit_hash("|".join(source_scene_ids)) * 3.0, 3),
                units="dB",
                source_uri=self._first_asset_uri(scenes, "vv"),
                source_timestamp=source_timestamp,
                processing_version=processing_version,
            ),
            "ndwi": self._observed_or_fallback(
                name="ndwi",
                observed_value=None,
                simulated_value=self._derive_ndwi(source_scene_ids),
                units="unitless_index",
                source_uri=None,
                source_timestamp=source_timestamp,
                processing_version=processing_version,
            ),
            "rainfall_mm_72h": self._observed_or_fallback(
                name="rainfall_mm_72h",
                observed_value=None,
                simulated_value=self._derive_imerg_mm_72h(support_layers.get("imerg", ""), source_scene_ids),
                units="mm",
                source_uri=support_layers.get("imerg") or None,
                source_timestamp=None,
                processing_version=processing_version,
            ),
            "glofas_return_period": self._observed_or_fallback(
                name="glofas_return_period",
                observed_value=None,
                simulated_value=self._derive_glofas_rp(support_layers.get("glofas", ""), source_scene_ids),
                units="years",
                source_uri=support_layers.get("glofas") or None,
                source_timestamp=None,
                processing_version=processing_version,
            ),
            "floodplain_distance_m": self._observed_or_fallback(
                name="floodplain_distance_m",
                observed_value=None,
                simulated_value=self._derive_floodplain_distance_m(aoi_name),
                units="m",
                source_uri=support_layers.get("floodplain") or None,
                source_timestamp=None,
                processing_version=processing_version,
            ),
        }
        integrity = summarize_integrity(observations, self._app_mode)
        if self._app_mode is AppMode.OPERATIONAL and (
            integrity.missing_required_inputs or integrity.contains_synthetic
        ):
            raise OperationalDataIntegrityError(
                "Required scientific observations are unavailable; operational detection was not run.",
                observations=observations,
            )

        derived = {name: observation.value for name, observation in observations.items()}
        if any(value is None for value in derived.values()):  # defensive: non-operational fallbacks must be complete
            raise RuntimeError("Test/demo feature fallback failed to produce a complete labelled fixture")

        features = DetectionFeatures(
            sar_drop_db=float(derived["sar_drop_db"]),
            ndwi=float(derived["ndwi"]),
            rainfall_mm_72h=float(derived["rainfall_mm_72h"]),
            glofas_return_period=float(derived["glofas_return_period"]),
            floodplain_distance_m=float(derived["floodplain_distance_m"]),
        )
        snapshot = FeatureSnapshot(
            run_id=run_id,
            aoi_name=aoi_name,
            processing_version=processing_version,
            threshold_version=threshold_version,
            source_scene_ids=source_scene_ids,
            parameters={"feature_hash_algo": "sha256", "ndwi_bounds_min": 0.05, "ndwi_bounds_max": 0.45},
            thresholds=thresholds,
            derived_features=derived,
            observations={name: value.model_dump(mode="json") for name, value in observations.items()},
            integrity=integrity.model_dump(mode="json"),
        )
        path = self._snapshot_root / aoi_name / f"{run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(snapshot), sort_keys=True, indent=2), encoding="utf-8")
        return ExtractedFeatureBundle(
            features=features,
            snapshot_path=path,
            source_scene_ids=source_scene_ids,
            observations=observations,
            integrity=integrity,
        )

    def _derive_sar_drop_db(self, scenes: list[SceneMetadata]) -> float | None:
        vv_values = []
        for scene in scenes:
            if scene.synthetic:
                continue
            if not scene.assets:
                continue
            vv_path = scene.assets.get("vv")
            if vv_path and Path(vv_path).exists():
                with rasterio.open(vv_path) as src:
                    arr = src.read(1, masked=True).filled(float("nan"))
                vv_values.append(float(arr.mean()))
        if len(vv_values) >= 2:
            baseline = min(vv_values)
            current = max(vv_values)
            return round(abs(current - baseline), 3)
        return None

    def _observed_or_fallback(
        self,
        *,
        name: str,
        observed_value: float | None,
        simulated_value: float,
        units: str,
        source_uri: str | None,
        source_timestamp: datetime | None,
        processing_version: str,
    ) -> ScientificObservation:
        if observed_value is not None:
            return ScientificObservation(
                name=name,
                value=observed_value,
                units=units,
                status=ObservationStatus.OBSERVED,
                availability=SourceAvailabilityStatus.AVAILABLE,
                source_uri=source_uri,
                source_timestamp=source_timestamp,
                processing_version=processing_version,
                quality_status="provisional_unvalidated",
            )
        if self._app_mode is AppMode.OPERATIONAL:
            return ScientificObservation(
                name=name,
                value=None,
                units=units,
                status=ObservationStatus.UNAVAILABLE,
                availability=SourceAvailabilityStatus.UNAVAILABLE,
                source_uri=source_uri,
                source_timestamp=source_timestamp,
                processing_version=processing_version,
                quality_status="source_unavailable",
            )
        return ScientificObservation(
            name=name,
            value=simulated_value,
            units=units,
            status=ObservationStatus.SIMULATED,
            availability=SourceAvailabilityStatus.DEGRADED,
            source_uri=source_uri,
            source_timestamp=source_timestamp,
            processing_version=processing_version,
            quality_status="simulated_fixture",
            synthetic=True,
        )

    @staticmethod
    def _latest_scene_timestamp(scenes: list[SceneMetadata]) -> datetime | None:
        if not scenes:
            return None
        latest = max(scene.acquisition_date for scene in scenes)
        return datetime.combine(latest, datetime.min.time(), tzinfo=UTC)

    @staticmethod
    def _first_asset_uri(scenes: list[SceneMetadata], asset_name: str) -> str | None:
        for scene in scenes:
            if scene.assets and scene.assets.get(asset_name):
                return scene.assets[asset_name]
        return None

    def _derive_ndwi(self, scene_ids: list[str]) -> float:
        return round(0.05 + self._unit_hash("ndwi:" + "|".join(scene_ids)) * 0.4, 3)

    def _derive_imerg_mm_72h(self, imerg_ref: str, scene_ids: list[str]) -> float:
        return round(20.0 + self._unit_hash(f"imerg:{imerg_ref}:{'|'.join(scene_ids)}") * 180.0, 2)

    def _derive_glofas_rp(self, glofas_ref: str, scene_ids: list[str]) -> float:
        return round(1.0 + self._unit_hash(f"glofas:{glofas_ref}:{'|'.join(scene_ids)}") * 9.0, 2)

    def _derive_floodplain_distance_m(self, aoi_name: str) -> float:
        return round(200.0 + self._unit_hash("floodplain:" + aoi_name) * 2600.0, 2)

    @staticmethod
    def _unit_hash(seed: str) -> float:
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) / 0xFFFFFFFF
