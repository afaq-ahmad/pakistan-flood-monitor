from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Mapping

from pydantic import BaseModel, Field, model_validator

from pakistan_flood_monitor.config import AppMode


class ObservationStatus(str, Enum):
    """Physical meaning of a value exposed by the platform."""

    OBSERVED = "OBSERVED"
    FORECAST = "FORECAST"
    ESTIMATED = "ESTIMATED"
    SIMULATED = "SIMULATED"
    FIELD_REPORTED = "FIELD_REPORTED"
    OFFICIAL = "OFFICIAL"
    UNAVAILABLE = "UNAVAILABLE"


class SourceAvailabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class ScientificObservation(BaseModel):
    """A numerical input plus enough metadata to judge whether it is real."""

    name: str
    value: float | None = None
    units: str
    status: ObservationStatus
    availability: SourceAvailabilityStatus
    source_uri: str | None = None
    source_timestamp: datetime | None = None
    processing_version: str
    quality_status: str
    synthetic: bool = False

    @model_validator(mode="after")
    def _validate_integrity(self) -> "ScientificObservation":
        if self.status is ObservationStatus.SIMULATED and not self.synthetic:
            raise ValueError("SIMULATED observations must set synthetic=true")
        if self.synthetic and self.status is not ObservationStatus.SIMULATED:
            raise ValueError("synthetic=true is only valid for SIMULATED observations")
        if self.availability is SourceAvailabilityStatus.UNAVAILABLE and self.value is not None:
            raise ValueError("UNAVAILABLE observations cannot contain a numerical value")
        if self.status is ObservationStatus.UNAVAILABLE and self.availability is not SourceAvailabilityStatus.UNAVAILABLE:
            raise ValueError("UNAVAILABLE status requires UNAVAILABLE availability")
        return self


class DataIntegritySummary(BaseModel):
    app_mode: AppMode
    data_availability: SourceAvailabilityStatus
    product_label: ObservationStatus
    contains_synthetic: bool
    missing_required_inputs: list[str] = Field(default_factory=list)
    synthetic_inputs: list[str] = Field(default_factory=list)
    watermark: str | None = None


def summarize_integrity(
    observations: Mapping[str, ScientificObservation],
    app_mode: AppMode,
) -> DataIntegritySummary:
    missing = sorted(
        name
        for name, observation in observations.items()
        if observation.availability is SourceAvailabilityStatus.UNAVAILABLE
    )
    synthetic = sorted(name for name, observation in observations.items() if observation.synthetic)

    if missing:
        availability = SourceAvailabilityStatus.UNAVAILABLE
        label = ObservationStatus.UNAVAILABLE
    elif synthetic:
        availability = SourceAvailabilityStatus.DEGRADED
        label = ObservationStatus.SIMULATED
    else:
        availability = SourceAvailabilityStatus.AVAILABLE
        label = ObservationStatus.OBSERVED

    watermark = "SIMULATED / DEMO DATA — NOT FOR OPERATIONAL DECISIONS" if synthetic else None
    return DataIntegritySummary(
        app_mode=app_mode,
        data_availability=availability,
        product_label=label,
        contains_synthetic=bool(synthetic),
        missing_required_inputs=missing,
        synthetic_inputs=synthetic,
        watermark=watermark,
    )


class OperationalDataIntegrityError(RuntimeError):
    """Raised when operational execution would need invented or missing data."""

    def __init__(
        self,
        message: str,
        *,
        observations: Mapping[str, ScientificObservation] | None = None,
    ) -> None:
        super().__init__(message)
        self.observations = dict(observations or {})

    def as_dict(self) -> dict[str, Any]:
        return {
            "error": "operational_data_integrity_error",
            "message": str(self),
            "app_mode": AppMode.OPERATIONAL.value,
            "data_availability": SourceAvailabilityStatus.UNAVAILABLE.value,
            "observations": {
                name: observation.model_dump(mode="json")
                for name, observation in sorted(self.observations.items())
            },
        }
