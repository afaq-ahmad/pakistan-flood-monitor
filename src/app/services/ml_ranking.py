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
DeploymentStatus = Literal["candidate", "shadow", "active", "rolled_back", "retired"]


_TARGET_LABEL_MAP: dict[RankingTarget, set[str]] = {
    "flood_confidence": {"flood"},
    "breach_confidence": {"possible_breach", "breach", "high-confidence protected-side flooding"},
    "false_positive_suppression": {"flood", "possible_breach", "breach", "high-confidence protected-side flooding", "likely_overflow"},
}


@dataclass(slots=True)
class TrainingRunRecord:
    model_id: str
    model_type: str
    target: RankingTarget
    candidate_kind: CandidateKind
    created_at: str
    training_dataset_snapshot: str
    feature_set_version: str
    hyperparameters: dict[str, Any]
    validation_metrics: dict[str, float]
    deployment_threshold: float
    deployment_status: DeploymentStatus = "candidate"
    rollback_parent_model_id: str | None = None
    rules_baseline_metrics: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_type": self.model_type,
            "target": self.target,
            "candidate_kind": self.candidate_kind,
            "created_at": self.created_at,
            "training_dataset_snapshot": self.training_dataset_snapshot,
            "feature_set_version": self.feature_set_version,
            "hyperparameters": self.hyperparameters,
            "validation_metrics": self.validation_metrics,
            "deployment_threshold": self.deployment_threshold,
            "deployment_status": self.deployment_status,
            "rollback_parent_model_id": self.rollback_parent_model_id,
            "rules_baseline_metrics": self.rules_baseline_metrics,
        }


@dataclass(slots=True)
class ThresholdVersionRecord:
    threshold_id: str
    target: RankingTarget
    version: str
    values: dict[str, float]
    created_at: str
    linked_model_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold_id": self.threshold_id,
            "target": self.target,
            "version": self.version,
            "values": self.values,
            "created_at": self.created_at,
            "linked_model_id": self.linked_model_id,
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


class ThresholdMetadataRegistry:
    """Versioned threshold registry kept separate from model binaries and metadata."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def register(self, record: ThresholdVersionRecord) -> Path:
        output_path = self.root_dir / f"{record.target}-{record.version}.json"
        output_path.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return output_path


@dataclass(slots=True)
class RetrainingSignal:
    label_quality_gain: float
    drift_score: float
    feature_schema_changed: bool


@dataclass(slots=True)
class RetrainingDecision:
    should_retrain: bool
    reasons: list[str]


class RetrainingTriggerPolicy:
    """Policy for retraining only on material evidence, never calendar cadence."""

    def __init__(
        self,
        *,
        min_label_quality_gain: float = 0.1,
        drift_threshold: float = 0.2,
    ) -> None:
        self._min_label_quality_gain = min_label_quality_gain
        self._drift_threshold = drift_threshold

    def evaluate(self, signal: RetrainingSignal) -> RetrainingDecision:
        reasons: list[str] = []
        if signal.label_quality_gain >= self._min_label_quality_gain:
            reasons.append("label_quality_improved")
        if signal.drift_score >= self._drift_threshold:
            reasons.append("data_drift_detected")
        if signal.feature_schema_changed:
            reasons.append("sensor_or_feature_changed")
        return RetrainingDecision(should_retrain=bool(reasons), reasons=reasons)


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

        split = _event_based_split(rows=rows)
        train_rows = split["train"]
        test_rows = split["test"]
        if not train_rows or not test_rows:
            raise ValueError("Event-based split requires at least one train and one test event.")

        train_labels = _extract_labels(rows=train_rows, target=target)
        if len(set(train_labels.tolist())) < 2:
            raise ValueError("Training labels need both positive and negative examples.")

        test_labels = _extract_labels(rows=test_rows, target=target)
        if len(set(test_labels.tolist())) < 2:
            raise ValueError("Test labels need both positive and negative examples for evaluation.")

        feature_columns = _feature_columns_for_target(target=target, sample_row=train_rows[0])
        train_matrix = _rows_to_matrix(rows=train_rows, feature_columns=feature_columns)
        test_matrix = _rows_to_matrix(rows=test_rows, feature_columns=feature_columns)

        params = {"solver": "liblinear", "max_iter": 400, "class_weight": "balanced"}
        if hyperparameters:
            params.update(hyperparameters)

        estimator = LogisticRegression(**params)
        estimator.fit(train_matrix, train_labels)

        train_probabilities = estimator.predict_proba(train_matrix)[:, 1]
        deployment_threshold = _select_threshold(labels=train_labels, probabilities=train_probabilities)

        test_probabilities = estimator.predict_proba(test_matrix)[:, 1]
        metrics = _evaluate(
            rows=test_rows,
            labels=test_labels,
            probabilities=test_probabilities,
            threshold=deployment_threshold,
            positive_on_alert=target != "false_positive_suppression",
        )

        rules_baseline = _evaluate_rules_baseline(rows=test_rows, labels=test_labels, target=target)

        model_id = f"{target}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
        record = TrainingRunRecord(
            model_id=model_id,
            model_type="logistic_regression",
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
            key not in {"snapshot_id", "candidate_id", "candidate_kind", "source_event_id", "extracted_at"}
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


def _evaluate(
    *,
    rows: list[dict[str, Any]],
    labels: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    positive_on_alert: bool,
) -> dict[str, float]:
    predictions = (probabilities >= threshold).astype(int)
    tp = int(np.sum((predictions == 1) & (labels == 1)))
    fp = int(np.sum((predictions == 1) & (labels == 0)))
    fn = int(np.sum((predictions == 0) & (labels == 1)))

    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    denom = precision + recall
    f1 = float((2 * precision * recall) / denom) if denom > 0 else 0.0

    iou_by_event = _event_iou(rows=rows, labels=labels, predictions=predictions)
    alert_acceptance_rate = precision if positive_on_alert else recall
    false_alarm_rate = float(fp / (tp + fp)) if (tp + fp) > 0 else 0.0
    top_k_precision = _top_k_breach_review_precision(rows=rows, labels=labels, probabilities=probabilities)

    return {
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "average_precision": float(average_precision_score(labels, probabilities)),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "iou": iou_by_event,
        "alert_acceptance_rate": alert_acceptance_rate,
        "false_alarm_rate": false_alarm_rate,
        "top_k_breach_review_precision": top_k_precision,
    }


def _event_iou(*, rows: list[dict[str, Any]], labels: np.ndarray, predictions: np.ndarray) -> float:
    event_scores: list[float] = []
    grouped: dict[str, list[int]] = {}
    for idx, row in enumerate(rows):
        event_id = str(row.get("source_event_id") or f"row-{idx}")
        grouped.setdefault(event_id, []).append(idx)

    for indices in grouped.values():
        event_labels = labels[indices]
        event_predictions = predictions[indices]
        intersection = int(np.sum((event_labels == 1) & (event_predictions == 1)))
        union = int(np.sum((event_labels == 1) | (event_predictions == 1)))
        if union == 0:
            continue
        event_scores.append(float(intersection / union))

    return float(np.mean(event_scores)) if event_scores else 0.0


def _top_k_breach_review_precision(*, rows: list[dict[str, Any]], labels: np.ndarray, probabilities: np.ndarray, k: int = 5) -> float:
    breach_indices = [idx for idx, row in enumerate(rows) if str(row.get("candidate_kind", "")).lower() == "breach"]
    if not breach_indices:
        return 0.0

    ranked_indices = sorted(breach_indices, key=lambda idx: float(probabilities[idx]), reverse=True)
    selected = ranked_indices[: min(k, len(ranked_indices))]
    positives = int(np.sum(labels[selected] == 1))
    return float(positives / len(selected)) if selected else 0.0


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


def _event_based_split(*, rows: list[dict[str, Any]], test_fraction: float = 0.25) -> dict[str, list[dict[str, Any]]]:
    event_to_rows: dict[str, list[dict[str, Any]]] = {}
    for idx, row in enumerate(rows):
        event_id = str(row.get("source_event_id") or f"event-{idx}")
        event_to_rows.setdefault(event_id, []).append(row)

    event_ids = sorted(event_to_rows.keys())
    if len(event_ids) < 2:
        raise ValueError("Need at least two distinct events for event-based train/test split.")

    n_test_events = max(1, int(round(len(event_ids) * test_fraction)))
    if n_test_events >= len(event_ids):
        n_test_events = len(event_ids) - 1

    test_event_ids = set(event_ids[-n_test_events:])
    train_rows: list[dict[str, Any]] = []
    test_rows: list[dict[str, Any]] = []
    for event_id in event_ids:
        bucket = test_rows if event_id in test_event_ids else train_rows
        bucket.extend(event_to_rows[event_id])

    return {"train": train_rows, "test": test_rows}


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
    return _evaluate(
        rows=rows,
        labels=labels,
        probabilities=baseline_probabilities,
        threshold=threshold,
        positive_on_alert=target != "false_positive_suppression",
    )
