from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.services.observability import log_failure, log_structured, metrics_registry
from pakistan_flood_monitor.config import AppMode, settings
from pakistan_flood_monitor.core.detection import FloodDetector
from pakistan_flood_monitor.core.exposure import ExposureAnalyzer
from pakistan_flood_monitor.data.sources import DataCatalog
from pakistan_flood_monitor.hazards.base import HazardModule, StubHazardModule
from pakistan_flood_monitor.hazards.registry import HazardRegistry
from pakistan_flood_monitor.models.observations import (
    DataIntegritySummary,
    ScientificObservation,
)
from pakistan_flood_monitor.models.schemas import (
    AlertLevel,
    AlertSummary,
    AssetExposureReport,
    BreachCategory,
    BreachSuspicionLayer,
    ConfirmedFloodExtent,
    EventClass,
    EventDecision,
    EventLineage,
    FloodCandidateMap,
    FloodDetectionResult,
    HistoricalEventRecord,
    LineageSceneAsset,
    ModelVersion,
    MVPOutputs,
    ProcessingReport,
    ReviewQueueEvent,
    ReviewStatus,
    RunLineage,
    SourceSceneLineage,
)
from pakistan_flood_monitor.pipeline.feature_generation import SceneFeatureExtractor
from pakistan_flood_monitor.services.alerts import AlertService
from pakistan_flood_monitor.services.probabilistic_forecast import (
    build_probabilistic_forecast,
    compute_calibration_stats,
)
from pakistan_flood_monitor.services.triggers import EventTriggerService, TriggerInputs


class FloodHazardModule(HazardModule):
    @property
    def hazard_type(self) -> str:
        return "flood"

    def __init__(self, app_mode: AppMode | None = None) -> None:
        self.app_mode = app_mode or settings.app_mode
        self.catalog = DataCatalog(app_mode=self.app_mode)
        self.detector = FloodDetector()
        self.alerts = AlertService()
        self.exposure = ExposureAnalyzer()
        self.triggers = EventTriggerService()
        self.feature_extractor = SceneFeatureExtractor(app_mode=self.app_mode)

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

    def _calibration_reference(self):
        probabilities = [0.15, 0.22, 0.35, 0.44, 0.58, 0.63, 0.74, 0.82, 0.91, 0.67]
        outcomes = [0, 0, 0, 1, 1, 0, 1, 1, 1, 1]
        return compute_calibration_stats(probabilities=probabilities, outcomes=outcomes, bins=5)

    def _scene_lineage(self, scenes) -> list[SourceSceneLineage]:
        output: list[SourceSceneLineage] = []
        for scene in scenes:
            assets = {
                name: LineageSceneAsset(href=href, roles=["source", name])
                for name, href in (scene.assets or {}).items()
            }
            output.append(
                SourceSceneLineage(
                    scene_id=scene.scene_id,
                    sensor=scene.sensor,
                    acquired_at=datetime.combine(scene.acquisition_date, datetime.min.time(), tzinfo=UTC),
                    assets=assets,
                    observation_status=scene.observation_status,
                    availability_status=scene.availability_status,
                    synthetic=scene.synthetic,
                    source_uri=scene.stac_item_url,
                )
            )
        return output

    def _build_event_lineage(
        self,
        *,
        run_id: str,
        source_scenes: list[SourceSceneLineage],
        thresholds: dict[str, float],
        processing_version: str,
        threshold_version: str,
        model: ModelVersion,
        observations: dict[str, ScientificObservation],
        integrity: DataIntegritySummary,
    ) -> EventLineage:
        return EventLineage(
            run_id=run_id,
            source_scene_ids=[scene.scene_id for scene in source_scenes],
            source_scenes=source_scenes,
            processing_version=processing_version,
            threshold_version=threshold_version,
            thresholds=thresholds,
            model=model.model_dump(),
            generated_at=datetime.now(UTC),
            observations=observations,
            contains_synthetic=integrity.contains_synthetic,
            data_availability=integrity.data_availability,
            product_label=integrity.product_label,
            watermark=integrity.watermark,
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
        lineage: EventLineage,
        integrity: DataIntegritySummary,
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
                product_label=integrity.product_label,
                data_availability=integrity.data_availability,
                watermark=integrity.watermark,
            ),
            model_version=self._active_model_version(),
            review_queue_event=ReviewQueueEvent(
                **self._build_review_queue_event(
                    run_id,
                    aoi_name,
                    source_scenes,
                    alert_level,
                    breach_risk,
                    confidence_score,
                    review_status,
                ).model_dump(exclude={"lineage"}),
                lineage=lineage,
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
        run_id = str(uuid4())
        started = datetime.utcnow()
        checkpoint = "validate_aoi"
        if not self._pilot_corridor_enabled(aoi_name):
            raise ValueError(f"AOI '{aoi_name}' is outside configured pilot corridors")

        try:
            today = datetime.utcnow().date()
            checkpoint = "fetch_inputs"
            scenes = self.catalog.fetch_scenes("sentinel-1", aoi_name, today - timedelta(days=2), today)
            support_layers = self.catalog.fetch_supporting_layers(aoi_name)
            processing_version = "sar-preprocess-v1"
            threshold_version = "alert-thresholds-v1"
            thresholds = {
                "sar_drop_db": settings.thresholds.sar_drop_db,
                "ndwi": settings.thresholds.ndwi,
                "confidence_warning": settings.thresholds.confidence_warning,
                "confidence_critical": settings.thresholds.confidence_critical,
            }
            extracted = self.feature_extractor.extract(
                run_id=run_id,
                aoi_name=aoi_name,
                scenes=scenes,
                support_layers=support_layers,
                processing_version=processing_version,
                threshold_version=threshold_version,
                thresholds=thresholds,
            )
            active_model = self._active_model_version()
            scene_lineage = self._scene_lineage(scenes)
            run_lineage = RunLineage(
                run_id=run_id,
                aoi=aoi_name,
                source_scene_ids=[scene.scene_id for scene in scene_lineage],
                source_scenes=scene_lineage,
                processing_version=processing_version,
                threshold_version=threshold_version,
                thresholds=thresholds,
                model=active_model.model_dump(),
                generated_at=datetime.now(UTC),
                observations=extracted.observations,
                contains_synthetic=extracted.integrity.contains_synthetic,
                data_availability=extracted.integrity.data_availability,
                product_label=extracted.integrity.product_label,
                watermark=extracted.integrity.watermark,
            )
            event_lineage = self._build_event_lineage(
                run_id=run_id,
                source_scenes=scene_lineage,
                thresholds=thresholds,
                processing_version=processing_version,
                threshold_version=threshold_version,
                model=active_model,
                observations=extracted.observations,
                integrity=extracted.integrity,
            )
            features = extracted.features
            source_sensors = sorted({scene.sensor for scene in scenes}) + ["imerg", "glofas"]
            source_identifiers = extracted.source_scene_ids + ["imerg", "glofas"]

            checkpoint = "event_trigger"
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
                    probabilistic_forecast=build_probabilistic_forecast(
                        flood_probability=0.0,
                        confidence_score=0.0,
                        indicators={"rainfall_mm_72h": 0.0, "glofas_return_period": 0.0},
                        calibration=self._calibration_reference(),
                        model_lineage=self._active_model_version().model_dump(),
                    ),
                    observation_statuses={
                        name: observation.status for name, observation in extracted.observations.items()
                    },
                    data_availability=extracted.integrity.data_availability,
                    product_label=extracted.integrity.product_label,
                )
                exposure = self.exposure.estimate(0.0)
                report = ProcessingReport(
                    run_id=run_id,
                    source_sensors=source_sensors,
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
                        source_identifiers,
                        exposure.model_dump(),
                        event_lineage,
                        extracted.integrity,
                    ),
                    run_lineage=run_lineage,
                    app_mode=self.app_mode,
                    data_availability=extracted.integrity.data_availability,
                    product_label=extracted.integrity.product_label,
                    contains_synthetic=extracted.integrity.contains_synthetic,
                    watermark=extracted.integrity.watermark,
                    observations=extracted.observations,
                )
            else:
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
                        "floodplain_distance_m": features.floodplain_distance_m,
                    },
                    probabilistic_forecast=build_probabilistic_forecast(
                        flood_probability=flood_probability,
                        confidence_score=confidence_score,
                        indicators={
                            "rainfall_mm_72h": features.rainfall_mm_72h,
                            "glofas_return_period": features.glofas_return_period,
                        },
                        calibration=self._calibration_reference(),
                        model_lineage=active_model.model_dump(),
                    ),
                    observation_statuses={
                        name: observation.status for name, observation in extracted.observations.items()
                    },
                    data_availability=extracted.integrity.data_availability,
                    product_label=extracted.integrity.product_label,
                )
                exposure = self.exposure.estimate(flood_area_km2)
                report = ProcessingReport(
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
                        source_identifiers,
                        exposure.model_dump(),
                        event_lineage,
                        extracted.integrity,
                    ),
                    run_lineage=run_lineage,
                    app_mode=self.app_mode,
                    data_availability=extracted.integrity.data_availability,
                    product_label=extracted.integrity.product_label,
                    contains_synthetic=extracted.integrity.contains_synthetic,
                    watermark=extracted.integrity.watermark,
                    observations=extracted.observations,
                )

            delay_hours = max(0.0, (datetime.utcnow() - detection.timestamp).total_seconds() / 3600)
            if extracted.integrity.contains_synthetic:
                metrics_registry.increment("pipeline.demo_previews_produced")
            else:
                metrics_registry.increment("product.alerts_produced")
                metrics_registry.increment("product.exposure_outputs_delivered")
                metrics_registry.observe_latency_ms("product.scene_to_alert_delay_ms", delay_hours * 3600 * 1000)
                metrics_registry.increment("pipeline.alerts_published")
            log_structured(
                "pipeline_run",
                run_id=run_id,
                corridor_id=aoi_name,
                scene_id=report.source_sensors[0],
                task_type="run_daily",
                duration_ms=(datetime.utcnow() - started).total_seconds() * 1000,
                success=True,
                output_paths=[f"event://{report.published_outputs.review_queue_event.event_id}"],
            )
            return report
        except Exception as exc:
            log_failure(
                "pipeline_run",
                error=exc,
                run_id=run_id,
                corridor_id=aoi_name,
                scene_id=None,
                task_type="run_daily",
                pipeline_stage="pipeline_runner",
                input_identifiers={"aoi_name": aoi_name},
                last_completed_checkpoint=checkpoint,
                duration_ms=(datetime.utcnow() - started).total_seconds() * 1000,
                output_paths=[],
            )
            raise


class FloodMonitoringPipeline:
    """Compatibility wrapper preserving the flood-first API while enabling multi-hazard plugins."""

    def __init__(self, app_mode: AppMode | None = None) -> None:
        self.app_mode = app_mode or settings.app_mode
        self.registry = HazardRegistry()
        self.register_module(FloodHazardModule(app_mode=self.app_mode))
        self.register_module(StubHazardModule("landslide"))
        self.register_module(StubHazardModule("heat"))

    def register_module(self, module: HazardModule) -> None:
        self.registry.register(module)

    def registered_hazards(self) -> list[str]:
        return self.registry.registered_hazards()

    @property
    def _flood_module(self) -> FloodHazardModule:
        module = self.registry.get("flood")
        if not isinstance(module, FloodHazardModule):  # pragma: no cover - defensive registry guard
            raise TypeError("Registered flood module does not implement FloodHazardModule")
        return module

    @property
    def catalog(self) -> DataCatalog:
        return self._flood_module.catalog

    @catalog.setter
    def catalog(self, value: DataCatalog) -> None:
        self._flood_module.catalog = value

    @property
    def feature_extractor(self) -> SceneFeatureExtractor:
        return self._flood_module.feature_extractor

    @feature_extractor.setter
    def feature_extractor(self, value: SceneFeatureExtractor) -> None:
        self._flood_module.feature_extractor = value

    def run_hazard_daily(self, hazard_type: str, aoi_name: str) -> ProcessingReport:
        return self.registry.get(hazard_type).run_daily(aoi_name)

    def run_daily(self, aoi_name: str) -> ProcessingReport:
        return self.run_hazard_daily("flood", aoi_name)
