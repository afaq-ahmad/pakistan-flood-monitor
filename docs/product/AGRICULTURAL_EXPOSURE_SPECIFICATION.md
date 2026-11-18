# Agricultural Exposure Analysis — Specification and Prerequisites

Status: **BLOCKED**

Task: PK-007 (depends on DATA-001, GIS-001, PK-006)

This document specifies the prerequisites for property or field-level
agricultural exposure analysis.  None of these prerequisites are currently met.
The feature must remain disabled until they are.

## Purpose

Estimate the intersection of validated flood extent with agricultural areas
(crop fields, orchards, grazing land, stored produce) to support damage
assessment and recovery planning.

This is **NOT**:
- A substitute for official damage assessment by revenue departments
- A basis for compensation claims without field verification
- An operational warning or evacuation instruction
- A farm-level flood prediction

## Prerequisites (All Required Before Implementation)

### 1. Licensed Field Boundaries

- **Status:** BLOCKED
- **Requirement:** Legitimately sourced agricultural field boundaries or
  land-use classification at appropriate resolution.
- **Sources to evaluate:** Pakistan Bureau of Statistics agricultural census
  data, provincial agricultural departments, FAO land-use mapping.
- **Constraints:** Boundaries must be licensed for use, with known provenance,
  resolution, and vintage.  Freely available global cropland masks (e.g.,
  ESA WorldCover) may provide initial approximation but lack field-level
  resolution.
- **Privacy:** Individual farm boundaries must not be published without
  owner consent.

### 2. User Consent and Access Control

- **Status:** BLOCKED (depends on SEC-001, P1-002)
- **Requirement:** Users must explicitly consent to exposure analysis of
  their reported or identified areas.
- **Constraints:**
  - Consent must be informed and recorded
  - Access to exposure results must be controlled
  - Results must not be shared without authorization
  - Farm-level results must not appear in public feeds

### 3. Validated Flood Extent

- **Status:** BLOCKED (depends on DATA-001)
- **Requirement:** Flood extent derived from validated satellite or gauge
  data, with known temporal coverage, spatial resolution, and accuracy.
- **Constraints:**
  - Must distinguish water from non-water with known error rates
  - Must have acquisition time and processing provenance
  - Cloud cover and revisit gaps must be documented
  - Extent must not be fabricated or interpolated without disclosure

### 4. CRS and Projection

- **Status:** BLOCKED (depends on GIS-001)
- **Requirement:** All spatial operations must use documented, appropriate
  coordinate reference systems.
- **Constraints:**
  - EPSG:4326 is NOT suitable for area or distance calculations
  - Must use a projected CRS appropriate for Pakistan (e.g., UTM Zone 42N
    for most regions, with zone selection documented)
  - CRS mismatch between flood extent and field boundaries must be detected
    and corrected
  - Area calculations must use metric units with stated precision

### 5. Spatial and Temporal Alignment

- **Status:** BLOCKED
- **Requirement:** Flood extent and agricultural boundaries must be aligned
  in space and time.
- **Constraints:**
  - Flood extent date must correspond to the crop calendar period
  - Pre-flood and post-flood imagery must be distinguished
  - Seasonal water bodies must be excluded from flood extent
  - Raster-vector alignment (snap, resample) must be documented

### 6. Baseline vs New Inundation

- **Status:** BLOCKED
- **Requirement:** Distinguish permanent or seasonal water from new flooding.
- **Constraints:**
  - Requires a baseline water mask (pre-monsoon or dry-season)
  - Baseline vintage and accuracy must be documented
  - Irrigated fields that normally have standing water must be handled

### 7. Crop Identification and Uncertainty

- **Status:** BLOCKED
- **Requirement:** If crop type is used in exposure estimation, the
  classification method and accuracy must be documented.
- **Constraints:**
  - Remote-sensing crop classification has known error rates
  - Crop stage (planting, growing, harvest) affects loss estimation
  - Mixed pixels and small fields reduce classification accuracy
  - Crop type does not establish loss without ground verification

### 8. Model Uncertainty

- **Status:** BLOCKED
- **Requirement:** Any model-derived exposure estimate must include
  uncertainty quantification.
- **Constraints:**
  - Report confidence intervals or error bounds
  - Document validation methodology and reference data
  - Do not present model estimates as verified loss
  - Do not use model estimates for compensation without field verification

### 9. Estimated Exposure vs Verified Loss

- **Status:** BLOCKED (depends on PK-006)
- **Requirement:** Strictly separate estimated exposure (satellite-derived
  overlap) from reported loss (community report) and verified damage (field
  assessment).
- **Constraints:**
  - Labels must be explicit: "estimated exposure", "reported loss",
    "field-verified damage"
  - Estimated exposure alone cannot establish actual crop loss
  - Community reports require moderation and verification
  - Official damage assessment requires authorized field teams

## Decision Required

Before any implementation:

1. **Source evaluation:** Identify and evaluate specific data sources for
   field boundaries, flood extent, and crop classification.
2. **Accuracy requirements:** Define minimum acceptable accuracy for each
   input and the resulting exposure estimate.
3. **Privacy review:** Conduct privacy impact assessment for farm-level data.
4. **Scientific validation:** Define validation methodology and minimum
   evidence before operational use.
5. **User research:** Validate that the proposed output is useful and
   understandable for the intended users.

## Implementation Order (When Prerequisites Are Met)

1. Implement validated flood extent ingestion (DATA-001)
2. Implement spatial audit and CRS contracts (GIS-001)
3. Obtain licensed agricultural boundaries
4. Implement baseline water masking
5. Implement overlay with documented uncertainty
6. Validate against known flood events with field data
7. Add consent and access controls
8. Enable for authorized users with explicit limitations

## References

- FAO Pakistan flood-impact assessments (methodology documentation)
- AGENTS.md § 4 (GIS and remote-sensing correctness)
- AGENTS.md § 6 (scientific and decision semantics)
- ADR-001 (operational data integrity)
