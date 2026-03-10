from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Protocol


@dataclass(slots=True)
class HydrometSummary:
    corridor_id: str
    timestamp: datetime
    rainfall_24h_mm: float
    rainfall_72h_mm: float
    rainfall_7d_mm: float
    rainfall_anomaly_z: float | None
    discharge_percentile: float
    watch_exceedance: bool
    warning_exceedance: bool
    critical_exceedance: bool
    stress_score: float


@dataclass(frozen=True, slots=True)
class ReachHydrologyThresholds:
    rainfall_watch_24h_mm: float
    rainfall_warning_24h_mm: float
    rainfall_critical_24h_mm: float
    rainfall_watch_72h_mm: float
    rainfall_warning_72h_mm: float
    rainfall_critical_72h_mm: float
    discharge_watch_percentile: float
    discharge_warning_percentile: float
    discharge_critical_percentile: float


DEFAULT_REACH_HYDROLOGY_THRESHOLDS = ReachHydrologyThresholds(
    rainfall_watch_24h_mm=35.0,
    rainfall_warning_24h_mm=65.0,
    rainfall_critical_24h_mm=100.0,
    rainfall_watch_72h_mm=70.0,
    rainfall_warning_72h_mm=130.0,
    rainfall_critical_72h_mm=190.0,
    discharge_watch_percentile=0.80,
    discharge_warning_percentile=0.90,
    discharge_critical_percentile=0.97,
)


REACH_HYDROLOGY_THRESHOLDS: dict[str, ReachHydrologyThresholds] = {
    "indus-lower": ReachHydrologyThresholds(
        rainfall_watch_24h_mm=30.0,
        rainfall_warning_24h_mm=55.0,
        rainfall_critical_24h_mm=85.0,
        rainfall_watch_72h_mm=60.0,
        rainfall_warning_72h_mm=110.0,
        rainfall_critical_72h_mm=165.0,
        discharge_watch_percentile=0.78,
        discharge_warning_percentile=0.88,
        discharge_critical_percentile=0.96,
    ),
    "indus-mid": ReachHydrologyThresholds(
        rainfall_watch_24h_mm=35.0,
        rainfall_warning_24h_mm=65.0,
        rainfall_critical_24h_mm=100.0,
        rainfall_watch_72h_mm=70.0,
        rainfall_warning_72h_mm=130.0,
        rainfall_critical_72h_mm=190.0,
        discharge_watch_percentile=0.80,
        discharge_warning_percentile=0.90,
        discharge_critical_percentile=0.97,
    ),
    "indus-upper": ReachHydrologyThresholds(
        rainfall_watch_24h_mm=45.0,
        rainfall_warning_24h_mm=75.0,
        rainfall_critical_24h_mm=120.0,
        rainfall_watch_72h_mm=90.0,
        rainfall_warning_72h_mm=155.0,
        rainfall_critical_72h_mm=230.0,
        discharge_watch_percentile=0.82,
        discharge_warning_percentile=0.91,
        discharge_critical_percentile=0.975,
    ),
}


def get_reach_hydrology_thresholds(corridor_reach: str | None) -> ReachHydrologyThresholds:
    if not corridor_reach:
        return DEFAULT_REACH_HYDROLOGY_THRESHOLDS

    normalized = corridor_reach.strip().lower()
    if normalized in REACH_HYDROLOGY_THRESHOLDS:
        return REACH_HYDROLOGY_THRESHOLDS[normalized]

    for key, value in REACH_HYDROLOGY_THRESHOLDS.items():
        if normalized.startswith(key):
            return value
    return DEFAULT_REACH_HYDROLOGY_THRESHOLDS


class RainfallProvider(Protocol):
    def fetch(self, corridor_geometry: dict, start_time: datetime, end_time: datetime) -> Iterable[float]:
        ...


class GloFASProvider(Protocol):
    def fetch_indicators(self, corridor_geometry: dict, valid_time: datetime) -> dict[str, float]:
        ...


class HydrometRepository(Protocol):
    def upsert_summary(self, summary: HydrometSummary) -> None:
        ...


class IMERGRainfallFetcher:
    def __init__(self, provider: RainfallProvider) -> None:
        self._provider = provider

    def corridor_summary(self, *, corridor_geometry: dict, reference_time: datetime, baseline_mm: float | None = None) -> dict:
        rainfall_24h = list(self._provider.fetch(corridor_geometry, reference_time - timedelta(hours=24), reference_time))
        rainfall_72h = list(self._provider.fetch(corridor_geometry, reference_time - timedelta(hours=72), reference_time))
        rainfall_7d = list(self._provider.fetch(corridor_geometry, reference_time - timedelta(days=7), reference_time))

        sum_24h = float(sum(rainfall_24h))
        sum_72h = float(sum(rainfall_72h))
        sum_7d = float(sum(rainfall_7d))

        anomaly = None
        if baseline_mm and baseline_mm > 0:
            anomaly = (sum_7d - baseline_mm) / baseline_mm

        return {
            "rainfall_24h_mm": sum_24h,
            "rainfall_72h_mm": sum_72h,
            "rainfall_7d_mm": sum_7d,
            "rainfall_anomaly_z": anomaly,
        }


class GloFASFetcher:
    def __init__(self, provider: GloFASProvider) -> None:
        self._provider = provider

    def corridor_summary(self, corridor_geometry: dict, valid_time: datetime) -> dict:
        indicators = self._provider.fetch_indicators(corridor_geometry, valid_time)
        percentile = float(indicators.get("percentile", 0.0))
        return {
            "discharge_percentile": percentile,
            "watch_exceedance": percentile >= 0.8,
            "warning_exceedance": percentile >= 0.9,
            "critical_exceedance": percentile >= 0.97,
        }


def compute_hydromet_stress_score(rainfall: dict, glofas: dict) -> float:
    rain_component = min(1.0, (rainfall["rainfall_24h_mm"] / 100.0) * 0.25 + (rainfall["rainfall_72h_mm"] / 180.0) * 0.35)
    anomaly_component = max(0.0, min(1.0, (rainfall.get("rainfall_anomaly_z") or 0.0))) * 0.15
    discharge_component = min(1.0, glofas.get("discharge_percentile", 0.0)) * 0.25
    return max(0.0, min(1.0, rain_component + anomaly_component + discharge_component))


class HydrometIngestionJob:
    def __init__(
        self,
        rainfall_fetcher: IMERGRainfallFetcher,
        glofas_fetcher: GloFASFetcher,
        repository: HydrometRepository,
    ) -> None:
        self._rainfall_fetcher = rainfall_fetcher
        self._glofas_fetcher = glofas_fetcher
        self._repository = repository

    def run(
        self,
        *,
        corridor_id: str,
        corridor_geometry: dict,
        timestamp: datetime,
        baseline_7d_mm: float | None = None,
    ) -> HydrometSummary:
        rainfall = self._rainfall_fetcher.corridor_summary(
            corridor_geometry=corridor_geometry,
            reference_time=timestamp,
            baseline_mm=baseline_7d_mm,
        )
        glofas = self._glofas_fetcher.corridor_summary(corridor_geometry=corridor_geometry, valid_time=timestamp)
        stress_score = compute_hydromet_stress_score(rainfall, glofas)

        summary = HydrometSummary(
            corridor_id=corridor_id,
            timestamp=timestamp,
            rainfall_24h_mm=rainfall["rainfall_24h_mm"],
            rainfall_72h_mm=rainfall["rainfall_72h_mm"],
            rainfall_7d_mm=rainfall["rainfall_7d_mm"],
            rainfall_anomaly_z=rainfall["rainfall_anomaly_z"],
            discharge_percentile=glofas["discharge_percentile"],
            watch_exceedance=glofas["watch_exceedance"],
            warning_exceedance=glofas["warning_exceedance"],
            critical_exceedance=glofas["critical_exceedance"],
            stress_score=stress_score,
        )
        self._repository.upsert_summary(summary)
        return summary


class InMemoryHydrometRepository:
    def __init__(self) -> None:
        self.records: dict[tuple[str, datetime], HydrometSummary] = {}

    def upsert_summary(self, summary: HydrometSummary) -> None:
        self.records[(summary.corridor_id, summary.timestamp)] = summary


class SequenceRainfallProvider:
    """Simple deterministic provider for tests/jobs; values represent mm per fetch window step."""

    def __init__(self, values: dict[int, list[float]]) -> None:
        self._values = values

    def fetch(self, corridor_geometry: dict, start_time: datetime, end_time: datetime) -> Iterable[float]:
        hours = int((end_time - start_time).total_seconds() / 3600)
        return self._values.get(hours, [])


class StaticGloFASProvider:
    def __init__(self, percentile: float) -> None:
        self._percentile = percentile

    def fetch_indicators(self, corridor_geometry: dict, valid_time: datetime) -> dict[str, float]:
        return {"percentile": self._percentile}
