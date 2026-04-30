from app.services.damage_classification import DamageBenchmarkValidator, DamageClassificationRequest, DamageClassificationService


def test_damage_classification_schema_and_lineage() -> None:
    service = DamageClassificationService()
    result = service.classify(
        DamageClassificationRequest(
            event_id="evt-1",
            district_id="d1",
            district_name="District 1",
            housing_exposed_population=12000,
            infrastructure_exposed_roads_km=30,
            infrastructure_facilities_exposed=4,
            flood_probability=0.9,
            breach_risk_score=0.7,
            confidence_score=0.8,
        )
    )

    assert result["housing"]["damage_class"] == "moderate"
    assert result["infrastructure"]["damage_class"] == "moderate"
    assert 0 <= result["confidence"] <= 1
    assert result["lineage"]["model_version"] == "damage-classifier-v1"


def test_damage_benchmark_validation() -> None:
    validator = DamageBenchmarkValidator()
    predictions = [
        {
            "event_id": "evt-1",
            "district_id": "d1",
            "housing": {"damage_class": "minor"},
            "infrastructure": {"damage_class": "major"},
        },
        {
            "event_id": "evt-1",
            "district_id": "d2",
            "housing": {"damage_class": "moderate"},
            "infrastructure": {"damage_class": "minor"},
        },
    ]
    benchmark = [
        {"event_id": "evt-1", "district_id": "d1", "expected_housing_class": "minor", "expected_infrastructure_class": "major"},
        {"event_id": "evt-1", "district_id": "d2", "expected_housing_class": "major", "expected_infrastructure_class": "minor"},
    ]
    metrics = validator.evaluate(predictions, benchmark)
    assert metrics["sample_size"] == 2
    assert metrics["housing_accuracy"] == 0.5
    assert metrics["infrastructure_accuracy"] == 1.0
