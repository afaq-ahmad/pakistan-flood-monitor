from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class ThresholdConfig(BaseModel):
    corridor_thresholds: dict[str, dict[str, float]] = Field(default_factory=dict)
    breach_weights: dict[str, float] = Field(default_factory=dict)
    hydromet_thresholds: dict[str, float] = Field(default_factory=dict)
    review_thresholds: dict[str, float] = Field(default_factory=dict)


def load_threshold_config(path: str | Path) -> ThresholdConfig:
    with Path(path).open("r", encoding="utf-8") as file_obj:
        payload: dict[str, Any] = yaml.safe_load(file_obj) or {}
    return ThresholdConfig(**payload)
