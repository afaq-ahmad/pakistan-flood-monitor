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


def test_snapshot_store_persists_immutable_feature_tables(tmp_path) -> None:
    store = FeatureSnapshotStore(tmp_path)
    snapshot_id = store.create_snapshot(feature_schema_version="v1", created_by="ml-pipeline")

    flood_row = build_candidate_feature_row(
        snapshot_id=snapshot_id,
        candidate_id="flood-001",
        candidate_kind="flood",
        label=CandidateLabelLink(
            candidate_id="flood-001",
            candidate_kind="flood",
            review_outcome="accepted",
            final_class="flood",
            label_quality_tier=3,
            reviewed_at=datetime.fromisoformat("2026-03-10T11:00:00+00:00"),
        ),
        **_shared_feature_kwargs(),
    )

    breach_row = build_candidate_feature_row(
        snapshot_id=snapshot_id,
        candidate_id="breach-001",
        candidate_kind="breach",
        breach_geometry=BreachGeometryFeatures(
            protected_side_ratio=0.79,
            distance_to_embankment_m=180.0,
            expansion_away_from_levee_score=0.68,
            split_merge_complexity=0.12,
        ),
        label=CandidateLabelLink(
            candidate_id="breach-001",
            candidate_kind="breach",
            review_outcome="accepted",
            final_class="possible_breach",
            label_quality_tier=2,
            reviewed_at=datetime.fromisoformat("2026-03-10T11:05:00+00:00"),
        ),
        **_shared_feature_kwargs(),
    )

    store.persist_feature_rows(snapshot_id=snapshot_id, rows=[flood_row, breach_row])

    manifest = json.loads((tmp_path / snapshot_id / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["frozen"] is True

    flood_rows = store.load_training_rows(snapshot_id=snapshot_id, candidate_kind="flood", min_label_quality_tier=2)
    breach_rows = store.load_training_rows(snapshot_id=snapshot_id, candidate_kind="breach", min_label_quality_tier=2)

    assert len(flood_rows) == 1
    assert flood_rows[0]["label_final_class"] == "flood"
    assert len(breach_rows) == 1
    assert breach_rows[0]["breach_distance_to_embankment_m"] == 180.0


def test_candidate_feature_row_validates_breach_geometry_requirements() -> None:
    kwargs = _shared_feature_kwargs()

    try:
        build_candidate_feature_row(
            snapshot_id="snapshot-1",
            candidate_id="flood-002",
            candidate_kind="flood",
            breach_geometry=BreachGeometryFeatures(
                protected_side_ratio=0.7,
                distance_to_embankment_m=210.0,
                expansion_away_from_levee_score=0.55,
                split_merge_complexity=0.2,
            ),
            **kwargs,
        )
    except ValueError as exc:
        assert "Flood candidates cannot include breach-specific geometric features" in str(exc)
    else:
        raise AssertionError("expected validation error")
