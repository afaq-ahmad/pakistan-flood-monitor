from __future__ import annotations

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session



def validate_geometry_wkt(db: Session, wkt_geometry: str) -> bool:
    statement = select(func.ST_IsValid(func.ST_GeomFromText(wkt_geometry, 4326)))
    return bool(db.scalar(statement))


def intersection_area_sqkm(db: Session, geom_a_wkt: str, geom_b_wkt: str) -> float:
    intersection = func.ST_Intersection(
        func.ST_GeomFromText(geom_a_wkt, 4326),
        func.ST_GeomFromText(geom_b_wkt, 4326),
    )
    statement = select(
        func.ST_Area(cast(intersection, Geography(srid=4326)))
        / 1_000_000.0
    )
    return float(db.scalar(statement) or 0.0)


def build_raster_metadata_payload(scene_id: str, asset_uri: str, band_count: int, crs: str) -> dict[str, str | int]:
    return {
        "scene_id": scene_id,
        "asset_uri": asset_uri,
        "band_count": band_count,
        "crs": crs,
    }
