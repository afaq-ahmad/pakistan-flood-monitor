"""Composable provenance, quality, freshness, and asset metadata contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

from pakistan_flood_monitor.config import AppMode
from pakistan_flood_monitor.models.observations import SourceAvailabilityStatus


class QualityGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    NO_DATA = "NO_DATA"


class FreshnessStatus(str, Enum):
    CURRENT = "CURRENT"
    AGING = "AGING"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class AssetStage(str, Enum):
    RAW = "raw"
    PREPARED = "prepared"
    DERIVED = "derived"
    PUBLISHED = "published"


class SourceIdentity(BaseModel):
    provider: str
    item_id: str | None = None
    uri: str | None = None


class TemporalMetadata(BaseModel):
    acquired_at: datetime | None = None
    valid_at: datetime | None = None
    source_published_at: datetime | None = None
    processed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("acquired_at", "valid_at", "source_published_at", "processed_at")
    @classmethod
    def _require_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(UTC) if value is not None else None


class SpatialMetadata(BaseModel):
    crs: str | None = None
    resolution_m: float | None = Field(default=None, gt=0, description="Native pixel or grid resolution in metres")


class ProcessingMetadata(BaseModel):
    processing_version: str
    code_version: str | None = None
    config_version: str | None = None
    model_version: str | None = None
    threshold_version: str | None = None
    reference_layer_versions: dict[str, str] = Field(default_factory=dict)


class LineageReference(BaseModel):
    identifier: str
    relationship: str = "input"
    checksum_sha256: str | None = None

    @field_validator("checksum_sha256")
    @classmethod
    def _validate_checksum(cls, value: str | None) -> str | None:
        return _normalise_sha256(value)


class AssetReference(BaseModel):
    href: str
    stage: AssetStage
    asset_id: str | None = None
    media_type: str | None = None
    checksum_sha256: str | None = None
    roles: list[str] = Field(default_factory=list)
    spatial: SpatialMetadata | None = None

    @field_validator("checksum_sha256")
    @classmethod
    def _validate_checksum(cls, value: str | None) -> str | None:
        return _normalise_sha256(value)


class FreshnessPolicy(BaseModel):
    """A product-family-specific age policy, expressed explicitly in hours."""

    product_family: str
    current_max_age_hours: float = Field(ge=0)
    aging_max_age_hours: float = Field(ge=0)

    @model_validator(mode="after")
    def _validate_bounds(self) -> "FreshnessPolicy":
        if self.aging_max_age_hours < self.current_max_age_hours:
            raise ValueError("aging_max_age_hours must be at least current_max_age_hours")
        return self

    def classify(self, timestamp: datetime | None, *, evaluated_at: datetime | None = None) -> FreshnessStatus:
        if timestamp is None:
            return FreshnessStatus.UNKNOWN
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        checked_at = evaluated_at or datetime.now(UTC)
        if checked_at.tzinfo is None or checked_at.utcoffset() is None:
            raise ValueError("evaluated_at must be timezone-aware")
        age_hours = max(0.0, (checked_at.astimezone(UTC) - timestamp.astimezone(UTC)).total_seconds() / 3600.0)
        if age_hours <= self.current_max_age_hours:
            return FreshnessStatus.CURRENT
        if age_hours <= self.aging_max_age_hours:
            return FreshnessStatus.AGING
        return FreshnessStatus.STALE


class FreshnessAssessment(BaseModel):
    status: FreshnessStatus
    policy_product_family: str | None = None
    source_timestamp: datetime | None = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("source_timestamp", "evaluated_at")
    @classmethod
    def _require_timezone_aware(cls, value: datetime | None) -> datetime | None:
        return TemporalMetadata._require_timezone_aware(value)


class FreshnessPolicyRegistry(BaseModel):
    """Configurable freshness policies rather than one global stale threshold."""

    policies: dict[str, FreshnessPolicy] = Field(default_factory=dict)

    def assess(
        self,
        product_family: str,
        source_timestamp: datetime | None,
        *,
        evaluated_at: datetime | None = None,
    ) -> FreshnessAssessment:
        policy = self.policies.get(product_family)
        if policy is None:
            return FreshnessAssessment(
                status=FreshnessStatus.UNKNOWN,
                policy_product_family=product_family,
                source_timestamp=source_timestamp,
                evaluated_at=evaluated_at or datetime.now(UTC),
            )
        return FreshnessAssessment(
            status=policy.classify(source_timestamp, evaluated_at=evaluated_at),
            policy_product_family=policy.product_family,
            source_timestamp=source_timestamp,
            evaluated_at=evaluated_at or datetime.now(UTC),
        )


class ProductMetadata(BaseModel):
    """Compact value object attached to a geospatial product or source scene."""

    schema_version: str = "geospatial-product-metadata/v1"
    source: SourceIdentity
    temporal: TemporalMetadata
    processing: ProcessingMetadata
    spatial: SpatialMetadata | None = None
    runtime_mode: AppMode
    quality: QualityGrade
    data_state: SourceAvailabilityStatus
    freshness: FreshnessAssessment | None = None
    limitations: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    parent_inputs: list[LineageReference] = Field(default_factory=list)
    assets: list[AssetReference] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_data_state(self) -> "ProductMetadata":
        if self.quality is QualityGrade.NO_DATA and self.data_state is SourceAvailabilityStatus.AVAILABLE:
            raise ValueError("NO_DATA quality cannot be paired with AVAILABLE data_state")
        return self


def _normalise_sha256(value: str | None) -> str | None:
    if value is not None and (len(value) != 64 or any(character not in "0123456789abcdefABCDEF" for character in value)):
        raise ValueError("checksum_sha256 must be a 64-character hexadecimal SHA-256 digest")
    return value.lower() if value is not None else None
