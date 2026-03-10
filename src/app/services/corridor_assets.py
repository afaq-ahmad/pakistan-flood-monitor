from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import geopandas as gpd
from shapely.geometry import LineString, MultiLineString, MultiPolygon
from shapely.ops import linemerge


@dataclass(slots=True)
class CorridorProductBundle:
    corridors: gpd.GeoDataFrame
    bounding_boxes: gpd.GeoDataFrame
    monitoring_buffers: gpd.GeoDataFrame
    basin_overlays: gpd.GeoDataFrame | None
    district_intersections: gpd.GeoDataFrame | None
    asset_masks: dict[str, gpd.GeoDataFrame]


def _as_multipolygon(geometry):
    if geometry.is_empty:
        return geometry
    if geometry.geom_type == "Polygon":
        return MultiPolygon([geometry])
    return geometry


def _as_multiline(geometry):
    if geometry.is_empty:
        return geometry
    if geometry.geom_type == "LineString":
        return MultiLineString([geometry])
    return geometry


def load_corridors(
    source_path: str | Path,
    target_crs: str = "EPSG:4326",
    corridor_id_column: str = "corridor_id",
    name_column: str = "name",
) -> gpd.GeoDataFrame:
    """Load corridor polygons from GeoJSON/GeoPackage/Shapefile with cleaned CRS and geometry."""
    corridors = gpd.read_file(source_path)
    if corridors.empty:
        raise ValueError("No corridor features found in source file")

    if corridors.crs is None:
        raise ValueError("Input corridors must include a source CRS")

    corridors = corridors.to_crs(target_crs)
    corridors["geometry"] = corridors.geometry.make_valid().buffer(0)
    corridors = corridors[~corridors.geometry.is_empty].copy()
    corridors = corridors[corridors.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    corridors["geometry"] = corridors.geometry.apply(_as_multipolygon)
    corridors = corridors.explode(index_parts=False).reset_index(drop=True)

    if corridor_id_column not in corridors.columns:
        corridors[corridor_id_column] = [f"corridor-{idx + 1}" for idx in corridors.index]
    corridors[corridor_id_column] = corridors[corridor_id_column].astype(str)

    if name_column not in corridors.columns:
        corridors[name_column] = corridors[corridor_id_column]

    return corridors[[corridor_id_column, name_column, "geometry"]].rename(
        columns={corridor_id_column: "corridor_id", name_column: "name"}
    )


def derive_corridor_products(
    corridors: gpd.GeoDataFrame,
    monitoring_buffer_meters: float,
    basins: gpd.GeoDataFrame | None = None,
    districts: gpd.GeoDataFrame | None = None,
    asset_layers: Mapping[str, gpd.GeoDataFrame] | None = None,
) -> CorridorProductBundle:
    """Generate corridor bbox, buffer, basin/district overlays, and optional asset masks."""
    corridors = corridors.to_crs("EPSG:4326")
    projected = corridors.to_crs("EPSG:3857")

    bbox = corridors.copy()
    bbox["geometry"] = corridors.geometry.envelope

    monitoring_buffer = projected.copy()
    monitoring_buffer["geometry"] = projected.geometry.buffer(monitoring_buffer_meters)
    monitoring_buffer = monitoring_buffer.to_crs("EPSG:4326")

    basin_overlay = None
    if basins is not None:
        basin_overlay = gpd.overlay(corridors, basins.to_crs("EPSG:4326"), how="intersection", keep_geom_type=False)

    district_intersections = None
    if districts is not None:
        district_intersections = gpd.overlay(corridors, districts.to_crs("EPSG:4326"), how="intersection", keep_geom_type=False)

    asset_masks: dict[str, gpd.GeoDataFrame] = {}
    if asset_layers:
        for asset_name, layer in asset_layers.items():
            asset_masks[asset_name] = gpd.overlay(
                monitoring_buffer,
                layer.to_crs("EPSG:4326"),
                how="intersection",
                keep_geom_type=False,
            )

    return CorridorProductBundle(
        corridors=corridors,
        bounding_boxes=bbox,
        monitoring_buffers=monitoring_buffer,
        basin_overlays=basin_overlay,
        district_intersections=district_intersections,
        asset_masks=asset_masks,
    )


def derive_embankment_side_polygons(
    embankments: gpd.GeoDataFrame,
    side_buffer_meters: float = 150,
    protected_side: str = "left",
) -> gpd.GeoDataFrame:
    """Build protected/river side polygons for embankment lines."""
    if protected_side not in {"left", "right"}:
        raise ValueError("protected_side must be either 'left' or 'right'")

    lines = embankments.to_crs("EPSG:3857").copy()
    lines["geometry"] = lines.geometry.make_valid()
    lines = lines[lines.geometry.geom_type.isin(["LineString", "MultiLineString"])].copy()
    lines["geometry"] = lines.geometry.apply(_as_multiline)
    lines = lines.explode(index_parts=False).reset_index(drop=True)

    side_rows: list[dict] = []
    for _, row in lines.iterrows():
        if isinstance(row.geometry, LineString):
            line_parts = [row.geometry]
        else:
            merged = linemerge(row.geometry)
            line_parts = [merged] if merged.geom_type == "LineString" else list(merged.geoms)

        for idx, line in enumerate(line_parts, start=1):
            left_side = line.buffer(side_buffer_meters, single_sided=True)
            right_side = line.buffer(-side_buffer_meters, single_sided=True)
            sides = {"left": left_side, "right": right_side}

            for side_name, geom in sides.items():
                if geom.is_empty:
                    continue
                side_rows.append(
                    {
                        "embankment_id": str(row.get("embankment_id", row.get("id", "embankment"))),
                        "segment_id": idx,
                        "side": "protected" if side_name == protected_side else "river",
                        "geometry": geom,
                    }
                )

    side_polygons = gpd.GeoDataFrame(side_rows, crs="EPSG:3857").to_crs("EPSG:4326")
    return side_polygons


def _write_vector_layer(layer: gpd.GeoDataFrame, output_path: Path) -> Path:
    try:
        layer.to_parquet(output_path)
        return output_path
    except ImportError:
        fallback = output_path.with_suffix(".geojson")
        layer.to_file(fallback, driver="GeoJSON")
        return fallback


def export_corridor_products(bundle: CorridorProductBundle, output_dir: str | Path) -> dict[str, Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, Path] = {}
    for name, layer in {
        "aoi_corridors": bundle.corridors,
        "corridor_bounding_boxes": bundle.bounding_boxes,
        "corridor_monitoring_buffers": bundle.monitoring_buffers,
    }.items():
        output_path = output_root / f"{name}.parquet"
        outputs[name] = _write_vector_layer(layer, output_path)

    if bundle.basin_overlays is not None:
        output_path = output_root / "corridor_basin_overlay.parquet"
        outputs["corridor_basin_overlay"] = _write_vector_layer(bundle.basin_overlays, output_path)

    if bundle.district_intersections is not None:
        output_path = output_root / "corridor_district_intersections.parquet"
        outputs["corridor_district_intersections"] = _write_vector_layer(bundle.district_intersections, output_path)

    for asset_name, layer in bundle.asset_masks.items():
        output_path = output_root / f"asset_mask_{asset_name}.parquet"
        outputs[f"asset_mask_{asset_name}"] = _write_vector_layer(layer, output_path)

    return outputs


def persist_corridor_products_to_postgis(bundle: CorridorProductBundle, engine) -> None:
    """Persist derived products to PostGIS tables for repeated reuse."""
    bundle.corridors.to_postgis("aoi_corridors", engine, if_exists="append", index=False)
    bundle.bounding_boxes.to_postgis("corridor_bounding_boxes", engine, if_exists="replace", index=False)
    bundle.monitoring_buffers.to_postgis("corridor_monitoring_buffers", engine, if_exists="replace", index=False)

    if bundle.basin_overlays is not None:
        bundle.basin_overlays.to_postgis("corridor_basin_overlay", engine, if_exists="replace", index=False)
    if bundle.district_intersections is not None:
        bundle.district_intersections.to_postgis("corridor_district_intersections", engine, if_exists="replace", index=False)

    for asset_name, layer in bundle.asset_masks.items():
        layer.to_postgis(f"asset_mask_{asset_name}", engine, if_exists="replace", index=False)
