"""
Real satellite data catalog using the free Earth Search STAC API.
No API key required — https://earth-search.aws.element84.com/v1

Supports: Sentinel-1 GRD (SAR), Sentinel-2 L2A (Optical),
          Landsat C2 L2, Copernicus DEM
"""
from __future__ import annotations

import json
import warnings
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from pakistan_flood_monitor.config import AppMode, settings
from pakistan_flood_monitor.models.observations import (
    ObservationStatus,
    OperationalDataIntegrityError,
    ScientificObservation,
    SourceAvailabilityStatus,
)

STAC_ENDPOINT = "https://earth-search.aws.element84.com/v1"

# ── Collection IDs on Earth Search ────────────────────────────────────────────
COLLECTION_SENTINEL1 = "sentinel-1-grd"
COLLECTION_SENTINEL2 = "sentinel-2-l2a"
COLLECTION_LANDSAT   = "landsat-c2-l2"
COLLECTION_COP_DEM   = "cop-dem-glo-30"

# ── Pilot corridor bounding boxes  [west, south, east, north]  (EPSG:4326) ───
CORRIDOR_BBOXES: Dict[str, List[float]] = {
    "Indus-Lower":   [66.8, 25.2, 69.5, 27.8],
    "Indus-Upper":   [70.5, 33.0, 74.0, 34.5],
    "Chenab-Middle": [71.5, 30.5, 73.5, 32.2],
    "Jhelum-Lower":  [72.8, 32.0, 74.2, 33.2],
    "Sutlej-Lower":  [70.2, 28.5, 72.5, 30.5],
    "Kabul-Nowshera":[71.5, 33.8, 72.8, 34.6],
}


@dataclass
class SceneMetadata:
    sensor: str
    scene_id: str
    acquisition_date: date
    cloud_cover: Optional[float] = None
    assets: Optional[Mapping[str, str]] = None
    # Extended real fields
    thumbnail_url: Optional[str] = None
    visual_url: Optional[str] = None
    bbox: Optional[List[float]] = None
    stac_item_url: Optional[str] = None
    properties: Dict = field(default_factory=dict)
    observation_status: ObservationStatus = ObservationStatus.OBSERVED
    availability_status: SourceAvailabilityStatus = SourceAvailabilityStatus.AVAILABLE
    synthetic: bool = False


class DataCatalog:
    """
    Real Earth Observation data catalog backed by the free Earth Search STAC API.
    No credentials required. Test/demo mode can use clearly labelled stubs when the
    network is unavailable; operational mode fails closed.
    """

    sensors = ("sentinel-1", "sentinel-2", "landsat", "hls")
    support = ("imerg", "glofas", "copernicus-dem", "jrc-gsw")

    _COLLECTION_MAP = {
        "sentinel-1": COLLECTION_SENTINEL1,
        "sentinel-2": COLLECTION_SENTINEL2,
        "landsat":    COLLECTION_LANDSAT,
    }

    def __init__(self, stac_endpoint: str = STAC_ENDPOINT, app_mode: AppMode | None = None):
        self.stac_endpoint = stac_endpoint
        self.app_mode = app_mode or settings.app_mode
        self._client = None

    def _unavailable_source(self, sensor: str) -> OperationalDataIntegrityError:
        observation = ScientificObservation(
            name=f"{sensor}_scene",
            value=None,
            units="scene",
            status=ObservationStatus.UNAVAILABLE,
            availability=SourceAvailabilityStatus.UNAVAILABLE,
            source_uri=self.stac_endpoint,
            processing_version="earth-search-discovery-v1",
            quality_status="source_unavailable",
            availability_reason_code="provider_unreachable",
        )
        return OperationalDataIntegrityError(
            f"Operational scene discovery failed for {sensor}; no synthetic fallback is permitted.",
            observations={observation.name: observation},
        )

    def _no_data_source(self, sensor: str, start: date, end: date) -> OperationalDataIntegrityError:
        observation = ScientificObservation(
            name=f"{sensor}_scene",
            value=None,
            units="scene",
            status=ObservationStatus.UNAVAILABLE,
            availability=SourceAvailabilityStatus.NO_DATA,
            source_uri=self.stac_endpoint,
            processing_version="earth-search-discovery-v1",
            quality_status="no_scenes_returned",
            availability_reason_code="no_scenes_in_requested_window",
            freshness_rule=f"scene acquisition between {start.isoformat()} and {end.isoformat()}",
        )
        return OperationalDataIntegrityError(
            f"No {sensor} scenes were available for the requested operational window.",
            observations={observation.name: observation},
        )

    def _get_client(self):
        """Lazily initialise the STAC client."""
        if self._client is None:
            try:
                import pystac_client
                self._client = pystac_client.Client.open(self.stac_endpoint)
            except Exception as exc:
                warnings.warn(f"Could not connect to STAC endpoint: {exc}")
                self._client = False   # sentinel value: unavailable
        return self._client if self._client is not False else None

    def _corridor_bbox(self, aoi_name: str) -> List[float]:
        if aoi_name in CORRIDOR_BBOXES:
            return CORRIDOR_BBOXES[aoi_name]
        # Fallback: whole-Pakistan bounding box
        return [60.5, 23.5, 77.5, 37.5]

    def fetch_scenes(
        self,
        sensor: str,
        aoi_name: str,
        start: date,
        end: date,
        max_items: int = 10,
        cloud_cover_max: float = 80.0,
    ) -> List[SceneMetadata]:
        """
        Query Earth Search for real satellite scenes over the given corridor.
        Test/demo mode falls back to labelled stub data. Operational mode returns
        an explicit unavailable state through ``OperationalDataIntegrityError``.
        """
        collection = self._COLLECTION_MAP.get(sensor)
        if collection is None:
            raise ValueError(f"Unknown sensor: {sensor}. Choose from: {list(self._COLLECTION_MAP)}")

        client = self._get_client()
        if client is None:
            if self.app_mode is AppMode.OPERATIONAL:
                raise self._unavailable_source(sensor)
            return self._stub_scenes(sensor, aoi_name, start)

        bbox = self._corridor_bbox(aoi_name)
        date_str = f"{start.isoformat()}/{end.isoformat()}"

        try:
            search_kwargs = dict(
                collections=[collection],
                bbox=bbox,
                datetime=date_str,
                max_items=max_items,
            )
            # Sentinel-2 supports cloud cover filtering
            if sensor == "sentinel-2" and cloud_cover_max < 100:
                search_kwargs["query"] = {"eo:cloud_cover": {"lt": cloud_cover_max}}

            results = client.search(**search_kwargs)
            items = list(results.items())
        except Exception as exc:
            if self.app_mode is AppMode.OPERATIONAL:
                raise self._unavailable_source(sensor) from exc
            warnings.warn(f"STAC search failed: {exc}. Returning labelled demo data.")
            return self._stub_scenes(sensor, aoi_name, start)

        if not items:
            if self.app_mode is AppMode.OPERATIONAL:
                raise self._no_data_source(sensor, start, end)
            warnings.warn("STAC search returned no scenes. Returning labelled demo data.")
            return self._stub_scenes(sensor, aoi_name, start)

        scenes: List[SceneMetadata] = []
        for item in items:
            assets_raw = {k: v.href for k, v in item.assets.items()}
            thumbnail = assets_raw.get("thumbnail") or assets_raw.get("rendered_preview") or ""
            visual    = assets_raw.get("visual") or assets_raw.get("TCI") or ""
            acquired  = item.datetime.date() if item.datetime else start

            scenes.append(SceneMetadata(
                sensor=sensor,
                scene_id=item.id,
                acquisition_date=acquired,
                cloud_cover=item.properties.get("eo:cloud_cover"),
                assets=assets_raw,
                thumbnail_url=thumbnail,
                visual_url=visual,
                bbox=list(item.bbox) if item.bbox else bbox,
                stac_item_url=item.get_self_href(),
                properties=dict(item.properties),
                observation_status=ObservationStatus.OBSERVED,
                availability_status=SourceAvailabilityStatus.AVAILABLE,
                synthetic=False,
            ))
        return scenes

    def fetch_all_corridors(
        self,
        sensor: str,
        days_back: int = 14,
        max_items_each: int = 5,
        cloud_cover_max: float = 60.0,
    ) -> Dict[str, List[SceneMetadata]]:
        """Fetch scenes for every configured corridor."""
        end   = datetime.utcnow().date()
        start = end - timedelta(days=days_back)
        result: Dict[str, List[SceneMetadata]] = {}
        for corridor in CORRIDOR_BBOXES:
            try:
                result[corridor] = self.fetch_scenes(
                    sensor, corridor, start, end,
                    max_items=max_items_each,
                    cloud_cover_max=cloud_cover_max,
                )
            except Exception as exc:
                if self.app_mode is AppMode.OPERATIONAL:
                    raise
                warnings.warn(f"Failed to fetch {sensor} for {corridor}: {exc}")
                result[corridor] = []
        return result

    def fetch_supporting_layers(self, aoi_name: str) -> Dict[str, str]:
        """
        Supporting science layers. These are free global datasets:
          - GPM-IMERG: NASA rainfall (https://gpm.nasa.gov/data/imerg)
          - GloFAS:    ECMWF river discharge forecasts (free, registration needed)
          - CopDEM:    Copernicus 30m DEM (available via Earth Search)
          - JRC-GSW:   Global Surface Water (static historical baseline)
        """
        bbox = self._corridor_bbox(aoi_name)
        return {
            "imerg":         "https://gpm.nasa.gov/data/imerg",
            "glofas":        "https://cds.climate.copernicus.eu/cdsapp#!/dataset/cems-glofas-historical",
            "dem":           "https://earth-search.aws.element84.com/v1/collections/cop-dem-glo-30",
            "water_history": "https://global-surface-water.appspot.com/download",
            "bbox":          json.dumps(bbox),
        }

    def _stub_scenes(
        self, sensor: str, aoi_name: str, start: date
    ) -> List[SceneMetadata]:
        """Offline test/demo fixture; never returned in operational mode."""
        if self.app_mode is AppMode.OPERATIONAL:
            raise self._unavailable_source(sensor)
        return [
            SceneMetadata(
                sensor=sensor,
                scene_id=f"{sensor}-{aoi_name}-{start}-STUB",
                acquisition_date=start,
                cloud_cover=0.0,
                assets={},
                thumbnail_url="",
                visual_url="",
                bbox=self._corridor_bbox(aoi_name),
                properties={"stub": True, "watermark": "SIMULATED / DEMO DATA"},
                observation_status=ObservationStatus.SIMULATED,
                availability_status=SourceAvailabilityStatus.DEGRADED,
                synthetic=True,
            )
        ]

    # ── Convenience helpers for the Streamlit page ────────────────────────────
    def available_corridors(self) -> List[str]:
        return list(CORRIDOR_BBOXES.keys())

    def collection_info(self) -> List[Dict]:
        return [
            {
                "collection": COLLECTION_SENTINEL1,
                "sensor":     "Sentinel-1 SAR",
                "provider":   "ESA / Copernicus",
                "auth":       "None (public)",
                "description":"C-band synthetic aperture radar — works through cloud and night. Used for SAR anomaly / backscatter change detection.",
                "resolution": "10 m IW mode",
                "revisit":    "~6 days",
                "endpoint":   f"{STAC_ENDPOINT}/collections/{COLLECTION_SENTINEL1}",
            },
            {
                "collection": COLLECTION_SENTINEL2,
                "sensor":     "Sentinel-2 Optical",
                "provider":   "ESA / Copernicus",
                "auth":       "None (public)",
                "description":"Multi-spectral optical. Blue/Green/NIR bands used for NDWI water index. Analyst visual corroboration.",
                "resolution": "10 m (visual), 20–60 m other bands",
                "revisit":    "~5 days",
                "endpoint":   f"{STAC_ENDPOINT}/collections/{COLLECTION_SENTINEL2}",
            },
            {
                "collection": COLLECTION_LANDSAT,
                "sensor":     "Landsat 8/9 Optical",
                "provider":   "USGS / NASA",
                "auth":       "None (public)",
                "description":"Longer historical record. Band 3 / Band 5 used for NDWI as backup to Sentinel-2.",
                "resolution": "30 m",
                "revisit":    "~16 days",
                "endpoint":   f"{STAC_ENDPOINT}/collections/{COLLECTION_LANDSAT}",
            },
            {
                "collection": "GPM-IMERG",
                "sensor":     "GPM IMERG Rainfall",
                "provider":   "NASA",
                "auth":       "Earthdata login (free)",
                "description":"Global precipitation (30-min, 0.1°). Used as hydromet trigger for SAR flood candidate escalation.",
                "resolution": "0.1 deg (~11 km)",
                "revisit":    "30 min",
                "endpoint":   "https://gpm.nasa.gov/data/imerg",
            },
            {
                "collection": "GloFAS",
                "sensor":     "GloFAS River Discharge",
                "provider":   "ECMWF / Copernicus",
                "auth":       "CDS registration (free)",
                "description":"Global river discharge forecasts and return period analysis. Confirms seasonal anomaly.",
                "resolution": "0.05 deg river network",
                "revisit":    "Daily forecast",
                "endpoint":   "https://cds.climate.copernicus.eu",
            },
        ]
