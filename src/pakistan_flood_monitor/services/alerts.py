from pakistan_flood_monitor.config import settings
from pakistan_flood_monitor.models.schemas import AlertLevel


class AlertService:
    def classify(self, flood_probability: float, breach_risk_score: float) -> AlertLevel:
        combined = (flood_probability * 0.7) + (breach_risk_score * 0.3)
        if combined >= settings.thresholds.confidence_critical:
            return AlertLevel.critical
        if combined >= settings.thresholds.confidence_warning:
            return AlertLevel.warning
        return AlertLevel.watch
