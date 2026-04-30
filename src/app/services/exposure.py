from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from shapely.geometry import shape


GeometryDict = dict[str, Any]


REVIEW_ACCEPTED_STATUSES = {"accepted", "published"}
STRONG_MACHINE_STATUSES = {"strong", "high_confidence", "auto_accepted"}


@dataclass(slots=True)
class OverlayFeature:
    feature_id: str
    geometry: GeometryDict
    properties: dict[str, Any]


@dataclass(slots=True)
class AssetLayer:
    name: str
    kind: Literal["polygon", "line", "point", "population"]
    features: list[OverlayFeature]
    value_field: str | None = None
    source_uri: str | None = None
    source_version: str | None = None
    source_timestamp: str | None = None
    quality_score: float = 1.0


@dataclass(slots=True)
class ExposureRequest:
    event_id: int
    review_status: str
    machine_status: str
    reviewed_geometry: GeometryDict | None
    machine_geometry: GeometryDict
    corridor_geometry: GeometryDict
    district_boundaries: list[OverlayFeature]
    asset_layers: list[AssetLayer]
    cloud_limited: bool = False
    processing_version: str = "exposure-overlay-v2"
    processing_parameters: dict[str, Any] | None = None


@dataclass(slots=True)
class ExposureComputationResult:
    event_id: int
    geometry_source: Literal["reviewed", "machine_provisional"]
    provisional_geometry: bool
    uncertainty_flag: bool
    exposure_results_rows: list[dict[str, Any]]
    summary_blob: dict[str, Any]


class ExposureComputationService:
    """Computes district/asset exposure overlays and emits both relational and API-friendly summaries."""

    def should_trigger(self, review_status: str, machine_status: str) -> bool:
        return should_trigger_exposure(review_status=review_status, machine_status=machine_status)

    def compute(self, request: ExposureRequest) -> ExposureComputationResult:
        if not self.should_trigger(review_status=request.review_status, machine_status=request.machine_status):
            raise ValueError("Exposure computation is allowed only after accepted review or strong machine status")

        target_geometry, source = _select_target_geometry(request.reviewed_geometry, request.machine_geometry)
        event_geom = shape(target_geometry)
        corridor_geom = shape(request.corridor_geometry)
        event_area_sqkm = _area_sqkm(event_geom)

        district_summaries, district_geoms = _district_summaries(
            event_geom=event_geom,
            corridor_geom=corridor_geom,
            event_area_sqkm=event_area_sqkm,
            districts=request.district_boundaries,
        )
        asset_summaries = _asset_summaries(
            event_geom=event_geom,
            district_summaries=district_summaries,
            district_geoms=district_geoms,
            layers=request.asset_layers,
        )

        lineage = _build_lineage(request=request, geometry_source=source)
        uncertainty = _build_uncertainty(
            request=request,
            geometry_source=source,
            district_summaries=district_summaries,
            asset_summaries=asset_summaries,
        )
        uncertainty_flag = request.cloud_limited or source == "machine_provisional" or request.review_status == "unreviewed"

        summary_blob = {
            "event_id": request.event_id,
            "geometry_source": source,
            "provisional": source == "machine_provisional",
            "uncertainty_flag": uncertainty_flag,
            "event_area_sqkm": round(event_area_sqkm, 6),
            "districts": [
                {
                    "district_id": row["district_id"],
                    "district_name": row["district_name"],
                    "flooded_area_sqkm": row["flooded_area_sqkm"],
                    "percent_of_event_area": row["percent_of_event_area"],
                    "impact_rank": row["impact_rank"],
                }
                for row in district_summaries
            ],
            "assets": asset_summaries,
            "lineage": lineage,
            "uncertainty": uncertainty,
        }

        relational_rows: list[dict[str, Any]] = []
        for row in district_summaries:
            row["event_id"] = request.event_id
            row["uncertainty_flag"] = uncertainty_flag
            row["geometry_source"] = source
            row["lineage_metadata"] = lineage
            row["uncertainty_bounds"] = uncertainty
            relational_rows.append(row)
        for district_id, assets in asset_summaries.items():
            for layer_name, metrics in assets.items():
                relational_rows.append(
                    {
                        "event_id": request.event_id,
                        "result_type": "asset",
                        "district_id": district_id,
                        "layer_name": layer_name,
                        "metrics": metrics,
                        "uncertainty_flag": uncertainty_flag,
                        "geometry_source": source,
                        "lineage_metadata": lineage,
                        "uncertainty_bounds": uncertainty,
                    }
                )

        return ExposureComputationResult(
            event_id=request.event_id,
            geometry_source=source,
            provisional_geometry=source == "machine_provisional",
            uncertainty_flag=uncertainty_flag,
            exposure_results_rows=relational_rows,
            summary_blob=summary_blob,
        )


def should_trigger_exposure(*, review_status: str, machine_status: str) -> bool:
    return review_status in REVIEW_ACCEPTED_STATUSES or machine_status in STRONG_MACHINE_STATUSES


def _select_target_geometry(
    reviewed_geometry: GeometryDict | None,
    machine_geometry: GeometryDict,
) -> tuple[GeometryDict, Literal["reviewed", "machine_provisional"]]:
    if reviewed_geometry:
        return reviewed_geometry, "reviewed"
    return machine_geometry, "machine_provisional"


def _district_summaries(
    *,
    event_geom,
    corridor_geom,
    event_area_sqkm: float,
    districts: list[OverlayFeature],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    output: list[dict[str, Any]] = []
    district_geoms: dict[str, Any] = {}
    corridor_overlap_area = _area_sqkm(event_geom.intersection(corridor_geom))

    for district in districts:
        district_geom = shape(district.geometry)
        district_geoms[district.feature_id] = district_geom
        intersection_area = _area_sqkm(event_geom.intersection(district_geom))
        if intersection_area <= 0:
            continue
        percent_of_event_area = 0.0 if event_area_sqkm == 0 else (intersection_area / event_area_sqkm) * 100.0
        output.append(
            {
                "event_id": None,
                "result_type": "district",
                "district_id": district.feature_id,
                "district_name": district.properties.get("name", district.feature_id),
                "flooded_area_sqkm": round(intersection_area, 6),
                "percent_of_event_area": round(percent_of_event_area, 4),
                "corridor_event_area_sqkm": round(corridor_overlap_area, 6),
                "impact_rank": 0,
                "uncertainty_flag": False,
                "geometry_source": None,
            }
        )
    output.sort(key=lambda row: row["flooded_area_sqkm"], reverse=True)
    for idx, row in enumerate(output, start=1):
        row["impact_rank"] = idx
    return output, district_geoms


def _asset_summaries(
    *,
    event_geom,
    district_summaries: list[dict[str, Any]],
    district_geoms: dict[str, Any],
    layers: list[AssetLayer],
) -> dict[str, dict[str, dict[str, float]]]:
    district_ids = [row["district_id"] for row in district_summaries]
    output = {district_id: {} for district_id in district_ids}

    for district_id in district_ids:
        for layer in layers:
            metric = _overlay_metric(event_geom=event_geom.intersection(district_geoms[district_id]), layer=layer)
            output[district_id][layer.name] = metric
    return output


def _overlay_metric(*, event_geom, layer: AssetLayer) -> dict[str, float]:
    if layer.kind == "line":
        total_m = 0.0
        for feature in layer.features:
            total_m += event_geom.intersection(shape(feature.geometry)).length
        return {"exposed_length_km": round(total_m / 1000.0, 6)}

    if layer.kind == "polygon":
        total_sqkm = 0.0
        for feature in layer.features:
            total_sqkm += _area_sqkm(event_geom.intersection(shape(feature.geometry)))
        return {"exposed_area_sqkm": round(total_sqkm, 6)}

    if layer.kind == "point":
        count = 0
        for feature in layer.features:
            if event_geom.intersects(shape(feature.geometry)):
                count += 1
        return {"exposed_count": float(count)}

    if layer.kind == "population":
        total_population = 0.0
        for feature in layer.features:
            cell_geom = shape(feature.geometry)
            intersected_area = _area_sqkm(event_geom.intersection(cell_geom))
            cell_area = _area_sqkm(cell_geom)
            if cell_area <= 0:
                continue
            value = float(feature.properties.get(layer.value_field or "population", 0.0))
            total_population += value * (intersected_area / cell_area)
        return {"estimated_population_exposed": round(total_population, 2)}

    raise ValueError(f"Unsupported asset layer kind: {layer.kind}")


def _build_lineage(*, request: ExposureRequest, geometry_source: str) -> dict[str, Any]:
    layers = []
    for layer in request.asset_layers:
        layers.append(
            {
                "layer_name": layer.name,
                "layer_kind": layer.kind,
                "source_uri": layer.source_uri or "inline-memory",
                "version": layer.source_version or "unknown",
                "source_timestamp": layer.source_timestamp,
                "feature_count": len(layer.features),
                "value_field": layer.value_field,
                "quality_score": round(layer.quality_score, 4),
            }
        )

    return {
        "model": "spatial_overlay_exposure",
        "processing_version": request.processing_version,
        "computed_at": datetime.now(tz=UTC).isoformat(),
        "geometry_source": geometry_source,
        "parameters": request.processing_parameters or {},
        "layers": layers,
    }


def _build_uncertainty(
    *,
    request: ExposureRequest,
    geometry_source: str,
    district_summaries: list[dict[str, Any]],
    asset_summaries: dict[str, dict[str, dict[str, float]]],
) -> dict[str, Any]:
    geometry_score = 0.15 if geometry_source == "machine_provisional" else 0.05
    cloud_score = 0.2 if request.cloud_limited else 0.0
    layer_quality = 1.0
    if request.asset_layers:
        layer_quality = sum(layer.quality_score for layer in request.asset_layers) / len(request.asset_layers)
    quality_score = max(0.0, min(1.0, 1.0 - layer_quality))
    base = min(1.0, geometry_score + cloud_score + quality_score)

    by_layer: dict[str, dict[str, float]] = {}
    for layer in request.asset_layers:
        layer_uncertainty = min(1.0, base + (1.0 - layer.quality_score) * 0.5)
        by_layer[layer.name] = {"relative_uncertainty": round(layer_uncertainty, 4)}

    return {
        "overall_uncertainty_score": round(base, 4),
        "geometry_source_uncertainty": round(geometry_score, 4),
        "cloud_uncertainty": round(cloud_score, 4),
        "layer_quality_uncertainty": round(quality_score, 4),
        "confidence_interval": {
            "lower_multiplier": round(max(0.0, 1.0 - base), 4),
            "upper_multiplier": round(1.0 + base, 4),
        },
        "components": by_layer,
        "district_count": len(district_summaries),
        "asset_district_records": sum(len(v) for v in asset_summaries.values()),
    }


def _area_sqkm(geom) -> float:
    return float(geom.area)


def compute_exposure(event_id: int) -> dict:
    """Legacy compatibility shim retained for existing API/tests."""
    return {"event_id": event_id, "population_exposed": 0}
