from datetime import UTC, datetime

from pakistan_flood_monitor.config import AppMode
from pakistan_flood_monitor.services.gis_qa import lineage_integrity_qa


def test_publication_rejects_missing_and_incomplete_lineage():
    for lineage in ({"observations": {}}, {"observations": {"rain": {"availability": "AVAILABLE"}}}):
        assert lineage_integrity_qa({"lineage": lineage}, AppMode.OPERATIONAL)
        assert lineage_integrity_qa({"lineage": lineage}, AppMode.DEMO)


def test_publication_requires_aware_time_and_usable_metadata():
    obs = {"name": "rain", "value": 1, "units": "mm", "status": "OBSERVED", "availability": "AVAILABLE", "source_uri": "https://example.test/rain", "source_timestamp": datetime.now(UTC).isoformat(), "processing_version": "v1", "quality_status": "validated"}
    event = {"lineage": {"observations": {"rain": obs}}}
    assert lineage_integrity_qa(event, AppMode.OPERATIONAL) == []
    for key, invalid in (("source_timestamp", "2026-01-01T00:00:00"), ("source_uri", ""), ("units", ""), ("value", None), ("status", "UNAVAILABLE")):
        changed = obs | {key: invalid}
        assert lineage_integrity_qa({"lineage": {"observations": {"rain": changed}}}, AppMode.OPERATIONAL)


def test_malformed_lineage_fails_closed():
    for lineage in ("invalid", {"observations": ["invalid"]}, {"observations": {"rain": "invalid"}}):
        assert lineage_integrity_qa({"lineage": lineage}, AppMode.OPERATIONAL)
