from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString, Polygon

from app.services.baseline_layers import (
    derive_terrain_layers,
    generate_permanent_water_masks,
    generate_seasonal_water_masks,
    prepare_exposure_baseline_layers,
)
from app.services.corridor_assets import derive_corridor_products, derive_embankment_side_polygons, load_corridors


def _write_test_raster(path: Path, array: np.ndarray) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=array.shape[0],
        width=array.shape[1],
        count=1,
        dtype=array.dtype,
        crs="EPSG:4326",
        transform=from_origin(0, 5, 1, 1),
    ) as dst:
        dst.write(array, 1)


def test_corridor_ingest_and_derived_products(tmp_path: Path) -> None:
    corridor_path = tmp_path / "corridors.geojson"
    corridor_gdf = gpd.GeoDataFrame(
        [{"corridor_id": "indus-1", "name": "Indus Reach", "geometry": Polygon([(0, 0), (0, 2), (2, 2), (2, 0)])}],
        crs="EPSG:4326",
    )
    corridor_gdf.to_file(corridor_path, driver="GeoJSON")

    loaded = load_corridors(corridor_path)
    bundle = derive_corridor_products(loaded, monitoring_buffer_meters=500)

    assert len(bundle.corridors) == 1
    assert not bundle.bounding_boxes.empty
    assert bundle.monitoring_buffers.geometry.iloc[0].area > bundle.corridors.geometry.iloc[0].area


def test_embankment_side_polygons_are_generated() -> None:
    embankments = gpd.GeoDataFrame(
        [{"embankment_id": "emb-1", "geometry": LineString([(0, 0), (1, 0)])}],
        crs="EPSG:4326",
    )

    sides = derive_embankment_side_polygons(embankments, side_buffer_meters=100)
    assert set(sides["side"]) == {"protected", "river"}


def test_baseline_mask_and_terrain_generation(tmp_path: Path) -> None:
    corridors = gpd.GeoDataFrame(
        [{"corridor_id": "indus-1", "name": "Indus Reach", "geometry": Polygon([(0, 0), (0, 5), (5, 5), (5, 0)])}],
        crs="EPSG:4326",
    )

    permanent_raster = tmp_path / "permanent.tif"
    seasonal_raster = tmp_path / "seasonal.tif"
    dem_raster = tmp_path / "dem.tif"

    _write_test_raster(permanent_raster, np.full((5, 5), 2, dtype=np.uint8))
    _write_test_raster(seasonal_raster, np.full((5, 5), 40, dtype=np.uint8))
    _write_test_raster(dem_raster, np.arange(25, dtype=np.float32).reshape(5, 5))

    permanent_outputs = generate_permanent_water_masks(corridors, permanent_raster, tmp_path / "permanent_out")
    seasonal_outputs = generate_seasonal_water_masks(corridors, seasonal_raster, tmp_path / "seasonal_out")
    terrain_outputs = derive_terrain_layers(corridors, dem_raster, tmp_path / "terrain_out")

    assert permanent_outputs["indus-1"].exists()
    assert seasonal_outputs["indus-1"].exists()
    assert terrain_outputs["indus-1"]["slope"].exists()


def test_exposure_baseline_preparation(tmp_path: Path) -> None:
    corridors = gpd.GeoDataFrame(
        [{"corridor_id": "indus-1", "name": "Indus Reach", "geometry": Polygon([(0, 0), (0, 2), (2, 2), (2, 0)])}],
        crs="EPSG:4326",
    )

    roads = gpd.GeoDataFrame(
        [{"road_id": "r1", "geometry": LineString([(0.5, 0.5), (1.5, 1.5)])}],
        crs="EPSG:4326",
    )
    roads_path = tmp_path / "roads.geojson"
    roads.to_file(roads_path, driver="GeoJSON")

    outputs = prepare_exposure_baseline_layers(corridors, {"roads": roads_path}, tmp_path / "exposure")
    assert outputs["indus-1"]["roads"].exists()
