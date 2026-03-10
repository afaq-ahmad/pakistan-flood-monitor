from dataclasses import dataclass

import numpy as np


@dataclass
class DetectionFeatures:
    sar_drop_db: float
    ndwi: float
    rainfall_mm_72h: float
    glofas_return_period: float
    floodplain_distance_m: float


class FloodDetector:
    def rule_based_probability(self, features: DetectionFeatures) -> float:
        score = 0.0
        score += min(max((features.sar_drop_db - 1.0) / 4.0, 0.0), 1.0) * 0.35
        score += min(max((features.ndwi - 0.05) / 0.35, 0.0), 1.0) * 0.25
        score += min(features.rainfall_mm_72h / 200.0, 1.0) * 0.2
        score += min(features.glofas_return_period / 10.0, 1.0) * 0.15
        score += (1.0 - min(features.floodplain_distance_m / 4000.0, 1.0)) * 0.05
        return float(np.clip(score, 0.0, 1.0))

    def detect_breach_risk(self, expansion_rate: float, embankment_side_water: float) -> float:
        return float(np.clip((expansion_rate * 0.6) + (embankment_side_water * 0.4), 0.0, 1.0))
