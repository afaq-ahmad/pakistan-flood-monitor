from pakistan_flood_monitor.config import settings
from pakistan_flood_monitor.models.schemas import AlertLevel, ReviewStatus


class AlertService:
    def confidence(self, flood_probability: float, breach_risk_score: float) -> float:
        return (flood_probability * 0.7) + (breach_risk_score * 0.3)

    def classify(self, flood_probability: float, breach_risk_score: float) -> AlertLevel:
        combined = self.confidence(flood_probability, breach_risk_score)
        if combined >= settings.thresholds.confidence_critical:
            return AlertLevel.critical
        if combined >= settings.thresholds.confidence_warning:
            return AlertLevel.warning
        return AlertLevel.watch

    def review_status(self, confidence_score: float) -> ReviewStatus:
        if confidence_score < settings.thresholds.analyst_review_min_confidence:
            return ReviewStatus.analyst_review_required
        return ReviewStatus.machine_only
