from __future__ import annotations

import argparse

import geopandas as gpd

from app.services.corridor_assets import derive_corridor_products, export_corridor_products, load_corridors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build corridor AOI derivative products.")
    parser.add_argument("--corridors", required=True, help="Input corridor polygon file (GeoJSON/GPKG/SHP).")
    parser.add_argument("--output-dir", required=True, help="Output directory for GeoParquet products.")
    parser.add_argument("--buffer-meters", type=float, default=1000)
    parser.add_argument("--basins", help="Optional basin polygon layer.")
    parser.add_argument("--districts", help="Optional district polygon layer.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    corridors = load_corridors(args.corridors)
    basins = gpd.read_file(args.basins) if args.basins else None
    districts = gpd.read_file(args.districts) if args.districts else None

    bundle = derive_corridor_products(
        corridors=corridors,
        monitoring_buffer_meters=args.buffer_meters,
        basins=basins,
        districts=districts,
    )
    outputs = export_corridor_products(bundle, args.output_dir)
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
