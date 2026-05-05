"""Tests for Dam-Aware Flood Risk Analysis Module."""
import sys, os, json, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.pakistan_flood_monitor.services.dam_service import (
    get_upstream_dams, get_dam_by_id, get_all_dams, get_dams_for_river,
    detect_reservoir_fill, compute_dam_aware_risk, load_fill_history,
    _haversine, _classify_fill, _generate_explanations,
    DAMS_DATABASE, RIVER_FLOW_GRAPH, CORRIDOR_RIVER_MAP,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Upstream Dam Mapping
# ═══════════════════════════════════════════════════════════════════════════════

class TestDamDatabase:
    def test_database_not_empty(self):
        assert len(DAMS_DATABASE) > 0

    def test_all_dams_have_required_fields(self):
        required = {"dam_id", "name", "country", "river", "lat", "lon",
                     "capacity_mcm", "height_m", "reservoir_bbox"}
        for dam in DAMS_DATABASE:
            missing = required - set(dam.keys())
            assert not missing, f"{dam['name']} missing fields: {missing}"

    def test_unique_dam_ids(self):
        ids = [d["dam_id"] for d in DAMS_DATABASE]
        assert len(ids) == len(set(ids)), "Duplicate dam IDs found"

    def test_get_dam_by_id(self):
        dam = get_dam_by_id("DAM_002")
        assert dam is not None
        assert dam["name"] == "Tarbela Dam"

    def test_get_dam_by_id_not_found(self):
        assert get_dam_by_id("DAM_999") is None

    def test_cross_border_dams_exist(self):
        countries = {d["country"] for d in DAMS_DATABASE}
        assert "India" in countries
        assert "Afghanistan" in countries
        assert "Pakistan" in countries


class TestUpstreamMapping:
    def test_indus_lower_has_dams(self):
        dams = get_upstream_dams("Indus-Lower")
        assert len(dams) > 0

    def test_dams_have_distance(self):
        dams = get_upstream_dams("Indus-Lower")
        for d in dams:
            assert "distance_km" in d
            assert d["distance_km"] > 0

    def test_dams_ordered_by_flow(self):
        dams = get_upstream_dams("Indus-Lower")
        orders = [d["river_connection_order"] for d in dams]
        assert orders == sorted(orders)

    def test_cross_border_flag(self):
        dams = get_upstream_dams("Chenab-Middle")
        cross = [d for d in dams if d["is_cross_border"]]
        assert len(cross) > 0, "Chenab should have Indian cross-border dams"

    def test_unknown_corridor(self):
        dams = get_upstream_dams("Unknown-Corridor")
        assert dams == []

    def test_all_corridors_have_mappings(self):
        for corridor in CORRIDOR_RIVER_MAP:
            dams = get_upstream_dams(corridor)
            assert len(dams) > 0, f"{corridor} has no upstream dams"

    def test_kabul_has_afghan_dams(self):
        dams = get_upstream_dams("Kabul-Nowshera")
        afghan = [d for d in dams if d["country"] == "Afghanistan"]
        assert len(afghan) > 0


class TestHaversine:
    def test_same_point(self):
        assert _haversine(30, 70, 30, 70) == 0.0

    def test_known_distance(self):
        # Islamabad to Karachi ≈ 1200 km
        dist = _haversine(33.69, 73.04, 24.86, 67.01)
        assert 1100 < dist < 1300


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2: Fill Level Classification
# ═══════════════════════════════════════════════════════════════════════════════

class TestFillClassification:
    def test_low(self):
        assert _classify_fill(20.0, 5000) == "low"

    def test_medium(self):
        assert _classify_fill(50.0, 5000) == "medium"

    def test_high(self):
        assert _classify_fill(75.0, 5000) == "high"

    def test_critical(self):
        assert _classify_fill(90.0, 5000) == "critical"

    def test_boundary_high(self):
        assert _classify_fill(65.0, 5000) == "high"

    def test_boundary_critical(self):
        assert _classify_fill(85.0, 5000) == "critical"


class TestReservoirFillDetection:
    def test_detect_fill_returns_required_fields(self):
        dam = get_dam_by_id("DAM_002")
        result = detect_reservoir_fill(dam)
        assert "dam_id" in result
        assert "water_pct" in result
        assert "fill_level" in result
        assert "trend" in result
        assert "confidence" in result
        assert result["fill_level"] in ("low", "medium", "high", "critical")
        assert result["trend"] in ("rising", "stable", "falling")

    def test_fill_saves_history(self):
        dam = get_dam_by_id("DAM_002")
        detect_reservoir_fill(dam)
        history = load_fill_history("DAM_002")
        assert len(history) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3: Flood Risk Scoring
# ═══════════════════════════════════════════════════════════════════════════════

class TestFloodRiskScoring:
    def test_risk_returns_required_fields(self):
        risk = compute_dam_aware_risk("Indus-Lower")
        assert "region_id" in risk
        assert "flood_probability" in risk
        assert "risk_level" in risk
        assert "main_reasons" in risk
        assert 0 <= risk["flood_probability"] <= 100
        assert risk["risk_level"] in ("low", "medium", "high", "critical")
        assert len(risk["main_reasons"]) > 0

    def test_unknown_corridor_risk(self):
        risk = compute_dam_aware_risk("NonExistent")
        assert risk["flood_probability"] == 10
        assert risk["risk_level"] == "low"
        assert risk["dam_count"] == 0

    def test_explainability(self):
        risk = compute_dam_aware_risk("Indus-Lower")
        assert isinstance(risk["main_reasons"], list)
        assert all(isinstance(r, str) for r in risk["main_reasons"])

    def test_all_corridors_produce_risk(self):
        for corridor in CORRIDOR_RIVER_MAP:
            risk = compute_dam_aware_risk(corridor)
            assert risk["region_id"] == corridor


# ═══════════════════════════════════════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_missing_imagery_still_works(self):
        dam = get_dam_by_id("DAM_040")  # Afghan dam — unlikely to have imagery
        result = detect_reservoir_fill(dam, image_path=None)
        assert result["fill_level"] in ("low", "medium", "high", "critical")

    def test_multiple_connected_dams(self):
        dams = get_upstream_dams("Indus-Lower")
        assert len(dams) >= 5, "Indus should have many dams"

    def test_reservoir_bbox_valid(self):
        for dam in DAMS_DATABASE:
            bbox = dam["reservoir_bbox"]
            assert len(bbox) == 4
            assert bbox[0] < bbox[2], f"{dam['name']}: lon_min >= lon_max"
            assert bbox[1] < bbox[3], f"{dam['name']}: lat_min >= lat_max"
