from app.services.scoring import score_flood_candidate_confidence


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
