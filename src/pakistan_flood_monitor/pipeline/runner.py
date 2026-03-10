from datetime import datetime, timedelta
from uuid import uuid4

from pakistan_flood_monitor.config import settings
from pakistan_flood_monitor.core.detection import DetectionFeatures, FloodDetector
from pakistan_flood_monitor.core.exposure import ExposureAnalyzer
from pakistan_flood_monitor.data.sources import DataCatalog
from pakistan_flood_monitor.models.schemas import (
    AlertLevel,
    AlertSummary,
    AssetExposureReport,
    BreachCategory,
    BreachSuspicionLayer,
    ConfirmedFloodExtent,
    EventClass,
    EventDecision,
    FloodCandidateMap,
    FloodDetectionResult,
    HistoricalEventRecord,
    ModelVersion,
    MVPOutputs,
    ProcessingReport,
    ReviewQueueEvent,
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

    def _event_class(self, alert_level: AlertLevel, breach_risk: float, confidence_score: float) -> EventClass:
        if confidence_score < 0.25:
            return EventClass.false_positive
        if breach_risk >= 0.75:
            return EventClass.possible_breach
        if alert_level == AlertLevel.critical:
            return EventClass.flood
        if alert_level == AlertLevel.warning:
            return EventClass.likely_overflow
        return EventClass.uncertain

    def _build_review_queue_event(
        self,
        run_id: str,
        aoi_name: str,
        source_scenes: list[str],
        alert_level: AlertLevel,
        breach_risk: float,
        confidence_score: float,
        review_status: ReviewStatus,
    ) -> ReviewQueueEvent:
        event_class = self._event_class(alert_level, breach_risk, confidence_score)
        decision = EventDecision.accept if review_status == ReviewStatus.machine_only else None
        return ReviewQueueEvent(
            event_id=f"evt-{run_id}",
            run_id=run_id,
            aoi=aoi_name,
            event_class=event_class,
            machine_confidence=round(confidence_score * 100, 2),
            analyst_confidence=None,
            decision=decision,
            notes="Auto-generated event for analyst queue.",
            source_scenes=source_scenes,
        )

    def _active_model_version(self) -> ModelVersion:
        return ModelVersion(
            model_id="rules-v1",
            training_data_snapshot_version="snapshot-2024-08-baseline",
            training_config_path="configs/training_config.yaml",
            threshold_file_path="configs/alert_thresholds.yaml",
            evaluation_report_path="reports/evaluation/rules_v1.md",
            reproducible_training_script="scripts/train_candidate_ranker.py",
            rollback_model_id=None,
        )

    def _build_outputs(
        self,
        run_id: str,
        aoi_name: str,
        review_status: ReviewStatus,
        alert_level: AlertLevel,
        confidence_score: float,
        breach_risk: float,
        source_scenes: list[str],
        exposure_report: dict,
    ) -> MVPOutputs:
        polygon_ids = [f"{aoi_name}-candidate-001", f"{aoi_name}-candidate-002"]
        breach_category = (
            BreachCategory.likely_embankment_failure
            if confidence_score >= 0.8
            else BreachCategory.uncertain_anomaly
        )

        return MVPOutputs(
            flood_candidate_map=FloodCandidateMap(aoi=aoi_name, run_id=run_id, polygon_ids=polygon_ids),
            confirmed_flood_extent=ConfirmedFloodExtent(
                aoi=aoi_name,
                run_id=run_id,
                review_status=review_status,
                approved_polygon_ids=polygon_ids if review_status == ReviewStatus.analyst_validated else [],
            ),
            breach_suspicion_layer=BreachSuspicionLayer(
                aoi=aoi_name,
                run_id=run_id,
                candidate_id=f"{aoi_name}-breach-001",
                category=breach_category,
                confidence_score=round(confidence_score * 100, 2),
            ),
            asset_exposure_report=AssetExposureReport(
                aoi=aoi_name,
                district=aoi_name,
                asset_class_exposure={
                    "population": exposure_report["affected_population"],
                    "cropland_km2": exposure_report["affected_cropland_km2"],
                    "roads_km": exposure_report["affected_roads_km"],
                    "schools": exposure_report["affected_schools"],
                    "hospitals": exposure_report["affected_hospitals"],
                },
            ),
            alert_feed_item=AlertSummary(
                alert_id=f"alert-{run_id}",
                aoi=aoi_name,
                alert_level=alert_level,
                confidence_score=round(confidence_score * 100, 2),
                summary=f"{alert_level.value} flood signal for {aoi_name}",
            ),
            model_version=self._active_model_version(),
            review_queue_event=self._build_review_queue_event(
                run_id,
                aoi_name,
                source_scenes,
                alert_level,
                breach_risk,
                confidence_score,
                review_status,
            ),
            historical_event_dashboard=[
                HistoricalEventRecord(
                    event_id=f"hist-{aoi_name}-2022",
                    aoi=aoi_name,
                    peak_date=datetime(2022, 8, 25),
                    flood_area_km2=135.4,
                    label_quality_tier=1,
                )
            ],
        )

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

        run_id = str(uuid4())
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
            exposure = self.exposure.estimate(0.0)
            return ProcessingReport(
                run_id=run_id,
                source_sensors=["imerg", "glofas"],
                detections=[detection],
                exposure={aoi_name: exposure},
                trigger_reason=trigger_reason,
                published_outputs=self._build_outputs(
                    run_id,
                    aoi_name,
                    ReviewStatus.machine_only,
                    AlertLevel.watch,
                    0.0,
                    0.0,
                    ["imerg", "glofas"],
                    exposure.model_dump(),
                ),
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

        source_sensors = ["sentinel-1", "sentinel-2", "landsat", "hls", "imerg", "glofas"]
        exposure = self.exposure.estimate(flood_area_km2)
        return ProcessingReport(
            run_id=run_id,
            source_sensors=source_sensors,
            detections=[detection],
            exposure={aoi_name: exposure},
            trigger_reason=trigger_reason,
            published_outputs=self._build_outputs(
                run_id,
                aoi_name,
                review_status,
                alert_level,
                confidence_score,
                breach_risk,
                source_sensors,
                exposure.model_dump(),
            ),
        )
