from pydantic import BaseModel, Field


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
    project_name: str = "Pakistan River Flood Monitoring and Breach Detection System"
    country: str = "Pakistan"
    thresholds: Thresholds = Thresholds()
    pilot_corridors: list[Corridor] = [
        Corridor(name="Indus-Lower", district="Sindh", priority=1),
        Corridor(name="Chenab-Middle", district="Punjab", priority=1),
        Corridor(name="Kabul-Nowshera", district="Khyber Pakhtunkhwa", priority=2),
    ]


settings = Settings()
