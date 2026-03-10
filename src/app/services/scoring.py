def score_flood_confidence(raw_score: float, hydromet_weight: float = 0.2) -> float:
    return max(0.0, min(1.0, raw_score * (1 - hydromet_weight) + hydromet_weight))
