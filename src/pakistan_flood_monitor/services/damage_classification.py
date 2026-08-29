"""Canonical home for the temporary, non-authoritative damage classifier."""
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
    HOUSING_THRESHOLDS = {"minor": 1000.0, "moderate": 10000.0, "major": 50000.0}
    INFRA_THRESHOLDS = {"minor": 5.0, "moderate": 25.0, "major": 60.0}

    def classify(self, request: DamageClassificationRequest) -> dict[str, Any]:
        housing_score = request.housing_exposed_population
        infrastructure_score = request.infrastructure_exposed_roads_km + request.infrastructure_facilities_exposed * 2.5
        confidence = max(0.0, min(1.0, mean([request.flood_probability, request.breach_risk_score, request.confidence_score])))
        return {
            "event_id": request.event_id,
            "district_id": request.district_id,
            "district_name": request.district_name,
            "housing": {"damage_class": _classify_threshold(housing_score, self.HOUSING_THRESHOLDS), "impact_score": round(housing_score, 3)},
            "infrastructure": {"damage_class": _classify_threshold(infrastructure_score, self.INFRA_THRESHOLDS), "impact_score": round(infrastructure_score, 3)},
            "confidence": round(confidence, 4),
            "uncertainty": round(max(0.0, 1.0 - confidence), 4),
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
        keyed = {(row["event_id"], row["district_id"]): row for row in predictions}
        total = housing_hits = infrastructure_hits = 0
        for row in benchmark_rows:
            prediction = keyed.get((row["event_id"], row["district_id"]))
            if not prediction:
                continue
            total += 1
            housing_hits += prediction["housing"]["damage_class"] == row["expected_housing_class"]
            infrastructure_hits += prediction["infrastructure"]["damage_class"] == row["expected_infrastructure_class"]
        if not total:
            return {"sample_size": 0, "housing_accuracy": 0.0, "infrastructure_accuracy": 0.0, "joint_accuracy": 0.0}
        return {
            "sample_size": total,
            "housing_accuracy": round(housing_hits / total, 4),
            "infrastructure_accuracy": round(infrastructure_hits / total, 4),
            "joint_accuracy": round(min(housing_hits, infrastructure_hits) / total, 4),
        }


def _classify_threshold(score: float, thresholds: dict[str, float]) -> str:
    if score < thresholds["minor"]:
        return "none"
    if score < thresholds["moderate"]:
        return "minor"
    if score < thresholds["major"]:
        return "moderate"
    return "major"
