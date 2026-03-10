from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
import os
from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PROD = "prod"


def _env_file_for(environment: Environment) -> str:
    return {
        Environment.LOCAL: ".env.local",
        Environment.STAGING: ".env.staging",
        Environment.PROD: ".env.prod",
    }[environment]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_nested_delimiter="__",
        extra="ignore",
    )

    environment: Environment = Environment.LOCAL

    database_dsn: str = Field(alias="DATABASE_DSN")
    storage_raw_root: Path = Field(alias="STORAGE_RAW_ROOT")
    storage_prepared_root: Path = Field(alias="STORAGE_PREPARED_ROOT")
    storage_derived_root: Path = Field(alias="STORAGE_DERIVED_ROOT")
    storage_published_root: Path = Field(alias="STORAGE_PUBLISHED_ROOT")

    api_base_url: str = Field(alias="API_BASE_URL")
    default_crs: str = Field(default="EPSG:4326", alias="DEFAULT_CRS")

    corridor_buffer_meters: int = Field(default=1000, alias="CORRIDOR_BUFFER_METERS")
    flood_thresholds_path: Path = Field(alias="FLOOD_THRESHOLDS_PATH")
    breach_weights_path: Path = Field(alias="BREACH_WEIGHTS_PATH")

    stac_endpoint: str = Field(alias="STAC_ENDPOINT")
    hydromet_endpoint: str = Field(alias="HYDROMET_ENDPOINT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    enable_prefect_workers: bool = Field(default=False, alias="ENABLE_PREFECT_WORKERS")

    stac_token: SecretStr | None = Field(default=None, alias="STAC_TOKEN")
    hydromet_token: SecretStr | None = Field(default=None, alias="HYDROMET_TOKEN")

    @model_validator(mode="after")
    def _validate_paths(self) -> "Settings":
        required_files = [self.flood_thresholds_path, self.breach_weights_path]
        for path in required_files:
            if not path.exists():
                raise ValueError(f"Required config file is missing: {path}")
        required_dirs = [
            self.storage_raw_root,
            self.storage_prepared_root,
            self.storage_derived_root,
            self.storage_published_root,
        ]
        for directory in required_dirs:
            if not directory.exists():
                raise ValueError(f"Required storage path is missing: {directory}")
        return self

    @classmethod
    def from_environment(cls, environment: Environment) -> "Settings":
        return cls(_env_file=_env_file_for(environment), environment=environment)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    env_value = os.getenv("APP_ENV", Environment.LOCAL.value)
    return Settings.from_environment(Environment(env_value))
