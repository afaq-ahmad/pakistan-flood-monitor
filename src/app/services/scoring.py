from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def score_flood_confidence(raw_score: float, hydromet_weight: float = 0.2) -> float:
    return max(0.0, min(1.0, raw_score * (1 - hydromet_weight) + hydromet_weight))


@dataclass(slots=True)
class FloodCandidateScoreConfig:
    anomaly_weight: float = 0.35
    terrain_weight: float = 0.15
    river_weight: float = 0.2
    hydromet_weight: float = 0.1
    novelty_weight: float = 0.1
    persistence_weight: float = 0.1
    analyst_review_threshold: float = 0.65
    monitor_only_threshold: float = 0.25


def score_flood_candidate_confidence(
    *,
    mean_anomaly_score: float,
    slope_mean: float,
    relative_elevation_mean: float,
    distance_to_river_m: float,
    seasonal_overlap_ratio: float,
    hydromet_stress_score: float,
    persistence_score: float,
    config: FloodCandidateScoreConfig | None = None,
) -> dict[str, Any]:
    """Explainable additive confidence model for analyst-facing candidate triage."""
    cfg = config or FloodCandidateScoreConfig()

    terrain_plausibility = max(
        0.0,
        min(
            1.0,
            1.0 - max((slope_mean - 6.0) / 20.0, 0.0) - max((relative_elevation_mean - 1.0) / 3.0, 0.0),
        ),
    )
    river_reasonableness = max(0.0, min(1.0, 1.0 - (distance_to_river_m / 20000.0)))
    seasonal_novelty = max(0.0, min(1.0, 1.0 - seasonal_overlap_ratio))

    components = {
        "sar_anomaly_strength": max(0.0, min(1.0, mean_anomaly_score)),
        "terrain_plausibility": terrain_plausibility,
        "distance_to_river_reasonableness": river_reasonableness,
        "hydromet_stress_support": max(0.0, min(1.0, hydromet_stress_score)),
        "seasonal_water_novelty": seasonal_novelty,
        "persistence_support": max(0.0, min(1.0, persistence_score)),
    }

    weighted_score = (
        components["sar_anomaly_strength"] * cfg.anomaly_weight
        + components["terrain_plausibility"] * cfg.terrain_weight
        + components["distance_to_river_reasonableness"] * cfg.river_weight
        + components["hydromet_stress_support"] * cfg.hydromet_weight
        + components["seasonal_water_novelty"] * cfg.novelty_weight
        + components["persistence_support"] * cfg.persistence_weight
    )
    confidence = max(0.0, min(1.0, weighted_score))

    if confidence >= cfg.analyst_review_threshold:
        status = "analyst_review"
    elif confidence < cfg.monitor_only_threshold:
        status = "monitor_only"
    else:
        status = "watchlist"

    return {
        "confidence": confidence,
        "status": status,
        "components": components,
        "weights": {
            "sar_anomaly_strength": cfg.anomaly_weight,
            "terrain_plausibility": cfg.terrain_weight,
            "distance_to_river_reasonableness": cfg.river_weight,
            "hydromet_stress_support": cfg.hydromet_weight,
            "seasonal_water_novelty": cfg.novelty_weight,
            "persistence_support": cfg.persistence_weight,
        },
    }
