from __future__ import annotations

import json
from pathlib import Path

from pakistan_flood_monitor.services.validation import (
    compute_precision_recall,
    evaluate_benchmark,
    load_benchmark_pack,
    write_monthly_report,
)


FIXTURE = Path("tests/fixtures/validation/known_events_benchmark.json")


def test_compute_precision_recall() -> None:
    metrics = compute_precision_recall(true_positives=8, false_positives=2, false_negatives=1)
    assert metrics.precision == 0.8
    assert metrics.recall == 8 / 9


def test_fixture_validation_outputs_corridor_metrics_and_trends() -> None:
    pack = load_benchmark_pack(FIXTURE)
    report = evaluate_benchmark(pack)

    assert report["overall"]["macro_precision"] == 0.8333
    assert report["overall"]["macro_recall"] == 0.7333

    assert report["corridors"]["indus-upper"]["monthly_false_positive_trend"] == {"2022-08": 2}
    assert report["corridors"]["indus-lower"]["monthly_false_positive_trend"] == {"2022-09": 0}


def test_report_generation_is_deterministic(tmp_path: Path) -> None:
    pack = load_benchmark_pack(FIXTURE)
    report = evaluate_benchmark(pack)

    first = write_monthly_report(report, tmp_path)
    second = write_monthly_report(report, tmp_path)

    first_payload = json.loads(first.read_text(encoding="utf-8"))
    second_payload = json.loads(second.read_text(encoding="utf-8"))

    assert first.name == "accuracy_report_2026-04.json"
    assert first_payload == second_payload
