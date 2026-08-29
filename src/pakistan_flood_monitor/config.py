from __future__ import annotations

import os
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class AppMode(str, Enum):
    """Runtime safety boundary for synthetic and operational data."""

    TEST = "test"
    DEMO = "demo"
    OPERATIONAL = "operational"


def _load_local_dotenv(path: Path = Path(".env")) -> None:
    """Load simple local configuration without overriding deployment env vars."""

    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key.replace("_", "").isalnum():
            os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def _app_mode_from_environment() -> AppMode:
    raw_value = os.getenv("APP_MODE", AppMode.DEMO.value).strip().lower()
    try:
        return AppMode(raw_value)
    except ValueError as exc:  # fail during startup instead of silently choosing a mode
        allowed = ", ".join(mode.value for mode in AppMode)
        raise RuntimeError(f"Invalid APP_MODE={raw_value!r}; expected one of: {allowed}") from exc


class Thresholds(BaseModel):
    sar_drop_db: float = Field(default=2.5, description="Backscatter drop threshold in dB")
    ndwi: float = Field(default=0.2, description="NDWI threshold for optical water")
    confidence_warning: float = 0.55
    confidence_critical: float = 0.75
    analyst_review_min_confidence: float = 0.45


class Corridor(BaseModel):
    name: str
    district: str
    priority: int = Field(default=1, description="1=highest pilot priority")


class Settings(BaseModel):
    """Configuration for the canonical runtime.

    ``APP_MODE`` is parsed explicitly at import time so an invalid value fails
    startup. Other runtime settings are loaded from the process environment
    without importing the legacy app configuration tree. Deployment tooling may
    load an untracked ``.env`` file into that environment before startup.
    """

    project_name: str = "Pakistan River Flood Monitoring and Breach Detection System"
    country: str = "Pakistan"
    app_mode: AppMode = AppMode.DEMO
    database_url: str = "sqlite:///./storage/pakistan_flood_monitor.db"
    workflow_max_attempts: int = Field(default=3, ge=1)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    pilot_corridors: list[Corridor] = Field(
        default_factory=lambda: [
            Corridor(name="Indus-Lower", district="Sindh", priority=1),
            Corridor(name="Chenab-Middle", district="Punjab", priority=1),
            Corridor(name="Kabul-Nowshera", district="Khyber Pakhtunkhwa", priority=2),
        ]
    )

    @property
    def synthetic_data_allowed(self) -> bool:
        return self.app_mode in {AppMode.TEST, AppMode.DEMO}

    @property
    def official_publication_allowed(self) -> bool:
        return self.app_mode is AppMode.OPERATIONAL


_load_local_dotenv()


settings = Settings(
    app_mode=_app_mode_from_environment(),
    database_url=os.getenv("DATABASE_URL", "sqlite:///./storage/pakistan_flood_monitor.db"),
    workflow_max_attempts=os.getenv("WORKFLOW_MAX_ATTEMPTS", "3"),
)
