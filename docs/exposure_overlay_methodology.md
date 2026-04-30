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
