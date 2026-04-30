# Multi-hazard module architecture

## Goal
Preserve flood API behavior while enabling pluggable hazard execution.

## Interface
- `HazardModule` defines `hazard_type` and `run_daily(aoi_name)`.
- `HazardRegistry` owns registration and resolution.
- `FloodMonitoringPipeline` is now a compatibility wrapper that delegates:
  - `run_daily(aoi_name)` -> flood module.
  - `run_hazard_daily(hazard_type, aoi_name)` -> selected module.

## Built-in modules
- `flood`: production implementation (`FloodHazardModule`).
- `landslide`: placeholder hook (`StubHazardModule`).
- `heat`: placeholder hook (`StubHazardModule`).

## Backward compatibility
Existing API routes still construct `FloodMonitoringPipeline` and call `run_daily`.
This keeps existing flood request/response contracts unchanged while supporting future hazard expansion.

## Developer guide: adding a new hazard
1. Implement `HazardModule`.
2. Register your module with `pipeline.register_module(...)` at app startup or composition root.
3. Add tests for registration and `run_hazard_daily` behavior.
4. Add API routes that call `run_hazard_daily("your-hazard", aoi)` while retaining legacy flood routes.
