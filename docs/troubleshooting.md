# Troubleshooting

## Flood information is unavailable or empty

Check `APP_MODE` and `API_BASE_URL` in the Streamlit process. When a source is
configured, try the canonical API's `/health` and `/public/events` endpoints.
A reachable server can return an empty eligible feed. A timeout or failed
response produces an unavailable message and does not expose fixture events.
Official-source links and preparedness pages remain available without the
event feed. See [API behavior](api.md).

For a local demo disconnected from the API, use `APP_MODE=demo` and unset
`API_BASE_URL`. Start from the repository root so checked-in fixture paths
resolve. See [local setup](setup.md).

## Forecast, dam or provider results are unavailable

Operational forecasts and dam-risk prototype output are disabled. Required
canonical scientific data failures are reported explicitly. Use the
[implementation ledger](engineering/IMPLEMENTATION_STATUS.md) to see which
providers and products are verified. Missing data gives no evidence of local
conditions.

The research pages can query providers independently. Check the selected
source and its error before interpreting a result. NASA POWER and
authenticated Earthdata products have different requirements. See
[configuration](configuration.md).

## A run or review is missing after restart

Use `flood-monitor run-status <run-id>` with the same `DATABASE_URL` used by
the original canonical run. Check the root migration state with
`alembic current`. Event and review views still depend partly on
process-local state, and an abandoned running task requires a recovery
procedure. See [architecture](architecture.md) and [deployment](deployment.md).

## An internal request is rejected

HTTP 401 means the bearer credential is missing or unrecognized. HTTP 403
means the configured role lacks access to that route. HTTP 429 means the
internal request limit was reached. Inspect the `Retry-After` header before
retrying. See [API authorization](api.md#authorization) and
[configuration](configuration.md).
