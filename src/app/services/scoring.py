from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class OpticalSupportMetrics:
    supported_fraction: float
    obscured_fraction: float
    uncertain_fraction: float
    observable_fraction: float
    optical_support_score: float


def compute_optical_candidate_support(
    *,
    candidate_mask,
    optical_water_confidence,
    optical_valid_mask,
    support_threshold: float = 0.55,
    uncertain_threshold: float = 0.35,
) -> OpticalSupportMetrics:
    candidate = candidate_mask.astype(bool)
    total = int(candidate.sum())
    if total == 0:
        return OpticalSupportMetrics(0.0, 0.0, 0.0, 0.0, 0.5)

    valid = optical_valid_mask.astype(bool) & candidate
    obscured = (~optical_valid_mask.astype(bool)) & candidate

    supported = valid & (optical_water_confidence >= support_threshold)
    uncertain = valid & (optical_water_confidence >= uncertain_threshold) & (optical_water_confidence < support_threshold)

    supported_fraction = float(supported.sum() / total)
    obscured_fraction = float(obscured.sum() / total)
    uncertain_fraction = float(uncertain.sum() / total)
    observable_fraction = float(valid.sum() / total)

    if observable_fraction < 0.15:
        optical_support_score = 0.5
    else:
        score_raw = (supported_fraction / max(observable_fraction, 1e-6)) - (uncertain_fraction / max(observable_fraction, 1e-6)) * 0.3
        optical_support_score = max(0.0, min(1.0, (score_raw + 0.15) / 1.15))

    return OpticalSupportMetrics(
        supported_fraction=supported_fraction,
        obscured_fraction=obscured_fraction,
        uncertain_fraction=uncertain_fraction,
        observable_fraction=observable_fraction,
        optical_support_score=optical_support_score,
    )

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
    optical_weight: float = 0.1
    analyst_review_threshold: float = 0.65
    monitor_only_threshold: float = 0.25


@dataclass(slots=True)
class BreachCandidateScoreConfig:
    protected_side_weight: float = 0.22
    embankment_proximity_weight: float = 0.2
    away_from_levee_expansion_weight: float = 0.16
    sudden_appearance_weight: float = 0.12
    hydromet_support_weight: float = 0.12
    terrain_plausibility_weight: float = 0.1
    persistence_weight: float = 0.08
    splitting_merging_penalty_weight: float = 0.08
    breach_alert_min_score: float = 0.68


def score_flood_candidate_confidence(
    *,
    mean_anomaly_score: float,
    slope_mean: float,
    relative_elevation_mean: float,
    distance_to_river_m: float,
    seasonal_overlap_ratio: float,
    hydromet_stress_score: float,
    persistence_score: float,
    optical_support_score: float | None = None,
    optical_observable_fraction: float = 0.0,
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

    optical_component = 0.5 if optical_support_score is None else max(0.0, min(1.0, optical_support_score))

    components = {
        "sar_anomaly_strength": max(0.0, min(1.0, mean_anomaly_score)),
        "terrain_plausibility": terrain_plausibility,
        "distance_to_river_reasonableness": river_reasonableness,
        "hydromet_stress_support": max(0.0, min(1.0, hydromet_stress_score)),
        "seasonal_water_novelty": seasonal_novelty,
        "persistence_support": max(0.0, min(1.0, persistence_score)),
        "optical_support": optical_component,
    }

    weighted_score = (
        components["sar_anomaly_strength"] * cfg.anomaly_weight
        + components["terrain_plausibility"] * cfg.terrain_weight
        + components["distance_to_river_reasonableness"] * cfg.river_weight
        + components["hydromet_stress_support"] * cfg.hydromet_weight
        + components["seasonal_water_novelty"] * cfg.novelty_weight
        + components["persistence_support"] * cfg.persistence_weight
    )
    if optical_observable_fraction > 0.15:
        weighted_score += (components["optical_support"] - 0.5) * cfg.optical_weight
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
            "optical_support": cfg.optical_weight if optical_observable_fraction > 0.15 else 0.0,
        },
    }


def score_breach_candidate(
    *,
    protected_side_ratio: float,
    distance_to_embankment_m: float,
    expansion_away_from_levee_score: float,
    sudden_emergence_score: float,
    hydromet_support_score: float,
    terrain_plausibility_score: float,
    persistence_score: float,
    split_merge_complexity: float,
    config: BreachCandidateScoreConfig | None = None,
) -> dict[str, Any]:
    """Second-stage breach scorer that operates on accepted flood candidates only."""
    cfg = config or BreachCandidateScoreConfig()

    embankment_proximity = max(0.0, min(1.0, 1.0 - (distance_to_embankment_m / 5000.0)))
    split_merge_penalty = max(0.0, min(1.0, split_merge_complexity))

    components = {
        "protected_side_flooding": max(0.0, min(1.0, protected_side_ratio)),
        "embankment_proximity": embankment_proximity,
        "expansion_away_from_levee": max(0.0, min(1.0, expansion_away_from_levee_score)),
        "sudden_appearance": max(0.0, min(1.0, sudden_emergence_score)),
        "hydromet_support": max(0.0, min(1.0, hydromet_support_score)),
        "terrain_plausibility": max(0.0, min(1.0, terrain_plausibility_score)),
        "persistence": max(0.0, min(1.0, persistence_score)),
        "split_merge_penalty": split_merge_penalty,
    }

    score = (
        components["protected_side_flooding"] * cfg.protected_side_weight
        + components["embankment_proximity"] * cfg.embankment_proximity_weight
        + components["expansion_away_from_levee"] * cfg.away_from_levee_expansion_weight
        + components["sudden_appearance"] * cfg.sudden_appearance_weight
        + components["hydromet_support"] * cfg.hydromet_support_weight
        + components["terrain_plausibility"] * cfg.terrain_plausibility_weight
        + components["persistence"] * cfg.persistence_weight
        - components["split_merge_penalty"] * cfg.splitting_merging_penalty_weight
    )
    breach_score = max(0.0, min(1.0, score))

    return {
        "breach_score": breach_score,
        "is_breach_candidate": breach_score >= cfg.breach_alert_min_score,
        "components": components,
        "weights": {
            "protected_side_flooding": cfg.protected_side_weight,
            "embankment_proximity": cfg.embankment_proximity_weight,
            "expansion_away_from_levee": cfg.away_from_levee_expansion_weight,
            "sudden_appearance": cfg.sudden_appearance_weight,
            "hydromet_support": cfg.hydromet_support_weight,
            "terrain_plausibility": cfg.terrain_plausibility_weight,
            "persistence": cfg.persistence_weight,
            "split_merge_penalty": cfg.splitting_merging_penalty_weight,
        },
        "alert_threshold": cfg.breach_alert_min_score,
    }
