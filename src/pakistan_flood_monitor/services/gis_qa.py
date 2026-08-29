from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pakistan_flood_monitor.config import AppMode, settings
from pakistan_flood_monitor.services.publication_eligibility import publication_eligibility


@dataclass(slots=True)
class QAResult:
    passed: bool
    errors: list[str]
    normalized_geometry: dict[str, Any] | None = None


REQUIRED_LABEL_FIELDS = (
    "label_type",
    "label_tier",
    "analyst",
    "date",
    "notes",
    "uncertainty",
)

REQUIRED_MAPPING_RULE_FIELDS = (
    "river_inclusion_exclusion",
    "cloud_limitation_notes",
    "disconnected_pool_handling",
    "certainty_class",
)


def enforce_review_sop(label_metadata: dict[str, Any] | None, mapping_rules: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    if label_metadata is None:
        return ["Missing label_metadata for reviewed geometry."]
    if mapping_rules is None:
        return ["Missing mapping_rules for reviewed geometry."]

    for field in REQUIRED_LABEL_FIELDS:
        if not label_metadata.get(field):
            errors.append(f"label_metadata.{field} is required.")

    uncertainty = label_metadata.get("uncertainty")
    if uncertainty is not None and not (0.0 <= float(uncertainty) <= 1.0):
        errors.append("label_metadata.uncertainty must be between 0 and 1.")

    for field in REQUIRED_MAPPING_RULE_FIELDS:
        if not mapping_rules.get(field):
            errors.append(f"mapping_rules.{field} is required.")

    return errors


def _dedupe_ring(ring: list[list[float]]) -> list[list[float]]:
    cleaned: list[list[float]] = []
    for point in ring:
        if not cleaned or cleaned[-1] != point:
            cleaned.append(point)
    if cleaned and cleaned[0] != cleaned[-1]:
        cleaned.append(cleaned[0])
    return cleaned


def _simplify_ring(ring: list[list[float]]) -> list[list[float]]:
    return [[round(float(point[0]), 6), round(float(point[1]), 6)] for point in ring]


def _validate_polygon_coords(coords: Any) -> tuple[list[list[list[float]]], list[str]]:
    errors: list[str] = []
    if not isinstance(coords, list) or not coords:
        return [], ["geometry.coordinates must contain at least one ring."]

    normalized: list[list[list[float]]] = []
    for index, ring in enumerate(coords):
        if not isinstance(ring, list) or len(ring) < 4:
            errors.append(f"geometry ring {index} must have at least 4 points.")
            continue

        if not all(isinstance(point, list) and len(point) == 2 for point in ring):
            errors.append(f"geometry ring {index} must contain [lon, lat] points.")
            continue

        deduped = _dedupe_ring(ring)
        simplified = _simplify_ring(deduped)
        if len(simplified) < 4:
            errors.append(f"geometry ring {index} is degenerate after duplicate removal.")
            continue
        if simplified[0] != simplified[-1]:
            errors.append(f"geometry ring {index} is not closed.")
            continue
        normalized.append(simplified)

    return normalized, errors


def geometry_qa(geometry: dict[str, Any] | None) -> QAResult:
    if geometry is None:
        return QAResult(False, ["geometry is required for publication."], None)

    errors: list[str] = []
    geometry_type = geometry.get("type")
    if geometry_type != "Polygon":
        errors.append("Only Polygon geometries are currently supported by QA.")

    crs = geometry.get("crs")
    if crs not in (None, "EPSG:4326"):
        errors.append("geometry.crs must be EPSG:4326.")

    normalized_geometry: dict[str, Any] | None = None
    if not errors:
        normalized_coords, coord_errors = _validate_polygon_coords(geometry.get("coordinates"))
        errors.extend(coord_errors)
        if not errors:
            normalized_geometry = {
                "type": "Polygon",
                "coordinates": normalized_coords,
                "crs": "EPSG:4326",
            }

    return QAResult(not errors, errors, normalized_geometry)


def semantic_qa(event: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_keys = ("event_class", "source_scenes", "notes", "timestamps", "district_overlays")
    for key in required_keys:
        value = event.get(key)
        if value in (None, "", []):
            errors.append(f"semantic field '{key}' is required.")

    timestamps = event.get("timestamps") or {}
    if not timestamps.get("detected_at"):
        errors.append("timestamps.detected_at is required.")

    if timestamps.get("detected_at"):
        try:
            datetime.fromisoformat(str(timestamps["detected_at"]).replace("Z", "+00:00"))
        except ValueError:
            errors.append("timestamps.detected_at must be a valid ISO timestamp.")

    return errors


def lineage_integrity_qa(event: dict[str, Any], app_mode: AppMode) -> list[str]:
    """Reject public publication when provenance is missing, simulated or unavailable."""

    if app_mode is AppMode.TEST:
        return []

    lineage = event.get("lineage") or {}
    if not lineage:
        return ["Scientific lineage is required before publication outside test mode."]

    observations = lineage.get("observations") or {}
    eligibility = publication_eligibility(observations, app_mode=app_mode)
    errors = list(eligibility.errors)
    if app_mode is AppMode.OPERATIONAL and not observations:
        errors.append("Operational publication requires per-observation provenance metadata.")
    return errors


def publication_gate(event: dict[str, Any], app_mode: AppMode | str | None = None) -> QAResult:
    resolved_mode = AppMode(app_mode) if isinstance(app_mode, str) else (app_mode or settings.app_mode)
    errors = []
    geometry_result = geometry_qa(event.get("geometry"))
    errors.extend(geometry_result.errors)
    errors.extend(semantic_qa(event))
    errors.extend(enforce_review_sop(event.get("label_metadata"), event.get("mapping_rules")))
    errors.extend(lineage_integrity_qa(event, resolved_mode))

    return QAResult(not errors, errors, geometry_result.normalized_geometry)
