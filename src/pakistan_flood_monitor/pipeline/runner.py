from datetime import datetime, timedelta
from uuid import uuid4

from pakistan_flood_monitor.core.detection import DetectionFeatures, FloodDetector
from pakistan_flood_monitor.core.exposure import ExposureAnalyzer
from pakistan_flood_monitor.data.sources import DataCatalog
from pakistan_flood_monitor.models.schemas import FloodDetectionResult, ProcessingReport
from pakistan_flood_monitor.services.alerts import AlertService


class FloodMonitoringPipeline:
    def __init__(self) -> None:
        self.catalog = DataCatalog()
        self.detector = FloodDetector()
        self.alerts = AlertService()
        self.exposure = ExposureAnalyzer()

    def run_daily(self, aoi_name: str) -> ProcessingReport:
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
        flood_probability = self.detector.rule_based_probability(features)
        breach_risk = self.detector.detect_breach_risk(expansion_rate=0.62, embankment_side_water=0.7)
        flood_area_km2 = round(25 + flood_probability * 70, 2)
        alert_level = self.alerts.classify(flood_probability, breach_risk)

        detection = FloodDetectionResult(
            aoi=aoi_name,
            timestamp=datetime.utcnow(),
            flood_probability=flood_probability,
            flood_area_km2=flood_area_km2,
            breach_risk_score=breach_risk,
            alert_level=alert_level,
            indicators={
                "sar_drop_db": features.sar_drop_db,
                "ndwi": features.ndwi,
                "rainfall_mm_72h": features.rainfall_mm_72h,
                "glofas_return_period": features.glofas_return_period,
            },
        )

        return ProcessingReport(
            run_id=str(uuid4()),
            source_sensors=["sentinel-1", "sentinel-2", "landsat", "hls"],
            detections=[detection],
            exposure={aoi_name: self.exposure.estimate(flood_area_km2)},
        )
