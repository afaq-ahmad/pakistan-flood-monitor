from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, precision_recall_curve, roc_auc_score

from app.services.ml_features import CandidateKind, FeatureSnapshotStore

RankingTarget = Literal["flood_confidence", "breach_confidence", "false_positive_suppression"]


_TARGET_LABEL_MAP: dict[RankingTarget, set[str]] = {
    "flood_confidence": {"flood"},
    "breach_confidence": {"possible_breach", "breach", "high-confidence protected-side flooding"},
    "false_positive_suppression": {"flood", "possible_breach", "breach", "high-confidence protected-side flooding", "likely_overflow"},
}


@dataclass(slots=True)
class TrainingRunRecord:
    model_id: str
    target: RankingTarget
    candidate_kind: CandidateKind
    created_at: str
    training_dataset_snapshot: str
    feature_set_version: str
    hyperparameters: dict[str, Any]
    validation_metrics: dict[str, float]
    deployment_threshold: float
    rules_baseline_metrics: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "target": self.target,
            "candidate_kind": self.candidate_kind,
            "created_at": self.created_at,
            "training_dataset_snapshot": self.training_dataset_snapshot,
            "feature_set_version": self.feature_set_version,
            "hyperparameters": self.hyperparameters,
            "validation_metrics": self.validation_metrics,
            "deployment_threshold": self.deployment_threshold,
            "rules_baseline_metrics": self.rules_baseline_metrics,
        }


class ModelMetadataRegistry:
    """Filesystem-backed metadata registry for classical ranking models."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def register(self, record: TrainingRunRecord) -> Path:
        output_path = self.root_dir / f"{record.model_id}.json"
        output_path.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return output_path


@dataclass(slots=True)
class RankedCandidate:
    candidate_id: str
    probability: float
    score: float
    above_threshold: bool


@dataclass(slots=True)
class TrainedRankingModel:
    model_id: str
    target: RankingTarget
    candidate_kind: CandidateKind
    feature_columns: list[str]
    deployment_threshold: float
    metrics: dict[str, float]
    rules_baseline_metrics: dict[str, float] | None
    estimator: LogisticRegression

    def rank_rows(self, rows: list[dict[str, Any]]) -> list[RankedCandidate]:
        if not rows:
            return []
        matrix = _rows_to_matrix(rows=rows, feature_columns=self.feature_columns)
        probabilities = self.estimator.predict_proba(matrix)[:, 1]
        ranked: list[RankedCandidate] = []
        for row, probability in zip(rows, probabilities, strict=True):
            score = float(probability)
            ranked.append(
                RankedCandidate(
                    candidate_id=str(row["candidate_id"]),
                    probability=score,
                    score=score,
                    above_threshold=score >= self.deployment_threshold,
                )
            )
        return sorted(ranked, key=lambda item: item.score, reverse=True)


class ClassicalCandidateRanker:
    """Rules-competing classical ML ranking for candidate objects from feature snapshots."""

    def __init__(
        self,
        *,
        snapshot_store: FeatureSnapshotStore,
        metadata_registry: ModelMetadataRegistry,
    ) -> None:
        self._snapshot_store = snapshot_store
        self._metadata_registry = metadata_registry

    def train(
        self,
        *,
        snapshot_id: str,
        target: RankingTarget,
        feature_set_version: str,
        min_label_quality_tier: int = 2,
        hyperparameters: dict[str, Any] | None = None,
    ) -> TrainedRankingModel:
        candidate_kind = "breach" if target == "breach_confidence" else "flood"
        rows = self._snapshot_store.load_training_rows(
            snapshot_id=snapshot_id,
            candidate_kind=candidate_kind,
            min_label_quality_tier=min_label_quality_tier,
        )
        if not rows:
            raise ValueError("No training rows were loaded from the candidate snapshot.")

        labels = _extract_labels(rows=rows, target=target)
        if len(set(labels.tolist())) < 2:
            raise ValueError("Training labels need both positive and negative examples.")

        feature_columns = _feature_columns_for_target(target=target, sample_row=rows[0])
        matrix = _rows_to_matrix(rows=rows, feature_columns=feature_columns)

        params = {"solver": "liblinear", "max_iter": 400, "class_weight": "balanced"}
        if hyperparameters:
            params.update(hyperparameters)

        estimator = LogisticRegression(**params)
        estimator.fit(matrix, labels)
        probabilities = estimator.predict_proba(matrix)[:, 1]

        deployment_threshold = _select_threshold(labels=labels, probabilities=probabilities)
        metrics = _evaluate(labels=labels, probabilities=probabilities, threshold=deployment_threshold)

        rules_baseline = _evaluate_rules_baseline(rows=rows, labels=labels, target=target)

        model_id = f"{target}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
        record = TrainingRunRecord(
            model_id=model_id,
            target=target,
            candidate_kind=candidate_kind,
            created_at=datetime.now(UTC).isoformat(),
            training_dataset_snapshot=snapshot_id,
            feature_set_version=feature_set_version,
            hyperparameters=params,
            validation_metrics=metrics,
            deployment_threshold=deployment_threshold,
            rules_baseline_metrics=rules_baseline,
        )
        self._metadata_registry.register(record)

        return TrainedRankingModel(
            model_id=model_id,
            target=target,
            candidate_kind=candidate_kind,
            feature_columns=feature_columns,
            deployment_threshold=deployment_threshold,
            metrics=metrics,
            rules_baseline_metrics=rules_baseline,
            estimator=estimator,
        )


def _feature_columns_for_target(*, target: RankingTarget, sample_row: dict[str, Any]) -> list[str]:
    columns = [
        key
        for key, value in sample_row.items()
        if (
            key not in {"snapshot_id", "candidate_id", "candidate_kind", "extracted_at"}
            and not key.startswith("label_")
            and value is not None
            and isinstance(value, (int, float))
        )
    ]

    if target == "breach_confidence":
        return sorted(columns)

    return sorted([name for name in columns if not name.startswith("breach_")])


def _rows_to_matrix(*, rows: list[dict[str, Any]], feature_columns: list[str]) -> np.ndarray:
    matrix = np.zeros((len(rows), len(feature_columns)), dtype=np.float64)
    for row_index, row in enumerate(rows):
        for col_index, feature in enumerate(feature_columns):
            matrix[row_index, col_index] = float(row.get(feature, 0.0) or 0.0)
    return matrix


def _extract_labels(*, rows: list[dict[str, Any]], target: RankingTarget) -> np.ndarray:
    if target == "false_positive_suppression":
        values = [1 if str(row.get("label_review_outcome", "")).lower() != "false_alarm" else 0 for row in rows]
        return np.asarray(values, dtype=np.int64)

    positives = _TARGET_LABEL_MAP[target]
    values = [1 if str(row.get("label_final_class", "")).lower() in positives else 0 for row in rows]
    return np.asarray(values, dtype=np.int64)


def _evaluate(*, labels: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict[str, float]:
    predictions = (probabilities >= threshold).astype(int)
    return {
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "average_precision": float(average_precision_score(labels, probabilities)),
        "f1": float(f1_score(labels, predictions)),
    }


def _select_threshold(*, labels: np.ndarray, probabilities: np.ndarray) -> float:
    precisions, recalls, thresholds = precision_recall_curve(labels, probabilities)
    if len(thresholds) == 0:
        return 0.5

    best_threshold = 0.5
    best_f1 = -1.0
    for precision, recall, threshold in zip(precisions[1:], recalls[1:], thresholds, strict=True):
        denom = precision + recall
        if denom <= 0:
            continue
        f1 = (2 * precision * recall) / denom
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = float(threshold)
    return best_threshold


def _evaluate_rules_baseline(
    *,
    rows: list[dict[str, Any]],
    labels: np.ndarray,
    target: RankingTarget,
) -> dict[str, float] | None:
    baseline_key = "rules_breach_confidence" if target == "breach_confidence" else "rules_flood_confidence"
    if not rows or baseline_key not in rows[0] or rows[0].get(baseline_key) is None:
        return None

    baseline_probabilities = np.asarray([float(row.get(baseline_key, 0.0) or 0.0) for row in rows], dtype=np.float64)
    threshold = _select_threshold(labels=labels, probabilities=baseline_probabilities)
    return _evaluate(labels=labels, probabilities=baseline_probabilities, threshold=threshold)
