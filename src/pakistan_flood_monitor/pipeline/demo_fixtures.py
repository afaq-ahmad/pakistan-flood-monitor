"""Deterministic fixtures that are deliberately limited to test and demo runs.

This module is the only canonical location where placeholder feature values,
probability-derived extents, or area-multiplier exposure estimates are allowed.
Operational processors must obtain measured inputs and derived products from
real providers instead.
"""
from __future__ import annotations

import hashlib
from datetime import datetime

from pakistan_flood_monitor.models.observations import (
    ObservationStatus,
    ScientificObservation,
    SourceAvailabilityStatus,
)
from pakistan_flood_monitor.models.schemas import ExposureStats


class DeterministicDemoFeatureFixtures:
    """Build reproducible, visibly simulated feature observations."""

    processing_version = "demo-feature-fixture-v1"

    @staticmethod
    def _unit_hash(seed: str) -> float:
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) / 0xFFFFFFFF

    def observation(
        self,
        *,
        name: str,
        units: str,
        source_uri: str | None,
        source_timestamp: datetime | None,
        processing_version: str,
        seed: str,
    ) -> ScientificObservation:
        value = self._value_for(name=name, seed=seed)
        return ScientificObservation(
            name=name,
            value=value,
            units=units,
            status=ObservationStatus.SIMULATED,
            availability=SourceAvailabilityStatus.DEGRADED,
            source_uri=source_uri,
            source_timestamp=source_timestamp,
            processing_version=processing_version,
            quality_status="simulated_fixture",
            availability_reason_code="demo_fixture_only",
            synthetic=True,
        )

    def _value_for(self, *, name: str, seed: str) -> float:
        value = self._unit_hash(f"{name}:{seed}")
        if name == "sar_drop_db":
            return round(1.5 + value * 3.0, 3)
        if name == "ndwi":
            return round(0.05 + value * 0.4, 3)
        if name == "rainfall_mm_72h":
            return round(20.0 + value * 180.0, 2)
        if name == "glofas_return_period":
            return round(1.0 + value * 9.0, 2)
        if name == "floodplain_distance_m":
            return round(200.0 + value * 2600.0, 2)
        raise ValueError(f"No demo fixture is defined for feature '{name}'")


class DemoFloodProductSimulator:
    """Explicitly synthetic product helper for test/demo user interfaces only."""

    def flood_area_from_probability(self, flood_probability: float) -> float:
        return round(25.0 + flood_probability * 70.0, 2)

    def estimate_exposure(self, flood_area_km2: float) -> ExposureStats:
        return ExposureStats(
            affected_population=int(flood_area_km2 * 3100),
            affected_cropland_km2=round(flood_area_km2 * 0.46, 2),
            affected_roads_km=round(flood_area_km2 * 3.2, 2),
            affected_schools=max(1, int(flood_area_km2 / 20)),
            affected_hospitals=max(1, int(flood_area_km2 / 45)),
        )
