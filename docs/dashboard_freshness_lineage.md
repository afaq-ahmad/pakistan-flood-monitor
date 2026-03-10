# Dashboard Freshness SLA and Lineage

## Freshness SLA
For production dashboard payloads backed by canonical APIs:

- Target freshness: <= 30 minutes from ingestion run completion to dashboard visibility.
- Hard alert threshold: > 60 minutes stale.

## Source-of-truth lineage
1. Ingestion and scoring run (`/internal/run/{aoi_name}`)
2. Event created in canonical event store
3. Analyst action (`/internal/admin/review-event`)
4. Public outputs (`/public/events/*`, `/public/alerts/latest`)
5. Dashboard consumes public/canonical state

## Lineage fields required in dashboard payloads
- `event_id`
- `run_id`
- `detected_at`
- `published_at`
- `status`
- `source_scenes`

## Monitoring controls
- Track `pipeline.alerts_published` and `product.alerts_confirmed`
- Alert if `ops.queue_backlog` grows while freshness SLA is violated
- Export metrics to Prometheus from `/internal/monitoring/metrics/prometheus`
