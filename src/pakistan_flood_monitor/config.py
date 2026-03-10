from pydantic import BaseModel, Field


class Thresholds(BaseModel):
    sar_drop_db: float = Field(default=2.5, description="Backscatter drop threshold in dB")
    ndwi: float = Field(default=0.2, description="NDWI threshold for optical water")
    confidence_warning: float = 0.55
    confidence_critical: float = 0.75


class Settings(BaseModel):
    project_name: str = "Pakistan River Flood Monitoring and Breach Detection System"
    country: str = "Pakistan"
    thresholds: Thresholds = Thresholds()


settings = Settings()
