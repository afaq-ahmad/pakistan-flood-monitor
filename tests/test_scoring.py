import numpy as np

from app.services.scoring import compute_optical_candidate_support, score_breach_candidate, score_flood_candidate_confidence


def test_score_flood_candidate_confidence_returns_explainable_breakdown() -> None:
    result = score_flood_candidate_confidence(
        mean_anomaly_score=0.9,
        slope_mean=2.0,
        relative_elevation_mean=0.4,
        distance_to_river_m=800.0,
        seasonal_overlap_ratio=0.1,
        hydromet_stress_score=0.8,
        persistence_score=1.0,
    )

    assert 0.0 <= result["confidence"] <= 1.0
    assert result["status"] == "analyst_review"
    assert set(result["components"].keys()) == {
        "sar_anomaly_strength",
        "terrain_plausibility",
        "distance_to_river_reasonableness",
        "hydromet_stress_support",
        "seasonal_water_novelty",
        "persistence_support",
        "optical_support",
    }
    assert set(result["weights"].keys()) == set(result["components"].keys())


def test_score_flood_candidate_confidence_assigns_monitor_only_when_low_signal() -> None:
    result = score_flood_candidate_confidence(
        mean_anomaly_score=0.05,
        slope_mean=30.0,
        relative_elevation_mean=4.0,
        distance_to_river_m=30000.0,
        seasonal_overlap_ratio=1.0,
        hydromet_stress_score=0.0,
        persistence_score=0.0,
    )

    assert result["confidence"] < 0.25
    assert result["status"] == "monitor_only"



def test_optical_support_is_non_blocking_nudge() -> None:
    base = score_flood_candidate_confidence(
        mean_anomaly_score=0.7,
        slope_mean=2.0,
        relative_elevation_mean=0.3,
        distance_to_river_m=1000.0,
        seasonal_overlap_ratio=0.2,
        hydromet_stress_score=0.7,
        persistence_score=0.8,
    )

    nudged = score_flood_candidate_confidence(
        mean_anomaly_score=0.7,
        slope_mean=2.0,
        relative_elevation_mean=0.3,
        distance_to_river_m=1000.0,
        seasonal_overlap_ratio=0.2,
        hydromet_stress_score=0.7,
        persistence_score=0.8,
        optical_support_score=1.0,
        optical_observable_fraction=0.8,
    )

    assert nudged["confidence"] > base["confidence"]


def test_compute_optical_candidate_support_breakdown() -> None:
    candidate = np.array([[1, 1], [1, 1]], dtype=bool)
    confidence = np.array([[0.9, 0.8], [0.2, 0.6]], dtype=float)
    valid = np.array([[1, 1], [0, 1]], dtype=bool)

    metrics = compute_optical_candidate_support(
        candidate_mask=candidate,
        optical_water_confidence=confidence,
        optical_valid_mask=valid,
    )

    assert metrics.supported_fraction > 0
    assert metrics.obscured_fraction > 0
    assert 0.0 <= metrics.optical_support_score <= 1.0


def test_score_breach_candidate_favors_plausible_breach_pattern() -> None:
    result = score_breach_candidate(
        protected_side_ratio=0.9,
        distance_to_embankment_m=120.0,
        expansion_away_from_levee_score=0.85,
        sudden_emergence_score=1.0,
        hydromet_support_score=0.8,
        terrain_plausibility_score=0.9,
        persistence_score=0.75,
        split_merge_complexity=0.0,
    )

    assert result["breach_score"] >= result["alert_threshold"]
    assert result["is_breach_candidate"] is True
    assert result["breach_category"] == "possible_breach_or_protected_side_flooding"
    assert result["published_terminology"] == "high-confidence protected-side flooding"
    assert result["operational_bucket"] in {"analyst review", "review-and-alert-ready"}
    assert set(result["evidence_vector"].keys()) == {
        "protected_side_score",
        "embankment_proximity_score",
        "growth_direction_score",
        "hydromet_stress_score",
        "terrain_plausibility_score",
        "persistence_score",
        "sar_optical_evidence_score",
    }


def test_score_breach_candidate_penalizes_noisy_split_merge_signal() -> None:
    result = score_breach_candidate(
        protected_side_ratio=0.1,
        distance_to_embankment_m=6500.0,
        expansion_away_from_levee_score=0.1,
        sudden_emergence_score=0.2,
        hydromet_support_score=0.1,
        terrain_plausibility_score=0.2,
        persistence_score=0.1,
        split_merge_complexity=1.0,
    )

    assert result["breach_score"] < 0.4
    assert result["is_breach_candidate"] is False
    assert result["breach_category"] == "uncertain_anomaly"
    assert result["published_terminology"] == "uncertain anomaly"
    assert result["operational_bucket"] == "monitor"


def test_score_breach_candidate_detects_likely_overflow_context() -> None:
    result = score_breach_candidate(
        protected_side_ratio=0.1,
        distance_to_embankment_m=5000.0,
        expansion_away_from_levee_score=0.2,
        sudden_emergence_score=0.7,
        hydromet_support_score=0.8,
        terrain_plausibility_score=0.8,
        persistence_score=0.9,
        split_merge_complexity=0.1,
    )

    assert result["breach_category"] == "likely_overflow"
    assert result["published_terminology"] == "likely overflow"
    assert 0.0 <= result["breach_confidence_100"] <= 100.0
