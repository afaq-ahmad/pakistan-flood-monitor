# Scientific and Geospatial Credibility Audit (2026-04-30)

Active roles:
- Lead role: Remote Sensing / SAR Lead
- Supporting roles: Hydrology / Flood Risk Lead, GIS Analyst, Geospatial QA Engineer, Data Architect, Exposure & Impact Modeler
- Why these roles are needed: This audit validates whether flood science, hydrology context, geospatial handling, and exposure outputs are credible enough for public-facing decisions.

## Flood Science and Remote Sensing Audit

### What is implemented
- A rule-based detection model exists with weighted features for SAR drop, NDWI, rainfall, GloFAS return period, and floodplain distance in `FloodDetector.rule_based_probability`.
- A breach-risk score exists as a weighted blend of expansion rate and embankment-side-water indicator in `detect_breach_risk`.
- EO catalog abstraction exists with Sentinel-1/2/Landsat/HLS sensor labels and support layers (`imerg`, `glofas`, `copernicus-dem`, `jrc-gsw`).
- Test coverage in `tests/test_sar_preprocessing_pipeline.py` demonstrates substantial prototype processing behavior in the `src/app/services` stack (asset selection, reprojection alignment checks, baseline grouping, optical indices).

### Credibility findings
1. **Canonical runtime detection path is currently synthetic, not scene-derived.**
   - In `pipeline/runner.py`, `DetectionFeatures` are hardcoded per run (`sar_drop_db=3.0`, `ndwi=0.31`, etc.) rather than computed from ingested rasters.
   - Classification: **hardcoded**.
2. **Canonical preprocessing module is a stub.**
   - `core/preprocessing.py` returns static booleans and does not perform real calibration/terrain correction/cloud logic.
   - Classification: **stubbed**.
3. **Optical+SAR fusion exists in concept, but implementation is split/partial.**
   - Canonical runtime path uses a single heuristic score; richer preprocessing/fusion behavior appears in prototype services/tests under `src/app/services`.
   - Classification: **partial** with **duplicate-stack risk**.
4. **Permanent water masking / recession tracking are not operationally integrated in canonical pipeline.**
   - Support layer pointers exist in `DataCatalog.fetch_supporting_layers`, but no canonical flood-mask differencing workflow is wired in `pipeline/runner.py`.
   - Classification: **documented but missing** in canonical runtime.
5. **Uncertainty communication is weakly encoded.**
   - Confidence score exists, but no explicit per-event uncertainty decomposition (SAR layover/shadow, urban effects, temporal gaps) is attached in canonical outputs.
   - Classification: **partial**.

## Hydrology and Breach Suspicion Audit

### What is implemented
- Trigger gating exists in `EventTriggerService.should_process` using rainfall, GloFAS return period, and seasonal anomaly thresholds.
- Hydromet ingestion abstractions exist in prototype services (`src/app/services/hydromet.py`) with rainfall windows, discharge percentile thresholds, and stress score calculation.
- Corridor reach threshold maps exist (`REACH_HYDROLOGY_THRESHOLDS`) with Indus reach variants.

### Credibility findings
1. **Hydrology in canonical runtime is minimally coupled.**
   - Canonical runner uses fixed feature values and does not integrate full `HydrometIngestionJob` pipeline outputs.
   - Classification: **partial**.
2. **Gauge/discharge context is represented as percentile logic but not validated against station/barrage lineage.**
   - `GloFASFetcher` accepts provider output but no explicit station-level provenance or barrage mapping is persisted.
   - Classification: **partial/unclear**.
3. **Breach suspicion logic is simplistic.**
   - `detect_breach_risk` uses only two numeric inputs and lacks explicit embankment geometry intersection checks in canonical path.
   - Classification: **partial**.
4. **Upstream/downstream and barrage operations context are not evident in canonical outputs.**
   - No clear object model in canonical package for gauge chains, barrages, or flow routing context.
   - Classification: **documented but missing**.

## Geospatial Correctness Audit

### What is implemented
- QA gate validates publication geometry type, polygon ring closure, coordinate formatting, EPSG:4326 CRS restriction, and required review metadata in `services/gis_qa.py`.
- Prototype preprocessing tests validate raster alignment consistency and CRS handling in `tests/test_sar_preprocessing_pipeline.py`.

### Credibility findings
1. **Geometry QA exists but is limited.**
   - Only Polygon type is accepted; no MultiPolygon or topology self-intersection checks in canonical gate.
   - Classification: **partial**.
2. **CRS policy is strict but narrow.**
   - Publication gate enforces EPSG:4326 only; no canonical reprojection strategy documentation for analytics-grade outputs.
   - Classification: **partial**.
3. **Raster/vector alignment checks are present in tests, mostly prototype-side.**
   - Strong signs of engineering intent, but canonical runtime integration of those checks is not verified.
   - Classification: **partial/unclear**.
4. **Administrative boundary joins and district overlays appear shallow.**
   - Event records include district overlays as a simple list and fixed geometry in canonical API record generation.
   - Classification: **hardcoded/partial**.
5. **GeoJSON compatibility exists, QGIS/ArcGIS compatibility is not formally validated end-to-end.**
   - Output format resembles GeoJSON, but interoperability test artifacts are not evident.
   - Classification: **partial**.

## Exposure and Impact Audit

### What is implemented
- Exposure estimates are generated by `ExposureAnalyzer.estimate` and propagated into output reports.
- Canonical output includes population, cropland, roads, schools, and hospitals.

### Credibility findings
1. **Exposure model is a scalar multiplier stub.**
   - Exposure uses flood area multiplied by constants, not spatial overlays with population grids/asset layers.
   - Classification: **stubbed**.
2. **No explicit modeling for bridges, livestock, housing, or tehsil summaries in canonical exposure object.**
   - These impact categories are absent from model outputs.
   - Classification: **documented but missing** relative to broad project framing.
3. **No lineage/version tagging for exposure source datasets in canonical report object.**
   - Limits auditability and reproducibility.
   - Classification: **partial**.

## Remote Sensing and Geospatial Improvement Plan

| Recommendation | Responsible Role | Owning Squad | Implementation Sketch | Acceptance Criteria | Dependencies | Effort | Release Relevance |
|---|---|---|---|---|---|---|---|
| Replace synthetic detection features with scene-derived metrics | EO Pipeline Engineer | Flood Detection & Remote Sensing | Compute SAR backscatter deltas and optical indices from preprocessed assets; persist feature snapshots per run | `runner.py` no longer uses fixed literals; feature provenance stored with run/event IDs | Scene ingestion + preprocessing integration | L | Pilot blocker |
| Integrate canonical SAR preprocessing pipeline | Remote Sensing / SAR Lead | Flood Detection & Remote Sensing | Promote tested preprocessing behavior from prototype to canonical module with calibration/terrain/noise metadata | Canonical pipeline outputs polarization rasters + QC stats; regression tests pass | Refactor from `src/app/services/preprocessing.py` | L | Pilot blocker |
| Add permanent water mask and flood recession products | GIS Analyst | Flood Detection & Remote Sensing | Use baseline water layer + temporal differencing to produce expansion/recession layers | Published outputs include new floodwater and recession metrics with versioned masks | Baseline dataset management | M | High |
| Strengthen breach suspicion with embankment geometry context | Hydrology / Flood Risk Lead | Analyst Review & Alerting | Add embankment-side intersection features, protected-side checks, and persistence windows | Breach score includes explainable components; false alarms reduced in validation set | Embankment dataset + spatial joins | M | Pilot blocker |
| Hydromet-gauge provenance and barrage context in event cards | Hydrology / Flood Risk Lead | Partnerships, Validation & Pilot Adoption | Link forecast/discharge context to named reaches/gauges/barrages and add upstream/downstream summaries | Each published event includes hydromet provenance and context annotations | External hydromet connectors | M | High |
| Expand geometry QA to topology and multipolygon support | Geospatial QA Engineer | Reliability, Security & Release | Add self-intersection checks, MultiPolygon handling, area sanity checks, and CRS transformation tests | QA gate blocks invalid topology; integration tests include failure cases | Shapely/GEOS validations | M | High |
| Replace scalar exposure stub with spatial overlays | Exposure & Impact Modeler | Exposure & Impact Intelligence | Intersect flood polygons with population/roads/health/education/agri layers; aggregate by district/tehsil | Exposure outputs match spatial overlay calculations and include uncertainty bounds | Curated baseline layers + admin boundaries | L | Pilot blocker |
| Add dataset/model lineage metadata to every published event | Data Architect | Core Platform & APIs | Attach source scene IDs, processing version, threshold versions, and exposure dataset versions | API responses include lineage block; reproducibility checks pass | Persistence schema update | M | High |
| Publish COG/GeoParquet/GeoJSON contracts with interoperability tests | GIS Analyst | Public Dashboard & Mobile UX | Define export schemas, generate COG rasters + GeoParquet vectors + simplified GeoJSON endpoints | QGIS/ArcGIS smoke tests pass; format validators run in CI | Storage and API export pipeline | M | High |
| Add scientific uncertainty narrative to public alerts | Technical Writer (with SAR Lead) | Public Dashboard & Mobile UX | Standardize uncertainty statements (SAR artifacts, cloud limits for optical corroboration, latency) | Every public alert includes confidence band + uncertainty explanation | Confidence model decomposition | S | Public trust blocker |

