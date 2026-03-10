from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.hydromet import get_reach_hydrology_thresholds


@dataclass(slots=True)
class OpticalSupportMetrics:
    supported_fraction: float
    obscured_fraction: float
    uncertain_fraction: float
    observable_fraction: float
    optical_support_score: float


@dataclass(slots=True)
class HydrologicPlausibilityResult:
    plausibility_score: float
    rainfall_sufficiency: float
    forecast_elevation: float
    terrain_allowance: float
    timing_consistency: float
    inland_penalty: float
    overtopping_signal: float


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
    plausibility_weight: float = 0.18
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


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _piecewise_threshold_score(value: float, watch: float, warning: float, critical: float) -> float:
    value = max(0.0, value)
    if value <= watch:
        return _clamp01(0.5 * (value / max(watch, 1e-6)))
    if value <= warning:
        return _clamp01(0.5 + 0.25 * ((value - watch) / max(warning - watch, 1e-6)))
    if value <= critical:
        return _clamp01(0.75 + 0.25 * ((value - warning) / max(critical - warning, 1e-6)))
    return 1.0


def compute_hydrologic_plausibility(
    *,
    corridor_reach: str | None,
    rainfall_24h_mm: float | None,
    rainfall_72h_mm: float | None,
    forecast_discharge_percentile: float | None,
    terrain_plausibility: float,
    persistence_score: float,
    inland_propagation_direction: float,
) -> HydrologicPlausibilityResult:
    thresholds = get_reach_hydrology_thresholds(corridor_reach)

    rain24 = _piecewise_threshold_score(
        float(rainfall_24h_mm or 0.0),
        thresholds.rainfall_watch_24h_mm,
        thresholds.rainfall_warning_24h_mm,
        thresholds.rainfall_critical_24h_mm,
    )
    rain72 = _piecewise_threshold_score(
        float(rainfall_72h_mm or 0.0),
        thresholds.rainfall_watch_72h_mm,
        thresholds.rainfall_warning_72h_mm,
        thresholds.rainfall_critical_72h_mm,
    )
    rainfall_sufficiency = _clamp01(0.45 * rain24 + 0.55 * rain72)

    forecast_elevation = _piecewise_threshold_score(
        float(forecast_discharge_percentile or 0.0),
        thresholds.discharge_watch_percentile,
        thresholds.discharge_warning_percentile,
        thresholds.discharge_critical_percentile,
    )
    terrain_allowance = _clamp01(terrain_plausibility)
    timing_consistency = _clamp01(0.65 * persistence_score + 0.35 * max(rainfall_sufficiency, forecast_elevation))

    inland_penalty = _clamp01(inland_propagation_direction * max(0.0, 0.7 - max(rainfall_sufficiency, forecast_elevation)))
    overtopping_signal = _clamp01((1.0 - inland_propagation_direction) * max(rainfall_sufficiency, forecast_elevation))

    plausibility_score = _clamp01(
        0.30 * rainfall_sufficiency
        + 0.25 * forecast_elevation
        + 0.20 * terrain_allowance
        + 0.15 * timing_consistency
        + 0.10 * overtopping_signal
        - 0.20 * inland_penalty
    )

    return HydrologicPlausibilityResult(
        plausibility_score=plausibility_score,
        rainfall_sufficiency=rainfall_sufficiency,
        forecast_elevation=forecast_elevation,
        terrain_allowance=terrain_allowance,
        timing_consistency=timing_consistency,
        inland_penalty=inland_penalty,
        overtopping_signal=overtopping_signal,
    )


def _bucketize_breach_confidence(confidence_100: float) -> str:
    if confidence_100 < 35.0:
        return "monitor"
    if confidence_100 < 55.0:
        return "watch"
    if confidence_100 < 75.0:
        return "analyst review"
    return "review-and-alert-ready"


def _classify_breach_category(
    *,
    protected_side_score: float,
    embankment_proximity_score: float,
    growth_direction_score: float,
    hydromet_stress_score: float,
    terrain_plausibility_score: float,
    persistence_score: float,
    sar_optical_evidence_score: float,
) -> str:
    strong_protected_side = protected_side_score >= 0.6
    near_embankment = embankment_proximity_score >= 0.55
    inland_growth = growth_direction_score >= 0.55
    supported_context = hydromet_stress_score >= 0.4 and terrain_plausibility_score >= 0.45

    if strong_protected_side and near_embankment and inland_growth and supported_context and sar_optical_evidence_score >= 0.45:
        return "possible_breach_or_protected_side_flooding"

    likely_overflow_context = (
        protected_side_score < 0.4
        and hydromet_stress_score >= 0.55
        and terrain_plausibility_score >= 0.55
        and persistence_score >= 0.4
        and growth_direction_score < 0.55
        and sar_optical_evidence_score >= 0.35
    )
    if likely_overflow_context:
        return "likely_overflow"

    return "uncertain_anomaly"


def score_flood_candidate_confidence(
    *,
    mean_anomaly_score: float,
    slope_mean: float,
    relative_elevation_mean: float,
    distance_to_river_m: float,
    seasonal_overlap_ratio: float,
    hydromet_stress_score: float,
    persistence_score: float,
    corridor_reach: str | None = None,
    rainfall_24h_mm: float | None = None,
    rainfall_72h_mm: float | None = None,
    forecast_discharge_percentile: float | None = None,
    inland_propagation_direction: float = 0.0,
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

    hydrologic_plausibility = compute_hydrologic_plausibility(
        corridor_reach=corridor_reach,
        rainfall_24h_mm=rainfall_24h_mm,
        rainfall_72h_mm=rainfall_72h_mm,
        forecast_discharge_percentile=forecast_discharge_percentile,
        terrain_plausibility=terrain_plausibility,
        persistence_score=persistence_score,
        inland_propagation_direction=inland_propagation_direction,
    )

    optical_component = 0.5 if optical_support_score is None else max(0.0, min(1.0, optical_support_score))

    components = {
        "sar_anomaly_strength": max(0.0, min(1.0, mean_anomaly_score)),
        "terrain_plausibility": terrain_plausibility,
        "distance_to_river_reasonableness": river_reasonableness,
        "hydromet_stress_support": max(0.0, min(1.0, hydromet_stress_score)),
        "seasonal_water_novelty": seasonal_novelty,
        "persistence_support": max(0.0, min(1.0, persistence_score)),
        "hydrologic_plausibility": hydrologic_plausibility.plausibility_score,
        "optical_support": optical_component,
    }

    weighted_score = (
        components["sar_anomaly_strength"] * cfg.anomaly_weight
        + components["terrain_plausibility"] * cfg.terrain_weight
        + components["distance_to_river_reasonableness"] * cfg.river_weight
        + components["hydromet_stress_support"] * cfg.hydromet_weight
        + components["seasonal_water_novelty"] * cfg.novelty_weight
        + components["persistence_support"] * cfg.persistence_weight
        + components["hydrologic_plausibility"] * cfg.plausibility_weight
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
        "hydrologic_plausibility": {
            "plausibility_score": hydrologic_plausibility.plausibility_score,
            "rainfall_sufficiency": hydrologic_plausibility.rainfall_sufficiency,
            "forecast_elevation": hydrologic_plausibility.forecast_elevation,
            "terrain_allowance": hydrologic_plausibility.terrain_allowance,
            "timing_consistency": hydrologic_plausibility.timing_consistency,
            "inland_penalty": hydrologic_plausibility.inland_penalty,
            "overtopping_signal": hydrologic_plausibility.overtopping_signal,
        },
        "weights": {
            "sar_anomaly_strength": cfg.anomaly_weight,
            "terrain_plausibility": cfg.terrain_weight,
            "distance_to_river_reasonableness": cfg.river_weight,
            "hydromet_stress_support": cfg.hydromet_weight,
            "seasonal_water_novelty": cfg.novelty_weight,
            "persistence_support": cfg.persistence_weight,
            "hydrologic_plausibility": cfg.plausibility_weight,
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

    embankment_proximity = _clamp01(1.0 - (distance_to_embankment_m / 5000.0))
    split_merge_penalty = _clamp01(split_merge_complexity)
    sar_optical_evidence_score = _clamp01(0.6 * sudden_emergence_score + 0.4 * (1.0 - split_merge_penalty))

    components = {
        "protected_side_flooding": _clamp01(protected_side_ratio),
        "embankment_proximity": embankment_proximity,
        "expansion_away_from_levee": _clamp01(expansion_away_from_levee_score),
        "sudden_appearance": _clamp01(sudden_emergence_score),
        "hydromet_support": _clamp01(hydromet_support_score),
        "terrain_plausibility": _clamp01(terrain_plausibility_score),
        "persistence": _clamp01(persistence_score),
        "split_merge_penalty": split_merge_penalty,
    }

    evidence_vector = {
        "protected_side_score": components["protected_side_flooding"],
        "embankment_proximity_score": components["embankment_proximity"],
        "growth_direction_score": components["expansion_away_from_levee"],
        "hydromet_stress_score": components["hydromet_support"],
        "terrain_plausibility_score": components["terrain_plausibility"],
        "persistence_score": components["persistence"],
        "sar_optical_evidence_score": sar_optical_evidence_score,
    }

    breach_category = _classify_breach_category(**evidence_vector)

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
    breach_score = _clamp01(score)
    breach_confidence_100 = round(breach_score * 100.0, 2)
    operational_bucket = _bucketize_breach_confidence(breach_confidence_100)

    if breach_category == "possible_breach_or_protected_side_flooding":
        published_terminology = (
            "high-confidence protected-side flooding"
            if breach_confidence_100 >= 70.0
            else "possible breach"
        )
    elif breach_category == "likely_overflow":
        published_terminology = "likely overflow"
    else:
        published_terminology = "uncertain anomaly"

    return {
        "breach_score": breach_score,
        "is_breach_candidate": breach_score >= cfg.breach_alert_min_score,
        "breach_confidence_100": breach_confidence_100,
        "operational_bucket": operational_bucket,
        "breach_category": breach_category,
        "published_terminology": published_terminology,
        "evidence_vector": evidence_vector,
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
