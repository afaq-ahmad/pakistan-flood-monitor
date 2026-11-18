"""
P0-003: Local exposure boundary and demo watermark tests.

Verifies that:
- In API mode, get_exposure() returns empty and exposure_data_source is "unavailable"
  (prevents mixing local CSV provenance with live API events).
- In demo mode (no API_BASE_URL, APP_MODE=demo), get_exposure() reads local CSV
  and marks exposure_data_source as "local_csv" (or "unavailable" if CSV absent).
- In operational mode (no API_BASE_URL, APP_MODE=operational), get_exposure()
  returns empty and exposure_data_source is "unavailable" (fail-closed).
- is_demo_mode is True only when no API_BASE_URL and APP_MODE in (demo, test).
- DEMO_WATERMARK constant is defined and non-empty.
- summary_stats() with empty exposure remains safe (does not raise).

Tests are deterministic, offline, and require no live data or external services.
"""
import os
import types
import importlib
import sys

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers to reload backend_service with specific env vars
# ---------------------------------------------------------------------------

def _load_backend(monkeypatch, api_base_url: str | None, app_mode: str):
    """Reload backend_service with the given env configuration."""
    if api_base_url is None:
        monkeypatch.delenv("API_BASE_URL", raising=False)
    else:
        monkeypatch.setenv("API_BASE_URL", api_base_url)
    monkeypatch.setenv("APP_MODE", app_mode)

    # Force reload so module-level constants pick up the env changes.
    if "backend_service" in sys.modules:
        del sys.modules["backend_service"]
    import backend_service as bs
    return bs


# ---------------------------------------------------------------------------
# DEMO_WATERMARK constant
# ---------------------------------------------------------------------------

def test_demo_watermark_constant_is_defined():
    import backend_service as bs
    assert hasattr(bs, "DEMO_WATERMARK"), "DEMO_WATERMARK must be exported"
    assert isinstance(bs.DEMO_WATERMARK, str) and len(bs.DEMO_WATERMARK) > 0
    assert "SIMULATED" in bs.DEMO_WATERMARK or "DEMO" in bs.DEMO_WATERMARK


# ---------------------------------------------------------------------------
# is_demo_mode property
# ---------------------------------------------------------------------------

def test_is_demo_mode_true_when_no_api_and_demo(monkeypatch, tmp_path):
    bs = _load_backend(monkeypatch, api_base_url=None, app_mode="demo")
    svc = bs.DataService()
    assert svc.is_demo_mode is True


def test_is_demo_mode_true_when_no_api_and_test(monkeypatch, tmp_path):
    bs = _load_backend(monkeypatch, api_base_url=None, app_mode="test")
    svc = bs.DataService()
    assert svc.is_demo_mode is True


def test_is_demo_mode_false_when_api_configured(monkeypatch):
    bs = _load_backend(monkeypatch, api_base_url="http://localhost:8000", app_mode="demo")
    svc = bs.DataService()
    assert svc.is_demo_mode is False


def test_is_demo_mode_false_when_operational_no_api(monkeypatch):
    bs = _load_backend(monkeypatch, api_base_url=None, app_mode="operational")
    svc = bs.DataService()
    assert svc.is_demo_mode is False


# ---------------------------------------------------------------------------
# get_exposure() — API mode must return empty (prevent mixed provenance)
# ---------------------------------------------------------------------------

def test_exposure_returns_empty_when_api_configured(monkeypatch, tmp_path):
    """When API_BASE_URL is set, local exposure CSV must NOT be returned."""
    bs = _load_backend(monkeypatch, api_base_url="http://localhost:8000", app_mode="operational")
    # Write a CSV that would normally be loaded — it must be suppressed.
    (tmp_path / "exposure_results.csv").write_text(
        "event_id,district,flooded_area_sqkm\nEV-001,Sindh,10.5\n"
    )
    # Point DATA_DIR at tmp_path so the CSV would be found if not suppressed.
    monkeypatch.setattr(bs, "DATA_DIR", tmp_path)
    svc = bs.DataService()
    result = svc.get_exposure()
    assert result.empty, (
        "get_exposure() must return empty when API_BASE_URL is set; "
        "local CSV data must not appear alongside live API events."
    )
    assert svc.exposure_data_source == "unavailable"


def test_exposure_data_source_unavailable_in_api_mode(monkeypatch, tmp_path):
    bs = _load_backend(monkeypatch, api_base_url="http://localhost:8000", app_mode="demo")
    monkeypatch.setattr(bs, "DATA_DIR", tmp_path)
    svc = bs.DataService()
    svc.get_exposure()
    assert svc.exposure_data_source == "unavailable"


# ---------------------------------------------------------------------------
# get_exposure() — Operational mode without API must fail closed
# ---------------------------------------------------------------------------

def test_exposure_fails_closed_in_operational_no_api(monkeypatch, tmp_path):
    """Operational mode without API_BASE_URL must return empty (fail closed)."""
    bs = _load_backend(monkeypatch, api_base_url=None, app_mode="operational")
    (tmp_path / "exposure_results.csv").write_text(
        "event_id,district,flooded_area_sqkm\nEV-001,Sindh,10.5\n"
    )
    monkeypatch.setattr(bs, "DATA_DIR", tmp_path)
    svc = bs.DataService()
    result = svc.get_exposure()
    assert result.empty, (
        "In operational mode without an API, get_exposure() must fail closed."
    )
    assert svc.exposure_data_source == "unavailable"


# ---------------------------------------------------------------------------
# get_exposure() — Demo mode may return local CSV with provenance tag
# ---------------------------------------------------------------------------

def test_exposure_returns_local_csv_in_demo_mode(monkeypatch, tmp_path):
    """In demo mode, local CSV data is returned but marked as local_csv."""
    bs = _load_backend(monkeypatch, api_base_url=None, app_mode="demo")
    csv_content = "event_id,district,flooded_area_sqkm\nEV-001,Sindh,10.5\n"
    (tmp_path / "exposure_results.csv").write_text(csv_content)
    monkeypatch.setattr(bs, "DATA_DIR", tmp_path)
    svc = bs.DataService()
    result = svc.get_exposure()
    assert not result.empty
    assert svc.exposure_data_source == "local_csv"


def test_exposure_unavailable_when_csv_absent_in_demo_mode(monkeypatch, tmp_path):
    """In demo mode with no CSV, exposure_data_source is 'unavailable'."""
    bs = _load_backend(monkeypatch, api_base_url=None, app_mode="demo")
    monkeypatch.setattr(bs, "DATA_DIR", tmp_path)  # tmp_path has no exposure CSV
    svc = bs.DataService()
    result = svc.get_exposure()
    assert result.empty
    assert svc.exposure_data_source == "unavailable"


# ---------------------------------------------------------------------------
# get_exposure() — Test APP_MODE behaves like demo
# ---------------------------------------------------------------------------

def test_exposure_returns_local_csv_in_test_mode(monkeypatch, tmp_path):
    bs = _load_backend(monkeypatch, api_base_url=None, app_mode="test")
    (tmp_path / "exposure_results.csv").write_text(
        "event_id,district,flooded_area_sqkm\nEV-TEST,Punjab,5.2\n"
    )
    monkeypatch.setattr(bs, "DATA_DIR", tmp_path)
    svc = bs.DataService()
    result = svc.get_exposure()
    assert not result.empty
    assert svc.exposure_data_source == "local_csv"


# ---------------------------------------------------------------------------
# summary_stats() safety with empty exposure
# ---------------------------------------------------------------------------

def test_summary_stats_does_not_raise_with_no_events(monkeypatch, tmp_path):
    """summary_stats() must return safe zero values when no events are present."""
    bs = _load_backend(monkeypatch, api_base_url=None, app_mode="demo")
    monkeypatch.setattr(bs, "DATA_DIR", tmp_path)  # no CSV files in tmp_path
    svc = bs.DataService()
    stats = svc.summary_stats()
    assert stats["total_events"] == 0
    assert stats["active_events"] == 0
    assert stats["total_population"] == 0
    assert stats["avg_confidence"] == 0.0


# ---------------------------------------------------------------------------
# get_exposure_for_event() safety
# ---------------------------------------------------------------------------

def test_get_exposure_for_event_returns_empty_when_exposure_is_empty(monkeypatch, tmp_path):
    """When exposure is suppressed (API mode), per-event exposure must also be empty."""
    bs = _load_backend(monkeypatch, api_base_url="http://localhost:8000", app_mode="operational")
    (tmp_path / "exposure_results.csv").write_text(
        "event_id,district,flooded_area_sqkm\nEV-001,Sindh,10.5\n"
    )
    monkeypatch.setattr(bs, "DATA_DIR", tmp_path)
    svc = bs.DataService()
    result = svc.get_exposure_for_event("EV-001")
    assert result.empty


# ---------------------------------------------------------------------------
# generate_export() demo_watermark field
# ---------------------------------------------------------------------------

def test_generate_export_includes_demo_watermark_without_api(monkeypatch, tmp_path):
    """In no-API (demo) mode, generate_export() must include a demo_watermark field."""
    bs = _load_backend(monkeypatch, api_base_url=None, app_mode="demo")
    # Provide a minimal flood_events.csv so get_event() can find EV-001.
    (tmp_path / "flood_events.csv").write_text(
        "event_id,corridor_id,status,severity,confidence,population_exposed,"
        "updated_at,published_at,latitude,longitude,district,event_class,"
        "confidence_band,breach_suspicion,source_scenes\n"
        "EV-001,corridor-1,published,warning,0.85,5000,"
        "2026-01-01T00:00:00Z,2026-01-01T00:00:00Z,30.0,70.0,"
        "Sindh,flood_event,high,False,\n"
    )
    monkeypatch.setattr(bs, "DATA_DIR", tmp_path)
    # Use a temp cache dir so exports don't pollute the repo.
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as cache_dir:
        monkeypatch.chdir(tmp_path)
        svc = bs.DataService()
        result = svc.generate_export("EV-001", "geojson")
    assert "demo_watermark" in result
    assert result["demo_watermark"] is not None
    assert "SIMULATED" in result["demo_watermark"] or "DEMO" in result["demo_watermark"]


# ---------------------------------------------------------------------------
# API event mapping completeness and empty fallback parity
# ---------------------------------------------------------------------------

def test_api_events_empty_fallback_has_all_expected_columns(monkeypatch):
    """When API returns empty, DataFrame columns must match full dashboard expectations."""
    bs = _load_backend(monkeypatch, api_base_url="http://localhost:8000", app_mode="demo")

    class _MockEmptyResponse:
        status_code = 200
        def json(self):
            return {"events": []}

    monkeypatch.setattr("httpx.get", lambda *a, **kw: _MockEmptyResponse())
    svc = bs.DataService()
    df = svc.get_events()
    expected = [
        "event_id", "corridor_id", "status", "severity", "confidence",
        "population_exposed", "updated_at", "published_at", "detected_at",
        "latitude", "longitude", "district", "tehsil", "event_class",
        "confidence_band", "breach_suspicion", "source_scenes",
        "affected_area_sqkm", "roads_exposed_km", "health_facilities_exposed",
        "schools_exposed", "cropland_exposed_sqkm", "what_changed",
        "what_this_means_en", "what_this_means_ur", "limitations",
    ]
    for col in expected:
        assert col in df.columns, f"Expected column {col} in empty API event fallback"


def test_api_events_mapping_populates_detected_at_and_exposure_fields(monkeypatch):
    """When API returns valid events, fields like detected_at, tehsil, etc. are mapped."""
    bs = _load_backend(monkeypatch, api_base_url="http://localhost:8000", app_mode="demo")

    sample_event = {
        "event_id": "EVT-TEST-001",
        "aoi": "Indus-Lower",
        "status": "published",
        "machine_confidence": 0.88,
        "confidence_band": "high",
        "breach_suspicion": 0.12,
        "district": "Dadu",
        "tehsil": "Mehar",
        "event_class": "flood",
        "latest_event_summary": {"alert_level": "critical"},
        "exposure": {
            "asset_class_exposure": {
                "population": 12000,
                "roads_km": 15.5,
                "health_facilities": 2,
                "schools": 5,
                "cropland_sqkm": 20.0,
            }
        },
        "timestamps": {
            "detected_at": "2026-05-01T04:00:00Z",
            "published_at": "2026-05-01T06:00:00Z",
        },
        "geometry": {"coordinates": [[[67.78, 26.73]]]},
        "what_changed": "Extent increased",
        "what_this_means_en": "Critical flooding near Dadu",
        "what_this_means_ur": "دادو کے قریب سیلاب",
        "limitations": "Model-derived",
    }

    class _MockValidResponse:
        status_code = 200
        def json(self):
            return {"events": [sample_event]}

    monkeypatch.setattr("httpx.get", lambda *a, **kw: _MockValidResponse())
    svc = bs.DataService()
    df = svc.get_events()
    assert len(df) == 1
    row = df.iloc[0]
    assert row["event_id"] == "EVT-TEST-001"
    assert row["detected_at"] == "2026-05-01T04:00:00Z"
    assert row["tehsil"] == "Mehar"
    assert row["roads_exposed_km"] == 15.5
    assert row["health_facilities_exposed"] == 2
    assert row["schools_exposed"] == 5
    assert row["cropland_exposed_sqkm"] == 20.0
    assert row["what_this_means_ur"] == "دادو کے قریب سیلاب"
