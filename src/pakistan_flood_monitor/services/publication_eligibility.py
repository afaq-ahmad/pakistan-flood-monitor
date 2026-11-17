"""Reusable lineage eligibility checks for operational publication boundaries."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

from pydantic import ValidationError

from pakistan_flood_monitor.config import AppMode
from pakistan_flood_monitor.models.observations import (
    ObservationStatus,
    ScientificObservation,
    SourceAvailabilityStatus,
)


@dataclass(frozen=True, slots=True)
class PublicationEligibility:
    eligible: bool
    errors: tuple[str, ...] = ()
    rejected_inputs: tuple[str, ...] = ()


def publication_eligibility(
    observations: Mapping[str, ScientificObservation | Mapping[str, object]],
    *,
    app_mode: AppMode,
    required_inputs: set[str] | None = None,
) -> PublicationEligibility:
    """Reject synthetic or non-available required inputs outside test mode.

    The function accepts either domain objects or serialized lineage so product
    code, API reviews, exports, and future workers share one decision rule.
    """

    if app_mode is AppMode.TEST:
        return PublicationEligibility(eligible=True)

    required = set(observations) if required_inputs is None else required_inputs
    errors: list[str] = []
    rejected: list[str] = []
    synthetic: list[str] = []
    non_available: list[str] = []
    incomplete: list[str] = []
    if not required:
        errors.append("Scientific observation lineage is required for publication.")

    for name in sorted(required):
        raw = observations.get(name)
        if raw is None:
            rejected.append(name)
            non_available.append(name)
            continue
        if isinstance(raw, ScientificObservation):
            is_synthetic = raw.synthetic or raw.status is ObservationStatus.SIMULATED
            availability = raw.availability.value
        elif isinstance(raw, Mapping):
            is_synthetic = bool(raw.get("synthetic")) or raw.get("status") == ObservationStatus.SIMULATED.value
            availability = str(raw.get("availability") or SourceAvailabilityStatus.UNAVAILABLE.value)
        else:
            rejected.append(name)
            incomplete.append(name)
            continue
        if is_synthetic:
            rejected.append(name)
            synthetic.append(name)
        if availability != SourceAvailabilityStatus.AVAILABLE.value:
            rejected.append(name)
            non_available.append(name)
        try:
            observation = raw if isinstance(raw, ScientificObservation) else ScientificObservation.model_validate(raw)
            timestamp = observation.source_timestamp
            complete = (
                observation.name == name
                and all(value and value.strip() for value in (
                    observation.units, observation.source_uri, observation.processing_version, observation.quality_status
                ))
                and timestamp is not None and timestamp.tzinfo is not None and timestamp.utcoffset() is not None
                and observation.value is not None and math.isfinite(observation.value)
            )
        except (ValidationError, TypeError, ValueError, AttributeError):
            complete = False
        if not complete:
            rejected.append(name)
            incomplete.append(name)

    if synthetic:
        errors.append("Synthetic lineage cannot be published as a public or operational event.")
    if non_available:
        errors.append(f"Required observations are unavailable: {', '.join(sorted(set(non_available)))}.")
    if incomplete:
        errors.append(f"Required observation provenance is incomplete or invalid: {', '.join(sorted(set(incomplete)))}.")
    return PublicationEligibility(
        eligible=not errors,
        errors=tuple(errors),
        rejected_inputs=tuple(sorted(set(rejected))),
    )
