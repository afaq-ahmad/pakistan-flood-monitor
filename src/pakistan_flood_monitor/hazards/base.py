from __future__ import annotations

from abc import ABC, abstractmethod

from pakistan_flood_monitor.models.schemas import ProcessingReport


class HazardModule(ABC):
    """Pluggable hazard contract for daily monitoring execution."""

    @property
    @abstractmethod
    def hazard_type(self) -> str:
        """Stable hazard identifier (e.g. flood, landslide, heat)."""

    @abstractmethod
    def run_daily(self, aoi_name: str) -> ProcessingReport:
        """Execute daily processing for the hazard and AOI."""


class StubHazardModule(HazardModule):
    """Base class for future hazards to extend while building implementation."""

    def __init__(self, hazard_type: str) -> None:
        self._hazard_type = hazard_type

    @property
    def hazard_type(self) -> str:
        return self._hazard_type

    def run_daily(self, aoi_name: str) -> ProcessingReport:  # pragma: no cover - integration hook
        raise NotImplementedError(f"Hazard module '{self.hazard_type}' is not implemented yet for AOI '{aoi_name}'")
