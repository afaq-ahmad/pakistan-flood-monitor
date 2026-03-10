from dataclasses import dataclass


@dataclass
class TriggerInputs:
    rainfall_mm_72h: float
    glofas_return_period: float
    seasonal_anomaly_score: float


class EventTriggerService:
    """Low-cost event-first trigger that avoids full-country brute-force processing."""

    def should_process(self, trigger: TriggerInputs) -> tuple[bool, str]:
        if trigger.rainfall_mm_72h >= 80:
            return True, "IMERG rainfall trigger"
        if trigger.glofas_return_period >= 3:
            return True, "GloFAS river forecast trigger"
        if trigger.seasonal_anomaly_score >= 0.5:
            return True, "historical water anomaly trigger"
        return False, "no event trigger"
