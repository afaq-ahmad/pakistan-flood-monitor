from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True)
class CalibrationStats:
    sample_size: int
    expected_calibration_error: float
    uncertainty_sharpness: float


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def compute_calibration_stats(*, probabilities: list[float], outcomes: list[int], bins: int = 5) -> CalibrationStats:
    if len(probabilities) != len(outcomes):
        raise ValueError("probabilities and outcomes must have the same length")
    if not probabilities:
        return CalibrationStats(sample_size=0, expected_calibration_error=0.0, uncertainty_sharpness=0.0)

    indexed_bins: list[list[tuple[float, int]]] = [[] for _ in range(bins)]
    for probability, outcome in zip(probabilities, outcomes, strict=True):
        p = _clamp01(float(probability))
        idx = min(bins - 1, int(p * bins))
        indexed_bins[idx].append((p, int(outcome)))

    n = len(probabilities)
    ece = 0.0
    variances: list[float] = []
    for bucket in indexed_bins:
        if not bucket:
            continue
        ps = [item[0] for item in bucket]
        ys = [item[1] for item in bucket]
        avg_p = sum(ps) / len(ps)
        avg_y = sum(ys) / len(ys)
        ece += (len(bucket) / n) * abs(avg_p - avg_y)
        variances.append(avg_p * (1.0 - avg_p))

    sharpness = sum(variances) / len(variances) if variances else 0.0
    return CalibrationStats(sample_size=n, expected_calibration_error=round(ece, 4), uncertainty_sharpness=round(sharpness, 4))


def build_probabilistic_forecast(*, flood_probability: float, confidence_score: float, indicators: dict[str, float], calibration: CalibrationStats, model_lineage: dict) -> dict:
    base_probability = _clamp01(0.6 * flood_probability + 0.4 * confidence_score)
    hydromet_intensity = _clamp01(0.5 * indicators.get("rainfall_mm_72h", 0.0) / 200.0 + 0.5 * indicators.get("glofas_return_period", 0.0) / 20.0)
    adjusted_probability = _clamp01(0.75 * base_probability + 0.25 * hydromet_intensity)

    epistemic = min(0.35, 1.0 / sqrt(max(calibration.sample_size, 1)))
    aleatoric = adjusted_probability * (1 - adjusted_probability)
    spread = min(0.45, epistemic + 0.6 * aleatoric)

    lower = _clamp01(adjusted_probability - spread)
    upper = _clamp01(adjusted_probability + spread)

    return {
        "schema": "probabilistic-forecast/v1",
        "probability_of_flooding": round(adjusted_probability, 4),
        "uncertainty_envelope": {
            "lower": round(lower, 4),
            "upper": round(upper, 4),
            "confidence_level": 0.9,
        },
        "uncertainty_metrics": {
            "epistemic": round(epistemic, 4),
            "aleatoric": round(aleatoric, 4),
            "expected_calibration_error": calibration.expected_calibration_error,
            "sharpness": calibration.uncertainty_sharpness,
            "calibration_sample_size": calibration.sample_size,
        },
        "assumptions": [
            "Hydromet intensity is represented by normalized 72h rainfall and GloFAS return period.",
            "Uncertainty envelope is heuristic and should not be used as a sole evacuation trigger.",
        ],
        "lineage": {
            "model": model_lineage,
            "method": "rules-v1 + hydromet-adapter-v1",
        },
    }
