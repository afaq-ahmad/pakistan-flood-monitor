from pakistan_flood_monitor.config import AppMode
from pakistan_flood_monitor.models.observations import (
    ObservationStatus, ScientificObservation, SourceAvailabilityStatus, summarize_integrity,
)


def test_degraded_observation_never_becomes_available():
    observation = ScientificObservation(
        name="rainfall", value=1.0, units="mm", status=ObservationStatus.OBSERVED,
        availability=SourceAvailabilityStatus.DEGRADED, processing_version="v1", quality_status="degraded",
    )
    summary = summarize_integrity({"rainfall": observation}, AppMode.OPERATIONAL)
    assert summary.data_availability is SourceAvailabilityStatus.DEGRADED
    assert "rainfall" in summary.missing_required_inputs
