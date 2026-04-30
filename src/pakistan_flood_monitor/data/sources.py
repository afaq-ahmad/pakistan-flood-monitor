from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Mapping


@dataclass
class SceneMetadata:
    sensor: str
    scene_id: str
    acquisition_date: date
    cloud_cover: float | None = None
    assets: Mapping[str, str] | None = None


class DataCatalog:
    """Abstracts free EO and supporting datasets used by the system."""

    sensors = ("sentinel-1", "sentinel-2", "landsat", "hls")
    support = ("imerg", "glofas", "copernicus-dem", "jrc-gsw")

    def fetch_scenes(self, sensor: str, aoi_name: str, start: date, end: date) -> List[SceneMetadata]:
        if sensor not in self.sensors:
            raise ValueError(f"Unknown sensor: {sensor}")
        return [
            SceneMetadata(
                sensor=sensor,
                scene_id=f"{sensor}-{aoi_name}-{start}",
                acquisition_date=start,
                cloud_cover=18.0,
                assets={"vv": f"memory://{aoi_name}/vv", "vh": f"memory://{aoi_name}/vh"} if sensor == "sentinel-1" else None,
            )
        ]

    def fetch_supporting_layers(self, aoi_name: str) -> Dict[str, str]:
        return {
            "imerg": f"imerg://{aoi_name}",
            "glofas": f"glofas://{aoi_name}",
            "dem": f"copdem://{aoi_name}",
            "water_history": f"jrc-gsw://{aoi_name}",
        }
