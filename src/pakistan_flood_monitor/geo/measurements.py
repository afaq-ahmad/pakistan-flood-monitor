"""CRS-aware physical measurements for vector geometries.

All public functions accept Shapely geometries in ``source_crs`` (EPSG:4326 by
default).  Areas and lengths use WGS84 geodesics so geographic coordinates are
never treated as planar metres.  Distance and buffer operations use a local
azimuthal-equidistant projection centred on the supplied geometry; this is
appropriate for the corridor-scale operations in this project.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pyproj import CRS, Geod, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


WGS84 = CRS.from_epsg(4326)
_WGS84_GEOD = Geod(ellps="WGS84")


def area_sqkm(geometry: BaseGeometry, *, source_crs: str | CRS = WGS84) -> float:
    """Return geodesic polygonal area in square kilometres.

    Lines and points have zero area.  The absolute value is returned because
    GeoJSON ring orientation is not guaranteed by upstream providers.
    """

    if geometry is None or geometry.is_empty:
        return 0.0
    geographic = _to_wgs84(geometry, source_crs)
    return _polygonal_area_sq_m(geographic) / 1_000_000.0


def length_km(geometry: BaseGeometry, *, source_crs: str | CRS = WGS84) -> float:
    """Return WGS84 geodesic length in kilometres."""

    if geometry is None or geometry.is_empty:
        return 0.0
    geographic = _to_wgs84(geometry, source_crs)
    return _geodesic_length_m(geographic) / 1_000.0


def distance_m(
    left: BaseGeometry,
    right: BaseGeometry,
    *,
    source_crs: str | CRS = WGS84,
) -> float:
    """Return shortest geometry-to-geometry distance in metres.

    A local azimuthal-equidistant CRS avoids treating longitude/latitude degrees
    as metres while preserving local distances and buffers at Pakistan-scale
    corridor extents.
    """

    _require_nonempty(left, "left")
    _require_nonempty(right, "right")
    left_wgs84 = _to_wgs84(left, source_crs)
    right_wgs84 = _to_wgs84(right, source_crs)
    metric_crs = local_metric_crs((left_wgs84, right_wgs84), source_crs=WGS84)
    return float(_transform(left_wgs84, WGS84, metric_crs).distance(_transform(right_wgs84, WGS84, metric_crs)))


def intersection_area_sqkm(
    left: BaseGeometry,
    right: BaseGeometry,
    *,
    source_crs: str | CRS = WGS84,
) -> float:
    """Return the geodesic area of two geometries' intersection in km²."""

    _require_nonempty(left, "left")
    _require_nonempty(right, "right")
    left_wgs84 = _to_wgs84(left, source_crs)
    right_wgs84 = _to_wgs84(right, source_crs)
    return area_sqkm(left_wgs84.intersection(right_wgs84), source_crs=WGS84)


def buffer_m(
    geometry: BaseGeometry,
    distance_metres: float,
    *,
    source_crs: str | CRS = WGS84,
    **buffer_kwargs: Any,
) -> BaseGeometry:
    """Buffer a geometry by metres and return it in ``source_crs``.

    ``buffer_kwargs`` are passed to Shapely, allowing callers to request such
    features as ``single_sided=True`` for embankment-side construction.
    """

    _require_nonempty(geometry, "geometry")
    if not isinstance(distance_metres, (int, float)) or distance_metres == 0:
        raise ValueError("distance_metres must be a non-zero numeric value")

    source = CRS.from_user_input(source_crs)
    geographic = _to_wgs84(geometry, source)
    metric_crs = local_metric_crs(geographic, source_crs=WGS84)
    projected = _transform(geographic, WGS84, metric_crs)
    buffered = projected.buffer(float(distance_metres), **buffer_kwargs)
    return _transform(buffered, metric_crs, source)


def local_metric_crs(
    geometry_or_geometries: BaseGeometry | Iterable[BaseGeometry],
    *,
    source_crs: str | CRS = WGS84,
) -> CRS:
    """Choose a local metre-based CRS centred on the supplied geometry/ies.

    A local azimuthal-equidistant projection is deliberately preferred to a
    guessed UTM zone.  It remains usable for corridors spanning a zone boundary
    and does not inherit Web Mercator's latitude-dependent scale distortion.
    """

    geometries = _as_geometries(geometry_or_geometries)
    geographic = [_to_wgs84(geometry, source_crs) for geometry in geometries]
    minx = min(geometry.bounds[0] for geometry in geographic)
    miny = min(geometry.bounds[1] for geometry in geographic)
    maxx = max(geometry.bounds[2] for geometry in geographic)
    maxy = max(geometry.bounds[3] for geometry in geographic)
    lon_0 = (minx + maxx) / 2.0
    lat_0 = (miny + maxy) / 2.0
    return CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat_0:.12f} +lon_0={lon_0:.12f} +datum=WGS84 +units=m +no_defs"
    )


def _as_geometries(geometry_or_geometries: BaseGeometry | Iterable[BaseGeometry]) -> list[BaseGeometry]:
    if isinstance(geometry_or_geometries, BaseGeometry):
        geometries = [geometry_or_geometries]
    else:
        geometries = list(geometry_or_geometries)
    if not geometries:
        raise ValueError("at least one geometry is required")
    for geometry in geometries:
        _require_nonempty(geometry, "geometry")
    return geometries


def _require_nonempty(geometry: BaseGeometry, name: str) -> None:
    if geometry is None or geometry.is_empty:
        raise ValueError(f"{name} must be a non-empty geometry")


def _to_wgs84(geometry: BaseGeometry, source_crs: str | CRS) -> BaseGeometry:
    _require_nonempty(geometry, "geometry")
    source = CRS.from_user_input(source_crs)
    return geometry if source == WGS84 else _transform(geometry, source, WGS84)


def _transform(geometry: BaseGeometry, source: str | CRS, target: str | CRS) -> BaseGeometry:
    transformer = Transformer.from_crs(source, target, always_xy=True)
    return transform(transformer.transform, geometry)


def _polygonal_area_sq_m(geometry: BaseGeometry) -> float:
    if geometry.geom_type in {"Polygon", "MultiPolygon"}:
        area, _ = _WGS84_GEOD.geometry_area_perimeter(geometry)
        return abs(float(area))
    if hasattr(geometry, "geoms"):
        return sum(_polygonal_area_sq_m(part) for part in geometry.geoms)
    return 0.0


def _geodesic_length_m(geometry: BaseGeometry) -> float:
    if geometry.geom_type in {"LineString", "LinearRing", "MultiLineString"}:
        return abs(float(_WGS84_GEOD.geometry_length(geometry)))
    if geometry.geom_type in {"Polygon", "MultiPolygon"}:
        _, perimeter = _WGS84_GEOD.geometry_area_perimeter(geometry)
        return abs(float(perimeter))
    if hasattr(geometry, "geoms"):
        return sum(_geodesic_length_m(part) for part in geometry.geoms)
    return 0.0
