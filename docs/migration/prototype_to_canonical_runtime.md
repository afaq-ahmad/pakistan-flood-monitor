# Migration Guide: Prototype Runtime to Canonical Runtime

## Summary

As of **April 30, 2026**, the official runtime entrypoint is:

- `pakistan_flood_monitor.api.main:app`

The prototype entrypoint:

- `app.api.main:app`

is deprecated for runtime integrations and scheduled for removal after **December 31, 2026**.

## What changes for integrators

Use the canonical runtime API for all deployments, smoke tests, and client integrations:

```bash
uvicorn pakistan_flood_monitor.api.main:app --reload
```

Canonical API surfaces:

- Internal API: `/internal/*`
- Public API: `/public/*`

Reference contract:

- `docs/runtime_api_contract.md`

## Migration checklist

1. **Update startup command**
   - Replace `uvicorn app.api.main:app --reload`
   - With `uvicorn pakistan_flood_monitor.api.main:app --reload`
2. **Update test clients and smoke scripts**
   - Prefer imports from `pakistan_flood_monitor.api.main`.
3. **Update deployment manifests and CI jobs**
   - Ensure all service commands target canonical runtime.
4. **Validate auth tokens for internal routes**
   - Configure `FLOOD_MONITOR_ADMIN_TOKEN`
   - Configure `FLOOD_MONITOR_ANALYST_TOKEN`
5. **Run post-migration verification**
   - Health endpoint checks under `/internal/*`
   - Public event/exposure/alert path checks under `/public/*`

## Compatibility and deprecation timeline

- **Current state (2026-04-30):** prototype runtime remains available for prototype/dashboard experimentation.
- **Deprecation period:** now through 2026-12-31.
- **Removal target:** first release after 2026-12-31.

During the deprecation period, importing `app.api.main` emits a `DeprecationWarning`.
