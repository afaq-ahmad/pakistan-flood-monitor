from datetime import datetime
from enum import Enum
from typing import Dict, List

from pydantic import BaseModel


class AlertLevel(str, Enum):
    watch = "watch"
    warning = "warning"
    critical = "critical"


class AOI(BaseModel):
    name: str
    district: str
    geometry_wkt: str


class FloodDetectionResult(BaseModel):
    aoi: str
    timestamp: datetime
    flood_probability: float
    flood_area_km2: float
    breach_risk_score: float
    alert_level: AlertLevel
    indicators: Dict[str, float]


class ExposureStats(BaseModel):
    affected_population: int
    affected_cropland_km2: float
    affected_roads_km: float
    affected_schools: int
    affected_hospitals: int


class ProcessingReport(BaseModel):
    run_id: str
    source_sensors: List[str]
    detections: List[FloodDetectionResult]
    exposure: Dict[str, ExposureStats]
