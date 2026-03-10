from datetime import datetime, timedelta
from uuid import uuid4

from pakistan_flood_monitor.config import settings
from pakistan_flood_monitor.core.detection import DetectionFeatures, FloodDetector
from pakistan_flood_monitor.core.exposure import ExposureAnalyzer
from pakistan_flood_monitor.data.sources import DataCatalog
from pakistan_flood_monitor.models.schemas import (
    AlertLevel,
    FloodDetectionResult,
    ProcessingReport,
    ReviewStatus,
)
from pakistan_flood_monitor.services.alerts import AlertService
from pakistan_flood_monitor.services.triggers import EventTriggerService, TriggerInputs


class FloodMonitoringPipeline:
    def __init__(self) -> None:
        self.catalog = DataCatalog()
        self.detector = FloodDetector()
        self.alerts = AlertService()
        self.exposure = ExposureAnalyzer()
        self.triggers = EventTriggerService()

    def _pilot_corridor_enabled(self, aoi_name: str) -> bool:
        return aoi_name in {corridor.name for corridor in settings.pilot_corridors}

    def run_daily(self, aoi_name: str) -> ProcessingReport:
        if not self._pilot_corridor_enabled(aoi_name):
            raise ValueError(f"AOI '{aoi_name}' is outside configured pilot corridors")

        today = datetime.utcnow().date()
        self.catalog.fetch_scenes("sentinel-1", aoi_name, today - timedelta(days=2), today)
        self.catalog.fetch_supporting_layers(aoi_name)

        features = DetectionFeatures(
            sar_drop_db=3.0,
            ndwi=0.31,
            rainfall_mm_72h=120,
            glofas_return_period=5.2,
            floodplain_distance_m=850,
        )

        should_process, trigger_reason = self.triggers.should_process(
            TriggerInputs(
                rainfall_mm_72h=features.rainfall_mm_72h,
                glofas_return_period=features.glofas_return_period,
                seasonal_anomaly_score=0.66,
            )
        )

        if not should_process:
            detection = FloodDetectionResult(
                aoi=aoi_name,
                timestamp=datetime.utcnow(),
                flood_probability=0.0,
                flood_area_km2=0.0,
                breach_risk_score=0.0,
                alert_level=AlertLevel.watch,
                confidence_score=0.0,
                review_status=ReviewStatus.machine_only,
                indicators={"event_trigger": 0.0},
            )
            return ProcessingReport(
                run_id=str(uuid4()),
                source_sensors=["imerg", "glofas"],
                detections=[detection],
                exposure={aoi_name: self.exposure.estimate(0.0)},
                trigger_reason=trigger_reason,
            )

        flood_probability = self.detector.rule_based_probability(features)
        breach_risk = self.detector.detect_breach_risk(expansion_rate=0.62, embankment_side_water=0.7)
        flood_area_km2 = round(25 + flood_probability * 70, 2)
        confidence_score = self.alerts.confidence(flood_probability, breach_risk)
        alert_level = self.alerts.classify(flood_probability, breach_risk)
        review_status = self.alerts.review_status(confidence_score)

        detection = FloodDetectionResult(
            aoi=aoi_name,
            timestamp=datetime.utcnow(),
            flood_probability=flood_probability,
            flood_area_km2=flood_area_km2,
            breach_risk_score=breach_risk,
            alert_level=alert_level,
            confidence_score=confidence_score,
            review_status=review_status,
            indicators={
                "sar_drop_db": features.sar_drop_db,
                "ndwi": features.ndwi,
                "rainfall_mm_72h": features.rainfall_mm_72h,
                "glofas_return_period": features.glofas_return_period,
            },
        )

        return ProcessingReport(
            run_id=str(uuid4()),
            source_sensors=["sentinel-1", "sentinel-2", "landsat", "hls", "imerg", "glofas"],
            detections=[detection],
            exposure={aoi_name: self.exposure.estimate(flood_area_km2)},
            trigger_reason=trigger_reason,
        )
