from __future__ import annotations

import json
from datetime import datetime

from app.services.ml_features import (
    BaselineContextFeatures,
    BreachGeometryFeatures,
    CandidateLabelLink,
    FeatureSnapshotStore,
    HydrometFeatures,
    OpticalSupportFeatures,
    SARFeatures,
    TerrainFeatures,
    build_candidate_feature_row,
)
from app.services.ml_ranking import ClassicalCandidateRanker, ModelMetadataRegistry


def _shared_feature_kwargs() -> dict:
    return {
        "sar": SARFeatures(mean_drop_db=2.5, min_drop_db=1.2, p90_drop_db=3.9, coherence_loss=0.32),
        "optical": OpticalSupportFeatures(
            support_score=0.73,
            supported_fraction=0.62,
            obscured_fraction=0.14,
            observable_fraction=0.86,
        ),
        "terrain": TerrainFeatures(
            slope_mean_deg=2.1,
            relative_elevation_m=0.7,
            distance_to_river_m=1100.0,
            floodplain_distance_m=350.0,
        ),
        "hydromet": HydrometFeatures(
            rainfall_mm_72h=130.0,
            rainfall_anomaly_z=1.8,
            glofas_return_period=7.0,
            upstream_discharge_anomaly=1.2,
        ),
        "baseline": BaselineContextFeatures(
            seasonal_overlap_ratio=0.15,
            persistence_score=0.84,
            historical_water_occurrence=0.2,
        ),
    }


def test_classical_ranker_trains_from_candidate_snapshot_and_registers_metadata(tmp_path) -> None:
    snapshots = FeatureSnapshotStore(tmp_path / "snapshots")
    metadata = ModelMetadataRegistry(tmp_path / "registry")
    ranker = ClassicalCandidateRanker(snapshot_store=snapshots, metadata_registry=metadata)

    snapshot_id = snapshots.create_snapshot(feature_schema_version="v2", created_by="ml-ranking")
    rows = []
    for event_idx in range(4):
        source_event_id = f"event-{event_idx}"
        for cand_idx in range(4):
            is_positive = cand_idx < 2
            candidate_index = event_idx * 4 + cand_idx
            row = build_candidate_feature_row(
                snapshot_id=snapshot_id,
                candidate_id=f"flood-{candidate_index}",
                candidate_kind="flood",
                source_event_id=source_event_id,
                rules_flood_confidence=0.75 if is_positive else 0.22,
                label=CandidateLabelLink(
                    candidate_id=f"flood-{candidate_index}",
                    candidate_kind="flood",
                    review_outcome="accepted" if is_positive else "false_alarm",
                    final_class="flood" if is_positive else "non_flood",
                    label_quality_tier=3,
                    reviewed_at=datetime.fromisoformat("2026-03-10T11:00:00+00:00"),
                ),
                **_shared_feature_kwargs(),
            )
            if not is_positive:
                row.sar = SARFeatures(mean_drop_db=0.3, min_drop_db=0.1, p90_drop_db=0.6, coherence_loss=0.05)
                row.optical = OpticalSupportFeatures(
                    support_score=0.18,
                    supported_fraction=0.14,
                    obscured_fraction=0.19,
                    observable_fraction=0.81,
                )
                row.hydromet = HydrometFeatures(
                    rainfall_mm_72h=12.0,
                    rainfall_anomaly_z=0.1,
                    glofas_return_period=1.2,
                    upstream_discharge_anomaly=0.05,
                )
            rows.append(row)

    snapshots.persist_feature_rows(snapshot_id=snapshot_id, rows=rows)
    model = ranker.train(snapshot_id=snapshot_id, target="flood_confidence", feature_set_version="v2")

    assert model.metrics["f1"] >= 0.6
    assert model.metrics["precision"] >= 0.5
    assert model.metrics["recall"] >= 0.6
    assert "iou" in model.metrics
    assert "alert_acceptance_rate" in model.metrics
    assert "false_alarm_rate" in model.metrics
    assert model.rules_baseline_metrics is not None

    registry_files = list((tmp_path / "registry").glob("*.json"))
    assert len(registry_files) == 1
    payload = json.loads(registry_files[0].read_text(encoding="utf-8"))
    assert payload["training_dataset_snapshot"] == snapshot_id
    assert payload["model_type"] == "logistic_regression"
    assert payload["feature_set_version"] == "v2"
    assert "deployment_threshold" in payload
    assert payload["deployment_status"] == "candidate"


def test_false_positive_suppression_target_uses_review_outcome_labels(tmp_path) -> None:
    snapshots = FeatureSnapshotStore(tmp_path / "snapshots")
    metadata = ModelMetadataRegistry(tmp_path / "registry")
    ranker = ClassicalCandidateRanker(snapshot_store=snapshots, metadata_registry=metadata)

    snapshot_id = snapshots.create_snapshot(feature_schema_version="v2", created_by="ml-ranking")
    rows = []
    for event_idx in range(3):
        for index in range(4):
            is_false_alarm = index % 2 == 0
            row = build_candidate_feature_row(
                snapshot_id=snapshot_id,
                candidate_id=f"cand-{event_idx}-{index}",
                candidate_kind="flood",
                source_event_id=f"event-{event_idx}",
                rules_flood_confidence=0.85 if not is_false_alarm else 0.25,
                label=CandidateLabelLink(
                    candidate_id=f"cand-{event_idx}-{index}",
                    candidate_kind="flood",
                    review_outcome="false_alarm" if is_false_alarm else "accepted",
                    final_class="flood" if not is_false_alarm else "non_flood",
                    label_quality_tier=2,
                    reviewed_at=datetime.fromisoformat("2026-03-10T11:00:00+00:00"),
                ),
                **_shared_feature_kwargs(),
            )
            rows.append(row)

    snapshots.persist_feature_rows(snapshot_id=snapshot_id, rows=rows)
    model = ranker.train(snapshot_id=snapshot_id, target="false_positive_suppression", feature_set_version="v2")

    training_rows = snapshots.load_training_rows(snapshot_id=snapshot_id, candidate_kind="flood", min_label_quality_tier=2)
    ranked = model.rank_rows(training_rows)
    assert len(ranked) == len(training_rows)
    assert ranked[0].score >= ranked[-1].score


def test_breach_ranking_reports_top_k_breach_review_precision(tmp_path) -> None:
    snapshots = FeatureSnapshotStore(tmp_path / "snapshots")
    metadata = ModelMetadataRegistry(tmp_path / "registry")
    ranker = ClassicalCandidateRanker(snapshot_store=snapshots, metadata_registry=metadata)

    snapshot_id = snapshots.create_snapshot(feature_schema_version="v2", created_by="ml-ranking")
    rows = []
    for event_idx in range(4):
        for index in range(3):
            positive = index < 2
            base_kwargs = _shared_feature_kwargs()
            if not positive:
                base_kwargs["sar"] = SARFeatures(mean_drop_db=0.2, min_drop_db=0.1, p90_drop_db=0.4, coherence_loss=0.03)
            row = build_candidate_feature_row(
                snapshot_id=snapshot_id,
                candidate_id=f"breach-{event_idx}-{index}",
                candidate_kind="breach",
                source_event_id=f"event-{event_idx}",
                breach_geometry=BreachGeometryFeatures(
                    protected_side_ratio=0.8 if positive else 0.1,
                    distance_to_embankment_m=120.0 if positive else 1200.0,
                    expansion_away_from_levee_score=0.7 if positive else 0.1,
                    split_merge_complexity=0.6 if positive else 0.2,
                ),
                rules_breach_confidence=0.82 if positive else 0.2,
                label=CandidateLabelLink(
                    candidate_id=f"breach-{event_idx}-{index}",
                    candidate_kind="breach",
                    review_outcome="accepted" if positive else "false_alarm",
                    final_class="breach" if positive else "non_flood",
                    label_quality_tier=3,
                    reviewed_at=datetime.fromisoformat("2026-03-10T11:00:00+00:00"),
                ),
                **base_kwargs,
            )
            rows.append(row)

    snapshots.persist_feature_rows(snapshot_id=snapshot_id, rows=rows)
    model = ranker.train(snapshot_id=snapshot_id, target="breach_confidence", feature_set_version="v2")

    assert model.metrics["top_k_breach_review_precision"] >= 0.5


def test_threshold_registry_and_retraining_policy_are_material_trigger_based(tmp_path) -> None:
    from datetime import UTC

    from app.services.ml_ranking import (
        RetrainingSignal,
        RetrainingTriggerPolicy,
        ThresholdMetadataRegistry,
        ThresholdVersionRecord,
    )

    threshold_registry = ThresholdMetadataRegistry(tmp_path / "thresholds")
    record_path = threshold_registry.register(
        ThresholdVersionRecord(
            threshold_id="thr-flood-v3",
            target="flood_confidence",
            version="v3",
            values={"deployment_threshold": 0.61},
            created_at=datetime.now(UTC).isoformat(),
            linked_model_id="flood_confidence-20260310-aaaa1111",
        )
    )

    payload = json.loads(record_path.read_text(encoding="utf-8"))
    assert payload["target"] == "flood_confidence"
    assert payload["version"] == "v3"

    policy = RetrainingTriggerPolicy(min_label_quality_gain=0.1, drift_threshold=0.2)
    no_retrain = policy.evaluate(RetrainingSignal(label_quality_gain=0.04, drift_score=0.09, feature_schema_changed=False))
    assert no_retrain.should_retrain is False
    assert no_retrain.reasons == []

    retrain = policy.evaluate(RetrainingSignal(label_quality_gain=0.12, drift_score=0.05, feature_schema_changed=False))
    assert retrain.should_retrain is True
    assert retrain.reasons == ["label_quality_improved"]
