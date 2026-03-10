from __future__ import annotations

import argparse
import json

from app.services.baseline_layers import (
    derive_terrain_layers,
    generate_permanent_water_masks,
    generate_seasonal_water_masks,
    prepare_exposure_baseline_layers,
)
from app.services.corridor_assets import load_corridors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build corridor baseline masks and terrain/exposure assets.")
    parser.add_argument("--corridors", required=True)
    parser.add_argument("--jrc-permanent-water", required=True)
    parser.add_argument("--seasonal-water", required=True)
    parser.add_argument("--dem", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--working-resolution", type=float)
    parser.add_argument(
        "--exposure-layers-json",
        help='JSON object like {"roads": "/data/roads.gpkg", "settlements": "/data/settlements.gpkg"}',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    corridors = load_corridors(args.corridors)

    permanent = generate_permanent_water_masks(
        corridors,
        args.jrc_permanent_water,
        output_dir=f"{args.output_dir}/permanent_water",
        working_resolution=args.working_resolution,
    )
    seasonal = generate_seasonal_water_masks(
        corridors,
        args.seasonal_water,
        output_dir=f"{args.output_dir}/seasonal_water",
        working_resolution=args.working_resolution,
    )
    terrain = derive_terrain_layers(
        corridors,
        args.dem,
        output_dir=f"{args.output_dir}/terrain",
        working_resolution=args.working_resolution,
    )

    print(f"Permanent masks built: {len(permanent)}")
    print(f"Seasonal masks built: {len(seasonal)}")
    print(f"Terrain bundles built: {len(terrain)}")

    if args.exposure_layers_json:
        layers = json.loads(args.exposure_layers_json)
        outputs = prepare_exposure_baseline_layers(corridors, layers, output_dir=f"{args.output_dir}/exposure")
        print(f"Exposure bundles built: {len(outputs)}")


if __name__ == "__main__":
    main()
