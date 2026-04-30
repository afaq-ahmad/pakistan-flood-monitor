from __future__ import annotations

import argparse
from pathlib import Path

from pakistan_flood_monitor.services.validation import evaluate_benchmark, load_benchmark_pack, write_monthly_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run known-event flood benchmark validation and write monthly accuracy report.")
    parser.add_argument("--benchmark", default="tests/fixtures/validation/known_events_benchmark.json")
    parser.add_argument("--output-dir", default="reports/validation")
    args = parser.parse_args()

    pack = load_benchmark_pack(args.benchmark)
    results = evaluate_benchmark(pack)
    report_path = write_monthly_report(results, Path(args.output_dir))
    print(f"Benchmark: {args.benchmark}")
    print(f"Report: {report_path}")
    print(f"Macro precision: {results['overall']['macro_precision']}")
    print(f"Macro recall: {results['overall']['macro_recall']}")


if __name__ == "__main__":
    main()
