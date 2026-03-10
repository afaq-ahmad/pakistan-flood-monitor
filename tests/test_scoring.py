import numpy as np

from app.services.scoring import compute_optical_candidate_support, score_flood_candidate_confidence


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
