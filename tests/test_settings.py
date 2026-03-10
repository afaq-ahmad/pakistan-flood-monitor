from pathlib import Path

from app.config.settings import Environment, Settings
from app.config.thresholds import load_threshold_config


def test_settings_load_local_env(tmp_path: Path) -> None:
    for directory_name in ["raw", "prepared", "derived", "published"]:
        (tmp_path / directory_name).mkdir()

    flood_threshold = tmp_path / "flood_thresholds.yaml"
    breach_weights = tmp_path / "breach_weights.yaml"
    flood_threshold.write_text("corridor_thresholds: {}\n", encoding="utf-8")
    breach_weights.write_text("breach_weights: {}\n", encoding="utf-8")

    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "\n".join(
            [
                "DATABASE_DSN=postgresql+psycopg://postgres:postgres@localhost:5432/flood_monitor",
                f"STORAGE_RAW_ROOT={tmp_path / 'raw'}",
                f"STORAGE_PREPARED_ROOT={tmp_path / 'prepared'}",
                f"STORAGE_DERIVED_ROOT={tmp_path / 'derived'}",
                f"STORAGE_PUBLISHED_ROOT={tmp_path / 'published'}",
                "API_BASE_URL=http://localhost:8000",
                "DEFAULT_CRS=EPSG:4326",
                "CORRIDOR_BUFFER_METERS=1000",
                f"FLOOD_THRESHOLDS_PATH={flood_threshold}",
                f"BREACH_WEIGHTS_PATH={breach_weights}",
                "STAC_ENDPOINT=https://example-stac.local",
                "HYDROMET_ENDPOINT=https://example-hydromet.local",
                "LOG_LEVEL=INFO",
                "ENABLE_PREFECT_WORKERS=false",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file, environment=Environment.LOCAL)
    assert settings.environment == Environment.LOCAL
    assert settings.default_crs == "EPSG:4326"


def test_threshold_config_loads() -> None:
    threshold_config = load_threshold_config("config/thresholds/flood_thresholds.yaml")
    assert "Indus-Lower" in threshold_config.corridor_thresholds
