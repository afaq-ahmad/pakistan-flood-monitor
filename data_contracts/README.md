# Data Contracts

Schema contracts for published flood events, alerts, and review payloads.

## Risk summary contract (`GET /public/risk-summary/{level}`)

- `level`: `tehsil`, `district`, or `province`.
- Supports sorting via `sort_by` (`risk_score`, `exposure_score`, `severity_score`, `confidence_score`, `province`, `district`, `tehsil`, `event_count`) and `order` (`asc` or `desc`).
- Supports filtering via `province`, `district`, `min_risk`, `min_exposure`, `min_severity`, and `min_confidence`.
- Includes only currently reviewed/approved events (`approved` or `published` lifecycle states).

### Success response example

```json
{
  "level": "district",
  "filters": {"province": "Sindh", "district": null, "min_risk": null, "min_exposure": null, "min_severity": null, "min_confidence": null},
  "sort": {"sort_by": "risk_score", "order": "desc"},
  "count": 1,
  "results": [
    {
      "province": "Sindh",
      "district": "Dadu",
      "tehsil": "ALL_TEHSILS",
      "event_count": 2,
      "risk_score": 0.74,
      "exposure_score": 83000.0,
      "severity_score": 11.9,
      "confidence_score": 0.81,
      "latest_event_id": "evt-2026-0007",
      "latest_event_status": "approved",
      "latest_review_status": "analyst_validated"
    }
  ],
  "baseline_dataset_requirements": {
    "district_tehsil_boundaries": "Required (properties: province, district, tehsil).",
    "event_admin_overlay_join": "Required for mapping reviewed/approved events to district/tehsil.",
    "exposure_baseline_layers": "Required for exposure score comparability."
  }
}
```

### Failure response example

```json
{
  "detail": {
    "error": "invalid_sort_by",
    "allowed": ["confidence_score", "district", "event_count", "exposure_score", "province", "risk_score", "severity_score", "tehsil"]
  }
}
```
