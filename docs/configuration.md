# Configuration

The Pakistan Flood Monitor uses two main configuration sources: environment variables and YAML threshold definitions.

## 1. Environment Variables

Environment files (`.env.local`, `.env.staging`, `.env.prod`) contain non-secret,
environment-specific toggles. Inject credentials such as `DATABASE_DSN` from the
deployment platform's secret manager; never commit them to these files.

### Example `.env.local`

```env
# Required safety boundary: test | demo | operational
APP_MODE=demo

# NASA Earthdata (Required for HLS/IMERG)
NASA_EARTHDATA_USERNAME=your_username
NASA_BEARER_TOKEN=your_token

# STAC APIs
STAC_ENDPOINT=https://earth-search.aws.element84.com/v1

# FastAPI Internal Security
FLOOD_MONITOR_ADMIN_TOKEN=secret_admin_token
FLOOD_MONITOR_ANALYST_TOKEN=secret_analyst_token
```

Production deployments must use `APP_MODE=operational`. In that mode, unavailable scientific inputs
produce an explicit `UNAVAILABLE` response; the application never substitutes hash/random/stub data.

> **Security Note:** Never commit `.env` files with actual secrets to version control. Use secret managers for production.

## 2. Threshold Configurations (`config/thresholds/`)

The application uses YAML files to configure physical and analytical thresholds. These can be adjusted without changing code.

### `flood_thresholds.yaml`
Configures SAR backscatter drop thresholds, NDWI cutoffs, and rainfall triggers.
Example:
```yaml
sar_backscatter_drop_db: 2.5
ndwi_threshold: 0.1
rainfall_trigger_mm: 50.0
```

### `breach_weights.yaml`
Configures the Evidence Scorecard weights for predicting levee/dam breaches.
Example:
```yaml
sar_anomaly_weight: 0.4
hydromet_context_weight: 0.3
embankment_proximity_weight: 0.2
exposure_significance_weight: 0.1
```
