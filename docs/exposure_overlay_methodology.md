# Exposure Overlay Methodology

## Canonical model
The canonical exposure pathway uses spatial overlays only:
- Flood event polygon ∩ district boundaries for flooded area.
- Flood event polygon ∩ baseline asset layers for exposure metrics.
- No scalar multipliers are used in the canonical path.

## Required baseline layers
- Population polygons or gridded cells with a numeric population field.
- Roads linework.
- Health facility points.
- School points.
- Cropland polygons.

Each layer should provide source URI/path, version, and source timestamp for lineage.

## Metric computation
- **District flooded area**: area of intersection in square kilometers (project-native units in tests).
- **Roads**: summed intersected line length.
- **Health/schools**: point counts intersecting flood polygon.
- **Cropland**: polygon overlap area.
- **Population**: areal-weighted allocation based on intersected cell fraction.

## Lineage and reproducibility
Outputs include:
- processing model and version,
- computation timestamp,
- geometry source (reviewed or provisional machine),
- processing parameters,
- layer metadata (name, type, source URI, version, timestamp, feature count, value field, quality score).

## Uncertainty
Uncertainty is reported as:
- overall uncertainty score,
- component scores (geometry source, cloud limitations, layer quality),
- multiplicative confidence interval bounds,
- per-layer relative uncertainty.

Uncertainty rises when geometry is machine-provisional, cloud-limited, or when layer quality is low.

## Evacuation route constraints and shelter proximity overlays

### Required datasets
- Flood event polygon (reviewed geometry preferred, machine provisional fallback).
- District administrative boundaries.
- Road network baseline (`line` features), with optional `evacuation_priority` boolean flag.
- Shelter baseline (`point` features), optionally configured with a distance threshold (`max_distance_m`).

### Methodology
1. **District flood footprint**: `event_polygon ∩ district_polygon` to derive flooded area by district.
2. **Route constraints**:
   - Intersect flooded district geometry with roads.
   - Compute impacted road length (`exposed_length_km`) and total district road length (`total_length_km`).
   - Derive impacted ratio: `impacted_road_km / total_length_km`.
   - Mark `routing_blocked=true` when any intersected `evacuation_priority` segment is impacted.
3. **Shelter proximity**:
   - Count shelters intersecting flooded geometry (`shelters_in_flood_zone`).
   - Use shelters outside flooded geometry as candidate safe shelters.
   - Compute nearest safe shelter distance from event boundary (`nearest_safe_shelter_m`).
   - Count safe shelters within threshold (`safe_shelters_within_threshold`).

### Output integration
District report rows include:
- `route_constraints`: impacted road km, impact ratio, blocked flag.
- `shelter_proximity`: in-zone shelters, nearest safe distance, threshold, and safe shelter count within threshold.

### Lineage and quality caveats
- Outputs include lineage metadata (`source_uri`, `version`, `source_timestamp`, `quality_score`) for each layer.
- Coordinate distances are computed directly in layer CRS units; meters are accurate only if input data are projected in meter-based CRS.
- Road block inference is geometric (flood overlap) and does not include elevation, embankment condition, culvert state, bridge status, or live closure reports.
- Shelter suitability is inferred only by flood non-intersection and proximity; field validation and operational shelter capacity checks are required.
