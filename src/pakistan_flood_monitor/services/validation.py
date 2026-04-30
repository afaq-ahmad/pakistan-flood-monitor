from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class ValidationMetrics:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def compute_precision_recall(*, true_positives: int, false_positives: int, false_negatives: int) -> ValidationMetrics:
    precision = _safe_ratio(true_positives, true_positives + false_positives)
    recall = _safe_ratio(true_positives, true_positives + false_negatives)
    return ValidationMetrics(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
    )


def load_benchmark_pack(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate_benchmark(pack: dict[str, Any]) -> dict[str, Any]:
    corridors: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    monthly_fp: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for event in pack["events"]:
        corridor = event["corridor"]
        observed = set(event.get("observed_detection_ids", []))
        expected = set(event.get("expected_detection_ids", []))
        tp = len(observed & expected)
        fp = len(observed - expected)
        fn = len(expected - observed)

        corridors[corridor]["tp"] += tp
        corridors[corridor]["fp"] += fp
        corridors[corridor]["fn"] += fn

        month = datetime.fromisoformat(event["event_date"]).strftime("%Y-%m")
        monthly_fp[corridor][month] += fp

    corridor_metrics: dict[str, Any] = {}
    precisions: list[float] = []
    recalls: list[float] = []
    for corridor, counts in sorted(corridors.items()):
        metrics = compute_precision_recall(
            true_positives=counts["tp"], false_positives=counts["fp"], false_negatives=counts["fn"]
        )
        precisions.append(metrics.precision)
        recalls.append(metrics.recall)
        corridor_metrics[corridor] = {
            "true_positives": metrics.true_positives,
            "false_positives": metrics.false_positives,
            "false_negatives": metrics.false_negatives,
            "precision": round(metrics.precision, 4),
            "recall": round(metrics.recall, 4),
            "monthly_false_positive_trend": dict(sorted(monthly_fp[corridor].items())),
        }

    return {
        "benchmark_pack": pack["benchmark_pack"],
        "generated_at": pack.get("generated_at", "fixed-input"),
        "overall": {
            "macro_precision": round(mean(precisions), 4) if precisions else 0.0,
            "macro_recall": round(mean(recalls), 4) if recalls else 0.0,
            "corridor_count": len(corridor_metrics),
        },
        "corridors": corridor_metrics,
    }


def write_monthly_report(results: dict[str, Any], output_dir: str | Path) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    month = datetime.fromisoformat(results["generated_at"]).strftime("%Y-%m") if results["generated_at"] != "fixed-input" else "fixed-input"
    output_path = out_dir / f"accuracy_report_{month}.json"
    output_path.write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    return output_path
