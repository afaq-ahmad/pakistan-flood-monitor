"""Reproducible training stub for candidate ranking model."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    output_dir = Path("artifacts")
    output_dir.mkdir(exist_ok=True)

    model_metadata = {
        "model_id": "ranker-v1",
        "training_data_snapshot": "snapshot-2024-08-baseline",
        "config": "configs/training_config.yaml",
        "thresholds": "configs/alert_thresholds.yaml",
    }

    (output_dir / "ranker-v1-metadata.json").write_text(json.dumps(model_metadata, indent=2))
    print("Training complete (stub). Metadata saved for reproducibility.")


if __name__ == "__main__":
    main()
