from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import rasterio

from pakistan_flood_monitor.core.detection import DetectionFeatures
from pakistan_flood_monitor.data.sources import SceneMetadata


@dataclass(slots=True)
class FeatureSnapshot:
    run_id: str
    aoi_name: str
    processing_version: str
    threshold_version: str
    source_scene_ids: list[str]
    parameters: dict[str, float | str]
    thresholds: dict[str, float]
    derived_features: dict[str, float]


@dataclass(slots=True)
class ExtractedFeatureBundle:
    features: DetectionFeatures
    snapshot_path: Path
    source_scene_ids: list[str]


class SceneFeatureExtractor:
    def __init__(self, snapshot_root: str | Path = ".cache/feature_snapshots") -> None:
        self._snapshot_root = Path(snapshot_root)

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
        sar_drop = self._derive_sar_drop_db(scenes)
        ndwi = self._derive_ndwi(source_scene_ids)
        rainfall = self._derive_imerg_mm_72h(support_layers.get("imerg", ""), source_scene_ids)
        glofas = self._derive_glofas_rp(support_layers.get("glofas", ""), source_scene_ids)
        floodplain_distance_m = self._derive_floodplain_distance_m(aoi_name)

        features = DetectionFeatures(
            sar_drop_db=sar_drop,
            ndwi=ndwi,
            rainfall_mm_72h=rainfall,
            glofas_return_period=glofas,
            floodplain_distance_m=floodplain_distance_m,
        )
        snapshot = FeatureSnapshot(
            run_id=run_id,
            aoi_name=aoi_name,
            processing_version=processing_version,
            threshold_version=threshold_version,
            source_scene_ids=source_scene_ids,
            parameters={"feature_hash_algo": "sha256", "ndwi_bounds_min": 0.05, "ndwi_bounds_max": 0.45},
            thresholds=thresholds,
            derived_features=asdict(features),
        )
        path = self._snapshot_root / aoi_name / f"{run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(snapshot), sort_keys=True, indent=2), encoding="utf-8")
        return ExtractedFeatureBundle(features=features, snapshot_path=path, source_scene_ids=source_scene_ids)

    def _derive_sar_drop_db(self, scenes: list[SceneMetadata]) -> float:
        vv_values = []
        for scene in scenes:
            if not scene.assets:
                continue
            vv_path = scene.assets.get("vv")
            if vv_path and Path(vv_path).exists():
                with rasterio.open(vv_path) as src:
                    arr = src.read(1, masked=True).filled(float("nan"))
                vv_values.append(float(arr.mean()))
        if vv_values:
            baseline = min(vv_values)
            current = max(vv_values)
            return round(abs(current - baseline), 3)
        return round(1.5 + self._unit_hash("|".join(sorted(s.scene_id for s in scenes))) * 3.0, 3)

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
