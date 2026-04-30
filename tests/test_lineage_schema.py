from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from pakistan_flood_monitor.models.schemas import EventLineage


def test_event_lineage_schema_validation_accepts_required_fields() -> None:
    payload = EventLineage(
        run_id="run-1",
        source_scene_ids=["S1A"],
        source_scenes=[],
        processing_version="sar-preprocess-v1",
        threshold_version="alert-thresholds-v1",
        thresholds={"sar_drop_db": 2.5},
        model={"model_id": "rules-v1"},
        generated_at=datetime.now(UTC),
    )
    assert payload.schema == "stac-lineage-event/v1"


def test_event_lineage_schema_validation_rejects_missing_processing_version() -> None:
    with pytest.raises(ValidationError):
        EventLineage(
            run_id="run-1",
            source_scene_ids=["S1A"],
            source_scenes=[],
            threshold_version="alert-thresholds-v1",
            thresholds={"sar_drop_db": 2.5},
            model={"model_id": "rules-v1"},
            generated_at=datetime.now(UTC),
        )
