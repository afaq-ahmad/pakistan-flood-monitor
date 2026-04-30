from pakistan_flood_monitor.services.probabilistic_forecast import (
    build_probabilistic_forecast,
    compute_calibration_stats,
)
from pakistan_flood_monitor.pipeline.runner import FloodMonitoringPipeline


def test_calibration_metrics_are_computed() -> None:
    stats = compute_calibration_stats(
        probabilities=[0.1, 0.2, 0.8, 0.9],
        outcomes=[0, 0, 1, 1],
        bins=2,
    )
    assert stats.sample_size == 4
    assert 0.0 <= stats.expected_calibration_error <= 1.0
    assert 0.0 <= stats.uncertainty_sharpness <= 0.25


def test_probabilistic_forecast_schema_contains_uncertainty_and_lineage() -> None:
    stats = compute_calibration_stats(probabilities=[0.2, 0.6, 0.7], outcomes=[0, 1, 1])
    payload = build_probabilistic_forecast(
        flood_probability=0.65,
        confidence_score=0.7,
        indicators={"rainfall_mm_72h": 140.0, "glofas_return_period": 10.0},
        calibration=stats,
        model_lineage={"model_id": "rules-v1", "training_data_snapshot_version": "snapshot"},
    )

    assert payload["schema"] == "probabilistic-forecast/v1"
    assert payload["uncertainty_envelope"]["lower"] <= payload["probability_of_flooding"] <= payload["uncertainty_envelope"]["upper"]
    assert payload["uncertainty_metrics"]["expected_calibration_error"] >= 0.0
    assert payload["lineage"]["model"]["model_id"] == "rules-v1"


def test_runner_includes_probabilistic_forecast_block() -> None:
    report = FloodMonitoringPipeline().run_daily("Indus-Lower")
    probabilistic = report.detections[0].probabilistic_forecast

    assert probabilistic["schema"] == "probabilistic-forecast/v1"
    assert "uncertainty_envelope" in probabilistic
    assert "uncertainty_metrics" in probabilistic
    assert probabilistic["lineage"]["model"]["model_id"] == "rules-v1"
