from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import mean
from typing import Any


@dataclass(slots=True)
class DamageClassificationRequest:
    event_id: str
    district_id: str
    district_name: str
    housing_exposed_population: float
    infrastructure_exposed_roads_km: float
    infrastructure_facilities_exposed: float
    flood_probability: float
    breach_risk_score: float
    confidence_score: float
    model_version: str = "damage-classifier-v1"


class DamageClassificationService:
    """Rule-based adapter that converts exposure + model signals to damage classes with lineage."""

    HOUSING_THRESHOLDS = {
        "minor": 1000.0,
        "moderate": 10000.0,
        "major": 50000.0,
    }
    INFRA_THRESHOLDS = {
        "minor": 5.0,
        "moderate": 25.0,
        "major": 60.0,
    }

    def classify(self, request: DamageClassificationRequest) -> dict[str, Any]:
        housing_score = request.housing_exposed_population
        infra_score = (request.infrastructure_exposed_roads_km * 1.0) + (request.infrastructure_facilities_exposed * 2.5)

        housing_class = _classify_threshold(housing_score, self.HOUSING_THRESHOLDS)
        infra_class = _classify_threshold(infra_score, self.INFRA_THRESHOLDS)

        confidence = max(0.0, min(1.0, mean([request.flood_probability, request.breach_risk_score, request.confidence_score])))
        uncertainty = round(max(0.0, 1.0 - confidence), 4)

        return {
            "event_id": request.event_id,
            "district_id": request.district_id,
            "district_name": request.district_name,
            "housing": {
                "damage_class": housing_class,
                "impact_score": round(housing_score, 3),
            },
            "infrastructure": {
                "damage_class": infra_class,
                "impact_score": round(infra_score, 3),
            },
            "confidence": round(confidence, 4),
            "uncertainty": uncertainty,
            "lineage": {
                "model": "rule_adapter_damage_classifier",
                "model_version": request.model_version,
                "generated_at": datetime.now(UTC).isoformat(),
                "inputs": {
                    "housing_exposed_population": request.housing_exposed_population,
                    "roads_exposed_km": request.infrastructure_exposed_roads_km,
                    "facilities_exposed_count": request.infrastructure_facilities_exposed,
                },
            },
        }


class DamageBenchmarkValidator:
    def evaluate(self, predictions: list[dict[str, Any]], benchmark_rows: list[dict[str, Any]]) -> dict[str, Any]:
        keyed = {(r["event_id"], r["district_id"]): r for r in predictions}
        total = 0
        housing_hits = 0
        infra_hits = 0
        for row in benchmark_rows:
            key = (row["event_id"], row["district_id"])
            pred = keyed.get(key)
            if not pred:
                continue
            total += 1
            if pred["housing"]["damage_class"] == row["expected_housing_class"]:
                housing_hits += 1
            if pred["infrastructure"]["damage_class"] == row["expected_infrastructure_class"]:
                infra_hits += 1

        if total == 0:
            return {"sample_size": 0, "housing_accuracy": 0.0, "infrastructure_accuracy": 0.0, "joint_accuracy": 0.0}

        joint = min(housing_hits, infra_hits)
        return {
            "sample_size": total,
            "housing_accuracy": round(housing_hits / total, 4),
            "infrastructure_accuracy": round(infra_hits / total, 4),
            "joint_accuracy": round(joint / total, 4),
        }


def _classify_threshold(score: float, thresholds: dict[str, float]) -> str:
    if score < thresholds["minor"]:
        return "none"
    if score < thresholds["moderate"]:
        return "minor"
    if score < thresholds["major"]:
        return "moderate"
    return "major"
