# Monitoring Exporter and Alert Rules

## Metrics exporter
The canonical API exposes Prometheus-format metrics at:

- `GET /internal/monitoring/metrics/prometheus`

Scrape with bearer auth through internal gateway.

## Suggested alerts
```yaml
groups:
  - name: flood-monitor-alerts
    rules:
      - alert: FloodMonitorInternalRateLimitSpike
        expr: increase(http_429_total[5m]) > 20
        for: 10m
      - alert: FloodMonitorQueueBacklogHigh
        expr: ops_queue_backlog > 25
        for: 15m
      - alert: FloodMonitorNoAlertsPublished
        expr: increase(pipeline_alerts_published_total[6h]) == 0
        for: 30m
      - alert: FloodMonitorFalseAlarmSpike
        expr: increase(product_false_alarms_total[24h]) > 10
        for: 30m
```

## Operational response
- Investigate ingestion job health.
- Validate downstream dependencies.
- Trigger reprocess via `/internal/admin/reprocess-scene` if needed.
